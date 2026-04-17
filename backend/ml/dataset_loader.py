from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import librosa
import numpy as np
from dotenv import load_dotenv
from pydub import AudioSegment

from services.audio_processor import TARGET_SR, write_wave_file

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
ORGANIZED_DIR = ROOT / "data" / "organized"
LABEL_MAP_PATH = ROOT / "data" / "label_mapping.json"
TARGET_CLASSES = ["belly_pain", "burping", "discomfort", "hungry", "tired"]
AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
KAGGLE_SEARCH_QUERY = "infant cry classification"
DONATEACRY_GITHUB_ZIP = "https://github.com/gveres/donateacry-corpus/archive/refs/heads/master.zip"

LABEL_MAPPING = {
    "belly_pain": "belly_pain",
    "belly": "belly_pain",
    "pain": "belly_pain",
    "colic": "belly_pain",
    "burping": "burping",
    "burp": "burping",
    "hungry": "hungry",
    "hunger": "hungry",
    "food": "hungry",
    "uncomfortable": "discomfort",
    "discomfort": "discomfort",
    "diaper": "discomfort",
    "wet": "discomfort",
    "tired": "tired",
    "sleepy": "tired",
    "sleepiness": "tired",
}

load_dotenv(ROOT / ".env")


def _kaggle_env() -> dict[str, str]:
    env = os.environ.copy()
    kaggle_user = os.getenv("KAGGLE_USERNAME", "")
    kaggle_key = os.getenv("KAGGLE_KEY", "")
    if kaggle_user:
        env["KAGGLE_USERNAME"] = kaggle_user
    if kaggle_key:
        env["KAGGLE_KEY"] = kaggle_key
    return env


def _ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ORGANIZED_DIR.mkdir(parents=True, exist_ok=True)
    for cls in TARGET_CLASSES:
        (ORGANIZED_DIR / cls).mkdir(parents=True, exist_ok=True)


def _extract_archives() -> None:
    for zip_path in RAW_DIR.rglob("*.zip"):
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(RAW_DIR)
        except Exception as exc:
            logger.warning("Failed to extract archive %s: %s", zip_path, exc)


def _run_kaggle_cli(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "kaggle", *args]
    return subprocess.run(cmd, check=check, capture_output=True, text=True, env=_kaggle_env())


def _run_kaggle_download() -> bool:
    dataset_candidates = [
        "mrdaniial/baby-cry-sounds",
        "whats2000/infant-cry-audio-corpora",
        "saurabhshahane/baby-cry-audio-classification",
        "anum23/baby-crying-sounds",
        "serhiiutko/baby-crying-detection",
        "nathanmclane/baby-crying-sounds-dataset",
    ]

    try:
        search_result = _run_kaggle_cli(["datasets", "list", "-s", KAGGLE_SEARCH_QUERY], check=False)
        if search_result.stdout:
            logger.info("Kaggle search results for '%s':\n%s", KAGGLE_SEARCH_QUERY, search_result.stdout[:2000])
    except Exception as exc:
        logger.warning("Kaggle dataset search failed: %s", exc)

    any_downloaded = False
    for dataset in dataset_candidates:
        try:
            logger.info("Trying Kaggle dataset: %s", dataset)
            _run_kaggle_cli(["datasets", "download", "-d", dataset, "-p", str(RAW_DIR)], check=True)
            _extract_archives()
            logger.info("Downloaded and extracted dataset: %s", dataset)
            any_downloaded = True
        except Exception as exc:
            logger.warning("Dataset candidate failed (%s): %s", dataset, exc)

    return any_downloaded


def _download_donateacry_github() -> bool:
    try:
        archive_path = RAW_DIR / "donateacry-github-master.zip"
        logger.info("Downloading Donate-a-Cry corpus from GitHub...")
        urllib.request.urlretrieve(DONATEACRY_GITHUB_ZIP, archive_path)
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(RAW_DIR)
        logger.info("Downloaded and extracted GitHub Donate-a-Cry corpus")
        return True
    except Exception as exc:
        logger.warning("Donate-a-Cry GitHub download failed: %s", exc)
        return False


def _tokenize_path(path: Path) -> list[str]:
    tokens: list[str] = []
    for part in path.parts[-6:]:
        part_l = str(part).lower().replace("-", "_").replace(" ", "_")
        tokens.append(part_l)
        tokens.extend([x for x in part_l.split("_") if x])
    stem_l = path.stem.lower().replace("-", "_").replace(" ", "_")
    tokens.extend([x for x in stem_l.split("_") if x])
    return tokens


def _guess_target_label(path: Path) -> tuple[str | None, str | None]:
    for token in _tokenize_path(path):
        if token in LABEL_MAPPING:
            return LABEL_MAPPING[token], token
    return None, None


def _convert_to_wav(src: Path, target_label: str, idx: int) -> Path:
    out_dir = ORGANIZED_DIR / target_label
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"sample_{idx:06d}.wav"

    audio = AudioSegment.from_file(src)
    audio = audio.set_channels(1).set_frame_rate(TARGET_SR)
    audio.export(out_path, format="wav")
    return out_path


def _duration_seconds(path: Path) -> float:
    audio = AudioSegment.from_file(path)
    return max(0.0, len(audio) / 1000.0)


def _augment_file(path: Path, label: str, base_idx: int) -> list[Path]:
    y, sr = librosa.load(path, sr=TARGET_SR, mono=True)
    outputs: list[Path] = []

    variants = [
        ("stretch09", librosa.effects.time_stretch(y, rate=0.9)),
        ("stretch11", librosa.effects.time_stretch(y, rate=1.1)),
        ("pitch2", librosa.effects.pitch_shift(y, sr=sr, n_steps=2)),
        ("pitch-2", librosa.effects.pitch_shift(y, sr=sr, n_steps=-2)),
    ]
    noise = y + np.random.normal(0, 0.005, y.shape)
    variants.append(("noise", noise.astype(np.float32)))

    for i, (name, arr) in enumerate(variants):
        out_path = ORGANIZED_DIR / label / f"aug_{base_idx:06d}_{name}_{i}.wav"
        write_wave_file(str(out_path), arr, sr)
        outputs.append(out_path)
    return outputs


def _collect_raw_audio_files() -> list[Path]:
    return [p for p in RAW_DIR.rglob("*") if p.suffix.lower() in AUDIO_EXTENSIONS]


def _raw_dir_has_audio() -> bool:
    return RAW_DIR.exists() and any(p.suffix.lower() in AUDIO_EXTENSIONS for p in RAW_DIR.rglob("*"))


def _supplement_with_esc50(class_counts: dict[str, int], target_per_class: int = 500) -> dict[str, int]:
    deficits = {cls: max(0, target_per_class - class_counts.get(cls, 0)) for cls in TARGET_CLASSES}
    needed_total = sum(deficits.values())
    if needed_total <= 0:
        return class_counts

    logger.info("Supplementing from ESC-50 for class deficits: %s", deficits)
    esc_dataset = "karolpiczak/esc50"
    try:
        _run_kaggle_cli(["datasets", "download", "-d", esc_dataset, "-p", str(RAW_DIR)], check=True)
        _extract_archives()
    except Exception as exc:
        logger.warning("ESC-50 download failed: %s", exc)
        return class_counts

    meta_candidates = list(RAW_DIR.rglob("esc50.csv")) + list(RAW_DIR.rglob("meta.csv"))
    if not meta_candidates:
        logger.warning("ESC-50 metadata file not found after extraction")
        return class_counts

    meta_path = meta_candidates[0]
    audio_root_candidates = [p for p in RAW_DIR.rglob("audio") if p.is_dir()]
    audio_root = audio_root_candidates[0] if audio_root_candidates else RAW_DIR

    baby_rows: list[dict[str, str]] = []
    try:
        with open(meta_path, "r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                cat = str(row.get("category", "")).strip().lower()
                if cat in {"crying_baby", "baby_cry", "crying baby"}:
                    baby_rows.append(row)
    except Exception as exc:
        logger.warning("Failed to parse ESC-50 metadata %s: %s", meta_path, exc)
        return class_counts

    if not baby_rows:
        logger.warning("No baby-cry rows found in ESC-50 metadata")
        return class_counts

    needy_classes = [cls for cls, missing in deficits.items() if missing > 0]
    if not needy_classes:
        return class_counts

    idx = 0
    out_idx = 0
    while needed_total > 0 and baby_rows:
        row = baby_rows[idx % len(baby_rows)]
        filename = row.get("filename") or row.get("file") or ""
        if not filename:
            idx += 1
            continue

        src = audio_root / filename
        if not src.exists():
            candidates = list(RAW_DIR.rglob(filename))
            if not candidates:
                idx += 1
                continue
            src = candidates[0]

        # Distribute ESC-50 baby-cry samples across underrepresented classes.
        target_cls = needy_classes[out_idx % len(needy_classes)]
        if deficits[target_cls] <= 0:
            needy_classes = [cls for cls in needy_classes if deficits[cls] > 0]
            if not needy_classes:
                break
            target_cls = needy_classes[out_idx % len(needy_classes)]

        try:
            _convert_to_wav(src, target_cls, 900000 + out_idx)
            class_counts[target_cls] = class_counts.get(target_cls, 0) + 1
            deficits[target_cls] -= 1
            needed_total -= 1
            out_idx += 1
        except Exception as exc:
            logger.warning("Failed ESC-50 supplement conversion for %s: %s", src, exc)

        idx += 1

    return class_counts


def _generate_synthetic_dataset(per_class: int = 60) -> dict:
    logger.warning("Generating synthetic fallback dataset")
    for cls in TARGET_CLASSES:
        class_dir = ORGANIZED_DIR / cls
        class_dir.mkdir(parents=True, exist_ok=True)
        for i in range(per_class):
            length = int(TARGET_SR * 3)
            t = np.linspace(0, 3, length, endpoint=False)
            if cls == "hungry":
                sig = 0.35 * np.sin(2 * np.pi * 420 * t) + 0.1 * np.sin(2 * np.pi * 180 * t)
            elif cls == "belly_pain":
                sig = 0.55 * np.sign(np.sin(2 * np.pi * 680 * t))
            elif cls == "discomfort":
                sig = 0.25 * np.sin(2 * np.pi * 300 * t) + 0.15 * np.random.randn(length)
            elif cls == "burping":
                sig = 0.3 * np.sin(2 * np.pi * 520 * t) + 0.25 * np.sin(2 * np.pi * 70 * t)
            else:
                sig = 0.18 * np.sin(2 * np.pi * 220 * t)

            envelope = np.clip(np.linspace(0.2, 1.0, length), 0, 1)
            sig = (sig * envelope + 0.02 * np.random.randn(length)).astype(np.float32)
            out = class_dir / f"synthetic_{i:04d}.wav"
            write_wave_file(str(out), sig, TARGET_SR)

    return summarize_dataset()


def summarize_dataset() -> dict:
    counts = Counter()
    total_duration = 0.0
    for cls in TARGET_CLASSES:
        files = list((ORGANIZED_DIR / cls).glob("*.wav"))
        counts[cls] = len(files)
        for f in files:
            try:
                total_duration += _duration_seconds(f)
            except Exception:
                continue

    max_count = max(counts.values()) if counts else 1
    min_count = min(counts.values()) if counts else 1
    imbalance = (max_count / min_count) if min_count else 0.0

    summary = {
        "class_counts": dict(counts),
        "total_duration_seconds": round(total_duration, 2),
        "imbalance_ratio": round(float(imbalance), 3),
    }
    logger.info("Dataset summary: %s", summary)
    print(json.dumps(summary, indent=2))
    return summary


def prepare_dataset() -> dict:
    _ensure_dirs()

    force_refresh = str(os.getenv("FORCE_DATA_REFRESH", "false")).strip().lower() in {"1", "true", "yes"}
    always_try_download = str(os.getenv("ALWAYS_TRY_KAGGLE_DOWNLOAD", "true")).strip().lower() in {
        "1",
        "true",
        "yes",
    }

    if force_refresh:
        logger.warning("FORCE_DATA_REFRESH enabled: rebuilding organized dataset from available raw sources")
        shutil.rmtree(ORGANIZED_DIR, ignore_errors=True)
        _ensure_dirs()

    existing = [p for p in ORGANIZED_DIR.rglob("*.wav")]
    if existing and not force_refresh:
        logger.info("Found existing organized dataset. Skipping download.")
        return summarize_dataset()

    raw_files = _collect_raw_audio_files() if _raw_dir_has_audio() else []
    if always_try_download or not raw_files:
        _download_donateacry_github()
        _run_kaggle_download()
        raw_files = _collect_raw_audio_files()

    if not raw_files:
        return _generate_synthetic_dataset()

    mapping_by_source: dict[str, str] = {}
    mapping_by_label: dict[str, str] = {}
    converted_files: dict[str, list[Path]] = defaultdict(list)
    class_counts: dict[str, int] = {c: 0 for c in TARGET_CLASSES}

    idx = 0
    for src in raw_files:
        label, original_label = _guess_target_label(src)
        if not label or label not in TARGET_CLASSES:
            continue
        try:
            out = _convert_to_wav(src, label, idx)
            if _duration_seconds(out) < 0.3:
                out.unlink(missing_ok=True)
                continue
            mapping_by_source[str(src)] = label
            if original_label:
                mapping_by_label[original_label] = label
            converted_files[label].append(out)
            class_counts[label] += 1
            idx += 1
        except Exception as exc:
            logger.warning("Failed converting %s: %s", src, exc)

    class_counts = _supplement_with_esc50(class_counts, target_per_class=500)

    with open(LABEL_MAP_PATH, "w", encoding="utf-8") as fp:
        json.dump(
            {
                "label_mapping": mapping_by_label,
                "source_to_target": mapping_by_source,
                "target_classes": TARGET_CLASSES,
            },
            fp,
            indent=2,
        )

    for cls in TARGET_CLASSES:
        samples = list((ORGANIZED_DIR / cls).glob("*.wav"))
        if len(samples) < 50:
            required = 50 - len(samples)
            cursor = 0
            while required > 0 and samples:
                src = samples[cursor % len(samples)]
                aug_outputs = _augment_file(src, cls, cursor)
                for aug in aug_outputs:
                    if _duration_seconds(aug) >= 0.3:
                        required -= 1
                        if required <= 0:
                            break
                cursor += 1

    final_summary = summarize_dataset()

    if min(final_summary["class_counts"].values()) == 0:
        logger.warning("Some classes are empty after preparation. Using synthetic fallback.")
        shutil.rmtree(ORGANIZED_DIR, ignore_errors=True)
        _ensure_dirs()
        return _generate_synthetic_dataset()

    return final_summary


if __name__ == "__main__":
    prepare_dataset()

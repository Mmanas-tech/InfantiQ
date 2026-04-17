from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from scipy.ndimage import zoom

logger = logging.getLogger(__name__)

TARGET_SR = 16000
TARGET_SECONDS = 3
TARGET_SAMPLES = TARGET_SR * TARGET_SECONDS
SUPPORTED_EXTENSIONS = {"wav", "mp3", "ogg", "m4a", "webm"}


def _candidate_ffmpeg_paths() -> list[tuple[str, str]]:
    ffmpeg_bin = os.getenv("FFMPEG_BINARY")
    ffprobe_bin = os.getenv("FFPROBE_BINARY")
    candidates: list[tuple[str, str]] = []

    if ffmpeg_bin and ffprobe_bin:
        candidates.append((ffmpeg_bin, ffprobe_bin))

    ffmpeg_which = shutil.which("ffmpeg")
    ffprobe_which = shutil.which("ffprobe")
    if ffmpeg_which and ffprobe_which:
        candidates.append((ffmpeg_which, ffprobe_which))

    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        winget_dir = (
            Path(local_app_data)
            / "Microsoft"
            / "WinGet"
            / "Packages"
            / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        )
        if winget_dir.exists():
            ffmpeg_files = list(winget_dir.rglob("ffmpeg.exe"))
            ffprobe_files = list(winget_dir.rglob("ffprobe.exe"))
            if ffmpeg_files and ffprobe_files:
                candidates.append((str(ffmpeg_files[0]), str(ffprobe_files[0])))

    return candidates


def _configure_ffmpeg() -> None:
    for ffmpeg_path, ffprobe_path in _candidate_ffmpeg_paths():
        if not (os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path)):
            continue

        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        current_path = os.getenv("PATH", "")
        if ffmpeg_dir not in current_path:
            os.environ["PATH"] = f"{ffmpeg_dir};{current_path}" if current_path else ffmpeg_dir

        AudioSegment.converter = ffmpeg_path
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
        os.environ["FFPROBE_BINARY"] = ffprobe_path
        logger.info("Configured ffmpeg backend: %s", ffmpeg_path)
        return

    logger.warning("ffmpeg/ffprobe not found. Audio conversion for compressed formats may fail.")


_configure_ffmpeg()


@dataclass
class ProcessedAudio:
    mel_spec: np.ndarray
    feature_vector: np.ndarray
    duration_seconds: float
    converted_path: str


def _normalize_length(signal: np.ndarray) -> np.ndarray:
    if len(signal) < TARGET_SAMPLES:
        signal = np.pad(signal, (0, TARGET_SAMPLES - len(signal)), mode="constant")
    elif len(signal) > TARGET_SAMPLES:
        signal = signal[:TARGET_SAMPLES]
    return signal


def _reduce_background_noise(signal: np.ndarray, sr: int) -> np.ndarray:
    if len(signal) < sr // 2:
        return signal

    stft = librosa.stft(signal, n_fft=1024, hop_length=256)
    magnitude = np.abs(stft)
    phase = np.angle(stft)

    frame_energy = np.mean(magnitude, axis=0)
    if frame_energy.size == 0:
        return signal

    threshold = np.percentile(frame_energy, 20)
    noise_frames = magnitude[:, frame_energy <= threshold]
    if noise_frames.size == 0:
        return signal

    noise_profile = np.mean(noise_frames, axis=1, keepdims=True)
    cleaned_mag = np.maximum(magnitude - (1.15 * noise_profile), 0.0)
    cleaned_stft = cleaned_mag * np.exp(1j * phase)
    denoised = librosa.istft(cleaned_stft, hop_length=256, length=len(signal))

    peak = np.max(np.abs(denoised))
    if peak > 0:
        denoised = denoised / peak * min(peak, 1.0)
    return denoised.astype(np.float32)


def _resize_mel(mel_db: np.ndarray, target_shape: tuple[int, int] = (128, 128)) -> np.ndarray:
    factors = (target_shape[0] / mel_db.shape[0], target_shape[1] / mel_db.shape[1])
    resized = zoom(mel_db, factors, order=1)
    return resized[: target_shape[0], : target_shape[1]]


def convert_to_wav_16k_mono(input_path: str) -> str:
    ext = os.path.splitext(input_path)[1].replace(".", "").lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {ext}")

    try:
        audio = AudioSegment.from_file(input_path)
    except FileNotFoundError as exc:
        raise ValueError(
            "Audio conversion backend is unavailable. Install ffmpeg and ensure it is on PATH."
        ) from exc
    except Exception as exc:
        raise ValueError(f"Could not decode audio file: {exc}") from exc

    audio = audio.set_channels(1).set_frame_rate(TARGET_SR)

    fd, output_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    audio.export(output_path, format="wav")
    return output_path


def extract_features(wav_path: str) -> tuple[np.ndarray, np.ndarray, float]:
    signal, sr = librosa.load(wav_path, sr=TARGET_SR, mono=True)
    duration = len(signal) / sr
    if duration < 0.5:
        raise ValueError("Audio too short. Minimum duration is 0.5 seconds")

    signal = _reduce_background_noise(signal, sr)
    signal = _normalize_length(signal)

    mfcc = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=40)
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    mel = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=128, hop_length=512)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_128 = _resize_mel(mel_db, (128, 128)).astype(np.float32)
    mel_128 = np.expand_dims(mel_128, axis=-1)

    chroma = librosa.feature.chroma_stft(y=signal, sr=sr, n_chroma=12)
    chroma_mean = np.mean(chroma, axis=1)

    spectral_centroid = librosa.feature.spectral_centroid(y=signal, sr=sr)
    spectral_rolloff = librosa.feature.spectral_rolloff(y=signal, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(signal)
    rms = librosa.feature.rms(y=signal)

    spectral_features = np.array(
        [
            np.mean(spectral_centroid),
            np.std(spectral_centroid),
            np.mean(spectral_rolloff),
            np.std(spectral_rolloff),
            np.mean(zcr),
            np.std(zcr),
            np.mean(rms),
            np.std(rms),
        ],
        dtype=np.float32,
    )

    feature_vector = np.concatenate(
        [mfcc_mean, mfcc_std, chroma_mean, spectral_features], axis=0
    ).astype(np.float32)

    return mel_128, feature_vector, float(duration)


def process_audio_file(input_path: str) -> ProcessedAudio:
    converted_path = convert_to_wav_16k_mono(input_path)
    mel_spec, feature_vector, duration = extract_features(converted_path)
    return ProcessedAudio(
        mel_spec=mel_spec,
        feature_vector=feature_vector,
        duration_seconds=duration,
        converted_path=converted_path,
    )


def write_wave_file(path: str, data: np.ndarray, sr: int = TARGET_SR) -> None:
    sf.write(path, data, sr)

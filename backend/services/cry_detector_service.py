from __future__ import annotations

import csv
import logging
import os
import urllib.request
from pathlib import Path

import librosa
import numpy as np
import tensorflow as tf

try:
    import tensorflow_hub as hub
except Exception:  # pragma: no cover
    hub = None

logger = logging.getLogger(__name__)

YAMNET_HANDLE = "https://tfhub.dev/google/yamnet/1"
YAMNET_CLASS_MAP_URL = "https://storage.googleapis.com/audioset/yamnet/yamnet_class_map.csv"


class CryDetectorService:
    _instance: "CryDetectorService | None" = None

    def __new__(cls) -> "CryDetectorService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = None
            cls._instance.baby_class_indices = []
            cls._instance.ready = False
            cls._instance.enable_yamnet = os.getenv("ENABLE_YAMNET_CRY_GATE", "false").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            cls._instance.threshold = float(os.getenv("CRY_GATE_YAMNET_THRESHOLD", "0.12"))
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if not self.enable_yamnet:
            logger.info("YAMNet cry detector disabled; using strict TensorFlow heuristic cry gate")
            return

        if hub is None:
            logger.warning("tensorflow_hub unavailable; falling back to heuristic cry gate")
            return

        try:
            self.model = hub.load(YAMNET_HANDLE)
            self.baby_class_indices = self._load_baby_class_indices()
            self.ready = bool(self.baby_class_indices)
            if self.ready:
                logger.info("YAMNet cry detector initialized with %d baby-cry classes", len(self.baby_class_indices))
            else:
                logger.warning("YAMNet loaded but baby-cry classes could not be identified")
        except Exception as exc:
            self.ready = False
            self.model = None
            logger.warning("YAMNet initialization failed, using fallback heuristic: %s", exc)

    def _load_baby_class_indices(self) -> list[int]:
        cache_dir = Path(__file__).resolve().parents[1] / "data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        class_map_path = cache_dir / "yamnet_class_map.csv"
        if not class_map_path.exists():
            urllib.request.urlretrieve(YAMNET_CLASS_MAP_URL, class_map_path)

        indices: list[int] = []
        with class_map_path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                display_name = (row.get("display_name") or "").strip().lower()
                if "baby cry" in display_name or "infant cry" in display_name:
                    try:
                        indices.append(int(row.get("index", "-1")))
                    except ValueError:
                        continue
        return sorted(set([i for i in indices if i >= 0]))

    def _fallback_gate(self, feature_vector: np.ndarray | None) -> tuple[bool, float]:
        if feature_vector is None or len(feature_vector) < 100:
            return False, 0.0

        vec = tf.convert_to_tensor(feature_vector, dtype=tf.float32)
        mean_centroid = vec[92]
        mean_rolloff = vec[94]
        mean_zcr = vec[96]
        mean_rms = vec[98]

        # Baby cries tend to be energetic, moderately high in spectral centroid,
        # and within a bounded zero-crossing range.
        centroid_score = tf.clip_by_value((mean_centroid - 700.0) / 2600.0, 0.0, 1.0)
        rolloff_score = tf.clip_by_value((mean_rolloff - 1400.0) / 3600.0, 0.0, 1.0)
        zcr_score = 1.0 - tf.clip_by_value(tf.abs(mean_zcr - 0.10) / 0.11, 0.0, 1.0)
        rms_score = tf.clip_by_value((mean_rms - 0.012) / 0.11, 0.0, 1.0)

        score = (0.35 * centroid_score) + (0.25 * rolloff_score) + (0.20 * zcr_score) + (0.20 * rms_score)

        # Hard guards to reduce false positives from music/speech/noise.
        hard_rules = tf.logical_and(
            tf.logical_and(mean_centroid >= 650.0, mean_centroid <= 5400.0),
            tf.logical_and(
                tf.logical_and(mean_zcr >= 0.02, mean_zcr <= 0.30),
                tf.logical_and(mean_rms >= 0.008, mean_rms <= 0.40),
            ),
        )

        is_cry = tf.logical_and(score >= 0.60, hard_rules)
        return bool(is_cry.numpy()), float(score.numpy())

    def detect_baby_cry(self, wav_path: str, feature_vector: np.ndarray | None = None) -> tuple[bool, float]:
        if not self.ready or self.model is None:
            return self._fallback_gate(feature_vector)

        try:
            waveform, _ = librosa.load(wav_path, sr=16000, mono=True)
            waveform = waveform.astype(np.float32)
            scores, _, _ = self.model(waveform)
            scores_np = np.asarray(scores)
            if scores_np.ndim != 2 or scores_np.shape[1] == 0:
                return self._fallback_gate(feature_vector)

            baby_scores = scores_np[:, self.baby_class_indices]
            baby_cry_score = float(np.max(baby_scores))
            return baby_cry_score >= self.threshold, baby_cry_score
        except Exception as exc:
            logger.warning("YAMNet cry detect failed, using fallback heuristic: %s", exc)
            return self._fallback_gate(feature_vector)


cry_detector_service = CryDetectorService()

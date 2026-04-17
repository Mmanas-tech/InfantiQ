from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf

logger = logging.getLogger(__name__)


class ModelService:
    _instance: "ModelService | None" = None

    def __new__(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = None
            cls._instance.classes = ["belly_pain", "burping", "discomfort", "hungry", "tired"]
            cls._instance.metadata = {
                "accuracy": 0.0,
                "total_samples": 0,
                "classes": cls._instance.classes,
                "trained_at": None,
                "epochs_trained": 0,
            }
        return cls._instance

    def load(self, model_path: str, classes_path: str, metadata_path: str) -> bool:
        try:
            if not os.path.exists(model_path):
                logger.warning("Model not trained. POST /api/model/train to train.")
                self.model = None
                return False

            self.model = tf.keras.models.load_model(model_path)
            if os.path.exists(classes_path):
                with open(classes_path, "r", encoding="utf-8") as fp:
                    self.classes = json.load(fp)

            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as fp:
                    self.metadata = json.load(fp)

            logger.info("Model loaded successfully from %s", model_path)
            return True
        except Exception as exc:
            logger.exception("Model loading failed: %s", exc)
            self.model = None
            return False

    def ready(self) -> bool:
        return self.model is not None

    def predict(
        self,
        features_dict: dict[str, np.ndarray] | None = None,
        mel_spec: np.ndarray | None = None,
        feature_vector: np.ndarray | None = None,
    ) -> dict[str, Any]:
        if self.model is None:
            return {"error": "inference_failed"}

        try:
            if features_dict is not None:
                mel_spec = features_dict.get("mel_spec")
                feature_vector = features_dict.get("feature_vector")

            if mel_spec is None or feature_vector is None:
                return {"error": "inference_failed"}

            mel_batch = np.expand_dims(mel_spec, axis=0)
            vec_batch = np.expand_dims(feature_vector, axis=0)

            probs = self.model.predict([mel_batch, vec_batch], verbose=0)[0]
            probs = np.asarray(probs, dtype=np.float32)
            probs = probs / np.sum(probs)

            prob_dict = {
                cls_name: float(probs[i]) for i, cls_name in enumerate(self.classes)
            }
            pred_idx = int(np.argmax(probs))
            prediction = self.classes[pred_idx]
            confidence = float(probs[pred_idx])

            return {
                "prediction": prediction,
                "confidence": confidence,
                "probabilities": prob_dict,
            }
        except Exception as exc:
            logger.exception("Inference failed: %s", exc)
            return {"error": "inference_failed"}


model_service = ModelService()


def model_paths(base_dir: str) -> tuple[str, str, str]:
    models_dir = Path(base_dir) / "models"
    return (
        str(models_dir / "cry_model.h5"),
        str(models_dir / "classes.json"),
        str(models_dir / "metadata.json"),
    )

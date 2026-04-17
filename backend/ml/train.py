from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
from tensorflow.keras import callbacks, layers, models

from ml.dataset_loader import ORGANIZED_DIR, TARGET_CLASSES, prepare_dataset
from services.audio_processor import extract_features

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODELS_DIR / "cry_model.h5"
CLASSES_PATH = MODELS_DIR / "classes.json"
METADATA_PATH = MODELS_DIR / "metadata.json"
CONF_MATRIX_PATH = MODELS_DIR / "confusion_matrix.png"
TRAINING_LOG_PATH = MODELS_DIR / "training_log.csv"


def _load_samples() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    mel_list = []
    vec_list = []
    y_list = []

    class_to_idx = {c: i for i, c in enumerate(TARGET_CLASSES)}
    for cls in TARGET_CLASSES:
        for wav in (ORGANIZED_DIR / cls).glob("*.wav"):
            try:
                mel, vec, _ = extract_features(str(wav))
                mel_list.append(mel)
                vec_list.append(vec)
                y_list.append(class_to_idx[cls])
            except Exception as exc:
                logger.warning("Skipping %s: %s", wav, exc)

    if not mel_list:
        raise RuntimeError("No training samples available after dataset preparation")

    X_mel = np.asarray(mel_list, dtype=np.float32)
    X_vec = np.asarray(vec_list, dtype=np.float32)
    y = np.asarray(y_list, dtype=np.int32)
    return X_mel, X_vec, y, TARGET_CLASSES


def _build_model(vec_dim: int, num_classes: int) -> tf.keras.Model:
    mel_input = layers.Input(shape=(128, 128, 1), name="mel_input")
    x = layers.Conv2D(32, (3, 3), activation="relu", padding="same")(mel_input)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(64, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(128, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.4)(x)

    vec_input = layers.Input(shape=(vec_dim,), name="vec_input")
    y = layers.Dense(256, activation="relu")(vec_input)
    y = layers.BatchNormalization()(y)
    y = layers.Dropout(0.3)(y)
    y = layers.Dense(128, activation="relu")(y)
    y = layers.BatchNormalization()(y)
    y = layers.Dropout(0.3)(y)

    merged = layers.Concatenate()([x, y])
    merged = layers.Dense(128, activation="relu")(merged)
    merged = layers.Dropout(0.4)(merged)
    out = layers.Dense(num_classes, activation="softmax")(merged)

    model = models.Model(inputs=[mel_input, vec_input], outputs=out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def run_training_pipeline() -> dict:
    logging.basicConfig(level=logging.INFO)

    prepare_dataset()
    X_mel, X_vec, y, classes = _load_samples()

    y_onehot = tf.keras.utils.to_categorical(y, num_classes=len(classes))

    X_mel_train, X_mel_temp, X_vec_train, X_vec_temp, y_train, y_temp = train_test_split(
        X_mel, X_vec, y_onehot, test_size=0.30, random_state=42, stratify=y
    )

    y_temp_int = np.argmax(y_temp, axis=1)
    X_mel_val, X_mel_test, X_vec_val, X_vec_test, y_val, y_test = train_test_split(
        X_mel_temp,
        X_vec_temp,
        y_temp,
        test_size=0.50,
        random_state=42,
        stratify=y_temp_int,
    )

    model = _build_model(vec_dim=X_vec.shape[1], num_classes=len(classes))

    cb = [
        callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
        callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-6),
        callbacks.ModelCheckpoint(filepath=str(MODEL_PATH), save_best_only=True, monitor="val_loss"),
        callbacks.CSVLogger(str(TRAINING_LOG_PATH)),
    ]

    history = model.fit(
        [X_mel_train, X_vec_train],
        y_train,
        validation_data=([X_mel_val, X_vec_val], y_val),
        epochs=100,
        batch_size=32,
        callbacks=cb,
        verbose=1,
    )

    model = tf.keras.models.load_model(MODEL_PATH)
    test_loss, test_acc = model.evaluate([X_mel_test, X_vec_test], y_test, verbose=0)

    y_true = np.argmax(y_test, axis=1)
    y_pred = np.argmax(model.predict([X_mel_test, X_vec_test], verbose=0), axis=1)

    report = classification_report(y_true, y_pred, target_names=classes, digits=4)
    logger.info("Classification report:\n%s", report)

    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    fig, ax = plt.subplots(figsize=(7, 6))
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    plt.title("Infant Cry Classification - Confusion Matrix")
    plt.tight_layout()
    plt.savefig(CONF_MATRIX_PATH)
    plt.close(fig)

    with open(CLASSES_PATH, "w", encoding="utf-8") as fp:
        json.dump(classes, fp, indent=2)

    metadata = {
        "accuracy": float(test_acc),
        "trained_at": datetime.utcnow().isoformat(),
        "total_samples": int(len(y)),
        "classes": classes,
        "epochs_trained": int(len(history.history.get("loss", []))),
        "test_loss": float(test_loss),
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as fp:
        json.dump(metadata, fp, indent=2)

    logger.info("Training complete. Metadata: %s", metadata)
    return metadata


if __name__ == "__main__":
    run_training_pipeline()

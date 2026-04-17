from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass

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

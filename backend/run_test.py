import os
import sys
import traceback
sys.path.insert(0, os.getcwd())
try:
    from services.model_service import model_service
    from services.audio_processor import extract_features
    model_service.load()
    file_path = "data/raw/manual_test.wav"
    mel_spec, feature_vector = extract_features(file_path)
    prediction, confidence, probabilities = model_service.predict(mel_spec, feature_vector)
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence:.4f}")
    print("Probabilities:")
    for label, prob in sorted_probs:
        print(f"  {label}: {prob:.4f}")
except Exception as e:
    traceback.print_exc()

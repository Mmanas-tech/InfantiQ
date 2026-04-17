# Infant Cry Intelligence System

End-to-end full-stack system for infant cry classification with audio ingestion, deep learning inference, and web UI visualization.

Current configured labels:
- hunger
- pain
- discomfort
- sleepiness

## 1. System Architecture

### High-level Flow

```text
User (Web UI)
   -> React Frontend (Vite)
      -> FastAPI Backend (/api/analyze)
         -> Audio Processor (convert + feature extraction)
            -> Model Service (TensorFlow inference)
               -> JSON response (prediction + probabilities + recommendation)
         -> Optional MongoDB persistence (analyses / model_runs)
```

### Component Breakdown

1. Frontend (React 18 + Vite)
- Landing page with parallax and animated sections.
- Analyzer page with:
   - microphone recording via MediaRecorder
   - drag-and-drop file upload
   - loading phases animation
   - results card with confidence/probability bars

2. Backend (FastAPI)
- REST endpoints for analysis, health, history, model status, model training.
- Audio validation and conversion pipeline.
- Asynchronous background training job support.
- Optional async MongoDB integration through Motor.

3. ML Pipeline (TensorFlow)
- Dataset preparation + augmentation pipeline.
- Dual-input model:
   - CNN branch for mel spectrogram
   - Dense branch for handcrafted features
- Model metadata + class mapping persisted under `backend/models/`.

4. Storage
- Model artifacts on disk (`backend/models/`).
- Optional MongoDB collections:
   - `analyses`
   - `model_runs`

## 2. Repository Structure

```text
infantiQ/
├── frontend/
│   ├── .env
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       ├── App.jsx
│       └── main.jsx
├── backend/
│   ├── .env
│   ├── main.py
│   ├── requirements.txt
│   ├── routers/
│   │   ├── analyze.py
│   │   └── history.py
│   ├── services/
│   │   ├── audio_processor.py
│   │   ├── db_service.py
│   │   └── model_service.py
│   ├── ml/
│   │   ├── dataset_loader.py
│   │   └── train.py
│   ├── schemas/
│   │   └── analysis.py
│   ├── models/
│   │   ├── cry_model.h5
│   │   ├── classes.json
│   │   ├── metadata.json
│   │   ├── training_log.csv
│   │   └── confusion_matrix.png
│   └── data/
│       ├── raw/
│       └── organized/
└── README.md
```

## 3. Prerequisites

- Python 3.11+ (current workspace is using Python 3.13 virtual environment)
- Node.js 18+
- ffmpeg installed and on PATH (required for robust audio conversion)
- Kaggle account/API credentials for dataset download
- MongoDB (optional; can be disabled via `ENABLE_MONGODB=false`)

## 4. Setup & Run

### 4.1 Environment Files

Frontend `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Backend `backend/.env`:

```env
MONGO_URI=mongodb://localhost:27017/infant_cry_db
ENABLE_MONGODB=false
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_AUDIO_SIZE_MB=10
MODEL_PATH=./models/cry_model.h5
```

### 4.2 Install Dependencies

Backend:

```powershell
cd backend
c:/Users/Admin/OneDrive/Desktop/coding/infantiQ/.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
```

### 4.3 Start Services

Backend:

```powershell
c:/Users/Admin/OneDrive/Desktop/coding/infantiQ/.venv/Scripts/python.exe -m uvicorn --app-dir backend main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

### 4.4 Verify

- Frontend: `http://localhost:5173`
- Backend docs: `http://127.0.0.1:8000/docs`
- Health: `GET http://127.0.0.1:8000/api/health`

## 5. API Endpoints

### `POST /api/analyze`
Accepts `multipart/form-data` with field `audio`.

Supported formats:
- wav
- mp3
- ogg
- m4a
- webm

Behavior:
1. Validates extension and max size.
2. Converts to 16kHz mono wav.
3. Extracts features.
4. Runs model inference.
5. Returns prediction payload.
6. Saves record to DB if enabled.

### `GET /api/history`
Returns latest 20 analysis records (if DB enabled and connected).

### `GET /api/health`
Returns backend liveliness and model load status.

### `GET /api/model/status`
Returns:
- trained flag
- accuracy
- classes
- total samples
- latest model run (if DB enabled)
- training flag

### `POST /api/model/train`
Triggers background training job.

## 6. Schemas

### 6.1 Analyze Response

```json
{
   "prediction": "hunger",
   "confidence": 0.87,
   "probabilities": {
      "hunger": 0.87,
      "pain": 0.06,
      "discomfort": 0.05,
      "sleepiness": 0.02
   },
   "recommendation": "Your baby is likely hungry. Try feeding them now or within the next 10-15 minutes.",
   "analysis_id": "uuid",
   "timestamp": "ISO-8601"
}
```

### 6.2 Error Response

```json
{
   "error": "Invalid audio",
   "detail": "Audio too short. Minimum duration is 0.5 seconds"
}
```

### 6.3 Mongo Collections

`analyses` document shape:

```json
{
   "analysis_id": "uuid",
   "timestamp": "ISODate",
   "prediction": "hunger",
   "confidence": 0.87,
   "probabilities": {},
   "audio_duration_seconds": 3.2,
   "audio_format": "wav",
   "file_size_bytes": 51200,
   "recommendation": "..."
}
```

`model_runs` document shape:

```json
{
   "run_id": "uuid",
   "started_at": "ISODate",
   "completed_at": "ISODate",
   "status": "running|completed|failed",
   "accuracy": 0.91,
   "total_samples": 1200,
   "epochs": 47,
   "error_message": null
}
```

## 7. ML Model

### 7.1 Input Features

For each clip:
1. Resample to 16kHz mono.
2. Normalize length to 3 seconds (48000 samples).
3. Extract:
- MFCCs (40) -> mean + std
- Chroma (12) -> mean
- Spectral centroid/rolloff/zcr/rms -> mean + std
- Mel spectrogram (128x128)

### 7.2 Architecture (Dual Branch)

Branch A (CNN on mel):
- Conv2D(32) + BN + MaxPool
- Conv2D(64) + BN + MaxPool
- Conv2D(128) + BN + MaxPool
- GlobalAveragePooling2D
- Dense(128) + Dropout(0.4)

Branch B (Dense on feature vector):
- Dense(256) + BN + Dropout(0.3)
- Dense(128) + BN + Dropout(0.3)

Merge:
- Concatenate
- Dense(128) + Dropout(0.4)
- Dense(4, softmax)

Training config:
- Optimizer: Adam(1e-3)
- Loss: categorical crossentropy
- Batch size: 32
- Max epochs: 100
- Split: 70/15/15 stratified
- Callbacks: EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, CSVLogger

### 7.3 Persisted Artifacts

- `backend/models/cry_model.h5`
- `backend/models/classes.json`
- `backend/models/metadata.json`
- `backend/models/training_log.csv`
- `backend/models/confusion_matrix.png`

## 8. Dataset Used

### 8.1 Intended Data Sources

Primary Kaggle candidates in pipeline:
- `mrdaniial/baby-cry-sounds`
- `whats2000/infant-cry-audio-corpora`
- `saurabhshahane/baby-cry-audio-classification`
- `anum23/baby-crying-sounds`

Supplement (if class counts are low):
- ESC-50 (`karolpiczak/esc50`) filtered to baby-cry category

### 8.2 Current Effective Dataset in this Workspace

Based on `backend/models/metadata.json`:
- `total_samples = 240`
- 4 classes

This corresponds to the synthetic fallback path in `dataset_loader.py` (60 samples/class), used when Kaggle download is unavailable.

## 9. Source References (Model, Data, Code)

### 9.1 Model Source
- Training script: `backend/ml/train.py`
- Feature extraction: `backend/services/audio_processor.py`
- Inference service: `backend/services/model_service.py`
- Active model artifact: `backend/models/cry_model.h5`

### 9.2 Dataset Source
- Dataset pipeline: `backend/ml/dataset_loader.py`
- Kaggle CLI query: `infant cry classification`
- Candidate Kaggle datasets listed in code (see section 8.1)
- ESC-50 supplement source listed in code: `karolpiczak/esc50`

### 9.3 API and App Source
- FastAPI entrypoint: `backend/main.py`
- Analyze route: `backend/routers/analyze.py`
- History route: `backend/routers/history.py`
- Frontend app shell: `frontend/src/App.jsx`
- Analyzer UI: `frontend/src/pages/Analyzer.jsx`

## 10. Known Operational Notes

1. ffmpeg is required for reliable mp3/m4a/webm decoding through pydub.
2. With `ENABLE_MONGODB=false`, inference works but no DB persistence/history is stored.
3. If Kaggle CLI is missing or credentials fail, synthetic fallback data is generated so training can still complete.
4. TensorFlow on native Windows runs CPU-only for current versions.

## 11. License and Usage

This repository is intended for educational and prototyping purposes. Validate model behavior on real clinical-grade datasets before any real-world healthcare use.

# Infant Cry Intelligence System

Production-grade full-stack system to classify infant cry audio into four categories: hunger, pain, discomfort, sleepiness.

## Project Tree

```text
infantiQ/
├── frontend/
│   ├── .env
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src/
│       ├── api/
│       │   └── analyzeApi.js
│       ├── components/
│       │   ├── FileUploader.jsx
│       │   ├── LoadingScreen.jsx
│       │   ├── MicRecorder.jsx
│       │   ├── ParallaxHero.jsx
│       │   └── ResultCard.jsx
│       ├── hooks/
│       │   ├── useAnalysis.js
│       │   └── useAudioRecorder.js
│       ├── pages/
│       │   ├── Analyzer.jsx
│       │   └── Landing.jsx
│       ├── App.jsx
│       ├── index.css
│       └── main.jsx
├── backend/
│   ├── .env
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── routers/
│   │   ├── analyze.py
│   │   └── history.py
│   ├── schemas/
│   │   └── analysis.py
│   ├── services/
│   │   ├── audio_processor.py
│   │   ├── db_service.py
│   │   └── model_service.py
│   ├── ml/
│   │   ├── dataset_loader.py
│   │   └── train.py
│   ├── models/
│   └── data/
│       ├── raw/
│       └── organized/
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Python 3.11
- Node.js 18+
- MongoDB Atlas account (or local MongoDB)
- Kaggle account
- ffmpeg installed on machine (required by pydub)

## Setup

1. Clone the repo and enter project:
   - `git clone <repo-url>`
   - `cd infantiQ`
2. Set up Kaggle API credentials:
   - Create `~/.kaggle/kaggle.json` with your Kaggle username/key
   - Or set `KAGGLE_USERNAME` and `KAGGLE_KEY` in backend `.env`
3. Create/update environment files:
   - `backend/.env` for backend settings
   - `frontend/.env` for API base URL
4. Install backend dependencies:
   - `cd backend`
   - `python -m venv .venv`
   - Windows: `.venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
5. Install frontend dependencies:
   - `cd ../frontend`
   - `npm install`
6. Start backend:
   - `cd ../backend`
   - `uvicorn main:app --reload --port 8000`
7. Start frontend (new terminal):
   - `cd frontend`
   - `npm run dev`
8. First run auto-trains model (typically 5-10 minutes depending on dataset size/hardware)
9. Open app:
   - `http://localhost:5173`

## API Docs

- Swagger UI: `http://localhost:8000/docs`

## Backend Endpoints

- `POST /api/analyze` : classify uploaded audio
- `GET /api/history` : latest 20 analyses
- `GET /api/health` : health + model load state
- `GET /api/model/status` : model metadata and latest run
- `POST /api/model/train` : trigger background training

## Notes

- If Kaggle download fails, system generates a synthetic fallback dataset to keep the pipeline functional.
- Frontend gracefully handles backend downtime with an offline banner.
- Upload validation is enforced on both frontend and backend.

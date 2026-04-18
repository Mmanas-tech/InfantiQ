# Deployment Guide (Reliable + Fast)

This guide gets InfantiQ live with high reliability and minimal friction.

## Recommended Setup

- Frontend: Cloudflare Pages
- Backend: Render Web Service (Starter plan recommended for always-on)
- Database: keep disabled first (`ENABLE_MONGODB=false`), then enable Atlas when ready

This gives you the fastest path to a stable launch.

## 1) Backend Deploy (Render)

1. Push latest code to GitHub.
2. Open Render dashboard and create a new Web Service from your repo.
3. Set:
- Root Directory: `backend`
- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables (copy from `backend/.env.example`):
- `ENABLE_MONGODB=false`
- `ALLOWED_ORIGINS=https://your-frontend-domain.pages.dev`
- `MAX_AUDIO_SIZE_MB=10`
- `MODEL_PATH=./models/cry_model.h5`
- `GROQ_API_KEY=<your-rotated-key>` (required for AI Insights)
- `GROQ_MODEL=llama-3.3-70b-versatile`
- `CRY_GATE_THRESHOLD=0.60`
- `CRY_GATE_YAMNET_THRESHOLD=0.12`
- `ENABLE_YAMNET_CRY_GATE=false`
5. Deploy and validate:
- `https://<render-backend-domain>/api/health`
- `https://<render-backend-domain>/docs`

## 2) Frontend Deploy (Cloudflare Pages)

1. Open Cloudflare Pages and create a new project from GitHub.
2. Configure:
- Project root: `frontend`
- Build command: `npm run build`
- Build output: `dist`
3. Add environment variable:
- `VITE_API_BASE_URL=https://<render-backend-domain>`
4. Deploy.

## 3) CORS Finalization

After frontend URL is assigned, update backend env:
- `ALLOWED_ORIGINS=https://<your-cloudflare-pages-domain>`

Redeploy backend once.

## 4) Post-Deploy Smoke Tests

1. Open frontend app and run one upload analysis.
2. Run one mic analysis and confirm non-baby playback is rejected.
3. Open AI Insights and ask a question.
4. Open Swagger docs and test:
- `POST /api/analyze`
- `POST /api/insights/ask`
- `GET /api/health`
- `GET /api/timeline`

## 5) Reliability Notes

- Free backend plans can sleep. For production reliability, use always-on starter plan.
- Keep Mongo disabled until baseline stability is confirmed.
- AI Insights is Groq-only. If `GROQ_API_KEY` is missing or invalid, `/api/insights/ask` returns an explicit error.
- Rotate API keys before go-live if any key was ever exposed.
- Do not commit `.env` files.

## 6) Optional Next Upgrade

Once stable, enable MongoDB Atlas and set:
- `ENABLE_MONGODB=true`
- `MONGO_URI=<atlas-uri>`

Then redeploy backend.

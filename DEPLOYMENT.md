# 🚀 BhaktiPurva Backend — Production Deployment Guide

This guide covers deploying the **BhaktiPurva FastAPI Backend** to various cloud platforms with zero-tunnel latency.

---

## 1. Option A: Render (Easiest / Free Tier Available)

1. Push your repository to GitHub.
2. Go to [dashboard.render.com](https://dashboard.render.com/) and click **New +** → **Web Service**.
3. Connect your repository and select root directory `bhaktipurv` (or use the root if deployed as a monorepo).
4. Configure settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4`
5. Under **Environment Variables**, add:
   - `MONGO_URL`: Your MongoDB Atlas URI
   - `REDIS_URL`: Your Redis connection URL (e.g. from [Upstash](https://upstash.com) or Render Redis)
   - `DATABASE_NAME`: `bhaktipurv`
   - `JWT_SECRET_KEY`: A secure 32+ character random secret
   - `JWT_ALGORITHM`: `HS256`
6. Click **Deploy Web Service**. Render provides a secure HTTPS URL (e.g. `https://bhaktipurv-api.onrender.com`).

---

## 2. Option B: Railway (One-Click Docker / Procfile)

1. Go to [railway.app](https://railway.app/) and create a **New Project**.
2. Add a **Redis** service from Railway template.
3. Deploy from GitHub Repo (`bhaktipurv` directory).
4. Railway will automatically detect the `Dockerfile` or `Procfile`.
5. Set environment variables (`MONGO_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, etc.).
6. Generate a public domain under **Settings** → **Networking** → **Generate Domain**.

---

## 3. Option C: VPS / DigitalOcean / Hetzner / AWS EC2 (Docker Compose)

1. SSH into your VPS:
   ```bash
   ssh user@your-server-ip
   ```
2. Clone the repository and navigate to `bhaktipurv`:
   ```bash
   cd bhaktipurv
   ```
3. Copy and customize `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
4. Run with Docker Compose:
   ```bash
   docker compose up -d --build
   ```
5. Set up **Nginx** or **Caddy** with SSL (`certbot`) to reverse proxy to `http://localhost:8000`.

---

## 4. Option D: Google Cloud Run (Serverless Container)

1. Build and push the container to Google Artifact Registry:
   ```bash
   gcloud builds submit --tag gcr.io/<PROJECT_ID>/bhaktipurv-backend
   ```
2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy bhaktipurv-backend \
     --image gcr.io/<PROJECT_ID>/bhaktipurv-backend \
     --platform managed \
     --region asia-south1 \
     --allow-unauthenticated \
     --set-env-vars MONGO_URL="<YOUR_MONGO_URL>",REDIS_URL="<YOUR_REDIS_URL>",DATABASE_NAME="bhaktipurv",JWT_SECRET_KEY="<YOUR_SECRET>"
   ```

---

## Updating Frontend Base URL

Once your backend is deployed and you have the live HTTPS domain (e.g., `https://bhaktipurv-api.onrender.com`):

1. Update `bhaktipurv_admin/.env`:
   ```env
   VITE_API_BASE_URL=https://your-backend-domain.com
   VITE_WS_BASE_URL=wss://your-backend-domain.com
   ```
2. Rebuild and redeploy frontend:
   ```bash
   cd bhaktipurv_admin
   npm run build
   firebase deploy --only hosting
   ```

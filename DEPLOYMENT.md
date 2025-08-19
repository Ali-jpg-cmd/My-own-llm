# Backend Deployment Guide

## Deploy to Railway (Free Tier)

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
```

### 2. Login to Railway
```bash
railway login
```

### 3. Initialize Railway Project
```bash
cd backend
railway init
```

### 4. Deploy
```bash
railway up
```

### 5. Get Your URL
```bash
railway domain
```

### 6. Update Frontend
Once deployed, update the "API Base URL" in your GitHub Pages frontend to your Railway URL.

## Alternative: Deploy to Render

### 1. Create New Web Service
- Go to [render.com](https://render.com)
- Connect your GitHub repo
- Select the `backend` folder
- Set build command: `pip install -r requirements.txt`
- Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2. Environment Variables
Set these in Render:
- `PORT`: 8000
- `DATABASE_URL`: Leave default (SQLite)

## Environment Variables
Create a `.env` file in the backend folder:
```env
DATABASE_URL=sqlite:///./llm_api.db
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
DEBUG=false
LOG_LEVEL=INFO
```

## Notes
- Railway provides a free tier with 500 hours/month
- Render provides a free tier with sleep after inactivity
- Both will auto-restart your service
- Your SQLite database will be persistent on Railway

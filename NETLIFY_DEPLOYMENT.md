# Netlify Deployment Guide for Neuro Assist

## Overview
This guide explains how to deploy the Neuro Assist application to Netlify.

**Architecture:**
- **Frontend**: Deployed on Netlify (static HTML/CSS/JS)
- **Backend**: Deployed separately (Render, Railway, or Heroku)

---

## Step 1: Deploy Frontend to Netlify

### 1.1 Push to GitHub (Already Done ✓)
Your repository is already at: `https://github.com/VikasThangallapally/Neuro-Assist-Application.git`

### 1.2 Connect to Netlify

1. Go to [netlify.com](https://netlify.com)
2. Sign up / Log in with GitHub
3. Click **"New site from Git"**
4. Select **GitHub** and authorize
5. Choose repository: `Neuro-Assist-Application`
6. Configure build settings:
   - **Build command**: Leave empty (static site)
   - **Publish directory**: `frontend`
7. Click **"Deploy site"**

### 1.3 Set Environment Variables in Netlify

1. Go to Site Settings → **Build & Deploy** → **Environment**
2. Add variable:
   ```
   REACT_APP_API_URL = https://your-backend-url.com
   ```
   (You'll get this after deploying the backend in Step 2)

---

## Step 2: Deploy Backend to Render (Recommended for ML Models)

### 2.1 Prepare Backend for Render

1. Install Render CLI or use web dashboard
2. Create a `render.yaml` file:

```yaml
services:
  - type: web
    name: neuro-assist-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.13"
```

### 2.2 Deploy to Render

1. Go to [render.com](https://render.com)
2. Sign up / Log in with GitHub
3. Click **"New +"** → **"Web Service"**
4. Select your GitHub repository
5. Configure:
   - **Name**: `neuro-assist-backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Standard (for ML models)
6. Click **"Create Web Service"**

### 2.3 Get Backend URL

Once deployed, you'll get a URL like: `https://neuro-assist-backend.onrender.com`

Copy this URL and:
1. Go back to Netlify
2. Update the `REACT_APP_API_URL` environment variable
3. Redeploy the frontend

---

## Step 3: Update Frontend API Calls

Your frontend needs to use the backend URL. Check your HTML files for API calls:

Look for fetch calls like:
```javascript
fetch('/api/predict', {...})
```

Update to use the environment variable:
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

fetch(`${API_BASE_URL}/api/predict`, {...})
```

Or simpler approach - update the URLs in your HTML/JS:
```javascript
// Instead of: fetch('/api/predict')
// Use: fetch('https://your-backend-url.com/api/predict')
```

---

## Step 4: Configure CORS in FastAPI

In your `fastapi_app.py`, add CORS support:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-netlify-domain.netlify.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Alternative: Deploy Everything to Render

If you prefer a single deployment:

1. Create `Procfile`:
```
web: uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT
```

2. Configure Render to serve:
   - Static files from `/frontend` directory
   - API routes from FastAPI

---

## Deployment Checklist

- [ ] Push latest code to GitHub
- [ ] Create Netlify account
- [ ] Connect GitHub repository to Netlify
- [ ] Configure build settings (publish: `frontend`)
- [ ] Deploy backend to Render/Railway/Heroku
- [ ] Get backend URL
- [ ] Update `REACT_APP_API_URL` in Netlify environment variables
- [ ] Update CORS settings in FastAPI
- [ ] Test API connection from frontend
- [ ] Deploy frontend
- [ ] Verify both frontend and backend work together

---

## Troubleshooting

### API calls not working
- Check browser console for CORS errors
- Verify `REACT_APP_API_URL` is set correctly
- Ensure backend CORS middleware allows your Netlify domain

### Models not loading
- Check Render/deployment logs
- Ensure models are included in Git
- Verify `models/` directory is in repository

### Frontend not loading
- Check Netlify build logs
- Verify `publish = "frontend"` in `netlify.toml`
- Ensure `frontend/` directory exists

---

## Useful Links
- Netlify Docs: https://docs.netlify.com/
- Render Docs: https://render.com/docs
- FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/

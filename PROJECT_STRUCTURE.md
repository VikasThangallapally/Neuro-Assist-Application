# Project Structure Guide

## Overview
The Neuro Assist project is now organized into two main directories: **Frontend** and **Backend**, for better separation of concerns and easier deployment.

```
neuro-assist-application/
├── frontend/                    # Frontend files (Netlify)
│   ├── index.html
│   ├── neuro_assist.html
│   ├── neuro_assist_enhanced.html
│   ├── neuro_intro.html
│   └── admin.html
│
├── backend/                     # Backend files (Render/Heroku)
│   ├── main.py                  # FastAPI app (renamed from fastapi_app.py)
│   ├── app.py                   # Alternative Flask app
│   ├── requirements.txt          # Python dependencies
│   ├── models/
│   │   ├── models/              # ML models and labels
│   │   │   ├── model.h5
│   │   │   ├── model_selected.h5
│   │   │   ├── labels.json
│   │   │   ├── models_evaluation.json
│   │   │   └── training_results.json
│   │   ├── feature_rf_wrapper.py
│   │   └── eval_results.json
│   ├── utils/                   # Utility modules
│   │   ├── chatbot.py           # Chatbot logic
│   │   ├── brain_tumor_knowledge.py
│   │   ├── medical_knowledge.py
│   │   ├── extract_pipeline.py
│   │   └── __init__.py
│   ├── tests/                   # Test files
│   │   ├── test_imports.py
│   │   ├── test_predict.py
│   │   ├── test_enhanced.py
│   │   ├── test_diagnostics.py
│   │   ├── load_model_check.py
│   │   ├── predict_testing.py
│   │   ├── testing_predictions.json
│   │   └── __init__.py
│   ├── brain tumor/             # Training data
│   │   └── Testing/
│   │       ├── glioma/
│   │       ├── meningioma/
│   │       ├── notumor/
│   │       └── pituitary/
│   ├── outputs/                 # Inference outputs
│   ├── train.py                 # Model training script
│   ├── evaluate_models.py       # Model evaluation
│   ├── start_server_simple.py   # Quick start script
│   ├── Dockerfile               # Docker config
│   ├── docker-compose.yml       # Docker Compose config
│   ├── render.yaml              # Render deployment config
│   ├── Procfile                 # Heroku deployment config
│   ├── run_backend.ps1          # PowerShell startup script
│   ├── run_docker.ps1           # Docker startup script
│   ├── run_local_server.ps1     # Local server startup
│   ├── start_server.bat         # Batch startup script
│   ├── start.sh                 # Bash startup script
│   └── __init__.py
│
├── netlify.toml                 # Netlify config
├── .netlifyignore               # Netlify ignore patterns
├── README.md                    # Main documentation
├── QUICK_DEPLOY.md             # Quick deployment guide
├── NETLIFY_DEPLOYMENT.md       # Detailed deployment guide
├── DEPLOYMENT_READY.md         # Deployment checklist
├── PROJECT_STRUCTURE.md        # This file
└── [other documentation files]
```

---

## Frontend (`/frontend`)

**Purpose**: Static HTML/CSS/JavaScript files served by Netlify  
**Technology**: HTML5, CSS3, Vanilla JavaScript  
**Deployment**: Netlify (automatic from GitHub)  

### Files:
- `index.html` - Main landing page
- `neuro_assist.html` - Main application interface
- `neuro_assist_enhanced.html` - Enhanced version with extra features
- `neuro_intro.html` - Introduction page
- `admin.html` - Admin dashboard

### Deployment:
```bash
# Netlify automatically deploys from /frontend when you push to GitHub
# Build command: (empty - it's static)
# Publish directory: frontend
```

---

## Backend (`/backend`)

**Purpose**: FastAPI server with ML models for inference  
**Technology**: Python 3.13, FastAPI, TensorFlow, Keras  
**Deployment**: Render, Heroku, or Docker  

### Main Modules:

#### `main.py`
- FastAPI application entry point
- Handles image upload and prediction
- Serves static frontend (optional)
- REST API endpoints for predictions
- ChatBot integration

**Run locally:**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### `utils/`
Utility modules for core functionality:
- `brain_tumor_knowledge.py` - Domain knowledge about brain tumors
- `medical_knowledge.py` - Medical terminology and info
- `chatbot.py` - Chatbot response generation
- `extract_pipeline.py` - Image processing pipeline

#### `models/`
Pre-trained ML models:
- `models/model.h5` - Main TensorFlow model
- `models/model_selected.h5` - Selected best model
- `models/labels.json` - Class labels (glioma, meningioma, notumor, pituitary)
- `models/models_evaluation.json` - Model metrics
- `feature_rf_wrapper.py` - Feature extraction wrapper

#### `tests/`
Test and validation scripts:
- `test_imports.py` - Check dependencies
- `test_predict.py` - Test predictions
- `test_enhanced.py` - Enhanced testing
- `load_model_check.py` - Verify model loads
- `predict_testing.py` - Batch predictions

#### Training Data (`brain tumor/Testing/`)
Organized test images by tumor type:
- `glioma/` - ~800 images
- `meningioma/` - ~800 images
- `notumor/` - ~800 images  
- `pituitary/` - ~800 images

#### Outputs (`outputs/`)
Generated predictions stored by request ID:
```
outputs/
├── [uuid-1]/
│   ├── cam.png          # Class activation map
│   └── predict.json     # Prediction results
├── [uuid-2]/
└── ...
```

---

## Configuration Files

### `netlify.toml` (Root)
Netlify build and deployment configuration:
- Frontend publish directory: `frontend`
- API redirect rules
- CORS headers

### `render.yaml` (Backend)
Render.com deployment configuration:
- Python version: 3.13
- Install command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/`

### `Procfile` (Backend)
Heroku deployment configuration:
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

### `Dockerfile` (Backend)
Docker containerization:
- Base: Python 3.13
- Installs dependencies
- Exposes port 8000
- Runs FastAPI server

### `docker-compose.yml` (Backend)
Multi-container setup with Redis (optional caching)

---

## Running Locally

### Prerequisites
```bash
# Python 3.13+
python --version

# Git
git --version
```

### Frontend Only
```bash
# No build needed - just open in browser
open frontend/index.html
# or
start frontend/index.html  # Windows
```

### Full Stack (Frontend + Backend)

#### 1. Backend Setup
```bash
cd backend

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)

# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup (in new terminal)
```bash
# Backend auto-serves frontend on localhost:8000
# Or open frontend/index.html directly
open http://localhost:8000
```

#### 3. Test
- Upload an MRI image
- Should get prediction result

---

## Deployment

### Option 1: Netlify + Render (Recommended)

**Frontend:**
```bash
# Push to GitHub
git push origin main

# Go to netlify.com
# → New site from Git
# → Select repo
# → Publish directory: frontend
# → Deploy
```

**Backend:**
```bash
# render.yaml pre-configured

# Go to render.com
# → New Web Service
# → Select repo
# → Deploy (auto from render.yaml)
```

### Option 2: Docker
```bash
cd backend
docker-compose up
# Access on localhost:8000
```

### Option 3: Heroku
```bash
cd backend
heroku login
heroku create your-app-name
git push heroku main
```

---

## File Organization Best Practices

### Adding New Features

**New Frontend Feature:**
1. Create `frontend/new-feature.html`
2. Update `main.py` routes if needed
3. Push to GitHub → Auto-deploys

**New Backend Utility:**
1. Add to `backend/utils/new_utility.py`
2. Import in `backend/main.py`
3. Update `requirements.txt` if new dependencies
4. Push to GitHub → Auto-redeploys

**New ML Model:**
1. Save as `backend/models/models/new_model.h5`
2. Update `backend/models/models/labels.json`
3. Test with `backend/tests/test_predict.py`
4. Push to GitHub

---

## Environment Variables

### Frontend (Netlify)
```
REACT_APP_API_URL = https://your-backend.onrender.com
```

### Backend (Render/Heroku)
```
PYTHON_VERSION = 3.13
FRONTEND_URL = https://your-site.netlify.app
OPENAI_API_KEY = sk-...  (optional, for ChatGPT)
```

---

## Key Imports

### In Backend (main.py)
```python
from utils.chatbot import ...           # Chatbot functions
from utils.brain_tumor_knowledge import ...
from utils.medical_knowledge import ...
from utils.extract_pipeline import ...
```

### Model Paths
```python
# Models are in: backend/models/models/
models/models/model.h5
models/models/labels.json
models/models/model_selected.h5
```

---

## Troubleshooting

### Issue: Import Errors
**Solution**: Ensure you're in the right directory
```bash
cd backend
python -m uvicorn main:app --reload
```

### Issue: Model Not Found
**Check paths:**
```bash
backend/models/models/model.h5          # Should exist
backend/models/models/labels.json       # Should exist
```

### Issue: CORS Errors in Frontend
**Check Netlify environment:**
```
REACT_APP_API_URL = https://correct-backend-url.onrender.com
```

---

## Next Steps

1. ✅ Structure is organized
2. → Test locally with `cd backend && uvicorn main:app --reload`
3. → Deploy frontend to Netlify
4. → Deploy backend to Render
5. → Update environment variables
6. → Test end-to-end

See [QUICK_DEPLOY.md](../QUICK_DEPLOY.md) for deployment steps!

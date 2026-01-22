# 🚀 Deployment Checklist

## ✅ Pre-Deployment Verification

### Code Structure
- [x] Backend files organized in `/backend` folder
- [x] Frontend files organized in `/frontend` folder
- [x] Python packages have `__init__.py` files
- [x] All imports use correct `from utils.*` structure
- [x] Model paths updated to `models/models/` structure
- [x] Template directory correctly points to `../frontend`

### Configuration Files
- [x] `netlify.toml` - Frontend deployment config
- [x] `render.yaml` - Backend deployment config
- [x] `Procfile` - Heroku deployment backup
- [x] `docker-compose.yml` - Local Docker setup
- [x] `Dockerfile` (root) - Production build
- [x] `backend/Dockerfile` - Backend build
- [x] `backend/.dockerignore` - Optimize Docker build

### Code Changes
- [x] `backend/main.py` - Uses correct imports and paths
- [x] `backend/requirements.txt` - Dependencies listed
- [x] `backend/utils/*.py` - Utility modules properly organized
- [x] FastAPI startup script uses `main:app`
- [x] CORS middleware configured for Netlify domains

### Git Repository
- [x] All changes committed to GitHub
- [x] Remote repository updated
- [x] Commit history clean and descriptive

---

## 📋 Netlify Frontend Deployment

### Prerequisites
- [ ] GitHub account connected to Netlify
- [ ] Netlify account created
- [ ] Repository pushed to GitHub ✅

### Steps
1. **Login to Netlify**
   - Go to https://app.netlify.com
   - Click "New site from Git"

2. **Connect Repository**
   - Select "GitHub" as Git provider
   - Authorize Netlify to access your repository
   - Select `VikasThangallapally/Neuro-Assist-Application`

3. **Configure Build Settings**
   - **Base directory:** (leave empty)
   - **Build command:** (leave empty - static files)
   - **Publish directory:** `frontend`

4. **Environment Variables** (if needed)
   - `REACT_APP_API_URL=https://your-render-backend.onrender.com`

5. **Deploy**
   - Click "Deploy site"
   - Wait for build to complete
   - Your frontend will be live!

### Expected Result
- Frontend accessible at: `https://[your-site-name].netlify.app`
- All HTML files served correctly
- API calls route to backend on Render

---

## 🔧 Render.com Backend Deployment

### Prerequisites
- [ ] Render.com account created
- [ ] GitHub repository connected to Render
- [ ] Backend folder properly configured ✅

### Steps
1. **Login to Render**
   - Go to https://dashboard.render.com
   - Click "New Web Service"

2. **Connect Repository**
   - Select "GitHub" as deployment source
   - Authorize Render to access your GitHub
   - Select `Neuro-Assist-Application` repository

3. **Configure Service**
   - **Name:** `neuro-assist-api` (or your preference)
   - **Environment:** `Docker`
   - **Region:** Choose closest to your users
   - **Branch:** `main`
   - **Dockerfile path:** `Dockerfile`
   - **Build command:** (leave as default for Docker)

4. **Environment Variables**
   - Create `.env` file in backend or set in Render dashboard:
   - `REDIS_URL=redis://...` (optional)
   - `ADMIN_USER=admin`
   - `ADMIN_PASSWORD=your_secure_password`
   - `OPENAI_API_KEY=your_key` (if using)

5. **Deploy**
   - Render will:
     - Clone your repository
     - Build the Docker image
     - Deploy the container
     - Generate a unique URL
   - Wait for deployment to complete

### Expected Result
- Backend API accessible at: `https://neuro-assist-api.onrender.com`
- Health check: `GET /` returns status
- Model endpoints ready: `POST /predict`

---

## 🔌 Backend Deployment (Heroku Alternative)

### Prerequisites
- [ ] Heroku account created
- [ ] Heroku CLI installed
- [ ] GitHub connected to Heroku (optional)

### Steps
1. **Create Heroku App**
   ```bash
   heroku create neuro-assist-api
   heroku stack:set container -a neuro-assist-api
   ```

2. **Deploy**
   ```bash
   git push heroku main
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set ADMIN_PASSWORD=your_password -a neuro-assist-api
   ```

### Expected Result
- Backend live at: `https://neuro-assist-api.herokuapp.com`

---

## 🧪 Verification Tests

### Backend Health Check
```bash
curl https://your-render-backend.onrender.com/
```
Expected: Status 200 with HTML response

### API Prediction Endpoint
```bash
curl -X POST https://your-render-backend.onrender.com/predict \
  -F "file=@test_image.jpg"
```
Expected: JSON response with prediction

### Frontend Connectivity
1. Open frontend URL in browser
2. Upload an MRI image
3. Verify prediction results appear
4. Check browser console for any errors

### Cross-Origin Request Test
```bash
curl -H "Origin: https://your-netlify-site.netlify.app" \
  https://your-render-backend.onrender.com/
```
Expected: CORS headers present in response

---

## 🔐 Security Checklist

- [ ] Remove sensitive data from `.env` (only in local)
- [ ] Set strong passwords in Render environment variables
- [ ] Enable HTTPS (automatic on Netlify and Render)
- [ ] Configure CORS to only allow your frontend domain
- [ ] Remove debug mode in production
- [ ] Keep dependencies updated
- [ ] Review `.gitignore` to exclude sensitive files

---

## 📊 Monitoring & Maintenance

### Netlify
- Monitor build logs: Dashboard → Deploys
- Check function logs (if using serverless)
- View traffic analytics: Analytics tab

### Render
- Monitor service logs: Logs tab
- Check metrics: Metrics tab
- Set up alerts for errors

### GitHub
- Monitor Actions for CI/CD status
- Review pull requests before merge
- Maintain clean commit history

---

## 🆘 Troubleshooting

### Docker Build Fails
**Error:** `/requirements.txt not found`
**Solution:** ✅ Fixed - Dockerfiles now reference `backend/requirements.txt`

### Frontend API Calls Fail
**Error:** CORS error or 404
**Solution:** 
- Verify `REACT_APP_API_URL` environment variable
- Check backend health endpoint
- Ensure CORS headers in FastAPI response

### Model Loading Fails
**Error:** Model file not found
**Solution:**
- Verify `models/models/` folder exists
- Check model paths in `backend/main.py`
- Ensure model files are in Git LFS or .gitignore'd

### Deployment Takes Too Long
**Solution:**
- Docker builds can take 5-10 minutes initially
- Subsequent builds use cache (faster)
- Monitor deployment logs for issues

---

## 📝 Post-Deployment

### Update Documentation
- [ ] Add deployed URLs to README.md
- [ ] Document API endpoints
- [ ] Create user guide for uploading images

### Setup Monitoring
- [ ] Enable error tracking (Sentry, etc.)
- [ ] Setup application monitoring
- [ ] Configure alerts for downtime

### Share with Users
- [ ] Deploy URL
- [ ] Usage instructions
- [ ] Image upload guidelines
- [ ] Interpretation tips

---

## 📞 Support Contacts

- **Netlify Support:** https://app.netlify.com/support
- **Render Support:** https://support.render.com
- **GitHub Support:** https://support.github.com

---

**Status:** ✅ **Ready for Deployment**

All configuration is complete. You can now proceed with deploying to Netlify (frontend) and Render.com (backend).


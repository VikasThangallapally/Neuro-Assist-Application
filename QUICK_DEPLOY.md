# 🚀 Deploy Neuro Assist to Netlify - Quick Start

## What's Included
✅ Frontend ready for Netlify  
✅ Backend ready for Render/Heroku  
✅ CORS configured  
✅ Configuration files created  

---

## **⚡ Quick Deployment (5-10 minutes)**

### **Step 1: Deploy Frontend to Netlify**

```bash
# Your code is already on GitHub - nothing to do here locally

# Go to netlify.com → Sign in with GitHub
# 1. Click "New site from Git"
# 2. Select "GitHub" → Authorize
# 3. Choose "Neuro-Assist-Application"
# 4. Set Build Settings:
#    - Build command: (leave empty - it's static)
#    - Publish directory: frontend
# 5. Click "Deploy site"
# 6. Wait for deployment... you'll get a URL like:
#    https://xxx.netlify.app
```

⏳ **Time: 2-3 minutes**

---

### **Step 2: Deploy Backend to Render (Recommended)**

```bash
# Go to render.com → Sign in with GitHub
# 1. Click "New +" → "Web Service"
# 2. Select "Neuro-Assist-Application"
# 3. Click "Connect"
# 4. Configure (pre-filled from render.yaml):
#    Name: neuro-assist-backend
#    Environment: Python
#    Build Command: (auto-filled)
#    Start Command: (auto-filled)
# 5. Select "Standard" plan
# 6. Click "Create Web Service"
# 7. Wait for deployment... you'll get a URL like:
#    https://neuro-assist-backend.onrender.com
```

⏳ **Time: 3-5 minutes**

---

### **Step 3: Connect Frontend ↔️ Backend**

1. **Copy your Render backend URL** (from Step 2)
   - Example: `https://neuro-assist-backend.onrender.com`

2. **Go back to Netlify** → Site settings → Build & Deploy → Environment
   - Add new variable:
     ```
     REACT_APP_API_URL = https://neuro-assist-backend.onrender.com
     ```

3. **Trigger redeploy**:
   - Netlify → Deploys → Trigger deploy → Deploy site
   - Wait for completion

⏳ **Time: 1-2 minutes**

---

## **✅ Testing**

1. Open your Netlify site in browser
2. Upload a brain MRI image
3. Should see prediction result
4. If not working, check browser console for errors

---

## **Alternative: Deploy Backend to Heroku (Free Credit)**

If Render is down or you prefer Heroku:

```bash
# 1. Go to heroku.com → Sign up (need credit card for dyno)
# 2. Create new app
# 3. Connect GitHub repository
# 4. Enable auto-deploys from main branch
# 5. Your Heroku app URL: https://your-app-name.herokuapp.com
# 6. Add to Netlify environment as REACT_APP_API_URL
```

---

## **⚠️ Important Notes**

### **Cold Start on Free Tier**
- Render free tier spins down after 15 minutes of inactivity
- First request may take 30-60 seconds
- For production, use paid plan

### **Environment Variables**
- Netlify frontend needs: `REACT_APP_API_URL`
- Render backend can auto-fill from `render.yaml`

### **CORS Configuration**
- ✅ Already added in `fastapi_app.py`
- ✅ Allows all `.netlify.app` domains
- ✅ Add custom domain if needed in code

---

## **📊 Deployment Architecture**

```
User Browser
    ↓
Netlify (Frontend)
    ↓ (HTTPS Requests)
Render (Backend + ML Models)
    ↓
TensorFlow Models
```

---

## **🔧 Troubleshooting**

### Problem: "CORS Error" in browser console
**Solution:**
- Verify `REACT_APP_API_URL` is set in Netlify
- Ensure it's the correct Render backend URL
- Wait 2-3 minutes for Netlify redeploy to finish

### Problem: "404 Not Found" when uploading
**Solution:**
- Check if Render backend is running (should say "Live" on render.com)
- If spinning down, wait 30-60 seconds for cold start

### Problem: Frontend doesn't update
**Solution:**
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
- Clear browser cache
- Check Netlify deploy logs

---

## **📱 Next Steps**

1. ✅ Deploy to Netlify
2. ✅ Deploy to Render
3. ✅ Connect them
4. ✅ Test in browser
5. 🎉 Share with others!

---

## **📚 Full Documentation**
See `NETLIFY_DEPLOYMENT.md` for detailed guide with screenshots and advanced options.

---

## **Need Help?**
- Netlify Status: https://www.netlify.com/status/
- Render Status: https://status.render.com/
- FastAPI Docs: https://fastapi.tiangolo.com/

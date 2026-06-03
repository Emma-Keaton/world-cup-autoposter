# 🚀 FREE DEPLOYMENT GUIDE

**Deploy your World Cup Autoposter for FREE and access from phone + laptop**

---

## 🎯 Complete Installation & Deployment

### Step 1: Install Backend

```bash
cd E:\Projects\world-cup-autoposter
pip install -e .
```

✅ Expected: "Successfully installed world-cup-autoposter"

### Step 2: Install Frontend

```bash
cd E:\Projects\world-cup-autoposter\frontend
npm install
npm run build
```

✅ Expected: "✓ built in X.XXs"

### Step 3: Test Locally

**Start Backend:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Frontend (dev mode):**
```bash
cd frontend
npm run dev
```

**Test Endpoints:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

**Verify:**
```bash
curl http://localhost:8000/api/system/features
# Should show: 100% - 11/11 features
```

---

## 🌐 FREE DEPLOYMENT OPTIONS

### Option 1: Render.com (RECOMMENDED - Easiest)

**Why Render:**
- ✅ FREE tier: 750 hours/month (enough for 24/7)
- ✅ Auto-deploy from GitHub
- ✅ PostgreSQL database included
- ✅ No credit card required
- ✅ HTTPS automatically

#### Steps:

1. **Prepare Repository**
   ```bash
   # Create .gitignore if not exists
   echo ".env
   *.db
   __pycache__/
   node_modules/
   frontend/dist/
   *.pyc" > .gitignore

   # Commit to GitHub
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPO
   git push -u origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub (recommended) or email
   - No credit card needed

3. **Create Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     ```
     Name: world-cup-autoposter
     Region: Choose closest to you
     Branch: main
     Root Directory: (leave blank)
     Runtime: Python 3
     Build Command: pip install -e . && cd frontend && npm install && npm run build
     Start Command: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

4. **Environment Variables**
   Add these in Render dashboard → Environment:
   ```
   NVIDIA_API_KEY=nvapi-your-key-here
   APP_ENV=production
   DEBUG=false
   DATABASE_URL=sqlite+aiosqlite:///./world_cup_autoposter.db
   PORT=10000
   ```

5. **Database Setup**
   - For SQLite (FREE, simple): Use default config above
   - For PostgreSQL (better): 
     - Click "New +" → "PostgreSQL"
     - Create free database
     - Copy connection string to `DATABASE_URL`

6. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for first deploy
   - Your URL: `https://world-cup-autoposter-xxxx.onrender.com`

**⚠️ Render Free Tier Notes:**
- Web service spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds to wake up
- To keep alive 24/7: Use uptime monitoring (below)

---

### Option 2: Railway.app

**Why Railway:**
- ✅ FREE $5/month credit (enough for small app)
- ✅ Better performance than Render
- ✅ One-click deploy

#### Steps:

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway auto-detects Python + Node
6. Add environment variables (same as Render)
7. Deploy!

**URL:** `https://your-app.up.railway.app`

---

### Option 3: Vercel (Frontend) + Render (Backend)

**Why Vercel:**
- ✅ Best for React/Vite frontends
- ✅ Faster load times
- ✅ Unlimited bandwidth on free tier

#### Deploy Frontend on Vercel:

1. Go to https://vercel.com
2. Import GitHub repository
3. Framework Preset: Vite
4. Root Directory: `frontend`
5. Build Command: `npm run build`
6. Output Directory: `dist`
7. Add environment variable: `VITE_API_URL=https://your-backend.onrender.com`
8. Deploy

#### Update Frontend API URL:
In `frontend/src/lib/api.ts`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
```

---

## 📱 Access from Phone & Laptop

### After Deployment:

1. **Get Your URL**
   - Render: `https://world-cup-autoposter-xxxx.onrender.com`
   - Railway: `https://your-app.up.railway.app`

2. **Open on Any Device**
   - Phone: Open browser → your URL
   - Laptop: Open browser → your URL
   - Tablet: Same URL

3. **Bookmark**
   - Add to phone home screen
   - Bookmark in laptop browser

4. **Configure API Keys**
   - Go to `/settings` page
   - Add NVIDIA API key
   - Add WhatsApp number (optional)
   - Save

5. **Keep Alive (Optional)**
   Use free uptime monitoring:
   - https://uptimerobot.com
   - Ping your URL every 5 minutes
   - Prevents Render spin-down

---

## 🔧 Post-Deployment Setup

### 1. Set NVIDIA API Key
```bash
# Via settings page (recommended)
Open: https://your-app.com/settings
Add NVIDIA API key
Save

# Or via environment variable (Render dashboard)
NVIDIA_API_KEY=nvapi-your-key
```

### 2. Test WhatsApp (Optional)
```bash
curl -X POST https://your-app.com/api/notifications/test/whatsapp
```

### 3. Create First Content
```bash
curl -X POST https://your-app.com/api/content/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "World Cup highlights"}'
```

### 4. Monitor Logs
- Render: Dashboard → Logs
- Railway: Dashboard → Logs
- Check for errors

---

## 💰 Cost Breakdown

| Service | Free Tier | What You Get |
|---------|-----------|--------------|
| **Render** | 750 hrs/month | Web service + PostgreSQL (500MB) |
| **Railway** | $5 credit | ~500 hours of usage |
| **Vercel** | Unlimited | Frontend hosting + CDN |
| **UptimeRobot** | Free | 50 monitors, 5-min checks |

**Total Monthly Cost: $0** 🎉

---

## 🐛 Troubleshooting

### "App won't start"
Check logs in Render/Railway dashboard:
```bash
# Common issues:
- Missing NVIDIA_API_KEY → Add in environment
- Database error → Check DATABASE_URL
- Port error → Use $PORT environment variable
```

### "Frontend can't connect to backend"
Set API URL in frontend:
```typescript
// frontend/src/lib/api.ts
const API_BASE_URL = 'https://your-backend.onrender.com'
```

Re-deploy frontend after change.

### "Database errors"
For Render PostgreSQL:
1. Create new PostgreSQL database
2. Copy connection string
3. Update `DATABASE_URL` environment variable
4. Redeploy

### "502 Bad Gateway"
- App is still starting (wait 2-3 minutes)
- Check logs for startup errors
- Verify start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### "Settings page shows 0 settings"
Initialize database manually:
```python
# In Render/Railway shell
python -c "
import asyncio
from app.core.database import init_db
from app.core.settings_service import get_settings_service

async def setup():
    await init_db()
    service = get_settings_service()
    await service.initialize()
    print('✅ Initialized')

asyncio.run(setup())
"
```

---

## ✅ Final Checklist

- [ ] Backend deployed and responding
- [ ] Frontend deployed and accessible
- [ ] NVIDIA API key configured
- [ ] Database initialized
- [ ] Can access from phone
- [ ] Can access from laptop
- [ ] Settings page working
- [ ] Can generate content
- [ ] WhatsApp notifications tested (optional)

---

## 🎉 Success!

Your World Cup Autoposter is now:
- ✅ Running in the cloud (FREE)
- ✅ Accessible from any device
- ✅ Auto-deploying on git push
- ✅ 100% feature complete

**Next Steps:**
1. Add competitors to monitor
2. Generate your first content
3. Configure auto-posting (optional)
4. Set up WhatsApp alerts

**Your deployed URL:** `https://your-app.onrender.com`

---

**Need Help?**
- Check logs in Render/Railway dashboard
- Review API docs: `https://your-app.com/docs`
- Test endpoints: `https://your-app.com/api/health`
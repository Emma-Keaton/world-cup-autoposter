# 🚀 DEPLOYMENT GUIDE

**Deploy your World Cup Autoposter and persist data across deployments**

---

## 🎯 Quick Start

### For Production Deployment (Render with PostgreSQL):

1. **Add PostgreSQL dependency** (already included):
   ```bash
   pip install asyncpg  # PostgreSQL support
   ```

2. **Create Render PostgreSQL Database**:
   - Go to Render Dashboard → New → PostgreSQL
   - Choose free tier (500MB)
   - Note the connection string

3. **Set Environment Variables** in Render:
   ```
   NVIDIA_API_KEY=nvapi-your-key-here
   APP_ENV=production
   DEBUG=false
   DATABASE_URL=postgresql://user:pass@host:5432/dbname  # From Render PostgreSQL
   ```

4. **Update Build/Start Commands**:
   ```
   Build: pip install -e . && cd frontend && npm install && npm run build
   Start: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   Pre-Deploy: python scripts/init_database.py
   ```

5. **Deploy** - Your data will now persist forever! ✅

---

## 📋 Complete Installation & Deployment

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

## 🌐 DEPLOYMENT TO RENDER (Recommended)

### Why PostgreSQL over SQLite?

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| **Persistence** | ❌ Lost on redeploy | ✅ Permanent |
| **Backups** | ❌ Manual | ✅ Automatic |
| **Performance** | OK for dev | ✅ Production-ready |
| **Scalability** | Limited | ✅ Unlimited |
| **Cost** | Free | Free tier (500MB) |

**Recommendation:** Use PostgreSQL for production (your data persists forever).

---

### Step-by-Step: Render + PostgreSQL

#### 1. Prepare Repository
```bash
# Ensure .gitignore exists
echo ".env
*.db
__pycache__/
node_modules/
frontend/dist/
*.pyc" > .gitignore

# Commit to GitHub
git add .
git commit -m "Ready for deployment"
git push
```

#### 2. Create Render Account
- Go to https://render.com
- Sign up with GitHub (recommended)
- No credit card needed

#### 3. Create PostgreSQL Database
1. Click "New +" → "PostgreSQL"
2. Choose database name: `world-cup-autoposter-db`
3. Choose region (closest to you)
4. Click "Create database"
5. **Copy the Internal Database URL** (looks like):
   ```
   postgresql://user:password@host.amazonaws.com:5432/dbname
   ```

#### 4. Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:

```yaml
Name: world-cup-autoposter
Region: Choose closest to you
Branch: main
Root Directory: (leave blank)
Runtime: Python 3
Build Command: pip install -e . && cd frontend && npm install && npm run build
Start Command: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Note:** Database initializes automatically on startup - no pre-deploy command needed!

#### 5. Environment Variables
Add these in Render dashboard → Environment:

```
# Required
NVIDIA_API_KEY=nvapi-your-key-here
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # From step 3

# Optional (but recommended)
APP_ENV=production
DEBUG=false
```

#### 6. Deploy
- Click "Create Web Service"
- Wait 5-10 minutes for first deploy
- Your URL: `https://world-cup-autoposter-xxxx.onrender.com`

---

### Step-by-Step: Render + SQLite (Simpler but data may be lost)

If you want to start simple and upgrade later:

#### 1-4. Same as PostgreSQL steps above

#### 5. Environment Variables (SQLite)
```
NVIDIA_API_KEY=nvapi-your-key-here
DATABASE_URL=sqlite+aiosqlite:///./world_cup_autoposter.db
APP_ENV=production
DEBUG=false
```

**⚠️ Warning:** SQLite file may be wiped on redeploy. For permanent data, use PostgreSQL.

---

## 🔄 Migrating from SQLite to PostgreSQL

If you deployed with SQLite and want to migrate:

### 1. Create PostgreSQL Database
Follow step 3 above to create Render PostgreSQL.

### 2. Export SQLite Data (Optional)
```bash
# Install SQLite browser or use Python script
python -c "
import sqlite3
import json

conn = sqlite3.connect('world_cup_autoposter.db')
cursor = conn.cursor()

# Export settings
cursor.execute('SELECT key, value FROM settings')
settings = cursor.fetchall()
print(json.dumps(settings, indent=2))

conn.close()
"
```

### 3. Update DATABASE_URL
In Render dashboard, change `DATABASE_URL` to PostgreSQL connection string.

### 4. Redeploy
Render will auto-redeploy. The `init_database.py` script will create all tables.

### 5. Re-enter Settings
Go to `/settings` page and re-enter your API keys (they'll now persist forever).

---

## 📱 Access from Phone & Laptop

### After Deployment:

1. **Get Your URL**
   - Render: `https://world-cup-autoposter-xxxx.onrender.com`

2. **Open on Any Device**
   - Phone: Open browser → your URL
   - Laptop: Open browser → your URL
   - Tablet: Same URL

3. **Bookmark**
   - Add to phone home screen
   - Bookmark in laptop browser

4. **Configure API Keys**
   - Go to `/settings` page
   - Add NVIDIA API key (if not set via env var)
   - Add other API keys as needed
   - Save

---

## 💰 Cost Breakdown

| Service | Free Tier | What You Get |
|---------|-----------|--------------|
| **Render Web Service** | 750 hrs/month | ~24/7 hosting |
| **Render PostgreSQL** | 500MB | Permanent database |
| **UptimeRobot** | Free | Keep-alive pings |

**Total Monthly Cost: $0** 🎉

**Note:** Render's free tier may require upgrading for heavy usage. PostgreSQL free tier is sufficient for thousands of settings and content briefs.

---

## 🔧 Troubleshooting

### "Database errors on startup"
```bash
# Check DATABASE_URL format:
# SQLite: sqlite+aiosqlite:///./world_cup_autoposter.db
# PostgreSQL: postgresql://user:pass@host:5432/dbname

# Manually initialize:
python scripts/init_database.py
```

### "Data lost after deploy"
You're using SQLite. Migrate to PostgreSQL (see "Migrating from SQLite to PostgreSQL" above).

### "Pre-deploy command failed"
Not using pre-deploy commands (free tier)? No problem! Database initializes automatically on app startup.

If you see database errors:
1. Check DATABASE_URL is correct
2. Ensure PostgreSQL database exists
3. Check logs - initialization happens in first 10 seconds of startup

### "Settings page empty"
Run initialization manually via Render shell:
```bash
python scripts/init_database.py
```

Or in Python shell:
```python
import asyncio
from app.core.database import init_db

asyncio.run(init_db())
```

### "PostgreSQL connection timeout"
- Verify DATABASE_URL is correct (copy from Render PostgreSQL dashboard)
- Ensure web service and database are in same region
- Check Render dashboard for database health

---

## ✅ Post-Deployment Checklist

- [ ] PostgreSQL database created and connected
- [ ] DATABASE_URL environment variable set
- [ ] NVIDIA_API_KEY configured (env var or settings page)
- [ ] Pre-deploy command runs successfully
- [ ] Settings page shows all configuration options
- [ ] Dashboard shows APIs as "Configured"
- [ ] Can access from phone
- [ ] Can access from laptop
- [ ] Data persists after redeploy

---

## 🎉 Success!

Your World Cup Autoposter is now:
- ✅ Running in the cloud
- ✅ Data persists across deployments (PostgreSQL)
- ✅ Accessible from any device
- ✅ Auto-deploying on git push
- ✅ 100% feature complete

**Next Steps:**
1. Add competitors to monitor
2. Generate your first content
3. Configure auto-posting (optional)
4. Set up WhatsApp notifications

**Your deployed URL:** `https://your-app.onrender.com`

---

**Need Help?**
- Check logs in Render dashboard
- Review API docs: `https://your-app.com/docs`
- Test health: `https://your-app.com/api/health/status`
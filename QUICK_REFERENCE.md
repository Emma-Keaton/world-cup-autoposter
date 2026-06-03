# ⚡ Quick Reference Card

## Local Development

```bash
# Terminal 1 - Backend
cd E:\Projects\world-cup-autoposter
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend  
cd E:\Projects\world-cup-autoposter\frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Production Deployment (FREE)

### 1. Push to GitHub
```bash
git add . && git commit -m "Deploy" && git push
```

### 2. Deploy to Render
1. https://render.com → New Web Service
2. Connect GitHub repo
3. Build: `pip install -e . && cd frontend && npm install && npm run build`
4. Start: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars: `NVIDIA_API_KEY`, `DATABASE_URL`
6. Deploy!

**URL:** `https://your-app.onrender.com`

---

## Essential Commands

```bash
# Install
pip install -e .
cd frontend && npm install

# Build frontend
npm run build

# Test
curl http://localhost:8000/api/health
curl http://localhost:8000/api/system/features

# Initialize DB
python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"
```

---

## Key URLs

| Endpoint | Purpose |
|----------|---------|
| `/` | API root |
| `/settings` | Configure API keys |
| `/api/health` | Health check |
| `/api/system/features` | Feature list |
| `/api/ab-testing/tests` | A/B tests |
| `/docs` | API documentation |

---

## Environment Variables

```env
# Required
NVIDIA_API_KEY=nvapi-your-key

# Optional
WHATSAPP_ENABLED=true
WHATSAPP_PHONE_NUMBER=+1234567890
BUFFER_API_KEY=your-buffer-key
API_KEY=your-secret-key
DATABASE_URL=sqlite+aiosqlite:///./world_cup_autoposter.db
```

---

## Free Hosting Options

| Platform | Free Tier | Best For |
|----------|-----------|----------|
| **Render** | 750 hrs/month | Backend + DB |
| **Railway** | $5 credit | Better performance |
| **Vercel** | Unlimited | Frontend only |

**Recommended:** Render (backend) + Vercel (frontend)

---

## Access Anywhere

Once deployed:
1. Open `https://your-app.onrender.com` on any device
2. Configure API keys in Settings
3. Start creating content!

**Phone:** Add to home screen  
**Laptop:** Bookmark in browser  
**Tablet:** Same URL works everywhere

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | Check logs, add NVIDIA_API_KEY |
| Database error | Initialize DB manually |
| Frontend 404 | Run `npm run build` |
| Settings error | Run DB init script |
| Port conflict | Use `--port 8001` |

---

**Full Guide:** See `DEPLOYMENT_GUIDE.md`

**Status:** ✅ 100% Complete - 11/11 Features
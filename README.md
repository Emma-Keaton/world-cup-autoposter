# 🚀 World Cup Autoposter

**Autonomous football content creation system for Instagram Reels and YouTube Shorts**

---

## Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Install FFmpeg
**Windows:** `choco install ffmpeg`  
**Linux:** `sudo apt install ffmpeg`  
**macOS:** `brew install ffmpeg`

### 3. Start Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Open Frontend
```bash
cd frontend && npm install && npm run dev
```

**Access:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## Configuration

### Set API Keys (Via Frontend)
1. Open Dashboard → Settings
2. Add NVIDIA API Key (required)
3. Add other optional keys
4. Click "Save Changes"

### Or Via .env File
```env
NVIDIA_API_KEY=nvapi-your-key
WHATSAPP_ENABLED=false
WHATSAPP_PHONE_NUMBER=+1234567890
API_KEY=your-secret-key
```

---

## Features

✅ AI Content Generation (NVIDIA NIM)  
✅ YouTube Clipper  
✅ Thumbnail Generator  
✅ TTS & Subtitles  
✅ Multi-Agent System  
✅ Publishers (Instagram, YouTube, Buffer)  
✅ React Dashboard  
✅ WhatsApp Notifications (errors + success alerts)  
✅ Rate Limiting  
✅ Content Scheduler  
✅ Analytics  
✅ Auto-Approval  
✅ Batch Processing  
✅ Self-Learning System  

---

## API Examples

```bash
# Health check
curl http://localhost:8000/api/health

# Generate content
curl -X POST http://localhost:8000/api/content/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "World Cup highlights"}'

# Test WhatsApp
curl -X POST http://localhost:8000/api/notifications/test/whatsapp

# System status
curl http://localhost:8000/api/system/services/status
```

---

## WhatsApp Notifications

1. Enable in Settings: `WHATSAPP_ENABLED=true`
2. Add phone: `WHATSAPP_PHONE_NUMBER=+1234567890`
3. First run: Scan QR code in console
4. Test: `curl -X POST http://localhost:8000/api/notifications/test/whatsapp`

You'll receive:
- 🚨 Error alerts
- ✅ Success notifications with post links
- 📊 Daily summaries

---

## Production

### Environment
```env
APP_ENV=production
DEBUG=false
NVIDIA_API_KEY=your-key
API_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/autoposter
ALLOWED_ORIGINS=https://yourdomain.com
```

### Run
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## Troubleshooting

**FFmpeg not found** → Install (see step 2)  
**NVIDIA API 401** → Check key at https://build.nvidia.com  
**WhatsApp not working** → Check phone format (+1234567890)  
**Server won't start** → `pip install -e .` and check `python --version`

---

## 🚀 FREE Deployment (Phone + Laptop Access)

### Quick Deploy to Render.com

**1. Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git push -u origin main
```

**2. Deploy on Render**
1. Go to https://render.com
2. New Web Service → Connect GitHub repo
3. Build: `pip install -e . && cd frontend && npm install && npm run build`
4. Start: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars: `NVIDIA_API_KEY`, `DATABASE_URL`
6. Deploy!

**Your URL:** `https://your-app.onrender.com`

✅ **Access from anywhere:**
- Phone: Open browser → your URL
- Laptop: Open browser → your URL  
- Tablet: Same URL works

📖 **Full Guide:** See `DEPLOYMENT_GUIDE.md`  
⚡ **Quick Ref:** See `QUICK_REFERENCE.md`

---

## Maintenance

**Daily:** Check `/api/health`, review logs  
**Weekly:** Backup database, check API usage  
**Monthly:** Update deps (`pip install -e . --upgrade`)

---

## Project Structure

```
world-cup-autoposter/
├── app/              # Backend (FastAPI)
├── frontend/         # React Dashboard
├── scripts/          # Utilities
├── .env              # Config
└── README.md         # This file
```

---

## Support

- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health
- **System Status**: http://localhost:8000/api/system/services/status

---

**🎉 Ready to create autonomous football content!**
@echo off
echo Starting World Cup Autoposter Server...
cd /d E:\Projects\world-cup-autoposter
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
@echo off
chcp 65001 >nul
cd /d %~dp0
where ffmpeg >nul 2>nul || (echo [!] FFmpeg 가 없습니다. 설치 중... & winget install -e --id Gyan.FFmpeg)
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate
pip install -q -r requirements.txt
streamlit run app.py
pause

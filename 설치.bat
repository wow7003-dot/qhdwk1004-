@echo off
chcp 65001 >nul
echo [1/3] 파이썬 확인
python --version || (echo 파이썬이 없습니다. https://www.python.org/downloads/ 에서 설치(Add to PATH 체크) 후 다시 실행하세요. & pause & exit /b)
echo [2/3] ffmpeg 확인
where ffmpeg >nul 2>&1 || (echo ffmpeg 설치 중... & winget install -e --id Gyan.FFmpeg)
echo [3/3] 라이브러리 설치
python -m pip install -r requirements.txt
echo 설치 완료! 이제 실행.bat 을 더블클릭하세요.
pause

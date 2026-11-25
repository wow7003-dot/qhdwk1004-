#!/usr/bin/env bash
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "FFmpeg 필요: macOS 'brew install ffmpeg' / Ubuntu 'sudo apt install ffmpeg'"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
streamlit run app.py

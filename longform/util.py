"""공용 유틸: HTTP, ffmpeg, 폰트, 로그."""
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("longform")
UA = {"User-Agent": "Mozilla/5.0 (longform-maker)"}


def setup_logging(level=logging.INFO):
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
        log.addHandler(h)
    log.setLevel(level)


def http(method, url, retries=2, timeout=(6, 90), **kw):
    """짧은 재시도가 있는 requests 래퍼. 실패하면 마지막 예외를 던진다."""
    kw.setdefault("headers", UA)
    last = None
    for i in range(retries + 1):
        try:
            r = requests.request(method, url, timeout=timeout, **kw)
            if r.status_code in (429, 502, 503, 504) and i < retries:
                time.sleep(4 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            if i < retries:
                time.sleep(1.5 * (i + 1))
    raise last


def slugify(text, n=36):
    s = re.sub(r"[^\w가-힣]+", "-", text, flags=re.UNICODE).strip("-")
    return (s[:n] or "video")


def short_hash(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:12]


def need_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg 가 설치되어 있지 않습니다. README의 설치 방법을 따라주세요.")


def run(cmd, cwd=None):
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"명령 실패: {' '.join(map(str, cmd[:6]))} ...\n{p.stderr[-1500:]}")
    return p


def duration(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(p.stdout.strip())


FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/AppleGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]
LAST_RESORT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf"


def find_font():
    """한글 폰트 경로. assets/fonts 우선 → OS 폰트 → 자동 다운로드(나눔고딕)."""
    for p in sorted((ROOT / "assets" / "fonts").glob("*.[to]tf")):
        return str(p)
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    dst = ROOT / "assets" / "fonts" / "NanumGothic-Bold.ttf"
    try:
        dst.write_bytes(http("GET", FONT_URL, timeout=(6, 60)).content)
        return str(dst)
    except Exception:  # noqa: BLE001
        log.info("[폰트] 한글 폰트를 찾지 못했습니다(한글이 □로 보일 수 있음). assets/fonts/ 에 .ttf 를 넣어주세요.")
        return LAST_RESORT if os.path.exists(LAST_RESORT) else None


def font_family(path):
    try:
        from PIL import ImageFont
        return ImageFont.truetype(path, 20).getname()[0]
    except Exception:  # noqa: BLE001
        return "Arial"

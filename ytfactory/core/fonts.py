"""한글 폰트 확보: fonts/ 폴더 → 무료 폰트 자동 다운로드(Pretendard, OFL) → 시스템 폰트."""
from pathlib import Path

import requests
from PIL import ImageFont

from .config import FONTS_DIR

DOWNLOADS = {
    "Pretendard-Bold.otf": "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/public/static/Pretendard-Bold.otf",
    "Pretendard-Black.otf": "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/public/static/Pretendard-Black.otf",
}
SYSTEM = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]


def ensure_fonts() -> None:
    FONTS_DIR.mkdir(exist_ok=True)
    for name, url in DOWNLOADS.items():
        p = FONTS_DIR / name
        if p.exists() and p.stat().st_size > 10000:
            continue
        try:
            r = requests.get(url, timeout=60)
            if r.ok and len(r.content) > 10000:
                p.write_bytes(r.content)
        except requests.RequestException:
            pass


def font_path(heavy: bool = False) -> Path | None:
    ensure_fonts()
    order = ["Pretendard-Black.otf", "Pretendard-Bold.otf"] if heavy else ["Pretendard-Bold.otf", "Pretendard-Black.otf"]
    for name in order:
        if (FONTS_DIR / name).exists():
            return FONTS_DIR / name
    for f in sorted(FONTS_DIR.glob("*.[ot]t[fc]")):
        return f
    for f in SYSTEM:
        if Path(f).exists():
            return Path(f)
    return None


def load_font(size: int, heavy: bool = False):
    p = font_path(heavy)
    return ImageFont.truetype(str(p), size) if p else ImageFont.load_default(size)


def family_name(path: Path | None) -> str:
    if not path:
        return "Arial"
    try:
        return ImageFont.truetype(str(path), 20).getname()[0]
    except Exception:
        return "Arial"

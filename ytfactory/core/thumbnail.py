"""유튜브 썸네일: 대표 이미지 + 큰 두 줄 문구(흰/노랑, 두꺼운 테두리)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

from .fonts import load_font


def _fit(draw, text, max_w, start, heavy=True):
    size = start
    while size > 30:
        font = load_font(size, heavy)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 6
    return load_font(size, heavy)


def make_thumbnail(bg: Path, top: str, bottom: str, out: Path, size=(1280, 720)) -> None:
    W, H = size
    img = Image.open(bg).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
    left, upper = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, upper, left + W, upper + H))
    img = ImageEnhance.Contrast(img).enhance(1.15)
    # 아래쪽을 어둡게 해서 글씨가 잘 보이도록
    shade = Image.new("L", (W, H))
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        sd.line([(0, y), (W, y)], fill=int(200 * max(0, (y / H - 0.35)) / 0.65))
    img = Image.composite(Image.new("RGB", (W, H), "black"), img, shade)
    d = ImageDraw.Draw(img)
    max_w = W * 0.92
    if top:
        f = _fit(d, top, max_w, 120)
        d.text((W // 2, int(H * 0.60)), top, font=f, fill="white", anchor="mm",
               stroke_width=10, stroke_fill="black")
    if bottom:
        f = _fit(d, bottom, max_w, 150)
        d.text((W // 2, int(H * 0.82)), bottom, font=f, fill="#FFE400", anchor="mm",
               stroke_width=12, stroke_fill="black")
    img.save(out, "JPEG", quality=95)

"""썸네일(1280x720) 3종: 이미지 보정 + 큰 글씨 + 외곽선. 스타일이 다른 변형을 만들어 A/B 테스트용으로 제공."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from . import images
from .util import find_font, log

W, H = 1280, 720
PALETTES = [((255, 230, 0), (255, 255, 255)), ((255, 255, 255), (255, 70, 70)), ((120, 255, 200), (255, 255, 255))]


def _lines(text):
    lines = [l.strip() for l in text.replace("\\n", "\n").split("\n") if l.strip()]
    if len(lines) == 1 and len(lines[0]) > 8:
        t = lines[0]
        mid = len(t) // 2
        cut = t.rfind(" ", 0, mid + 3)
        cut = cut if cut > 2 else mid
        lines = [t[:cut].strip(), t[cut:].strip()]
    return lines[:3]


def _fit_font(fp, lines, maxw, start=200):
    size = start
    while size > 40:
        f = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
        if max(f.getlength(l) for l in lines) <= maxw:
            return f, size
        size -= 6
    return f, size


def _base(img, variant):
    im = images._fit(img, W, H)
    im = ImageEnhance.Color(im).enhance(1.35)
    im = ImageEnhance.Contrast(im).enhance(1.18)
    im = ImageEnhance.Brightness(im).enhance(1.05 if variant != 1 else 0.95)
    return im


def make_variant(img, text, out, variant):
    im = _base(img, variant).convert("RGBA")
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for x in range(W):   # 왼쪽(글씨 영역)을 어둡게 하는 그라데이션
        a = int(190 * max(0, 1 - x / (W * 0.85))) if variant != 2 else 0
        d.line([(x, 0), (x, H)], fill=(0, 0, 0, a))
    if variant == 2:     # 하단 띠
        for y in range(H):
            d.line([(0, y), (W, y)], fill=(0, 0, 0, int(200 * max(0, (y - H * 0.45) / (H * 0.55)))))
    im = Image.alpha_composite(im, shade)
    fp = find_font()
    lines = _lines(text)
    maxw = W * (0.62 if variant != 2 else 0.9)
    font, size = _fit_font(fp, lines, maxw)
    c1, c2 = PALETTES[variant % 3]
    draw = ImageDraw.Draw(im)
    lh = int(size * 1.12)
    total = lh * len(lines)
    y = (H - total) // 2 if variant != 2 else H - total - 50
    for i, l in enumerate(lines):
        x = 50 if variant != 2 else (W - font.getlength(l)) / 2
        draw.text((x, y + i * lh), l, font=font, fill=c1 if i == 0 else c2, stroke_width=max(6, size // 10), stroke_fill=(0, 0, 0))
    im.convert("RGB").save(out, quality=94)
    return out


def make_all(pdir, plan, scenes, cfg, progress=None):
    pdir = Path(pdir)
    tdir = pdir / "thumbnails"
    tdir.mkdir(exist_ok=True)
    text = plan.get("thumbnail_text") or plan["title"]
    cand = [pdir / scenes[0]["image"], pdir / scenes[len(scenes) // 2]["image"], pdir / scenes[-1]["image"]]
    # 썸네일 전용 이미지 시도(더 극적인 구도). 실패 시 장면 이미지 재사용.
    special = tdir / "base_dramatic.jpg"
    src = images.make_one(f"{plan['title']}, extreme dramatic close-up, vivid colors, high contrast, mysterious glow, "
                          "wide empty space on the left side", special, cfg, 1280, 720, style=plan.get("visual_style", ""))
    if src != "placeholder":
        cand[0] = special
    outs = []
    for v, p in enumerate(cand):
        outs.append(make_variant(Image.open(p), text, tdir / f"thumbnail_{v + 1}.jpg", v))
    log.info(f"[썸네일] {len(outs)}종 생성 → {tdir}")
    return outs

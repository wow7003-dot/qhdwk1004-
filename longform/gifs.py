"""GIF: ① 자체 제작 팝업 강조 GIF(완전 무료/오프라인) ② 선택: Giphy 무료 키 ③ assets/gifs 폴더 ④ 완성 영상 미리보기 GIF."""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .util import ROOT, find_font, http, log, run, short_hash


def callout_gif(text, out, height, accent=(255, 214, 0)):
    """팝인(0.3초) 후 정지 상태를 길게 유지하는 강조 박스 GIF (투명 배경)."""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fp = find_font()
    fs = max(24, int(height * 0.062))
    font = ImageFont.truetype(fp, fs) if fp else ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = int(probe.textlength(text, font=font))
    pad = int(fs * 0.55)
    W, H = tw + pad * 2 + 16, fs + pad * 2 + 16
    frames, durs = [], []
    for i, sc in enumerate([0.2, 0.55, 0.85, 1.08, 1.0]):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        w2, h2 = int(W * sc), int(H * sc)
        box = Image.new("RGBA", (w2, h2), (0, 0, 0, 0))
        d = ImageDraw.Draw(box)
        d.rounded_rectangle([0, 0, w2 - 1, h2 - 1], radius=int(fs * 0.4), fill=(15, 15, 20, 225), outline=accent + (255,), width=max(3, fs // 12))
        if sc > 0.8:
            f2 = ImageFont.truetype(fp, int(fs * sc)) if fp else font
            d.text((w2 / 2, h2 / 2), text, font=f2, fill=(255, 255, 255, 255), anchor="mm")
        im.paste(box, ((W - w2) // 2, (H - h2) // 2))
        frames.append(im)
        durs.append(60)
    durs[-1] = 20000   # 마지막 프레임을 오래 유지 → 루프가 다시 팝인하지 않음
    # GIF 팔레트 변환 (투명 유지)
    pal = []
    for f in frames:
        a = f.split()[3]
        p = f.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
        p.paste(255, Image.eval(a, lambda v: 255 if v < 128 else 0))
        pal.append(p)
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs, loop=0, transparency=255, disposal=2)
    return out, W, H


def giphy(keyword, cfg, out_dir):
    key = cfg["keys"].get("giphy")
    if not (key and keyword and cfg["gif"]["giphy"]):
        return None
    out = Path(out_dir) / f"giphy_{short_hash(keyword)}.gif"
    if out.exists():
        return out
    try:
        r = http("GET", "https://api.giphy.com/v1/gifs/search", params={"api_key": key, "q": keyword, "limit": 8, "rating": "g"}, retries=1)
        items = r.json()["data"]
        if not items:
            return None
        url = random.choice(items)["images"]["fixed_height_small"]["url"]
        out.write_bytes(http("GET", url, retries=1).content)
        return out
    except Exception as e:  # noqa: BLE001
        log.info(f"[GIF] giphy 실패: {str(e)[:80]}")
        return None


def local_gif(keyword):
    files = list((ROOT / "assets" / "gifs").glob("*.gif"))
    if not files:
        return None
    m = [f for f in files if keyword and keyword.lower() in f.stem.lower()]
    return random.choice(m) if m else None


def preview_gif(video, out, seconds=8, start=20, width=480):
    """완성 영상의 하이라이트 구간을 가벼운 GIF 로 (SNS/커뮤니티 홍보용)."""
    flt = f"fps=12,scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"
    run(["ffmpeg", "-y", "-ss", str(start), "-t", str(seconds), "-i", video, "-vf", flt, "-an", out])
    return out

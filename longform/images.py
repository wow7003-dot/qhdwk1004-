"""무료 이미지 생성: Pollinations(키 불필요) → AI Horde(익명) → 로컬 폴더 → 자체 생성 플레이스홀더."""
import io
import random
import time
import urllib.parse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .util import ROOT, find_font, http, log, short_hash


def _valid(data):
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return im.width >= 256 and im.height >= 144
    except Exception:  # noqa: BLE001
        return False


def _pollinations(prompt, w, h, cfg, seed):
    q = urllib.parse.quote(prompt[:900])
    r = http("GET", f"https://image.pollinations.ai/prompt/{q}", retries=2, timeout=(6, 120),
             params={"width": 1280, "height": 720, "model": cfg["image"]["model"], "nologo": "true", "seed": seed})
    if not _valid(r.content):
        raise RuntimeError("이미지가 아님")
    return r.content


def _horde(prompt, w, h, cfg, seed):
    hdr = {"apikey": "0000000000", "Client-Agent": "longform-maker:1:anon"}
    r = http("POST", "https://stablehorde.net/api/v2/generate/async", headers=hdr, retries=1,
             json={"prompt": prompt[:900], "params": {"width": 896, "height": 512, "steps": 25, "n": 1, "seed": str(seed)},
                   "nsfw": False, "censor_nsfw": True, "r2": True})
    rid = r.json()["id"]
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(6)
        st = http("GET", f"https://stablehorde.net/api/v2/generate/check/{rid}", headers=hdr, retries=1).json()
        if st.get("done"):
            gen = http("GET", f"https://stablehorde.net/api/v2/generate/status/{rid}", headers=hdr).json()["generations"][0]
            data = http("GET", gen["img"], retries=1).content
            if _valid(data):
                return data
            raise RuntimeError("horde 이미지 오류")
    raise RuntimeError("horde 대기시간 초과")


_local_used = set()


def _local(prompt, w, h, cfg, seed):
    files = [p for p in (ROOT / "assets" / "images").glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not files:
        raise RuntimeError("assets/images 비어있음")
    random.Random(seed).shuffle(files)
    return files[0].read_bytes()


def placeholder(text, w, h, seed):
    """네트워크 없이도 보기 괜찮은 그라데이션 배경."""
    rnd = random.Random(seed)
    c1 = tuple(rnd.randint(10, 70) for _ in range(3))
    c2 = tuple(rnd.randint(60, 170) for _ in range(3))
    im = Image.new("RGB", (w, h), c1)
    px = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        px.line([(0, y), (w, y)], fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(6):
        r = rnd.randint(h // 6, h // 2)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        col = tuple(min(255, c + rnd.randint(30, 90)) for c in c2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    layer = layer.filter(ImageFilter.GaussianBlur(h // 8))
    return Image.blend(im, layer, 0.35)


def _fit(img, w, h):
    img = img.convert("RGB")
    r = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


PROV = {"pollinations": _pollinations, "horde": _horde, "local": _local}


def make_one(prompt, out, cfg, w=1920, h=1080, seed=None, style=""):
    """장면 이미지 1장. 반환 provider 이름('placeholder' 이면 나중에 재시도 대상)."""
    out = Path(out)
    seed = seed if seed is not None else int(short_hash(prompt)[:6], 16)
    full = f"{prompt}, {style or cfg['image']['style']}, no text, no watermark"
    for name in cfg["image"]["providers"]:
        if name == "placeholder":
            break
        try:
            data = PROV[name](full, w, h, cfg, seed)
            _fit(Image.open(io.BytesIO(data)), w, h).save(out, quality=92)
            return name
        except Exception as e:  # noqa: BLE001
            log.info(f"[이미지:{name}] 실패: {str(e)[:90]}")
    placeholder(prompt, w, h, seed).save(out, quality=92)
    return "placeholder"


def make_all(scenes, img_dir, cfg, size, style="", progress=None):
    img_dir = Path(img_dir)
    img_dir.mkdir(parents=True, exist_ok=True)
    w, h = size
    stats = {}
    online_fail = 0
    for i, s in enumerate(scenes):
        out = img_dir / f"scene_{i:03d}.jpg"
        tag = out.with_suffix(".src")
        key = short_hash(s["image_prompt"], style)
        if out.exists() and tag.exists() and tag.read_text().startswith(key) and not tag.read_text().endswith("placeholder"):
            src = tag.read_text().split(",")[1]
        else:
            # 네트워크가 계속 막혀있으면 시간 낭비 없이 바로 플레이스홀더
            if online_fail >= 3:
                placeholder(s["image_prompt"], w, h, i).save(out, quality=92)
                src = "placeholder"
            else:
                src = make_one(s["image_prompt"], out, cfg, w, h, style=style)
                online_fail = online_fail + 1 if src == "placeholder" else 0
            tag.write_text(f"{key},{src}")
            time.sleep(cfg["image"]["gap_seconds"] if src not in ("placeholder", "local") else 0)
        s["image"] = f"images/scene_{i:03d}.jpg"
        stats[src] = stats.get(src, 0) + 1
        if progress:
            progress("이미지", (i + 1) / len(scenes), f"{i + 1}/{len(scenes)} ({src})")
    if stats.get("placeholder"):
        log.info(f"[이미지] ⚠ {stats['placeholder']}장이 임시 배경입니다. 연결 확인 후 'images' 단계를 다시 실행하면 해당 장면만 재생성합니다.")
    return stats

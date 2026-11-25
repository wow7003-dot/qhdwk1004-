"""무료 이미지 소스: Pollinations(FLUX) / Hugging Face 무료 추론 / Pexels / Pixabay / 자체 생성 배경."""
import hashlib
import random
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

from .config import Settings
from .fonts import load_font


class ImageError(RuntimeError):
    pass


def _save(content: bytes, out: Path) -> None:
    try:
        img = Image.open(BytesIO(content)).convert("RGB")
    except Exception:
        raise ImageError("이미지가 아닌 응답을 받았습니다")
    img.save(out, "JPEG", quality=92)


def pollinations(s: Settings, prompt: str, out: Path, w: int, h: int, seed: int) -> None:
    q = urllib.parse.quote(prompt[:900])
    params = {"width": w, "height": h, "seed": seed, "model": "flux", "nologo": "true"}
    attempts = []
    if s.pollinations_key:
        attempts.append((f"https://gen.pollinations.ai/image/{q}", {"Authorization": f"Bearer {s.pollinations_key}"}))
    attempts.append((f"https://image.pollinations.ai/prompt/{q}", {}))
    err = None
    for url, headers in attempts:
        for i in range(3):
            try:
                r = requests.get(url, params=params, headers=headers, timeout=180)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    return _save(r.content, out)
                err = f"{r.status_code} {r.text[:200]}"
                if r.status_code == 429:  # 무키 사용 시 속도 제한 → 대기
                    time.sleep(16 * (i + 1))
                    continue
                break
            except requests.RequestException as e:
                err = str(e)
                time.sleep(5)
    raise ImageError(f"Pollinations 실패: {err}")


def huggingface(s: Settings, prompt: str, out: Path, w: int, h: int, seed: int) -> None:
    if not s.hf_token:
        raise ImageError("Hugging Face 토큰이 없습니다")
    url = f"https://router.huggingface.co/hf-inference/models/{s.hf_model}"
    body = {"inputs": prompt, "parameters": {"width": min(w, 1344), "height": min(h, 768) if w > h else min(h, 1344),
                                             "seed": seed}}
    for i in range(3):
        r = requests.post(url, headers={"Authorization": f"Bearer {s.hf_token}"}, json=body, timeout=180)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            return _save(r.content, out)
        if r.status_code in (429, 503):
            time.sleep(20 * (i + 1))
            continue
        raise ImageError(f"HF 오류 {r.status_code}: {r.text[:200]}")
    raise ImageError("HF 한도 초과")


def _keywords(prompt: str) -> str:
    words = [w.strip(",.") for w in prompt.split() if len(w) > 3][:6]
    return " ".join(words) or "landscape"


def pexels(s: Settings, prompt: str, out: Path, w: int, h: int, seed: int) -> None:
    if not s.pexels_key:
        raise ImageError("Pexels 키가 없습니다")
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": s.pexels_key},
                     params={"query": _keywords(prompt), "per_page": 10,
                             "orientation": "landscape" if w >= h else "portrait"}, timeout=60)
    photos = r.json().get("photos", []) if r.ok else []
    if not photos:
        raise ImageError("Pexels 검색 결과 없음")
    url = random.Random(seed).choice(photos)["src"]["large2x"]
    _save(requests.get(url, timeout=120).content, out)


def pixabay(s: Settings, prompt: str, out: Path, w: int, h: int, seed: int) -> None:
    if not s.pixabay_key:
        raise ImageError("Pixabay 키가 없습니다")
    r = requests.get("https://pixabay.com/api/", params={
        "key": s.pixabay_key, "q": _keywords(prompt)[:100], "image_type": "photo", "per_page": 10,
        "orientation": "horizontal" if w >= h else "vertical", "safesearch": "true"}, timeout=60)
    hits = r.json().get("hits", []) if r.ok else []
    if not hits:
        raise ImageError("Pixabay 검색 결과 없음")
    url = random.Random(seed).choice(hits)["largeImageURL"]
    _save(requests.get(url, timeout=120).content, out)


def placeholder(prompt: str, out: Path, w: int, h: int, seed: int, label: str = "") -> None:
    """오프라인/실패 시: 그라데이션 배경 이미지(나중에 장면별로 다시 생성 가능)."""
    rnd = random.Random(int(hashlib.md5(prompt.encode()).hexdigest(), 16) + seed)
    c1 = tuple(rnd.randint(10, 90) for _ in range(3))
    c2 = tuple(rnd.randint(60, 180) for _ in range(3))
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    for _ in range(25):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(40, 260)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 40), width=2)
    img = img.filter(ImageFilter.GaussianBlur(3))
    if label:
        d = ImageDraw.Draw(img)
        font = load_font(int(h * 0.05))
        d.text((w // 2, h // 2), label, font=font, fill="white", anchor="mm", stroke_width=3, stroke_fill="black")
    img.save(out, "JPEG", quality=90)


PROVIDERS = {"pollinations": pollinations, "huggingface": huggingface, "pexels": pexels, "pixabay": pixabay}


def make_image(s: Settings, prompt: str, out: Path, seed: int, label: str = "") -> str:
    """선택한 제공자 → 다른 무료 제공자 → 자체 배경 순으로 시도. 사용된 제공자 이름 반환."""
    w, h = s.size
    order = [s.image_provider] + [p for p in PROVIDERS if p != s.image_provider]
    errors = []
    for name in order:
        fn = PROVIDERS.get(name)
        if not fn:
            continue
        try:
            fn(s, prompt, out, w, h, seed)
            return name
        except Exception as e:
            errors.append(f"{name}: {e}")
    placeholder(prompt, out, w, h, seed, label)
    if s.image_provider != "placeholder":
        print("⚠️ 이미지 생성 실패 → 임시 배경 사용. 원인:", " | ".join(e[:150] for e in errors[:2]), flush=True)
    return "placeholder"

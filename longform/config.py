"""설정 로드. config.json 이 있으면 기본값 위에 덮어쓴다. API 키는 전부 선택사항."""
import copy
import json
import os

from .util import ROOT

DEFAULTS = {
    "language": "ko",
    "niche": "역사·미스터리·과학·경제 상식 같은 대중 교양",
    "minutes": 8,
    "llm": {
        # 앞에서부터 시도. 키가 없는 gemini/groq 는 자동 건너뜀.
        "providers": ["pollinations", "gemini", "groq"],
        "gemini_model": "gemini-2.0-flash",
        "groq_model": "llama-3.3-70b-versatile",
    },
    "tts": {
        "providers": ["edge", "gtts", "espeak"],
        "voice": "ko-KR-SunHiNeural",   # 남성: ko-KR-InJoonNeural
        "rate": "+0%",
        "pitch": "+0Hz",
        "gtts_lang": "ko",
    },
    "image": {
        "providers": ["pollinations", "horde", "local", "placeholder"],
        "style": "cinematic illustration, highly detailed, dramatic lighting, 16:9",
        "model": "flux",
        "gap_seconds": 3.0,
    },
    "video": {"quality": "final", "kenburns": True},   # final=1080p30, draft=720p24
    "music": {"enabled": True, "mood": "auto", "volume": 0.14},
    "subtitles": {"enabled": True, "max_chars": 22, "size": 0.058},
    "gif": {"callouts": True, "giphy": True, "preview_gif": True},
    "keys": {"gemini": "", "groq": "", "giphy": ""},
}


def _merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _merge(a[k], v)
        else:
            a[k] = v
    return a


def load(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    p = path or ROOT / "config.json"
    try:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                _merge(cfg, json.load(f))
    except Exception as e:  # noqa: BLE001
        print(f"[config] config.json 읽기 실패, 기본값 사용: {e}")
    for name, env in (("gemini", "GEMINI_API_KEY"), ("groq", "GROQ_API_KEY"), ("giphy", "GIPHY_API_KEY")):
        if os.environ.get(env):
            cfg["keys"][name] = os.environ[env]
    return cfg


def video_size(cfg):
    if cfg["video"]["quality"] == "draft":
        return 1280, 720, 24
    return 1920, 1080, 30

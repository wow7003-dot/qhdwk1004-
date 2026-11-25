"""설정 저장/로드. API 키는 로컬 config.json 에만 저장된다 (git 에는 올리지 않음)."""
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
PROJECTS_DIR = ROOT / "projects"
FONTS_DIR = ROOT / "fonts"


@dataclass
class Settings:
    # ── LLM (대본 / 이미지 프롬프트) ──
    llm_provider: str = "gemini"          # gemini | ollama | none
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    # ── 이미지 ──
    image_provider: str = "pollinations"  # pollinations | huggingface | pexels | pixabay | placeholder
    pollinations_key: str = ""
    hf_token: str = ""
    hf_model: str = "black-forest-labs/FLUX.1-schnell"
    pexels_key: str = ""
    pixabay_key: str = ""
    # ── 음성 ──
    tts_provider: str = "edge"            # edge | silent
    voice: str = "ko-KR-InJoonNeural"
    rate: str = "+0%"
    # ── 영상 ──
    aspect: str = "16:9"                  # 16:9 (롱폼) | 9:16 (쇼츠)
    fps: int = 30
    ken_burns: bool = True
    bgm_volume: float = 0.12
    subtitle_size: int = 64
    extra: dict = field(default_factory=dict)

    @property
    def size(self) -> tuple[int, int]:
        return (1080, 1920) if self.aspect == "9:16" else (1920, 1080)


def load_settings() -> Settings:
    s = Settings()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for k, v in data.items():
                if hasattr(s, k):
                    setattr(s, k, v)
        except Exception:
            pass
    return s


def save_settings(s: Settings) -> None:
    CONFIG_PATH.write_text(json.dumps(asdict(s), ensure_ascii=False, indent=2), encoding="utf-8")

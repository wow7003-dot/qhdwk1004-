"""대본 생성 → 장면 분할 → 장면별 이미지 프롬프트 → 제목/설명/태그/썸네일 문구."""
import re

from . import llm
from .config import Settings

CHARS_PER_MIN = 330  # 한국어 TTS 기준 대략 1분당 글자 수


def write_script(s: Settings, topic: str, minutes: int, tone: str, extra: str = "") -> str:
    target = minutes * CHARS_PER_MIN
    prompt = f"""당신은 조회수 높은 한국 유튜브 롱폼 채널의 전문 대본 작가입니다.
주제: {topic}
분위기/장르: {tone}
목표 길이: 약 {minutes}분 분량 (공백 포함 약 {target}자)
추가 요청: {extra or '없음'}

규칙:
- 첫 2~3문장은 시청자를 붙잡는 강력한 훅으로 시작
- 내레이션으로 읽을 문장만 출력 (장면 지시문, 괄호, 화자 표시, 마크다운, 이모지 금지)
- 문장은 짧고 말하듯 자연스럽게, 문단 사이 빈 줄
- 중간중간 궁금증을 유발하는 전환 문장 사용
- 마지막은 구독/좋아요 유도 한 문장으로 마무리"""
    text = llm.generate(s, prompt)
    return clean_script(text)


def clean_script(text: str) -> str:
    text = re.sub(r"[*#`>]+", "", text)
    text = re.sub(r"\[[^\]]*\]|\([^)]*(장면|효과음|BGM|음악)[^)]*\)", "", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(lines).strip()


def split_sentences(text: str) -> list[str]:
    out = []
    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        parts = re.split(r"(?<=[.!?。…~])\s+", para)
        out.extend(p.strip() for p in parts if p.strip())
    return out


def split_scenes(text: str, min_chars: int = 70, max_chars: int = 160) -> list[str]:
    """문장을 묶어 장면(이미지 1장 ≈ 8~15초)을 만든다."""
    scenes, buf = [], ""
    for sent in split_sentences(text):
        if buf and len(buf) + len(sent) > max_chars:
            scenes.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip()
        if len(buf) >= min_chars:
            scenes.append(buf)
            buf = ""
    if buf:
        if scenes and len(buf) < min_chars // 2:
            scenes[-1] += " " + buf
        else:
            scenes.append(buf)
    return scenes


def style_bible(s: Settings, script: str, style: str) -> str:
    """등장인물/배경을 고정해서 장면마다 그림체·캐릭터가 일관되게 나오도록 하는 설정."""
    prompt = f"""다음 유튜브 대본에 들어갈 이미지들의 일관성을 위한 '비주얼 설정'을 영어로 작성하세요.
그림 스타일: {style}
- 주요 등장인물마다 외형(나이, 성별, 머리, 옷, 특징)을 한 줄씩
- 시대/장소/색감/조명 한 줄
- 전체 120단어 이내, 영어만 출력
대본:
{script[:6000]}"""
    return llm.generate(s, prompt)


def image_prompts(s: Settings, scenes: list[str], style: str, bible: str, batch: int = 15) -> list[str]:
    prompts: list[str] = []
    for i in range(0, len(scenes), batch):
        chunk = scenes[i:i + batch]
        numbered = "\n".join(f"{n + 1}. {t}" for n, t in enumerate(chunk))
        prompt = f"""You write prompts for an AI image generator (FLUX / Stable Diffusion) for a YouTube video.
Art style: {style}
Visual bible (keep characters/setting consistent): {bible}

For EACH narration line below, write ONE English image prompt (30-60 words) describing a single cinematic
16:9 shot that illustrates it: subject, action, setting, camera angle, lighting, mood. No text, no letters,
no captions in the image. Return JSON: {{"prompts": ["...", "..."]}} with exactly {len(chunk)} items.

Narration lines:
{numbered}"""
        try:
            data = llm.generate_json(s, prompt)
            got = data.get("prompts", []) if isinstance(data, dict) else data
            got = [str(p) for p in got]
        except Exception:
            got = []
        if len(got) < len(chunk):
            got += [fallback_prompt(t, style) for t in chunk[len(got):]]
        prompts.extend(got[:len(chunk)])
    return prompts


def fallback_prompt(narration: str, style: str) -> str:
    return f"{style}, cinematic illustration of: {narration[:150]}, highly detailed, dramatic lighting, no text"


def metadata(s: Settings, script: str, topic: str) -> dict:
    prompt = f"""다음 유튜브 대본으로 클릭률 높은 메타데이터를 만드세요.
JSON 형식: {{"title": "제목(60자 이내, 호기심 자극)", "description": "설명(3~5줄, 핵심 요약 + 해시태그 3개)",
"tags": ["태그", ...10개], "thumbnail_top": "썸네일 윗줄 문구(8자 이내)", "thumbnail_bottom": "썸네일 아랫줄 강조 문구(10자 이내)"}}
주제: {topic}
대본:
{script[:5000]}"""
    try:
        data = llm.generate_json(s, prompt)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    first = split_sentences(script)[0] if script else topic
    return {"title": topic or first[:50], "description": first, "tags": [],
            "thumbnail_top": (topic or first)[:8], "thumbnail_bottom": (topic or first)[8:18]}

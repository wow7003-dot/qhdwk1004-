"""장면별 음성 타이밍 → ASS 자막 (굵은 흰 글씨 + 검은 테두리, 유튜브 스타일)."""
import re

from .script import split_sentences


def _chunks(text: str, max_chars: int) -> list[str]:
    """긴 문장을 비슷한 길이의 자막 줄로 균등 분할 (끝에 짧은 꼬리 줄이 남지 않게)."""
    words, out, buf = text.split(), [], ""
    pieces = -(-len(text) // max_chars)
    target = min(max_chars, -(-len(text) // max(pieces, 1)) + 2)
    for w in words:
        if buf and len(buf) + 1 + len(w) > target:
            out.append(buf)
            buf = w
        else:
            buf = f"{buf} {w}".strip()
    if buf:
        out.append(buf)
    return out


def scene_cues(text: str, duration: float, tts_cues: list[dict], max_chars: int) -> list[dict]:
    """장면 내부 기준(0초 시작) 자막 cue 목록."""
    base = [c for c in tts_cues if c.get("text", "").strip()]
    if not base:  # 타이밍 정보가 없으면 글자 수 비례 배분
        sents = split_sentences(text) or [text]
        total = sum(len(x) for x in sents) or 1
        t, base = 0.0, []
        for sent in sents:
            d = duration * len(sent) / total
            base.append({"start": t, "end": t + d, "text": sent})
            t += d
    out = []
    for c in base:
        parts = _chunks(c["text"], max_chars)
        total = sum(len(p) for p in parts) or 1
        t = c["start"]
        span = max(0.3, c["end"] - c["start"])
        for p in parts:
            d = span * len(p) / total
            out.append({"start": t, "end": t + d, "text": p})
            t += d
    return out


def _ts(sec: float) -> str:
    sec = max(0.0, sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _escape(text: str) -> str:
    return re.sub(r"[{}\\]", "", text).replace("\n", "\\N")


def write_ass(path, cues: list[dict], font: str, size: int, w: int, h: int) -> None:
    margin_v = int(h * 0.07) if w > h else int(h * 0.25)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{_ts(c['start'])},{_ts(c['end'])},Default,,0,0,0,,{_escape(c['text'])}" for c in cues]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def write_srt(path, cues: list[dict]) -> None:
    def ts(sec):
        ms = int(round(sec * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    blocks = [f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n" for i, c in enumerate(cues, 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")

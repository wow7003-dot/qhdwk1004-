"""자막: 장면 길이에 맞춰 문장을 짧게 쪼개 타이밍 배분 → ASS(영상에 입힘) + SRT(유튜브 업로드용)."""
import re


def chunk(text, max_chars=22):
    """문장 → 최대 max_chars 글자의 한 줄 자막 조각들 (띄어쓰기 기준)."""
    parts = []
    for sent in re.split(r"(?<=[.!?。…])\s+", text.strip()):
        words, cur = sent.split(), ""
        for w in words:
            if cur and len(cur) + 1 + len(w) > max_chars:
                parts.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            parts.append(cur)
    # 너무 짧은 조각은 앞 조각에 붙임
    merged = []
    for p in parts:
        if merged and len(p) < 5 and len(merged[-1]) + len(p) + 1 <= max_chars + 6:
            merged[-1] += " " + p
        else:
            merged.append(p)
    return merged or [text]


def build_cues(scenes, starts, max_chars=22):
    """scenes[i]['audio_dur'] 와 장면 시작시간 starts[i] 로 [(start,end,text)] 생성."""
    cues = []
    for s, t0 in zip(scenes, starts):
        pieces = chunk(s["narration"], max_chars)
        total = sum(len(p) for p in pieces) or 1
        t = t0 + 0.05
        span = max(0.5, s["audio_dur"] - 0.1)
        for p in pieces:
            d = span * len(p) / total
            cues.append((t, t + d, p.rstrip(".,")))
            t += d
    return cues


def _ts_ass(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ts_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_ass(cues, path, W, H, family, size_ratio=0.058):
    fs = int(H * size_ratio)
    head = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
        "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Default,{family},{fs},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{max(3, fs // 14)},1,2,60,60,{int(H * 0.07)},1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    lines = [f"Dialogue: 0,{_ts_ass(a)},{_ts_ass(b)},Default,,0,0,0,,{t}" for a, b, t in cues]
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(head + "\n".join(lines) + "\n")


def write_srt(cues, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, t) in enumerate(cues, 1):
            f.write(f"{i}\n{_ts_srt(a)} --> {_ts_srt(b)}\n{t}\n\n")

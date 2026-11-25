"""전체 흐름: (1) 기획 = 대본·장면·프롬프트·메타데이터  (2) 제작 = 이미지·음성·자막·영상·썸네일."""
import json
import time
from pathlib import Path
from typing import Callable

from . import llm, script as sc
from .config import PROJECTS_DIR, Settings
from .fonts import family_name, font_path
from .images import make_image
from .subtitles import scene_cues, write_ass, write_srt
from .thumbnail import make_thumbnail
from .tts import synthesize
from .video import GAP, concat, finalize, scene_clip

Progress = Callable[[float, str], None]


def _noop(p: float, msg: str) -> None:
    print(f"[{p * 100:5.1f}%] {msg}", flush=True)


def new_project_dir(name: str) -> Path:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in " _-")[:30].strip() or "video"
    d = PROJECTS_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_{safe}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(project: dict) -> None:
    Path(project["dir"], "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def load(project_dir: Path) -> dict:
    return json.loads((Path(project_dir) / "project.json").read_text(encoding="utf-8"))


def plan(s: Settings, *, topic: str = "", script_text: str = "", minutes: int = 10, tone: str = "",
         style: str = "", extra: str = "", progress: Progress = _noop) -> dict:
    """대본이 없으면 AI 로 작성하고, 장면 분할 + 이미지 프롬프트 + 메타데이터까지 만든다."""
    use_llm = llm.available(s)
    if not script_text.strip():
        if not use_llm:
            raise llm.LLMError("대본을 직접 넣거나, Gemini 키/Ollama 를 설정해 AI 대본 생성을 켜세요.")
        progress(0.05, "AI 가 대본을 쓰는 중…")
        script_text = sc.write_script(s, topic, minutes, tone, extra)
    script_text = sc.clean_script(script_text)
    scenes = sc.split_scenes(script_text)
    progress(0.35, f"장면 {len(scenes)}개로 분할 완료")

    bible, prompts = "", []
    if use_llm:
        progress(0.40, "등장인물/배경 설정 정리 중…")
        try:
            bible = sc.style_bible(s, script_text, style)
        except Exception:
            bible = ""
        progress(0.50, "장면별 이미지 프롬프트 작성 중…")
        prompts = sc.image_prompts(s, scenes, style, bible)
        progress(0.85, "제목/설명/태그/썸네일 문구 작성 중…")
        meta = sc.metadata(s, script_text, topic)
    else:
        prompts = [sc.fallback_prompt(t, style) for t in scenes]
        meta = sc.metadata(s, script_text, topic)

    d = new_project_dir(meta.get("title") or topic or "video")
    project = {
        "dir": str(d), "topic": topic, "style": style, "tone": tone, "bible": bible,
        "script": script_text, "meta": meta,
        "scenes": [{"text": t, "prompt": p} for t, p in zip(scenes, prompts)],
    }
    save(project)
    progress(1.0, "기획 완료")
    return project


def render(s: Settings, project: dict, bgm: Path | None = None, progress: Progress = _noop,
           regenerate_images: bool = False) -> dict:
    d = Path(project["dir"])
    for sub in ("images", "audio", "clips"):
        (d / sub).mkdir(exist_ok=True)
    scenes = project["scenes"]
    n = len(scenes)
    w, h = s.size
    max_chars = 26 if w > h else 14
    sub_font = font_path(heavy=False)
    family = family_name(sub_font)

    all_cues, clips, t = [], [], 0.0
    for i, sc_ in enumerate(scenes):
        base = i / n
        img = d / "images" / f"{i:03d}.jpg"
        if regenerate_images or not img.exists():
            progress(base * 0.85, f"[{i + 1}/{n}] 이미지 생성 중…")
            sc_["image_source"] = make_image(s, sc_["prompt"], img, seed=1000 + i, label=f"장면 {i + 1}")
        progress((base + 0.4 / n) * 0.85, f"[{i + 1}/{n}] 음성 합성 중…")
        aud = d / "audio" / f"{i:03d}.mp3"
        dur, tts_cues = synthesize(s, sc_["text"], aud)
        progress((base + 0.6 / n) * 0.85, f"[{i + 1}/{n}] 장면 영상 편집 중…")
        clip = d / "clips" / f"{i:03d}.mp4"
        total = scene_clip(s, i, img, aud, dur, clip)
        for c in scene_cues(sc_["text"], dur, tts_cues, max_chars):
            all_cues.append({"start": t + c["start"], "end": t + c["end"], "text": c["text"]})
        sc_["start"], sc_["duration"] = round(t, 2), round(total, 2)
        clips.append(clip)
        t += total
        save(project)

    progress(0.87, "장면 이어붙이는 중…")
    body = d / "body.mp4"
    concat(clips, body)
    write_ass(d / "subs.ass", all_cues, family, s.subtitle_size if w > h else int(s.subtitle_size * 1.2), w, h)
    write_srt(d / "subtitles.srt", all_cues)  # 유튜브에 별도 업로드 가능한 자막 파일
    progress(0.90, "자막 입히고 BGM 섞는 중 (최종 인코딩)…")
    final = d / "final.mp4"
    finalize(s, body, d / "subs.ass", sub_font, final, bgm)

    progress(0.97, "썸네일 만드는 중…")
    meta = project.get("meta", {})
    make_thumbnail(d / "images" / "000.jpg", meta.get("thumbnail_top", ""), meta.get("thumbnail_bottom", ""),
                   d / "thumbnail.jpg")
    _write_upload_info(d, meta, scenes)
    project.update({"video": str(final), "thumbnail": str(d / "thumbnail.jpg"), "length_sec": round(t, 1)})
    save(project)
    progress(1.0, f"완료! ({int(t // 60)}분 {int(t % 60)}초)")
    return project


def _write_upload_info(d: Path, meta: dict, scenes: list[dict]) -> None:
    chapters = []
    step = max(1, len(scenes) // 8)  # 챕터(타임스탬프) 자동 생성
    for i in range(0, len(scenes), step):
        sec = int(scenes[i].get("start", 0))
        chapters.append(f"{sec // 60:02d}:{sec % 60:02d} {scenes[i]['text'][:28]}…")
    if chapters:
        chapters[0] = "00:00" + chapters[0][5:]
    txt = (f"[제목]\n{meta.get('title', '')}\n\n[설명]\n{meta.get('description', '')}\n\n[챕터]\n"
           + "\n".join(chapters) + f"\n\n[태그]\n{', '.join(meta.get('tags', []))}\n")
    (d / "upload_info.txt").write_text(txt, encoding="utf-8")

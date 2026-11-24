"""전체 파이프라인. 각 단계는 결과를 프로젝트 폴더에 저장하므로 중간에 멈춰도 이어서 실행 가능."""
import datetime as dt
import json
from pathlib import Path

from . import gifs, images, music, planner, reference, subtitles, thumbnail, topics, tts, video
from .config import video_size
from .util import ROOT, log, need_ffmpeg, slugify

STEPS = ["plan", "script", "voice", "images", "render", "thumb", "meta"]
STEP_KO = {"plan": "기획", "script": "대본", "voice": "음성", "images": "이미지", "render": "영상 렌더링", "thumb": "썸네일", "meta": "업로드 정보"}


class Project:
    def __init__(self, path, cfg):
        self.dir = Path(path)
        self.cfg = cfg
        self.f = self.dir / "project.json"
        self.state = json.loads(self.f.read_text(encoding="utf-8")) if self.f.exists() else {}

    def save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.f.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def create(cls, topic, cfg, ref_url=None, base=None):
        base = Path(base or ROOT / "output")
        p = cls(base / f"{dt.datetime.now():%Y%m%d-%H%M}-{slugify(topic)}", cfg)
        p.state = {"topic": topic, "ref_url": ref_url, "created": dt.datetime.now().isoformat(timespec="seconds")}
        p.save()
        return p


def _noop(*a, **k):
    pass


def step_plan(p, progress=_noop):
    cfg = p.cfg
    if p.state.get("ref_url") and "analysis" not in p.state:
        progress("기획", 0.1, "참고 링크 분석")
        ref = reference.fetch(p.state["ref_url"])
        p.state["ref"] = {k: ref[k] for k in ("url", "kind", "title", "stats")}
        p.state["analysis"] = reference.analyze(ref, cfg)
        if ref.get("stats", {}).get("minutes") and not cfg.get("_minutes_set"):
            log.info(f"[참고] 참고 영상 길이 {ref['stats']['minutes']}분 / 분당 {ref['stats']['chars_per_min']}자")
        p.save()
    progress("기획", 0.5, "기획서 작성")
    p.state["plan"] = planner.make_plan(p.state["topic"], cfg, p.state.get("analysis"))
    p.save()


def step_script(p, progress=_noop):
    plan = p.state["plan"]
    p.state["scenes"] = planner.write_script(plan, p.cfg, p.state.get("analysis"), progress)
    p.save()
    lines = [f"# {plan['title']}\n"]
    cur = -1
    for s in p.state["scenes"]:
        if s["chapter"] != cur:
            cur = s["chapter"]
            lines.append(f"\n## {cur + 1}. {plan['chapters'][cur]['title']}\n")
        lines.append(s["narration"] + "\n")
    (p.dir / "script.md").write_text("\n".join(lines), encoding="utf-8")
    n = sum(len(s["narration"]) for s in p.state["scenes"])
    log.info(f"[대본] 장면 {len(p.state['scenes'])}개 / {n}자 (약 {n / planner.CHARS_PER_MIN:.1f}분) → {p.dir / 'script.md'}")


def step_voice(p, progress=_noop):
    tts.synth_all(p.state["scenes"], p.dir / "audio", p.cfg, progress)
    p.save()


def step_images(p, progress=_noop):
    W, H, _ = video_size(p.cfg)
    style = p.state["plan"].get("visual_style", "")
    images.make_all(p.state["scenes"], p.dir / "images", p.cfg, (W, H), style, progress)
    p.save()


def step_render(p, progress=_noop):
    cfg = p.cfg
    need_ffmpeg()
    W, H, fps = video_size(cfg)
    scenes = p.state["scenes"]
    family = video.prepare_font(p.dir)
    # 장면 시작 시각(= 클립 길이 누적). render_all 과 같은 규칙으로 계산해 자막을 먼저 만든다.
    durs = [video.quantize(s["audio_dur"] + video.PAD, fps) for s in scenes]
    starts = [sum(durs[:i]) for i in range(len(durs))]
    total = sum(durs)
    cues = subtitles.build_cues(scenes, starts, cfg["subtitles"]["max_chars"])
    subtitles.write_srt(cues, p.dir / "subtitles.srt")
    ass = None
    if cfg["subtitles"]["enabled"]:
        subtitles.write_ass(cues, p.dir / "subs.ass", W, H, family, cfg["subtitles"]["size"])
        ass = "subs.ass"
    bgm = None
    if cfg["music"]["enabled"]:
        mood = cfg["music"]["mood"]
        mood = p.state["plan"].get("music_mood", "calm") if mood == "auto" else mood
        bgm = music.pick_bgm(mood if mood in music.MOODS else "calm", total + 5, p.dir)
    out, durs2 = video.render_all(p.dir, scenes, cfg, (W, H, fps), bgm, ass, progress)
    p.state["video"] = {"file": out.name, "seconds": round(sum(durs2), 1), "starts": starts}
    p.save()
    if cfg["gif"]["preview_gif"]:
        try:
            gifs.preview_gif(out, p.dir / "preview.gif", 8, min(20, max(0, int(total) - 10)))
        except Exception as e:  # noqa: BLE001
            log.info(f"[GIF] 미리보기 생성 실패: {str(e)[:80]}")


def step_thumb(p, progress=_noop):
    thumbnail.make_all(p.dir, p.state["plan"], p.state["scenes"], p.cfg, progress)


def _stamp(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def step_meta(p, progress=_noop):
    plan, scenes = p.state["plan"], p.state["scenes"]
    starts = p.state.get("video", {}).get("starts") or [0] * len(scenes)
    chap_lines, seen = [], set()
    for s, t in zip(scenes, starts):
        if s["chapter"] not in seen:
            seen.add(s["chapter"])
            chap_lines.append(f"{_stamp(t)} {plan['chapters'][s['chapter']]['title']}")
    desc = (plan.get("description") or "") + "\n\n" + "\n".join(chap_lines)
    desc += "\n\n※ 이 영상은 AI(음성·이미지·대본 작성 보조)를 활용해 제작되었습니다."
    tags = ", ".join(plan.get("tags", []))
    (p.dir / "upload_info.txt").write_text(
        f"[제목]\n{plan['title']}\n\n[제목 대안]\n" + "\n".join(plan.get("title_alternatives", [])) +
        f"\n\n[설명]\n{desc}\n\n[태그]\n{tags}\n\n[업로드 체크]\n- 썸네일: thumbnails/ 중 1개 선택\n- 자막: subtitles.srt 업로드\n"
        "- 유튜브 스튜디오에서 '변경되거나 합성된 콘텐츠' 항목에 해당되면 공개 설정에서 체크\n", encoding="utf-8")


FUNCS = {"plan": step_plan, "script": step_script, "voice": step_voice, "images": step_images,
         "render": step_render, "thumb": step_thumb, "meta": step_meta}


def run(p, steps=None, progress=_noop):
    steps = steps or STEPS
    for i, s in enumerate(steps):
        log.info(f"━━ [{i + 1}/{len(steps)}] {STEP_KO[s]}")
        FUNCS[s](p, progress)
    log.info(f"✔ 완료: {p.dir}")
    return p

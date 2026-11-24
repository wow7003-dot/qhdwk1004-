"""ffmpeg 렌더링: 장면별 켄번스 클립(+GIF 오버레이) → 이어붙이기 → 나레이션+BGM(자동 덕킹)+자막 합성."""
import math
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import gifs
from .util import duration, find_font, font_family, log, run, short_hash

PAD = 0.35   # 장면 끝 여유(초)


def quantize(sec, fps):
    return math.ceil(sec * fps) / fps


def _motion(idx, frames, W, H):
    """장면마다 줌인/줌아웃/좌우 팬을 번갈아 적용."""
    m = idx % 4
    if m == 0:
        z, x, y = f"1+0.14*on/{frames}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif m == 1:
        z, x, y = "1.12", f"(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"
    elif m == 2:
        z, x, y = f"1.14-0.14*on/{frames}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z, x, y = "1.12", f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"
    return z, x, y


def render_clip(pdir, scene, idx, W, H, fps, cfg, preset):
    dur = quantize(scene["audio_dur"] + PAD, fps)
    frames = int(round(dur * fps))
    out = pdir / "clips" / f"clip_{idx:03d}.mp4"
    overlays = []   # (path, x, y, 시작초, 스케일폭 or None)
    if cfg["gif"]["callouts"] and scene.get("callout"):
        g, gw, gh = gifs.callout_gif(scene["callout"], pdir / "gifs" / f"callout_{idx:03d}.gif", H)
        overlays.append((g, f"W-w-{int(W*0.04)}", f"{int(H*0.07)}", 0.6, None))
    gk = scene.get("gif_keyword")
    if gk:
        (pdir / "gifs").mkdir(exist_ok=True)
        g = gifs.giphy(gk, cfg, pdir / "gifs") or gifs.local_gif(gk)
        if g:
            overlays.append((g, f"{int(W*0.03)}", f"H-h-{int(H*0.2)}", 1.0, int(W * 0.16)))
    key = short_hash(scene["image"], scene["audio_dur"], scene.get("callout"), gk, W, H, fps, preset, bool(overlays))
    tag = out.with_suffix(".key")
    if out.exists() and tag.exists() and tag.read_text() == key:
        return out, dur
    z, x, y = _motion(idx, frames, W, H)
    if cfg["video"]["kenburns"]:
        bg = (f"[0:v]scale={2*W}:{2*H}:force_original_aspect_ratio=increase,crop={2*W}:{2*H},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={fps},format=yuv420p[v0]")
    else:
        bg = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},format=yuv420p[v0]"
    parts, cmd_in = [bg], ["-i", pdir / scene["image"]]
    last = "v0"
    for k, (path, ox, oy, t0, sw) in enumerate(overlays):
        cmd_in += ["-ignore_loop", "0", "-i", path]
        sc = f"scale={sw}:-1," if sw else ""
        parts.append(f"[{k+1}:v]{sc}format=rgba,setpts=PTS-STARTPTS+{t0}/TB[o{k}]")
        parts.append(f"[{last}][o{k}]overlay=x={ox}:y={oy}:eof_action=pass:enable='between(t,{t0},{dur-0.3:.2f})'[v{k+1}]")
        last = f"v{k+1}"
    out.parent.mkdir(exist_ok=True)
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *cmd_in, "-filter_complex", ";".join(parts), "-map", f"[{last}]",
         "-frames:v", frames, "-r", fps, "-an", "-c:v", "libx264", "-preset", preset, "-crf", "20", out])
    tag.write_text(key)
    return out, dur


def build_narration(pdir, scenes, durs):
    """장면별 음성을 정확한 길이로 맞춰 하나의 wav 로 → 영상과 싱크 어긋남 없음."""
    wdir = pdir / "audio_wav"
    wdir.mkdir(exist_ok=True)
    lst = []
    for i, (s, d) in enumerate(zip(scenes, durs)):
        w = wdir / f"{i:03d}.wav"
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", pdir / s["audio"], "-ar", "44100", "-ac", "2",
             "-af", "apad", "-t", f"{d:.4f}", w])
        lst.append(f"file '{w.resolve().as_posix()}'")
    (pdir / "narr.txt").write_text("\n".join(lst), encoding="utf-8")
    out = pdir / "narration.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", pdir / "narr.txt", "-c", "copy", out])
    return out


def render_all(pdir, scenes, cfg, size, bgm_path, ass_name, progress=None):
    W, H, fps = size
    preset = "veryfast" if cfg["video"]["quality"] == "draft" else "medium"
    jobs = [(s, i) for i, s in enumerate(scenes)]
    done = [0]
    results = {}

    def work(job):
        s, i = job
        r = render_clip(pdir, s, i, W, H, fps, cfg, "veryfast")
        done[0] += 1
        if progress:
            progress("렌더", done[0] / len(jobs) * 0.8, f"장면 {done[0]}/{len(jobs)}")
        return i, r

    with ThreadPoolExecutor(max_workers=2) as ex:
        for i, r in ex.map(work, jobs):
            results[i] = r
    clips = [results[i][0] for i in range(len(scenes))]
    durs = [results[i][1] for i in range(len(scenes))]
    (pdir / "clips.txt").write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips), encoding="utf-8")
    concat = pdir / "video_nosound.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", pdir / "clips.txt", "-c", "copy", concat])
    narr = build_narration(pdir, scenes, durs)
    total = sum(durs)
    if progress:
        progress("렌더", 0.85, "최종 합성(자막·음악)")

    inputs = ["-i", concat.name, "-i", narr.name]
    af = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[n]"
    if bgm_path:
        inputs += ["-stream_loop", "-1", "-i", str(Path(bgm_path).resolve())]
        vol = cfg["music"]["volume"]
        af = (f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit[n1][n2];[2:a]volume={vol}[m];"
              "[m][n2]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=600[duck];"
              "[n1][duck]amix=inputs=2:duration=first:normalize=0[n]")
    vf = f"[0:v]ass={ass_name}:fontsdir=fonts[v]" if ass_name else "[0:v]null[v]"
    out = pdir / "final.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[n]",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", preset, "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out.name], cwd=pdir)
    if progress:
        progress("렌더", 1.0, "완료")
    return out, durs


def prepare_font(pdir):
    """프로젝트 폴더에 폰트를 복사(ffmpeg 경로 이스케이프 문제 회피). 반환: 폰트 패밀리명."""
    fp = find_font()
    if not fp:
        return "Arial"
    d = pdir / "fonts"
    d.mkdir(exist_ok=True)
    shutil.copy(fp, d / Path(fp).name)
    return font_family(fp)

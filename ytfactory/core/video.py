"""FFmpeg 로 편집: 장면별 켄번스(줌/팬) 클립 → 이어붙이기 → 자막 굽기 + BGM 믹스."""
import shutil
import subprocess
from pathlib import Path

from .config import Settings

GAP = 0.35  # 장면 사이 숨 고르기(초)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("FFmpeg 오류:\n" + p.stderr[-2000:])


def _motion(idx: int, frames: int, w: int, h: int) -> str:
    n = max(frames - 1, 1)
    z = 0.15
    kinds = [
        (f"1+{z}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),                    # 줌 인
        (f"{1 + z}-{z}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),              # 줌 아웃
        (f"{1 + z}", f"(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),                    # 왼→오 팬
        (f"{1 + z}", f"(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),                # 오→왼 팬
    ]
    zx, xx, yx = kinds[idx % len(kinds)]
    return f"zoompan=z='{zx}':x='{xx}':y='{yx}':d={frames}:s={w}x{h}:fps={{fps}}"


def scene_clip(s: Settings, idx: int, image: Path, audio: Path, duration: float, out: Path) -> float:
    w, h = s.size
    total = duration + GAP
    frames = int(round(total * s.fps))
    if s.ken_burns:
        big_w, big_h = w * 2, h * 2  # 고해상도에서 줌해야 떨림이 없음
        vf = (f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase,crop={big_w}:{big_h},"
              + _motion(idx, frames, w, h).format(fps=s.fps) + ",format=yuv420p")
        vin = ["-i", str(image)]
    else:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p"
        vin = ["-loop", "1", "-framerate", str(s.fps), "-i", str(image)]
    run(["ffmpeg", "-y", "-loglevel", "error", *vin, "-i", str(audio),
         "-filter_complex", f"[0:v]{vf}[v];[1:a]aresample=44100,apad[a]",
         "-map", "[v]", "-map", "[a]", "-r", str(s.fps), "-frames:v", str(frames), "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "192k", "-ac", "2", str(out)])
    return total


def concat(clips: list[Path], out: Path) -> None:
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def finalize(s: Settings, body: Path, ass: Path, font_file: Path | None, out: Path, bgm: Path | None) -> None:
    """자막 굽기 + BGM. 경로 이스케이프 문제를 피하려고 작업 폴더 기준 상대경로 사용."""
    work = body.parent
    fonts = work / "fonts"
    fonts.mkdir(exist_ok=True)
    if font_file:
        shutil.copy(font_file, fonts / font_file.name)
    vf = f"ass={ass.name}:fontsdir=fonts"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", body.name]
    if bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm.resolve())]
        fc = (f"[0:v]{vf}[v];[1:a]volume={s.bgm_volume},aresample=44100[b];"
              f"[0:a][b]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", vf, "-map", "0:v", "-map", "0:a"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out.resolve())]
    run(cmd, cwd=work)

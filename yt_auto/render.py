import subprocess, textwrap
from config import W, H, FPS, FONT

def run(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)

def scene_clip(video, audio, dur, text, out, idx):
    """영상(없으면 어두운 그라데이션 배경) + 나레이션 + 하단 자막"""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
          f"drawbox=y=ih-220:w=iw:h=220:color=black@0.45:t=fill,"
          f"drawtext=fontfile={FONT}:textfile=sub{idx}.txt:fontcolor=white:fontsize=48:"
          f"x=(w-text_w)/2:y=h-190:line_spacing=12")
    open(f"sub{idx}.txt", "w").write("\n".join(textwrap.wrap(text, 28)[:3]))
    src = ["-stream_loop", "-1", "-i", video] if video else ["-f", "lavfi", "-i", f"color=c=0x1b2a41:s={W}x{H}:r={FPS}"]
    run(*src, "-i", audio, "-t", f"{dur:.2f}", "-vf", vf, "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", out)

def concat(clips, out):
    open("list.txt", "w").write("".join(f"file '{c}'\n" for c in clips))
    run("-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", out)

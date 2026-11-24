import asyncio, subprocess

from config import VOICE

async def _gen(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="+5%").save(path)

def speak(text: str, path: str):
    asyncio.run(_gen(text, path))

def silence(path: str, sec: float = 4):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", str(sec), "-q:a", "9", path], check=True)

def duration(path: str) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path])
    return float(out.strip())

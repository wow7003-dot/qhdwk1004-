"""무료 음성 합성: Microsoft Edge TTS (API 키 불필요). 문장 타이밍을 함께 받아 자막 싱크에 사용."""
import asyncio
import subprocess
from pathlib import Path

from .config import Settings

VOICES = {
    "ko-KR-InJoonNeural": "인준 (남성, 차분한 내레이션)",
    "ko-KR-HyunsuMultilingualNeural": "현수 (남성, 다국어)",
    "ko-KR-SunHiNeural": "선희 (여성, 밝은 톤)",
}


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip() or 0)


async def _edge(text: str, voice: str, rate: str, out: Path) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary")
    cues = []
    with open(out, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                start = chunk["offset"] / 1e7
                cues.append({"start": start, "end": start + chunk["duration"] / 1e7, "text": chunk["text"]})
    return cues


def _silent(text: str, out: Path) -> list[dict]:
    """네트워크 없이 테스트할 때: 글자 수로 길이를 추정한 무음 오디오."""
    dur = max(2.0, len(text) / 5.5)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", f"{dur:.2f}", "-c:a", "libmp3lame", "-b:a", "64k", str(out)], check=True)
    return []


def synthesize(s: Settings, text: str, out: Path) -> tuple[float, list[dict]]:
    """text 를 out(mp3)로 합성. (길이초, 문장 타이밍 리스트) 반환."""
    cues: list[dict] = []
    if s.tts_provider == "edge":
        last_err = None
        for _ in range(3):
            try:
                cues = asyncio.run(_edge(text, s.voice, s.rate, out))
                if out.exists() and out.stat().st_size > 0:
                    break
            except Exception as e:  # 네트워크 일시 오류 재시도
                last_err = e
        else:
            raise RuntimeError(f"Edge TTS 실패: {last_err}")
    else:
        cues = _silent(text, out)
    return probe_duration(out), cues

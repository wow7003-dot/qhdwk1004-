"""무료 TTS: edge-tts(마이크로소프트 신경망 음성, 키 불필요) → gTTS → espeak → 무음(최후)."""
import asyncio
import shutil
import threading
from pathlib import Path

from .util import duration, log, run, short_hash


def _run_async(coro):
    box = {}

    def target():
        try:
            box["v"] = asyncio.run(coro)
        except Exception as e:  # noqa: BLE001
            box["e"] = e
    t = threading.Thread(target=target)
    t.start()
    t.join()
    if "e" in box:
        raise box["e"]


def _edge(text, out, cfg):
    import edge_tts
    c = cfg["tts"]
    _run_async(edge_tts.Communicate(text, c["voice"], rate=c["rate"], pitch=c["pitch"]).save(str(out)))


def _gtts(text, out, cfg):
    from gtts import gTTS
    gTTS(text, lang=cfg["tts"]["gtts_lang"]).save(str(out))


def _espeak(text, out, cfg):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak 없음")
    wav = Path(out).with_suffix(".wav")
    run([exe, "-v", cfg["language"], "-w", wav, text])
    run(["ffmpeg", "-y", "-i", wav, out])


def _silent(text, out, cfg):
    sec = max(2.0, len(text) / 5.5)   # 말하기 속도 추정
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{sec:.2f}", out])


PROV = {"edge": _edge, "gtts": _gtts, "espeak": _espeak}


def synth(text, out, cfg):
    """장면 1개 합성. 반환: (사용한 provider, 길이초). 무음이면 provider='silent'."""
    out = Path(out)
    tag = out.with_suffix(".tag")
    key = short_hash(text, cfg["tts"]["voice"], cfg["tts"]["rate"], cfg["tts"]["pitch"])
    if out.exists() and tag.exists():
        k, prov = tag.read_text().split(",")
        if k == key and prov != "silent":
            return prov, duration(out)
    for name in cfg["tts"]["providers"]:
        try:
            PROV[name](text, str(out), cfg)
            d = duration(out)
            if d > 0.3:
                tag.write_text(f"{key},{name}")
                return name, d
        except Exception as e:  # noqa: BLE001
            log.info(f"[TTS:{name}] 실패: {str(e)[:100]}")
    _silent(text, str(out), cfg)
    tag.write_text(f"{key},silent")
    return "silent", duration(out)


def synth_all(scenes, audio_dir, cfg, progress=None):
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    used = {}
    for i, s in enumerate(scenes):
        prov, d = synth(s["narration"], audio_dir / f"scene_{i:03d}.mp3", cfg)
        s["audio"] = f"audio/scene_{i:03d}.mp3"
        s["audio_dur"] = round(d, 3)
        used[prov] = used.get(prov, 0) + 1
        if progress:
            progress("음성", (i + 1) / len(scenes), f"{i + 1}/{len(scenes)}")
    if used.get("silent"):
        log.info(f"[TTS] ⚠ {used['silent']}개 장면이 무음입니다. 인터넷 연결/edge-tts 설치를 확인하고 'voice' 단계를 다시 실행하세요.")
    return used

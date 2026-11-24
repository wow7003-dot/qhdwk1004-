"""저작권 걱정 없는 BGM: 코드로 직접 합성(패드+아르페지오+에코). assets/music/ 에 곡을 넣으면 그걸 우선 사용."""
import random
import wave
from pathlib import Path

import numpy as np

from .util import ROOT, log

SR = 44100
MOODS = {  # (루트 MIDI, 코드 진행: 반음 오프셋 리스트, 마이너 여부, BPM)
    "calm":    (57, [(0, 'maj'), (5, 'maj'), (7, 'maj'), (0, 'maj')], 66),
    "epic":    (50, [(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], 84),
    "mystery": (52, [(0, 'min'), (8, 'maj'), (5, 'min'), (7, 'maj')], 60),
    "upbeat":  (60, [(0, 'maj'), (7, 'maj'), (9, 'min'), (5, 'maj')], 100),
    "sad":     (55, [(0, 'min'), (5, 'min'), (8, 'maj'), (7, 'maj')], 58),
}
TRI = {"maj": (0, 4, 7), "min": (0, 3, 7)}


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _loop(mood, seed=7):
    root, prog, bpm = MOODS.get(mood, MOODS["calm"])
    beat = 60 / bpm
    bar = beat * 4
    n = int(bar * len(prog) * 2 * SR)           # 코드 진행 2회 = 1 루프
    buf = np.zeros(n + int(bar * SR))           # 꼬리 여유(나중에 앞으로 접어 이음새 제거)
    rnd = random.Random(seed)
    for rep in range(2):
        for ci, (off, kind) in enumerate(prog):
            t0 = int((rep * len(prog) + ci) * bar * SR)
            L = int(bar * 1.15 * SR)
            t = np.arange(L) / SR
            env = np.minimum(1, t / 0.6) * np.minimum(1, (bar * 1.15 - t) / 0.9)
            pad = np.zeros(L)
            for k in TRI[kind]:
                for det in (-0.4, 0, 0.4):
                    f = _hz(root + off + k) * 2 ** (det / 100)
                    pad += np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
            pad += 1.2 * np.sin(2 * np.pi * _hz(root + off - 12) * t)       # 베이스
            buf[t0:t0 + L] += pad * env * 0.05
            steps = [0, 1, 2, 1, 0, 2, 1, 2]
            notes = [root + off + 12 + TRI[kind][s] for s in steps]
            for i, m in enumerate(notes):
                s0 = t0 + int(i * beat / 2 * SR)
                tt = np.arange(int(1.4 * SR)) / SR
                pluck = np.sin(2 * np.pi * _hz(m) * tt) * np.exp(-tt * 3.2) * 0.07 * (0.7 + 0.3 * rnd.random())
                e = min(len(pluck), len(buf) - s0)
                buf[s0:s0 + e] += pluck[:e]
    loop = buf[:n].copy()
    loop[:len(buf) - n] += buf[n:]              # 꼬리를 앞에 합침 → 이음새 없는 루프
    d = int(0.33 * SR)                          # 에코(순환)
    out = loop.copy()
    for k in range(1, 4):
        out += 0.28 ** k * np.roll(loop, d * k)
    out /= max(1e-6, np.abs(out).max()) * 1.1
    return out


def make_bgm(mood, seconds, out_wav):
    """seconds 길이의 스테레오 wav 생성(루프 반복 + 페이드)."""
    loop = _loop(mood)
    reps = int(np.ceil(seconds * SR / len(loop)))
    sig = np.tile(loop, reps)[: int(seconds * SR)]
    fade = int(2.5 * SR)
    sig[:fade] *= np.linspace(0, 1, fade)
    sig[-fade:] *= np.linspace(1, 0, fade)
    st = np.stack([sig, np.roll(sig, int(0.012 * SR))], axis=1)   # 약한 스테레오 폭
    pcm = (st * 32767 * 0.9).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_wav


def pick_bgm(mood, seconds, out_dir):
    """사용자 음악 폴더 우선, 없으면 합성. 반환: 파일 경로."""
    mine = [p for p in (ROOT / "assets" / "music").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
    if mine:
        p = random.choice(mine)
        log.info(f"[음악] 사용자 음악 사용: {p.name}")
        return p
    log.info(f"[음악] '{mood}' 분위기 BGM 합성")
    return make_bgm(mood, seconds, Path(out_dir) / "bgm.wav")

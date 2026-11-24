"""사용: python main.py "주제" [--minutes 8] [--upload] [--dry-run]"""
import argparse, json, os
import config, script_gen, tts, footage, render, thumbnail

ap = argparse.ArgumentParser()
ap.add_argument("topic"); ap.add_argument("--minutes", type=int, default=8)
ap.add_argument("--upload", action="store_true"); ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

os.makedirs(config.OUT, exist_ok=True); os.chdir(config.OUT)
meta = script_gen.sample(a.topic) if a.dry_run else script_gen.generate(a.topic, a.minutes)
json.dump(meta, open("script.json", "w"), ensure_ascii=False, indent=1)

clips = []
for i, s in enumerate(meta["scenes"]):
    audio = f"a{i}.mp3"
    tts.silence(audio, 3) if a.dry_run else tts.speak(s["narration"], audio)
    dur = tts.duration(audio) + 0.4
    video = None if a.dry_run else footage.fetch(s["keywords"], f"v{i}.mp4")
    render.scene_clip(video, audio, dur, s["narration"], f"c{i}.mp4", i)
    clips.append(f"c{i}.mp4"); print(f"장면 {i+1}/{len(meta['scenes'])} 완료")
render.concat(clips, "final.mp4")
thumbnail.make(meta["thumbnail_text"], "thumbnail.png")
print("완료: output/final.mp4, thumbnail.png, script.json")
if a.upload:
    import upload; print("업로드 ID:", upload.upload("final.mp4", "thumbnail.png", meta))

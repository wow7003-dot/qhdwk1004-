"""명령줄 실행 예:
  python cli.py --topic "조선 최강의 검객 이야기" --minutes 10 --style "korean martial arts anime, dark fantasy"
  python cli.py --script-file 대본.txt --bgm bgm.mp3
"""
import argparse
from pathlib import Path

from core.config import load_settings
from core.pipeline import plan, render


def main():
    ap = argparse.ArgumentParser(description="AI 유튜브 롱폼 자동 제작")
    ap.add_argument("--topic", default="")
    ap.add_argument("--script-file", help="직접 쓴 대본 txt (있으면 AI 대본 생략)")
    ap.add_argument("--minutes", type=int, default=10)
    ap.add_argument("--tone", default="몰입감 있는 스토리텔링")
    ap.add_argument("--style", default="cinematic digital painting, dramatic lighting")
    ap.add_argument("--bgm", help="배경음악 mp3 (선택)")
    ap.add_argument("--shorts", action="store_true", help="9:16 세로 영상")
    ap.add_argument("--offline", action="store_true", help="네트워크 없이 파이프라인 테스트(무음+자체 배경)")
    a = ap.parse_args()

    s = load_settings()
    if a.shorts:
        s.aspect = "9:16"
    if a.offline:
        s.tts_provider, s.image_provider, s.llm_provider = "silent", "placeholder", "none"
    script = Path(a.script_file).read_text(encoding="utf-8") if a.script_file else ""
    project = plan(s, topic=a.topic, script_text=script, minutes=a.minutes, tone=a.tone, style=a.style)
    project = render(s, project, bgm=Path(a.bgm) if a.bgm else None)
    print("\n영상:", project["video"], "\n썸네일:", project["thumbnail"])


if __name__ == "__main__":
    main()

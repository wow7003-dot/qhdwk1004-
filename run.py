#!/usr/bin/env python3
"""AI 롱폼 제작기 CLI.

  python run.py topics                         오늘의 추천 주제 보기
  python run.py auto                           주제 자동 선정 → 영상까지 전부 제작
  python run.py make --topic "주제" --minutes 8
  python run.py make --ref https://youtu.be/xxxx   참고 링크 스타일로 새 영상 제작
  python run.py resume output/폴더 --steps voice images render thumb meta
  python run.py demo                           인터넷 없이 전체 흐름 시험(짧은 영상)
"""
import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from longform import config, pipeline, topics  # noqa: E402
from longform.util import log, setup_logging  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="AI 유튜브 롱폼 제작기")
    ap.add_argument("cmd", choices=["topics", "auto", "make", "resume", "demo"])
    ap.add_argument("path", nargs="?", help="resume 할 프로젝트 폴더")
    ap.add_argument("--topic")
    ap.add_argument("--ref", help="참고할 유튜브/웹 링크")
    ap.add_argument("--minutes", type=float)
    ap.add_argument("--niche")
    ap.add_argument("--voice")
    ap.add_argument("--draft", action="store_true", help="720p 빠른 렌더(테스트용)")
    ap.add_argument("--steps", nargs="+", choices=pipeline.STEPS, help="실행할 단계만 지정")
    ap.add_argument("--until", choices=pipeline.STEPS, help="이 단계까지만 (예: script 로 대본 검토 후 resume)")
    a = ap.parse_args()

    setup_logging()
    cfg = config.load()
    if a.minutes:
        cfg["minutes"] = a.minutes
    if a.niche:
        cfg["niche"] = a.niche
    if a.voice:
        cfg["tts"]["voice"] = a.voice
    if a.draft:
        cfg["video"]["quality"] = "draft"

    if a.cmd == "topics":
        for i, t in enumerate(topics.suggest(cfg, 8), 1):
            print(f"{i}. {t['topic']}\n   후킹: {t['hook']}\n   이유: {t['why']}")
        return

    steps = a.steps
    if a.until:
        steps = pipeline.STEPS[: pipeline.STEPS.index(a.until) + 1]

    if a.cmd == "resume":
        p = pipeline.Project(a.path, cfg)
        if not p.state:
            sys.exit("project.json 이 없는 폴더입니다.")
        pipeline.run(p, steps or pipeline.STEPS[2:])
        return

    if a.cmd == "demo":
        cfg["minutes"] = 1
        cfg["video"]["quality"] = "draft"
        cfg["llm"]["providers"] = []
        cfg["tts"]["providers"] = ["edge", "gtts", "espeak"]
        cfg["image"]["providers"] = ["placeholder"]
        p = pipeline.Project.create("데모 영상 - 로마 제국은 왜 멸망했을까", cfg)
        pipeline.run(p, steps)
        return

    topic = a.topic
    if a.cmd == "auto" or (not topic and not a.ref):
        topic = topics.pick(cfg)
        log.info(f"[주제] 자동 선정: {topic}")
    if a.ref and not topic:
        topic = "참고 링크 기반 영상"
    p = pipeline.Project.create(topic, cfg, a.ref)
    if a.ref and topic == "참고 링크 기반 영상":
        # 참고 영상 제목을 주제로 사용
        from longform import reference
        r = reference.fetch(a.ref)
        if r["title"]:
            p.state["topic"] = f"{r['title']} (새 관점으로 재구성)"
            p.save()
    pipeline.run(p, steps)


if __name__ == "__main__":
    main()

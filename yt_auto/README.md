# AI 유튜브 자동화 파이프라인
주제 입력 → Claude 대본 → edge-tts 나레이션 → Pexels B롤 → ffmpeg 자막 합성 → 썸네일 → (선택) 업로드

    pip install -r requirements.txt && cp .env.example .env  # 키 입력 후 export
    python main.py "주제" --minutes 8
    python main.py "테스트" --dry-run   # API 없이 렌더링 점검
수익화(YPP)는 구독자 1,000명+시청 4,000시간 필요. AI 음성·스톡 영상만 반복 생산하는 "재사용 콘텐츠"는 수익화 거절 위험이 있으니 대본·편집에 독창성을 더하세요.

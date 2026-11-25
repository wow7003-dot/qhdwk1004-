# 🎬 AI 유튜브 롱폼 공장

**주제만 넣거나 대본만 넣으면** 대본 → 장면 분할 → AI 이미지 → AI 음성 → 자막 → 편집(줌/이동 효과, BGM) → 썸네일 → 업로드용 제목/설명/챕터/태그까지 자동으로 만들어 주는 프로그램입니다.
**모든 단계에 무료 도구만** 씁니다.

## 단계별 무료 도구

| 단계 | 기본 도구 | 비용 | 대안 |
|---|---|---|---|
| 대본·이미지 프롬프트·제목 | **Google Gemini API** (무료 티어) | 무료 키 | **Ollama**: 내 PC에서 돌리는 완전 무료·무제한 LLM (qwen2.5, gemma3 등) |
| 이미지 | **Pollinations.ai** (FLUX 모델) | 키 없이 사용 가능(느림). 무료 키를 넣으면 더 빠름 | Hugging Face FLUX.1-schnell(무료 토큰), Pexels·Pixabay 무료 스톡 사진 |
| 음성(TTS) | **Microsoft Edge TTS** (`edge-tts`) | 키 필요 없음 | 한국어 목소리: 인준, 현수, 선희 |
| 자막 | TTS 문장 타이밍으로 자동 싱크 | 무료 | 영상에 바로 입히고 `.srt` 파일도 따로 저장 |
| 편집·렌더링 | **FFmpeg** | 무료 | 켄번스 줌/이동 효과, 장면 이어붙이기, BGM 믹스 |
| 썸네일 | Pillow + Pretendard 폰트(무료 OFL) | 무료 | 흰색/노란색 큰 글씨에 두꺼운 테두리 |
| BGM | 직접 업로드 | 무료 | YouTube 오디오 보관함, Pixabay Music |

> 한 가지라도 실패하면 다음 무료 소스로 자동으로 넘어갑니다. 이미지가 모두 실패하면 단색 배경을 넣고, 나중에 그 장면만 🔄 버튼으로 다시 만들 수 있어요.

## 📱 핸드폰에서 쓰기 (PC 없이, 무료)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/wow7003-dot/qhdwk1004-/blob/main/ytfactory/colab.ipynb)

1. 핸드폰 크롬에서 위 **Open in Colab** 버튼을 누르고 구글 계정으로 로그인하세요.
2. **① 준비 → ② 설정 → ③ 간단 모드** 순서로 각 칸의 ▶를 누르세요. ③ 대신 **④ 화면 모드**를 쓰면 PC와 똑같은 화면이 열립니다.
3. 결과물은 구글 드라이브 `내 드라이브/유튜브공장` 폴더에 저장돼요.

> 만드는 동안 화면을 오래 끄면 무료 코랩이 끊길 수 있어요.

**PC를 켜둔 채 핸드폰으로 조작**할 수도 있어요. PC에서 실행하면 나오는 `Network URL`(http://192.168.x.x:8501)을 같은 와이파이에 연결된 핸드폰 브라우저에 입력하세요. 첫 실행 때 Windows 방화벽 창이 뜨면 "허용"을 누르세요.

## 다운로드

1. https://github.com/wow7003-dot/qhdwk1004- 에서 초록색 **`<> Code` → Download ZIP**을 누르세요.
2. 받은 ZIP 파일을 우클릭해서 **압축 풀기** → `ytfactory` 폴더로 들어가세요.

## 설치 (처음 한 번)

1. **Python 3.10 이상**을 설치하세요. Windows에서는 설치할 때 "Add to PATH"를 체크하세요.
2. **FFmpeg**를 설치하세요.
   - Windows: `run_windows.bat`가 없으면 자동으로 설치합니다(`winget install Gyan.FFmpeg`).
   - Mac: `brew install ffmpeg`
3. 무료 키를 발급하세요. 선택 사항이지만 추천합니다.
   - Gemini: https://aistudio.google.com/apikey (구글 로그인만 하면 됨)
   - Pollinations: https://enter.pollinations.ai (이미지 생성이 빨라짐)

## 실행

- Windows: `run_windows.bat` 더블클릭
- Mac/Linux: `./run_mac_linux.sh`

브라우저에 프로그램 화면이 열립니다.

1. **왼쪽 ⚙️ 설정**에 Gemini 키를 넣고 💾 저장을 누르세요.
2. **① 기획**에서 주제(또는 대본), 길이, 그림 스타일을 고른 뒤 🚀 기획 시작을 누르세요.
3. **② 장면 편집**에서 내레이션과 이미지 프롬프트, 제목, 썸네일 문구를 고치세요. 이미지는 미리 만들어 보고 마음에 안 들면 🔄로 다시 만들 수 있어요.
4. **③ 영상 만들기**에서 BGM을 넣고(선택) 🎬 버튼을 누르세요. mp4, 썸네일, srt, 업로드 정보를 내려받을 수 있습니다.

결과물은 `projects/날짜_제목/` 폴더에 저장됩니다: `final.mp4`, `thumbnail.jpg`, `subtitles.srt`, `upload_info.txt`

### 명령줄로 실행하기

```bash
python cli.py --topic "조선 최강의 이름 없는 검객" --minutes 10 --style "korean martial arts anime, dark fantasy"
python cli.py --script-file 내대본.txt --bgm bgm.mp3
python cli.py --script-file 내대본.txt --offline   # 네트워크 없이 편집 파이프라인만 테스트
```

## 팁

- **렌더링 속도**: 켄번스 효과를 켜면 10분짜리 영상에 PC 성능에 따라 10~20분 정도 걸립니다. 끄면 훨씬 빨라요.
- **그림 일관성**: AI가 먼저 등장인물과 배경 설정(비주얼 바이블)을 만들고 모든 장면 프롬프트에 반영합니다.
- **무료 한도**: Gemini 무료 티어는 분당·일일 요청 수가 정해져 있습니다. 한도에 걸리면 자동으로 기다렸다가 다시 시도합니다. 정확한 한도는 AI Studio에서 확인하세요.
- **저작권**: Pollinations, Pexels, Pixabay 이미지와 Edge TTS 음성을 상업적으로 쓰기 전에 각 서비스 약관을 확인하세요. 수익화 채널이라면 특히 확인이 필요합니다.

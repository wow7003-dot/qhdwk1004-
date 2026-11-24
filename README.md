# 🎬 AI 유튜브 롱폼 제작기 (무료 / API 키 없이)

주제 선정 → 기획 → 대본 → 목소리 → 이미지 → GIF → BGM → 자막 → 썸네일 → 업로드용 제목·설명·태그까지 한 번에.
참고 링크(유튜브/블로그/기사)를 넣으면 **구조·후킹·말투를 분석해서 비슷한 느낌으로, 내용은 새로** 만듭니다.

## 쓰는 무료 서비스 (전부 키 불필요)
| 단계 | 기본 | 실패 시 자동 대체 |
|---|---|---|
| 대본/기획 LLM | Pollinations 텍스트 | Gemini·Groq 무료키(선택) → 템플릿 |
| 주제 | 구글 트렌드(KR) + 위키 인기문서 + LLM | 내장 주제 목록 |
| 목소리 | edge-tts (MS 신경망 한국어 음성) | gTTS → espeak → 무음 |
| 이미지 | Pollinations (flux) | AI Horde(익명) → `assets/images` → 그라데이션 배경 |
| GIF | 자체 제작 팝업 GIF + 완성 영상 미리보기 GIF | Giphy 무료키(선택), `assets/gifs` 폴더 |
| BGM | 코드로 직접 합성(저작권 무관) | `assets/music` 에 mp3 넣으면 그걸 우선 사용 |
| 자막 | 장면 길이에 맞춰 자동 분할 → 영상에 입힘 + `subtitles.srt` | |
| 썸네일 | 1280x720 3종(A/B 테스트용) | |

## 설치 (Windows)
1. Python 3.10+ 설치 (https://www.python.org/downloads/ — **Add to PATH 체크**)
2. `설치.bat` 더블클릭 (ffmpeg 와 라이브러리 자동 설치)
3. `실행.bat` 더블클릭 → 브라우저에 UI가 열립니다.

macOS/Linux: `brew install ffmpeg`(또는 apt) → `pip install -r requirements.txt` → `streamlit run app.py`

## 명령어로 쓰기
```
python run.py topics                              # 오늘의 추천 주제
python run.py auto                                # 주제 자동 선정 → 영상까지
python run.py make --topic "로마는 왜 멸망했나" --minutes 8
python run.py make --ref https://youtu.be/XXXX    # 참고 링크 스타일로
python run.py make --topic "..." --until script   # 대본까지만 → output/.../script.md 검토
python run.py resume output/폴더 --steps voice images render thumb meta
python run.py demo                                # 인터넷 없이 전체 흐름 시험
```
결과는 `output/날짜-제목/` 에: `final.mp4`, `thumbnails/`, `subtitles.srt`, `preview.gif`, `script.md`, `upload_info.txt`.
중간에 실패해도 같은 폴더에서 `resume` 하면 **된 부분은 건너뛰고** 이어갑니다.
처음엔 `--draft`(720p)로 짧게(`--minutes 2`) 돌려 품질을 확인하세요. 8분 1080p 는 PC 사양에 따라 10~30분 걸립니다.

## 선택: 무료 키를 넣으면 더 안정적
`config.example.json` 을 `config.json` 으로 복사해 `keys` 에 입력 (또는 환경변수 `GEMINI_API_KEY`, `GROQ_API_KEY`, `GIPHY_API_KEY`).
Pollinations 가 막히거나 느릴 때 Gemini(aistudio.google.com) / Groq(console.groq.com) 무료 키가 백업이 됩니다. 키 발급은 본인 계정이 필요해서 제가 대신 만들 수는 없습니다.

## 폰트·음악·GIF 직접 넣기
- `assets/fonts/` 한글 .ttf (없으면 윈도우 맑은고딕 → 나눔고딕 자동 다운로드)
- `assets/music/` mp3 (유튜브 오디오 라이브러리 등 상업 이용 가능한 곡)
- `assets/gifs/` gif (파일명에 키워드 포함 시 해당 장면에 사용)

## 꼭 알아둘 점
- 참고 링크는 **분석용**입니다. 다른 사람 영상의 대본·이미지를 그대로 쓰면 저작권 문제가 됩니다. 이 도구는 새 대본을 쓰도록 설계돼 있습니다.
- AI 음성/이미지는 유튜브 스튜디오의 "변경되거나 합성된 콘텐츠" 공개 항목에 해당할 수 있습니다. 반복적·대량 재활용 콘텐츠는 수익화 심사에서 불리하므로 `script.md` 를 직접 훑어 사실 확인·다듬기를 권장합니다.
- LLM 이 만든 사실은 틀릴 수 있습니다(연도·수치 확인).
- 이미지에 글자가 들어가면 깨지므로 프롬프트에서 글자를 금지했습니다. 강조 문구는 GIF 팝업으로 넣습니다.

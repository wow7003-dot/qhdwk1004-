---
name: stock-footage
description: 유튜브 롱폼 영상용 무료·상업 이용 가능한 B롤/영상/GIF/효과음/BGM 소스를 Pexels, Pixabay, Mixkit, Coverr에서 찾아 추천한다. "B롤 찾아줘", "영상 소스", "스톡 영상", "배경 영상", "무료 영상 찾아줘", "효과음/BGM 찾아줘", "/stock-footage" 같은 요청에 사용.
---

# 스톡 영상 소스 찾기 (유튜브 롱폼용)

사용자는 **유튜브 롱폼(수익화) 영상**을 만든다. 저작권 문제가 없는 소스만 추천한다.
GIPHY/Tenor의 영화·드라마·예능 짤은 Content ID 위험이 있으니 추천하지 않는다.

## 사용 사이트 (모두 무료, 상업 이용 가능, 출처 표기 불필요)

| 사이트 | 강점 | 검색 URL 형식 |
|---|---|---|
| Pexels Videos | 고화질 실사 영상, 무제한 | `https://www.pexels.com/search/videos/{영문키워드}/` |
| Pixabay | 영상·GIF·이미지·효과음·BGM | 영상 `https://pixabay.com/videos/search/{키워드}/` · 음악 `https://pixabay.com/music/search/{키워드}/` · 효과음 `https://pixabay.com/sound-effects/search/{키워드}/` |
| Mixkit | 영상 템플릿, 트랜지션, 효과 | `https://mixkit.co/free-stock-video/{키워드}/` |
| Coverr | 배경용 감성 영상 | `https://coverr.co/s?q={키워드}` |

## 작업 순서

1. 사용자의 요청(대본, 장면 설명, 주제)에서 장면별로 필요한 영상을 뽑는다.
2. 각 장면마다 **영문 검색 키워드 2~3개**를 만든다. 스톡 사이트는 영어 검색 결과가 훨씬 많다.
   - 예: "출근길 지친 직장인" → `tired office worker`, `morning commute`, `subway crowd`
3. 장면에 맞는 사이트를 고른다.
   - 실사 B롤 → Pexels, Pixabay
   - 배경이나 분위기용 영상 → Coverr
   - 트랜지션이나 효과 → Mixkit
   - 효과음, BGM → Pixabay Music / Sound Effects
4. 아래 형식으로 결과를 정리한다. 키워드는 URL에 넣을 때 공백을 `-`(Pexels, Pixabay, Mixkit) 또는 `%20`(Coverr)으로 바꾼다.

```
### 장면 1: {장면 설명}
- 키워드: tired office worker, morning commute
- Pexels: https://www.pexels.com/search/videos/tired-office-worker/
- Pixabay: https://pixabay.com/videos/search/morning-commute/
- 팁: 세로 영상 말고 가로(Landscape) 필터, 4K/HD 선택
```

5. 마지막에 BGM과 효과음 추천 검색 링크를 1~3개 덧붙인다.

## 주의사항 (항상 짧게 안내)
- 다운로드할 때 **가로(16:9) 영상과 HD 이상**을 고른다.
- 영상 속 사람 얼굴이나 로고가 크게 나오는 장면은 썸네일에 쓰지 않는다.
- 각 사이트 라이선스는 바뀔 수 있으니, 수익화 전에 해당 영상 페이지의 라이선스를 한 번 확인한다.
- 답변은 한국어로 한다.

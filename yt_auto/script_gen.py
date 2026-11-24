"""주제 -> 장면별 대본(JSON). 장면 = {narration, keywords(영문 스톡영상 검색어)}"""
import json, re

from config import MODEL

PROMPT = """너는 한국어 유튜브 롱폼 채널 작가다. 주제: "{topic}"
목표 길이: 약 {minutes}분. 첫 15초 안에 시청자를 붙잡는 훅, 본론 3~5개 파트, 요약과 구독 유도 마무리.
JSON만 출력:
{{"title":"클릭을 부르는 제목(40자 이내)","description":"설명(해시태그 포함)","tags":["태그"],
"thumbnail_text":"썸네일 문구(12자 이내)",
"scenes":[{{"narration":"구어체 나레이션 1~3문장","keywords":"영문 B-roll 검색어 2~3단어"}}]}}
장면은 {n}개 내외, 각 나레이션은 10~25초 분량."""

def generate(topic: str, minutes: int = 8) -> dict:
    n = minutes * 60 // 15
    import anthropic
    msg = anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=8000,
        messages=[{"role": "user", "content": PROMPT.format(topic=topic, minutes=minutes, n=n)}])
    text = msg.content[0].text
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))

def sample(topic: str) -> dict:  # 오프라인 테스트용
    return {"title": topic, "description": "#test", "tags": ["test"], "thumbnail_text": "테스트",
            "scenes": [{"narration": f"{topic} 첫 번째 장면입니다.", "keywords": "city"},
                       {"narration": "두 번째 장면입니다. 구독과 좋아요 부탁드려요.", "keywords": "nature"}]}

"""주제 자동 선정: 구글 트렌드(KR) + 위키백과 인기문서 + LLM 으로 롱폼용 주제 제안. 모두 무료/무키."""
import datetime as dt
import random
import re

from .llm import chat_json
from .util import http, log

EVERGREEN = [
    "로마 제국은 왜 멸망했을까? 우리가 몰랐던 진짜 이유",
    "블랙홀 안으로 들어가면 실제로 벌어지는 일",
    "역사상 가장 미스터리한 실종 사건 5가지",
    "인플레이션의 진짜 원인: 돈이 사라지는 구조",
    "잠을 못 자면 우리 뇌에서 벌어지는 일",
    "타이타닉 침몰 직전 선내에서 일어난 일들",
    "인류가 아직도 풀지 못한 수학 난제들",
    "심해 1만 미터 아래에는 무엇이 살고 있을까",
    "세계 최강 스파이 조직들의 숨겨진 이야기",
    "AI가 바꿀 10년 뒤 직업 지도",
]


def google_trends(geo="KR", n=15):
    try:
        xml = http("GET", f"https://trends.google.com/trending/rss?geo={geo}", retries=1).text
        titles = re.findall(r"<item>.*?<title>(.*?)</title>", xml, flags=re.S)
        return [re.sub(r"<!\[CDATA\[|\]\]>", "", t).strip() for t in titles][:n]
    except Exception as e:  # noqa: BLE001
        log.info(f"[주제] 구글 트렌드 실패: {str(e)[:80]}")
        return []


def wiki_top(lang="ko", n=15):
    day = dt.date.today() - dt.timedelta(days=2)
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{day:%Y/%m/%d}"
    try:
        items = http("GET", url, retries=1).json()["items"][0]["articles"]
        bad = ("특수:", "위키백과:", "대문", "Special:", "Main_Page", "분류:", "파일:")
        return [a["article"].replace("_", " ") for a in items if not a["article"].startswith(bad)][:n]
    except Exception as e:  # noqa: BLE001
        log.info(f"[주제] 위키 인기문서 실패: {str(e)[:80]}")
        return []


def suggest(cfg, n=5):
    """[{topic, hook, why}] 반환. 네트워크/LLM 이 전부 실패해도 기본 주제로 동작."""
    trends = google_trends() + wiki_top()
    log.info(f"[주제] 트렌드 키워드 {len(trends)}개 수집")
    prompt = (
        f"유튜브 롱폼({cfg['minutes']}분) 채널 기획자로서 주제를 {n}개 제안해줘.\n"
        f"채널 분야: {cfg['niche']}\n오늘의 트렌드 키워드(참고용, 분야와 맞는 것만 활용): {', '.join(trends[:25]) or '없음'}\n"
        "조건: 클릭을 부르는 구체적인 제목형 주제, 사실 기반(허위/논란성 인물 비방 금지), 8분 이상 풀 수 있는 깊이.\n"
        'JSON 형식: {"topics":[{"topic":"제목형 주제","hook":"첫 문장 후킹","why":"추천 이유 한 줄"}]}'
    )
    data = chat_json(prompt, cfg)
    out = []
    if isinstance(data, dict):
        for t in data.get("topics", []):
            if isinstance(t, dict) and t.get("topic"):
                out.append({"topic": t["topic"], "hook": t.get("hook", ""), "why": t.get("why", "")})
    if not out:
        pool = random.sample(EVERGREEN, min(n, len(EVERGREEN)))
        out = [{"topic": t, "hook": "", "why": "기본 추천 주제(오프라인)"} for t in pool]
    return out[:n]


def pick(cfg):
    return suggest(cfg, 5)[0]["topic"]

"""참고 링크 분석: 유튜브(자막+제목) 또는 일반 웹페이지 → 구조/후킹/톤 분석.
분석은 '스타일과 구조를 참고'하는 용도이며, 대본은 항상 새로 쓰도록 프롬프트에서 강제한다."""
import html
import re

from .llm import chat_json
from .util import http, log


def yt_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    return m.group(1) if m else None


def _transcript(vid):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        log.info("[참고] youtube-transcript-api 미설치 → 자막 없이 진행")
        return []
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            return [(s.start, s.duration, s.text) for s in api.fetch(vid, languages=["ko", "en"])]
        return [(s["start"], s["duration"], s["text"]) for s in YouTubeTranscriptApi.get_transcript(vid, languages=["ko", "en"])]
    except Exception as e:  # noqa: BLE001
        log.info(f"[참고] 자막 가져오기 실패: {str(e)[:100]}")
        return []


def fetch(url):
    """{kind,title,text,stats}"""
    ref = {"url": url, "kind": "web", "title": "", "text": "", "stats": {}}
    vid = yt_id(url)
    if vid:
        ref["kind"] = "youtube"
        try:
            ref["title"] = http("GET", "https://www.youtube.com/oembed", params={"url": url, "format": "json"}, retries=1).json().get("title", "")
        except Exception:  # noqa: BLE001
            pass
        segs = _transcript(vid)
        if segs:
            ref["text"] = " ".join(html.unescape(s[2]).replace("\n", " ") for s in segs)
            total = segs[-1][0] + segs[-1][1]
            ref["stats"] = {"minutes": round(total / 60, 1), "chars_per_min": int(len(ref["text"]) / max(total / 60, 0.1))}
        return ref
    try:
        raw = http("GET", url, retries=1).text
        ref["title"] = html.unescape((re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I) or [None, ""])[1]).strip()
        raw = re.sub(r"<(script|style|noscript)[\s\S]*?</\1>", " ", raw, flags=re.I)
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        ref["text"] = re.sub(r"\s+", " ", text).strip()
    except Exception as e:  # noqa: BLE001
        log.info(f"[참고] 페이지 읽기 실패: {str(e)[:100]}")
    return ref


def analyze(ref, cfg):
    if not ref.get("text") and not ref.get("title"):
        return None
    prompt = (
        "다음은 참고용 유튜브/웹 콘텐츠의 제목과 본문(또는 자막)이다. 이 콘텐츠가 '왜 잘 먹히는지'를 분석해줘.\n"
        f"제목: {ref.get('title')}\n통계: {ref.get('stats')}\n본문 일부:\n{ref['text'][:9000]}\n\n"
        "JSON으로만 답해: {\"summary\":\"내용 요약 3줄\",\"hook_style\":\"도입부 후킹 방식\","
        "\"structure\":[\"전개 순서 단계들\"],\"tone\":\"말투/분위기\",\"pace\":\"전개 속도와 리듬\","
        "\"key_points\":[\"핵심 정보들\"],\"improve\":[\"더 낫게 만들 지점\"]}"
    )
    return chat_json(prompt, cfg)

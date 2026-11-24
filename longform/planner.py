"""기획(제목/챕터/스타일) → 챕터별 대본(장면 단위: 나레이션 + 이미지 프롬프트 + 강조문구)."""
import re

from .llm import chat_json
from .util import log

CHARS_PER_MIN = 330   # 한국어 TTS 기준 분당 글자 수(공백 포함) 대략값
SCENE_CHARS = 95      # 한 장면(이미지 1장) 나레이션 목표 글자 수


def _ref_block(analysis):
    if not analysis:
        return ""
    return (
        "\n[참고 영상 분석 — 구조·호흡·후킹 방식만 참고하고, 문장/표현/내용은 절대 그대로 쓰지 말고 완전히 새로 쓸 것]\n"
        f"후킹: {analysis.get('hook_style')}\n전개: {analysis.get('structure')}\n말투: {analysis.get('tone')}\n"
        f"속도: {analysis.get('pace')}\n개선점: {analysis.get('improve')}\n"
    )


def make_plan(topic, cfg, analysis=None):
    minutes = cfg["minutes"]
    n_ch = max(3, min(8, round(minutes / 1.6)))
    prompt = (
        f"유튜브 롱폼 영상 기획서를 만들어줘. 주제: {topic}\n분량: 약 {minutes}분, 챕터 {n_ch}개. 한국어.{_ref_block(analysis)}\n"
        "규칙: 사실에 기반, 과장/허위 금지, 실존 인물 비방 금지. 챕터는 호기심을 이어가는 흐름(도입-전개-반전-정리).\n"
        'JSON만 답해: {"title":"클릭을 부르는 제목(40자 이내)","title_alternatives":["대안 제목 3개"],'
        '"hook":"첫 30초 후킹 2~3문장","thumbnail_text":"썸네일 문구(2줄, 줄당 8자 내외, 줄바꿈은 \\n)",'
        '"chapters":[{"title":"챕터 제목","summary":"이 챕터에서 다룰 내용 2문장"}],'
        '"visual_style":"일관된 이미지 스타일을 설명하는 영어 문구","music_mood":"calm|epic|mystery|upbeat|sad 중 하나",'
        '"tags":["태그 10개"],"description":"영상 설명 3문장"}'
    )
    plan = chat_json(prompt, cfg)
    if not (isinstance(plan, dict) and plan.get("chapters")):
        log.info("[기획] LLM 사용 불가 → 오프라인 템플릿 기획 사용 (품질 낮음, 네트워크 확인 필요)")
        plan = offline_plan(topic, n_ch)
    plan.setdefault("title", topic)
    plan.setdefault("title_alternatives", [])
    plan.setdefault("thumbnail_text", topic[:8] + "\n" + topic[8:16])
    plan.setdefault("visual_style", cfg["image"]["style"])
    plan.setdefault("music_mood", "calm")
    plan.setdefault("tags", [])
    plan.setdefault("description", "")
    return plan


def offline_plan(topic, n_ch):
    names = ["도입: 문제 제기", "배경 이야기", "핵심 사건", "반전과 진실", "우리에게 남은 의미", "마무리"]
    return {
        "title": topic, "title_alternatives": [], "hook": f"{topic}. 오늘은 이 이야기를 깊이 파헤쳐 봅니다.",
        "thumbnail_text": topic[:8] + "\n" + topic[8:16] if len(topic) > 8 else topic,
        "chapters": [{"title": names[i % len(names)], "summary": f"{topic} — {names[i % len(names)]}"} for i in range(n_ch)],
        "visual_style": "cinematic illustration, dramatic lighting", "music_mood": "mystery", "tags": [], "description": "",
    }


def clean_narration(t):
    t = re.sub(r"[*_#`>\[\]]", "", t or "")
    t = re.sub(r"[\U0001F000-\U0001FFFF☀-➿]", "", t)   # 이모지 제거(TTS 오독 방지)
    return re.sub(r"\s+", " ", t).strip()


def write_chapter(plan, idx, cfg, analysis=None, prev_tail=""):
    chs = plan["chapters"]
    ch = chs[idx]
    total_chars = cfg["minutes"] * CHARS_PER_MIN
    target = int(total_chars / len(chs))
    n_scenes = max(3, round(target / SCENE_CHARS))
    first, last = idx == 0, idx == len(chs) - 1
    extra = ""
    if first:
        extra += f"- 이 챕터는 영상의 시작이다. 첫 장면은 이 후킹으로 시작: {plan.get('hook')}\n"
    if last:
        extra += "- 마지막 챕터다. 핵심 요약 후 시청자에게 의견을 묻고, 마지막 문장에서만 가볍게 구독/좋아요를 부탁한다.\n"
    prompt = (
        f"영상 제목: {plan['title']}\n전체 챕터: {[c['title'] for c in chs]}\n"
        f"지금 쓸 챕터 ({idx + 1}/{len(chs)}): {ch['title']} — {ch.get('summary')}\n"
        f"이전 챕터 마지막 나레이션(자연스럽게 이어받기): {prev_tail or '없음'}\n{_ref_block(analysis)}{extra}"
        f"요구: 나레이션 총 약 {target}자, 장면 {n_scenes}개. 장면당 나레이션은 1~2문장({SCENE_CHARS}자 안팎), 구어체 존댓말, 읽었을 때 자연스러운 문장.\n"
        "이모지/마크다운/괄호 지시문 금지. 숫자·고유명사는 정확하게(모르면 단정하지 말 것). 'callout'은 화면에 띄울 핵심 키워드 12자 이내(없으면 빈 문자열, 장면의 1/3 정도만 채움).\n"
        "image_prompt는 영어, 장면을 구체적으로 묘사. 글자/로고/워터마크 없는 이미지, 실존 인물 얼굴 지정 금지. "
        f"스타일은 항상: {plan.get('visual_style')}\n"
        'JSON만: {"scenes":[{"narration":"...","image_prompt":"...","callout":"","gif_keyword":"영어 한 단어 리액션 키워드(없으면 빈 문자열)"}]}'
    )
    data = chat_json(prompt, cfg)
    scenes = []
    if isinstance(data, dict):
        for s in data.get("scenes", []):
            n = clean_narration(s.get("narration"))
            if n:
                scenes.append({"narration": n, "image_prompt": s.get("image_prompt") or f"{plan['title']}, {ch['title']}",
                               "callout": (s.get("callout") or "")[:14], "gif_keyword": s.get("gif_keyword", "")})
    if not scenes:
        log.info(f"[대본] 챕터 {idx + 1} LLM 실패 → 템플릿 장면 사용")
        scenes = offline_scenes(plan, ch, n_scenes)
    for s in scenes:
        s["chapter"] = idx
    return scenes


def offline_scenes(plan, ch, n):
    out = []
    for i in range(n):
        out.append({
            "narration": f"{ch['title']}, 그 {i + 1}번째 이야기입니다. {plan['title']}에 대해 조금 더 깊이 들어가 보겠습니다.",
            "image_prompt": f"{plan['title']}, {ch['title']}, scene {i + 1}, {plan.get('visual_style', '')}",
            "callout": ch["title"][:10] if i == 0 else "", "gif_keyword": "",
        })
    return out


def write_script(plan, cfg, analysis=None, progress=None):
    scenes = []
    for i in range(len(plan["chapters"])):
        if progress:
            progress("대본", i / len(plan["chapters"]), f"챕터 {i + 1}/{len(plan['chapters'])} 작성 중")
        tail = scenes[-1]["narration"] if scenes else ""
        scenes += write_chapter(plan, i, cfg, analysis, tail)
    return scenes

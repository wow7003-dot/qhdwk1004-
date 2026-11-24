"""무료 LLM 호출. 키 없이 되는 Pollinations → (선택) Gemini/Groq 무료 키 → 실패 시 None."""
import json
import re
import urllib.parse

from .util import http, log


def _pollinations(prompt, system, json_mode, cfg):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    try:
        r = http("POST", "https://text.pollinations.ai/openai", retries=1, timeout=(6, 150),
                 json={"model": "openai", "messages": msgs, "private": True,
                       **({"response_format": {"type": "json_object"}} if json_mode else {})})
        return r.json()["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001  구형 GET 엔드포인트로 재시도
        q = urllib.parse.quote(prompt[:6000])
        r = http("GET", f"https://text.pollinations.ai/{q}", retries=0, timeout=(6, 150),
                 params={"model": "openai", "system": system or "", "private": "true"})
        return r.text


def _gemini(prompt, system, json_mode, cfg):
    key = cfg["keys"].get("gemini")
    if not key:
        raise RuntimeError("no key")
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    m = cfg["llm"]["gemini_model"]
    r = http("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
             params={"key": key}, json=body, timeout=(6, 150))
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt, system, json_mode, cfg):
    key = cfg["keys"].get("groq")
    if not key:
        raise RuntimeError("no key")
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    r = http("POST", "https://api.groq.com/openai/v1/chat/completions", timeout=(6, 150),
             headers={"Authorization": f"Bearer {key}"},
             json={"model": cfg["llm"]["groq_model"], "messages": msgs,
                   **({"response_format": {"type": "json_object"}} if json_mode else {})})
    return r.json()["choices"][0]["message"]["content"]


PROVIDERS = {"pollinations": _pollinations, "gemini": _gemini, "groq": _groq}


def chat(prompt, cfg, system="", json_mode=False):
    for name in cfg["llm"]["providers"]:
        fn = PROVIDERS.get(name)
        if not fn:
            continue
        if name in ("gemini", "groq") and not cfg["keys"].get(name):
            continue
        try:
            out = fn(prompt, system, json_mode, cfg)
            if out and out.strip():
                return out.strip()
        except Exception as e:  # noqa: BLE001
            log.info(f"[LLM:{name}] 실패: {str(e)[:120]}")
    return None


def extract_json(text):
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    for cand in (text, text[text.find("{"): text.rfind("}") + 1], text[text.find("["): text.rfind("]") + 1]):
        try:
            return json.loads(cand)
        except Exception:  # noqa: BLE001
            continue
    return None


def chat_json(prompt, cfg, system="", tries=2):
    for _ in range(tries):
        data = extract_json(chat(prompt, cfg, system, json_mode=True))
        if data is not None:
            return data
    return None

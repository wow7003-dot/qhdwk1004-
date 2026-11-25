"""무료 LLM 호출: Google Gemini(무료 티어 API 키) 또는 로컬 Ollama."""
import json
import re
import time

import requests

from .config import Settings


class LLMError(RuntimeError):
    pass


def _gemini(s: Settings, prompt: str, json_mode: bool) -> str:
    """스트리밍으로 받는다: 긴 대본도 중간중간 데이터가 와서 '시간 초과'가 나지 않음."""
    if not s.gemini_api_key:
        raise LLMError("Gemini API 키가 없습니다. https://aistudio.google.com/apikey 에서 무료로 발급하세요.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:streamGenerateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 16384},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    last = None
    for attempt in range(4):
        try:
            with requests.post(url, params={"key": s.gemini_api_key, "alt": "sse"}, json=body,
                               stream=True, timeout=(20, 300)) as r:
                if r.status_code == 429 or r.status_code >= 500:  # 무료 티어 분당 제한 → 잠시 대기 후 재시도
                    last = f"{r.status_code} {r.text[:300]}"
                    time.sleep(20 * (attempt + 1))
                    continue
                if r.status_code == 404:
                    raise LLMError(f"모델 '{s.gemini_model}' 을 찾을 수 없습니다. 설정에서 모델 이름을 "
                                   "'gemini-flash-latest' 또는 AI Studio 에 보이는 이름으로 바꾸세요.")
                if r.status_code != 200:
                    raise LLMError(f"Gemini 오류 {r.status_code}: {r.text[:500]}")
                out = []
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = json.loads(line[5:].strip())
                    for cand in data.get("candidates", []):
                        for part in cand.get("content", {}).get("parts", []):
                            if not part.get("thought"):
                                out.append(part.get("text", ""))
                text = "".join(out)
                if text.strip():
                    return text
                last = "빈 응답"
        except (requests.Timeout, requests.ConnectionError) as e:  # 네트워크 지연 → 재시도
            last = str(e)
            time.sleep(5)
    raise LLMError(f"Gemini 요청 실패 (잠시 후 다시 시도하세요): {last}")


def _ollama(s: Settings, prompt: str, json_mode: bool) -> str:
    body = {"model": s.ollama_model, "prompt": prompt, "stream": False}
    if json_mode:
        body["format"] = "json"
    try:
        r = requests.post(f"{s.ollama_url.rstrip('/')}/api/generate", json=body, timeout=600)
    except requests.RequestException as e:
        raise LLMError(f"Ollama 에 연결할 수 없습니다 ({s.ollama_url}). Ollama 를 설치/실행했는지 확인하세요: {e}")
    if r.status_code != 200:
        raise LLMError(f"Ollama 오류 {r.status_code}: {r.text[:300]}")
    return r.json().get("response", "")


def available(s: Settings) -> bool:
    if s.llm_provider == "gemini":
        return bool(s.gemini_api_key)
    return s.llm_provider == "ollama"


def generate(s: Settings, prompt: str) -> str:
    fn = _ollama if s.llm_provider == "ollama" else _gemini
    return fn(s, prompt, json_mode=False).strip()


def generate_json(s: Settings, prompt: str):
    fn = _ollama if s.llm_provider == "ollama" else _gemini
    text = fn(s, prompt + "\n\n반드시 유효한 JSON 만 출력하세요.", json_mode=True)
    return parse_json(text)


def parse_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            return json.loads(m.group(1))
        raise LLMError(f"JSON 파싱 실패: {text[:300]}")

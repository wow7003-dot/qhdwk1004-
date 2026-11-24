"""Pexels 무료(상업 이용 가능) 영상 검색/다운로드. 실패 시 None -> 단색 배경 사용"""
import os, requests

def fetch(query: str, path: str):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                         params={"query": query, "orientation": "landscape", "per_page": 5}, timeout=20)
        for v in r.json().get("videos", []):
            files = [f for f in v["video_files"] if f["width"] and 1280 <= f["width"] <= 1920]
            if files:
                data = requests.get(files[0]["link"], timeout=60).content
                open(path, "wb").write(data)
                return path
    except Exception as e:
        print("footage 실패:", query, e)
    return None

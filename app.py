"""웹 UI:  streamlit run app.py  (또는 실행.bat 더블클릭)"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from longform import config, pipeline, topics  # noqa: E402
from longform.util import setup_logging  # noqa: E402

setup_logging()
st.set_page_config(page_title="AI 롱폼 제작기", page_icon="🎬", layout="wide")
st.title("🎬 AI 유튜브 롱폼 제작기")

cfg = config.load()
with st.sidebar:
    st.header("설정")
    cfg["minutes"] = st.slider("영상 길이(분)", 2, 20, 8)
    cfg["niche"] = st.text_input("채널 분야", cfg["niche"])
    cfg["tts"]["voice"] = st.selectbox("목소리", ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural", "ko-KR-HyunsuMultilingualNeural"])
    cfg["music"]["mood"] = st.selectbox("배경음악 분위기", ["auto", "calm", "epic", "mystery", "upbeat", "sad"])
    if st.checkbox("빠른 테스트(720p)"):
        cfg["video"]["quality"] = "draft"
    cfg["subtitles"]["enabled"] = st.checkbox("자막 넣기", True)
    cfg["gif"]["callouts"] = st.checkbox("강조 GIF 팝업", True)

tab1, tab2 = st.tabs(["① 주제 · 참고링크", "② 제작 결과"])
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔥 오늘의 추천 주제 불러오기"):
            with st.spinner("트렌드 수집 중..."):
                st.session_state["sug"] = topics.suggest(cfg, 6)
        for t in st.session_state.get("sug", []):
            if st.button(f"➜ {t['topic']}", help=t.get("why", ""), key=t["topic"]):
                st.session_state["topic"] = t["topic"]
        topic = st.text_input("주제 (비워두면 자동 선정)", key="topic")
    with c2:
        ref = st.text_input("참고 링크 (유튜브/블로그/기사, 선택)", placeholder="https://youtu.be/...")
        st.caption("참고 링크는 구조·호흡·후킹만 분석하고, 대본은 새로 씁니다. 그대로 베끼지 않습니다.")
    only_script = st.checkbox("대본까지만 만들고 검토하기(project 폴더의 script.md 수정 후 이어서 제작)")
    if st.button("🚀 제작 시작", type="primary"):
        bar, msg = st.progress(0.0), st.empty()
        steps = pipeline.STEPS
        names = {"기획": 0, "대본": 1, "음성": 2, "이미지": 3, "렌더": 4}

        def progress(stage, frac, text=""):
            base = names.get(stage, 5) / 6
            bar.progress(min(1.0, base + frac / 6))
            msg.write(f"**{stage}** {text}")

        t = topic or topics.pick(cfg)
        p = pipeline.Project.create(t, cfg, ref or None)
        if only_script:
            steps = steps[:2]
        pipeline.run(p, steps, progress)
        st.session_state["proj"] = str(p.dir)
        bar.progress(1.0)
        st.success(f"완료! 폴더: {p.dir}")

with tab2:
    d = st.session_state.get("proj")
    if d and (Path(d) / "final.mp4").exists():
        d = Path(d)
        st.video(str(d / "final.mp4"))
        cols = st.columns(3)
        for i, c in enumerate(cols, 1):
            f = d / "thumbnails" / f"thumbnail_{i}.jpg"
            if f.exists():
                c.image(str(f), caption=f"썸네일 {i}")
        st.text_area("업로드 정보(제목/설명/태그)", (d / "upload_info.txt").read_text(encoding="utf-8"), height=300)
        st.caption(f"저장 위치: {d}")
    else:
        st.info("제작이 끝나면 여기에 결과가 표시됩니다. (output 폴더에도 저장됩니다)")

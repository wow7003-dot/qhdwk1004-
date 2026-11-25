"""AI 유튜브 롱폼 공장 — 대본만 넣으면 영상 뚝딱 (전부 무료 도구).
실행:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from core import pipeline
from core.config import PROJECTS_DIR, load_settings, save_settings
from core.images import make_image
from core.tts import VOICES

st.set_page_config(page_title="AI 유튜브 롱폼 공장", page_icon="🎬", layout="wide")

STYLES = {
    "무협 애니메이션 (어두운 판타지)": "korean martial arts anime style, dark fantasy, snowy mountains, dramatic cinematic lighting, highly detailed digital painting",
    "실사 시네마틱": "photorealistic cinematic film still, 35mm, shallow depth of field, moody lighting, ultra detailed",
    "역사 다큐 (조선/사극)": "joseon dynasty korea historical drama, cinematic, realistic painting, warm candle light",
    "수채화 동화": "soft watercolor storybook illustration, pastel colors, gentle light",
    "3D 애니메이션 (픽사풍)": "3d animated movie style, cute characters, vibrant colors, soft global illumination",
    "미스터리/공포": "dark horror atmosphere, foggy, eerie, cinematic, desaturated, film grain",
    "경제/지식 인포그래픽": "clean modern editorial illustration, flat design, infographic mood, minimal",
    "직접 입력": "",
}

s = load_settings()
if "project" not in st.session_state:
    st.session_state.project = None

# ───────────────────────── 사이드바: 무료 API 설정 ─────────────────────────
with st.sidebar:
    st.header("⚙️ 설정 (전부 무료)")
    with st.expander("🧠 대본 AI", expanded=not s.gemini_api_key):
        s.llm_provider = st.selectbox("AI 엔진", ["gemini", "ollama", "none"],
                                      index=["gemini", "ollama", "none"].index(s.llm_provider),
                                      format_func={"gemini": "Google Gemini (무료 키)", "ollama": "Ollama (내 PC, 완전 무료)",
                                                   "none": "사용 안 함 (대본 직접 입력)"}.get)
        if s.llm_provider == "gemini":
            s.gemini_api_key = st.text_input("Gemini API 키", s.gemini_api_key, type="password",
                                             help="https://aistudio.google.com/apikey 에서 무료 발급")
            s.gemini_model = st.text_input("모델", s.gemini_model)
        elif s.llm_provider == "ollama":
            s.ollama_url = st.text_input("Ollama 주소", s.ollama_url)
            s.ollama_model = st.text_input("모델", s.ollama_model, help="예: qwen2.5:7b, gemma3:12b")
    with st.expander("🖼️ 이미지"):
        opts = ["pollinations", "huggingface", "pexels", "pixabay", "placeholder"]
        s.image_provider = st.selectbox("이미지 소스", opts, index=opts.index(s.image_provider), format_func={
            "pollinations": "Pollinations AI 생성 (키 없이 가능)", "huggingface": "Hugging Face FLUX (무료 토큰)",
            "pexels": "Pexels 스톡 사진", "pixabay": "Pixabay 스톡 사진", "placeholder": "단색 배경 (테스트용)"}.get)
        s.pollinations_key = st.text_input("Pollinations 키 (선택, 더 빠름)", s.pollinations_key, type="password",
                                           help="https://enter.pollinations.ai 무료 가입")
        s.hf_token = st.text_input("Hugging Face 토큰 (선택)", s.hf_token, type="password")
        s.pexels_key = st.text_input("Pexels 키 (선택)", s.pexels_key, type="password")
        s.pixabay_key = st.text_input("Pixabay 키 (선택)", s.pixabay_key, type="password")
    with st.expander("🎙️ 음성 / 🎞️ 영상", expanded=True):
        s.voice = st.selectbox("목소리", list(VOICES), index=list(VOICES).index(s.voice) if s.voice in VOICES else 0,
                               format_func=VOICES.get)
        rate = st.slider("말 빠르기", -30, 50, int(s.rate.strip("%+") or 0), 5)
        s.rate = f"{rate:+d}%"
        s.aspect = st.radio("화면 비율", ["16:9", "9:16"], index=0 if s.aspect == "16:9" else 1, horizontal=True,
                            format_func={"16:9": "16:9 롱폼", "9:16": "9:16 쇼츠"}.get)
        s.ken_burns = st.toggle("켄번스 효과 (천천히 줌/이동)", s.ken_burns, help="끄면 렌더링이 훨씬 빠름")
        s.subtitle_size = st.slider("자막 크기", 40, 100, s.subtitle_size)
        s.bgm_volume = st.slider("BGM 볼륨", 0.0, 0.5, float(s.bgm_volume), 0.01)
    if st.button("💾 설정 저장", use_container_width=True):
        save_settings(s)
        st.success("저장됨 (config.json)")

    st.divider()
    olds = sorted([p for p in PROJECTS_DIR.glob("*/project.json")], reverse=True) if PROJECTS_DIR.exists() else []
    pick = st.selectbox("📂 이전 프로젝트 열기", ["—"] + [p.parent.name for p in olds])
    if pick != "—" and st.button("불러오기", use_container_width=True):
        st.session_state.project = pipeline.load(PROJECTS_DIR / pick)
        st.rerun()

st.title("🎬 AI 유튜브 롱폼 공장")
st.caption("대본 → 장면 분할 → AI 이미지 → AI 음성 → 자막 → 편집 → 썸네일까지 자동으로 만듭니다. 모두 무료 도구만 사용해요.")

tab1, tab2, tab3 = st.tabs(["① 기획 (대본)", "② 장면 편집", "③ 영상 만들기"])

# ───────────────────────── ① 기획 ─────────────────────────
with tab1:
    mode = st.radio("시작 방법", ["주제만 입력 → AI 가 대본 작성", "내 대본 붙여넣기"], horizontal=True)
    c1, c2 = st.columns(2)
    topic = c1.text_input("주제 / 영상 제목 아이디어", placeholder="예: 조선 최강의 이름 없는 검객 이야기")
    minutes = c2.slider("목표 길이 (분)", 1, 40, 10)
    tone = c1.text_input("분위기 / 장르", "몰입감 있는 스토리텔링, 긴장감")
    style_name = c2.selectbox("그림 스타일", list(STYLES))
    style = STYLES[style_name] or c2.text_input("스타일 (영어 권장)", "cinematic digital painting")
    extra = ""
    script_text = ""
    if mode.startswith("주제"):
        extra = st.text_area("추가 요청 (선택)", placeholder="예: 반전 결말, 1인칭 시점, 초반 30초에 사건 발생")
    else:
        script_text = st.text_area("대본", height=300, placeholder="여기에 대본을 붙여넣으세요. 문단마다 빈 줄을 넣으면 좋아요.")

    if st.button("🚀 기획 시작", type="primary"):
        bar = st.progress(0.0, "시작…")
        try:
            st.session_state.project = pipeline.plan(
                s, topic=topic, script_text=script_text, minutes=minutes, tone=tone, style=style, extra=extra,
                progress=lambda p, m: bar.progress(min(p, 1.0), m))
            st.success("기획 완료! ② 장면 편집 탭에서 확인/수정하세요.")
        except Exception as e:
            st.error(str(e))

    pj = st.session_state.project
    if pj:
        st.subheader("📜 대본")
        st.text_area("생성된 대본 (수정은 ② 탭의 장면에서)", pj["script"], height=250, disabled=True)

# ───────────────────────── ② 장면 편집 ─────────────────────────
with tab2:
    pj = st.session_state.project
    if not pj:
        st.info("먼저 ① 기획을 진행하세요.")
    else:
        meta = pj.setdefault("meta", {})
        c1, c2 = st.columns(2)
        meta["title"] = c1.text_input("유튜브 제목", meta.get("title", ""))
        meta["thumbnail_top"] = c2.text_input("썸네일 윗줄 (흰색)", meta.get("thumbnail_top", ""))
        meta["description"] = c1.text_area("설명", meta.get("description", ""), height=110)
        meta["thumbnail_bottom"] = c2.text_input("썸네일 아랫줄 (노란색 강조)", meta.get("thumbnail_bottom", ""))
        tags = c2.text_input("태그 (쉼표 구분)", ", ".join(meta.get("tags", [])))
        meta["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

        st.markdown(f"**장면 {len(pj['scenes'])}개** — 내레이션과 이미지 프롬프트를 자유롭게 고치고, 행을 추가/삭제할 수 있어요.")
        df = pd.DataFrame([{"내레이션": x["text"], "이미지 프롬프트": x["prompt"]} for x in pj["scenes"]])
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=380,
                                column_config={"내레이션": st.column_config.TextColumn(width="large"),
                                               "이미지 프롬프트": st.column_config.TextColumn(width="large")})
        if st.button("✅ 변경사항 저장"):
            old = pj["scenes"]
            new = []
            for i, row in edited.fillna("").iterrows():
                if not str(row["내레이션"]).strip():
                    continue
                item = {"text": str(row["내레이션"]).strip(), "prompt": str(row["이미지 프롬프트"]).strip()}
                if i < len(old) and old[i]["prompt"] != item["prompt"]:
                    (Path(pj["dir"]) / "images" / f"{i:03d}.jpg").unlink(missing_ok=True)  # 프롬프트 바뀌면 다시 생성
                new.append(item)
            pj["scenes"] = new
            pipeline.save(pj)
            st.success("저장했습니다.")

        st.divider()
        st.markdown("#### 🖼️ 이미지 미리보기 (마음에 안 들면 다시 생성)")
        if st.button("모든 장면 이미지 미리 생성"):
            bar = st.progress(0.0)
            (Path(pj["dir"]) / "images").mkdir(exist_ok=True)
            for i, x in enumerate(pj["scenes"]):
                img = Path(pj["dir"]) / "images" / f"{i:03d}.jpg"
                if not img.exists():
                    make_image(s, x["prompt"], img, seed=1000 + i, label=f"장면 {i + 1}")
                bar.progress((i + 1) / len(pj["scenes"]), f"{i + 1}/{len(pj['scenes'])}")
        cols = st.columns(4)
        for i, x in enumerate(pj["scenes"]):
            img = Path(pj["dir"]) / "images" / f"{i:03d}.jpg"
            with cols[i % 4]:
                if img.exists():
                    st.image(str(img), caption=f"{i + 1}. {x['text'][:30]}…")
                    if st.button("🔄 다시", key=f"re{i}"):
                        import random
                        make_image(s, x["prompt"], img, seed=random.randint(1, 10 ** 6), label=f"장면 {i + 1}")
                        st.rerun()

# ───────────────────────── ③ 영상 만들기 ─────────────────────────
with tab3:
    pj = st.session_state.project
    if not pj:
        st.info("먼저 ① 기획을 진행하세요.")
    else:
        bgm_file = st.file_uploader("🎵 배경음악 (선택, mp3/wav) — 무료 BGM: 유튜브 오디오 보관함, Pixabay Music",
                                    type=["mp3", "wav", "m4a"])
        regen = st.checkbox("이미지 전부 새로 생성", False)
        if st.button("🎬 영상 만들기", type="primary"):
            bgm = None
            if bgm_file:
                bgm = Path(pj["dir"]) / f"bgm{Path(bgm_file.name).suffix}"
                bgm.write_bytes(bgm_file.getvalue())
            bar = st.progress(0.0, "시작…")
            try:
                st.session_state.project = pipeline.render(
                    s, pj, bgm=bgm, regenerate_images=regen,
                    progress=lambda p, m: bar.progress(min(p, 1.0), m))
                st.balloons()
            except Exception as e:
                st.error(str(e))
        pj = st.session_state.project
        if pj.get("video") and Path(pj["video"]).exists():
            d = Path(pj["dir"])
            c1, c2 = st.columns([2, 1])
            c1.video(pj["video"])
            c2.image(pj["thumbnail"], caption="썸네일")
            c2.download_button("⬇️ 영상 (mp4)", Path(pj["video"]).read_bytes(), "video.mp4", "video/mp4")
            c2.download_button("⬇️ 썸네일 (jpg)", Path(pj["thumbnail"]).read_bytes(), "thumbnail.jpg", "image/jpeg")
            c2.download_button("⬇️ 자막 (srt)", (d / "subtitles.srt").read_bytes(), "subtitles.srt")
            st.text_area("📋 업로드 정보 (제목/설명/챕터/태그)", (d / "upload_info.txt").read_text(encoding="utf-8"),
                         height=260)
            st.caption(f"저장 위치: {d}")

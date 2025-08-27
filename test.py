import streamlit as st
import os
import json
import datetime

FILE = "diary.json"

# 파일 읽기
if os.path.exists(FILE):
    with open(FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {}

# 스타일 추가
st.markdown("""
    <style>
    body {
        background-color: #fffafc;
    }
    .title {
        font-size: 40px;
        font-weight: bold;
        color: #ff4d6d;
        text-align: center;
    }
    .subtitle {
        font-size: 20px;
        color: #555;
        text-align: center;
    }
    .diary-card {
        background-color: #ffffff;
        border: 2px solid #ffd6e0;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# 경고문구
st.warning("⚠️ 아이디는 곧 일기 저장/불러오기 키입니다. 아이디를 잊으면 저장된 일기를 찾을 수 없으니 꼭 기억하세요!")

# 제목 꾸미기
st.markdown("<div class='title'>📔 두근두근 비밀 일기 ❤️</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>소중한 하루를 기록해보세요 ✨</div>", unsafe_allow_html=True)

# 아이디 입력
user_id = st.text_input("✨ 아이디를 입력하세요", key="user_id")

if user_id.strip():
    if user_id not in data:
        data[user_id] = {}

    # 날짜 선택
    date = st.date_input("📅 날짜", datetime.date.today())
    date_str = str(date)

    if date_str not in data[user_id]:
        data[user_id][date_str] = []

    # 새 일기 작성
    title = st.text_input("💌 제목", key="title_input")
    content = st.text_area("✏️ 나는 오늘... ", height=150)

    if st.button("🌸 페이지 추가"):
        if title.strip() and content.strip():
            data[user_id][date_str].append({"title": title, "content": content})
            with open(FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            st.success("하루가 기록되었습니다! 🌷")
        else:
            st.warning("제목과 내용을 모두 입력해주세요!")

    # 저장된 일기 확인
    st.subheader(f"📖 {user_id} 의 일기 목록")
    for d, entries in sorted(data[user_id].items(), reverse=True):
        st.markdown(f"### 🌼 {d}")
        for entry in entries:
            with st.expander(f"💖 {entry['title']}"):
                st.markdown(f"<div class='diary-card'>{entry['content']}</div>", unsafe_allow_html=True)
        st.divider()
else:
    st.info("먼저 아이디를 입력해주세요 🌙")

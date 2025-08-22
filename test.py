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

st.title("📔 개인 일기장 (아이디 기반)")

# 아이디 입력
user_id = st.text_input("아이디를 입력하세요", key="user_id")

if user_id:
    if user_id not in data:
        data[user_id] = {}

    # 날짜 선택
    date = st.date_input("날짜", datetime.date.today())
    date_str = str(date)

    # 이전 내용 불러오기
    content = data[user_id].get(date_str, "")
    text = st.text_area("오늘의 일기 내용", value=content, height=300)

    if st.button("저장"):
        data[user_id][date_str] = text
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success(f"{user_id} 님의 일기가 저장되었습니다!")

    # 저장된 일기 확인
    st.subheader(f"📖 {user_id} 님의 기존 일기")
    for d, c in sorted(data[user_id].items(), reverse=True):
        st.write(f"📅 {d}")
        st.write(c)
        st.divider()

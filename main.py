import streamlit as st
import random

# 히라가나 데이터 (예시)
hiragana = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "wo", "ん": "n"
}

# Streamlit 앱 시작
st.title("히라가나 암기 퀴즈")
st.write("히라가나 글자를 보고 올바른 로마자 표기를 선택하세요.")

# 세션 상태 초기화
if "questions" not in st.session_state:
    st.session_state.questions = random.sample(list(hiragana.items()), 30)
    st.session_state.index = 0
    st.session_state.score = 0

# 현재 문제
question, answer = st.session_state.questions[st.session_state.index]

# 선택지 생성 (정답 + 4개 랜덤 오답)
options = [answer]
while len(options) < 5:
    option = random.choice(list(hiragana.values()))
    if option not in options:
        options.append(option)
random.shuffle(options)

# 사용자 선택
user_answer = st.radio(f"문제 {st.session_state.index + 1} / 30: '{question}'", options)

if st.button("제출"):
    if user_answer == answer:
        st.session_state.score += 1
        st.success("정답!")
    else:
        st.error(f"오답! 정답은 '{answer}' 입니다.")

    # 다음 문제
    st.session_state.index += 1
    if st.session_state.index >= len(st.session_state.questions):
        st.write(f"퀴즈 종료! 최종 점수: {st.session_state.score} / 30")
        # 세션 초기화 옵션
        if st.button("다시 시작"):
            st.session_state.questions = random.sample(list(hiragana.items()), 30)
            st.session_state.index = 0
            st.session_state.score = 0
    else:
        st.experimental_rerun()

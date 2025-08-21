import streamlit as st
import subprocess
import sys

# py-hanspell 설치 (Streamlit Cloud 등 환경에서도 동작)
try:
    from hanspell import spell_checker
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/ssut/py-hanspell.git"])
    from hanspell import spell_checker

def rude_spell_checker(text):
    result = spell_checker.check(text)
    checked_text = result.checked
    errors = result.errors

    if errors:
        feedback = (
            "😏 문장 꼬라지 봐라. 발로 썼냐?\n\n"
            f"💀 머저리 같은 네 문장: {text}\n\n"
            f"✨ 자애로운 내가 고친 문장: {checked_text}\n\n"
            "🏆 축하해, 넌 내가 아는 생물 중 단연코 가장 멍청한 자식이야."
        )
    else:
        feedback = "👌 허. 그래, 이건 맞네. 드물게 잘했어."
    return feedback

# Streamlit 앱 UI
st.set_page_config(page_title="Rude Spell Checker 📝", page_icon="📝", layout="centered")
st.title("📝 Rude Spell Checker")
st.write(" 문장 내놔봐. 내가 시간 못 내줄 것도 없지. 😎")

user_input = st.text_area("뭐라고 쓸 건데? (꺼질거면 아무것도 안 쓰면 됨):", height=100)

if st.button("검사하기"):
    if user_input.strip() == "":
        st.warning(" 문장입력. 어렵냐? 😤")
    else:
        feedback = rude_spell_checker(user_input)
        st.markdown(f"### 피드백 결과:")
        st.text(feedback)

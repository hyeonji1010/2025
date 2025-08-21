import streamlit as st

# MBTI별 직업 추천 데이터 (예시)
mbti_jobs = {
    "INTJ": ["전략 컨설턴트", "연구원", "데이터 사이언티스트"],
    "INTP": ["소프트웨어 개발자", "연구원", "분석가"],
    "ENTJ": ["경영자", "프로젝트 매니저", "기업가"],
    "ENTP": ["스타트업 창업가", "마케팅 전문가", "발명가"],
    "INFJ": ["상담사", "작가", "교육자"],
    "INFP": ["작가", "심리상담사", "디자이너"],
    "ENFJ": ["교사", "HR 매니저", "코치"],
    "ENFP": ["마케터", "창작 활동가", "행사 기획자"],
    "ISTJ": ["회계사", "변호사", "공무원"],
    "ISFJ": ["간호사", "교사", "사회복지사"],
    "ESTJ": ["경영자", "프로젝트 매니저", "군인"],
    "ESFJ": ["간호사", "교사", "행정가"],
    "ISTP": ["엔지니어", "파일럿", "기술자"],
    "ISFP": ["디자이너", "예술가", "사진작가"],
    "ESTP": ["영업사원", "마케터", "트레이더"],
    "ESFP": ["연예인", "이벤트 플래너", "호스피탈리티 전문가"]
}

st.title("MBTI 기반 직업 추천 웹 앱")
st.write("당신의 MBTI를 선택하면 어울리는 직업을 추천해드립니다.")

# MBTI 선택
selected_mbti = st.selectbox("MBTI를 선택하세요:", list(mbti_jobs.keys()))

# 추천 직업 표시
if selected_mbti:
    st.subheader(f"{selected_mbti}에게 어울리는 직업:")
    for job in mbti_jobs[selected_mbti]:
        st.write(f"- {job}")

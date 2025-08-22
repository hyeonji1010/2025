import streamlit as st
import sqlite3
import hashlib
import datetime
import os

DB_FILE = "app.db"

# -----------------------------
# DB 초기화
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # users 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # diaries 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            content TEXT
        )
    """)

    conn.commit()
    conn.close()

# -----------------------------
# 유틸
# -----------------------------
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(uid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    u = c.fetchone()
    conn.close()
    return u

# -----------------------------
# 개인 일기 페이지
# -----------------------------
def page_personal(user_id):
    st.subheader("📔 개인 비밀 일기장")

    date = st.date_input("날짜", datetime.date.today())
    content = st.text_area("오늘의 일기 내용")

    if st.button("저장"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM diaries WHERE user_id=? AND date=?", (user_id, str(date)))
        exists = c.fetchone()
        if exists:
            c.execute("UPDATE diaries SET content=? WHERE id=?", (content, exists[0]))
        else:
            c.execute("INSERT INTO diaries (user_id,date,content) VALUES (?,?,?)", (user_id, str(date), content))
        conn.commit()
        conn.close()
        st.success("저장 완료!")

# -----------------------------
# 로그인 페이지
# -----------------------------
def login_page():
    st.subheader("🔑 로그인")
    username = st.text_input("아이디", key="login_user")
    password = st.text_input("비밀번호", type="password", key="login_pw")

    if st.button("로그인"):
        user = get_user(username)
        if user and user[2] == hash_pw(password):
            st.session_state["user"] = user
            st.success("로그인 성공!")
            st.rerun()
        else:
            st.error("로그인 실패")

# -----------------------------
# 회원가입 페이지
# -----------------------------
def signup_page():
    st.subheader("📝 회원가입")
    new_user = st.text_input("새 아이디", key="signup_user")
    new_pw = st.text_input("새 비밀번호", type="password", key="signup_pw")

    if st.button("회원가입"):
        if get_user(new_user):
            st.error("이미 존재하는 아이디")
        else:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO users (username,password) VALUES (?,?)", (new_user, hash_pw(new_pw)))
            conn.commit()
            conn.close()
            st.success("회원가입 성공! 로그인 해주세요.")

# -----------------------------
# 메인
# -----------------------------
def main():
    st.title("📓 개인 일기장")

    init_db()

    if "user" not in st.session_state:
        tab1, tab2 = st.tabs(["로그인", "회원가입"])
        with tab1:
            login_page()
        with tab2:
            signup_page()
        return

    user = st.session_state["user"]
    st.sidebar.write(f"안녕하세요, **{user[1]}** 님")
    choice = st.sidebar.radio("메뉴", ["개인 일기", "로그아웃"])

    if choice == "개인 일기":
        page_personal(user[0])
    elif choice == "로그아웃":
        st.session_state.pop("user")
        st.rerun()

if __name__ == "__main__":
    main()

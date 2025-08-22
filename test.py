import streamlit as st
import sqlite3
import hashlib
import datetime
import json

# -----------------------------
# DB 초기화
# -----------------------------
def init_db():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    # 유저 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT
        )
    """)

    # 개인 일기
    c.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            content TEXT,
            tags TEXT
        )
    """)

    # 공유 일기장
    c.execute("""
        CREATE TABLE IF NOT EXISTS shared_diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            members TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS shared_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diary_id INTEGER,
            author_id INTEGER,
            date TEXT,
            content TEXT
        )
    """)

    # 릴레이 소설
    c.execute("""
        CREATE TABLE IF NOT EXISTS relay_stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            participants TEXT,
            current_turn INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS relay_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER,
            author_id INTEGER,
            turn_order INTEGER,
            content TEXT
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# 유틸
# -----------------------------
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def get_user(username):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user


# -----------------------------
# 페이지: 개인 일기
# -----------------------------
def page_personal(user_id):
    st.subheader("📔 개인 비밀 일기장")

    date = st.date_input("날짜", datetime.date.today())
    content = st.text_area("내용")
    tags = st.text_input("태그 (쉼표 구분)")

    if st.button("저장"):
        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("SELECT id FROM diaries WHERE user_id=? AND date=?", (user_id, str(date)))
        exists = c.fetchone()
        if exists:
            c.execute("UPDATE diaries SET content=?, tags=? WHERE id=?", (content, tags, exists[0]))
        else:
            c.execute("INSERT INTO diaries (user_id,date,content,tags) VALUES (?,?,?,?)",
                      (user_id, str(date), content, tags))
        conn.commit()
        conn.close()
        st.success("저장 완료!")

    st.divider()
    st.subheader("🔍 검색")
    keyword = st.text_input("검색 키워드")
    if st.button("검색"):
        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("SELECT date, content, tags FROM diaries WHERE user_id=? AND (content LIKE ? OR tags LIKE ?)",
                  (user_id, f"%{keyword}%", f"%{keyword}%"))
        rows = c.fetchall()
        conn.close()
        for r in rows:
            st.write(f"📅 {r[0]}  |  🏷 {r[2]}")
            st.write(r[1])
            st.divider()


# -----------------------------
# 페이지: 공유 일기
# -----------------------------
def page_shared(user_id):
    st.subheader("👥 공유 일기장")

    # 새로운 공유 일기장 생성
    with st.expander("새 공유 일기장 만들기"):
        title = st.text_input("제목")
        members = st.text_input("멤버 유저명 (쉼표로 구분, 본인 자동 포함)")
        if st.button("생성"):
            member_list = [m.strip() for m in members.split(",") if m.strip()]
            user = get_user_by_id(user_id)
            if user and user[1] not in member_list:
                member_list.append(user[1])
            conn = sqlite3.connect("app.db")
            c = conn.cursor()
            c.execute("INSERT INTO shared_diaries (title, members) VALUES (?,?)",
                      (title, json.dumps(member_list)))
            conn.commit()
            conn.close()
            st.success("공유 일기장 생성 완료!")

    # 내가 속한 공유 일기장 목록
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT id,title,members FROM shared_diaries")
    diaries = c.fetchall()
    conn.close()

    my_diaries = []
    me = get_user_by_id(user_id)[1]
    for d in diaries:
        members = json.loads(d[2])
        if me in members:
            my_diaries.append(d)

    choice = st.selectbox("내 공유 일기장", [""] + [d[1] for d in my_diaries])
    if choice:
        diary = [d for d in my_diaries if d[1] == choice][0]
        st.write(f"멤버: {', '.join(json.loads(diary[2]))}")

        entry = st.text_area("오늘의 기록")
        if st.button("작성"):
            conn = sqlite3.connect("app.db")
            c = conn.cursor()
            c.execute("INSERT INTO shared_entries (diary_id, author_id, date, content) VALUES (?,?,?,?)",
                      (diary[0], user_id, str(datetime.date.today()), entry))
            conn.commit()
            conn.close()
            st.success("작성 완료!")

        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("""SELECT e.date,u.username,e.content
                     FROM shared_entries e JOIN users u ON e.author_id=u.id
                     WHERE diary_id=? ORDER BY e.id DESC""", (diary[0],))
        rows = c.fetchall()
        conn.close()
        for r in rows:
            st.write(f"📅 {r[0]} | ✍ {r[1]}")
            st.write(r[2])
            st.divider()


# -----------------------------
# 페이지: 릴레이 소설
# -----------------------------
def page_relay(user_id):
    st.subheader("📖 릴레이 소설")

    with st.expander("새 소설 시작하기"):
        title = st.text_input("소설 제목")
        participants = st.text_input("참여자 유저명 (쉼표, 본인 자동 포함)")
        if st.button("소설 생성"):
            p_list = [p.strip() for p in participants.split(",") if p.strip()]
            me = get_user_by_id(user_id)[1]
            if me not in p_list:
                p_list.append(me)
            conn = sqlite3.connect("app.db")
            c = conn.cursor()
            c.execute("INSERT INTO relay_stories (title, participants, current_turn) VALUES (?,?,?)",
                      (title, json.dumps(p_list), 0))
            conn.commit()
            conn.close()
            st.success("소설 생성 완료!")

    # 목록 불러오기
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT id,title,participants,current_turn FROM relay_stories")
    stories = c.fetchall()
    conn.close()

    choice = st.selectbox("참여중인 소설", [""] + [s[1] for s in stories])
    if choice:
        story = [s for s in stories if s[1] == choice][0]
        participants = json.loads(story[2])
        current_turn = story[3]
        me = get_user_by_id(user_id)[1]
        st.write(f"참여자: {', '.join(participants)}")
        st.write(f"현재 차례: {participants[current_turn]}")

        # 이어쓰기
        if participants[current_turn] == me:
            part = st.text_area("내 차례! 이어쓰기")
            if st.button("작성 완료"):
                conn = sqlite3.connect("app.db")
                c = conn.cursor()
                c.execute("INSERT INTO relay_entries (story_id,author_id,turn_order,content) VALUES (?,?,?,?)",
                          (story[0], user_id, current_turn, part))
                next_turn = (current_turn + 1) % len(participants)
                c.execute("UPDATE relay_stories SET current_turn=? WHERE id=?", (next_turn, story[0]))
                conn.commit()
                conn.close()
                st.success("작성 완료!")
                st.rerun()
        else:
            st.info("당신의 차례가 아닙니다.")

        # 전체 소설
        st.divider()
        st.subheader("📜 소설 내용")
        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("""SELECT e.turn_order,u.username,e.content
                     FROM relay_entries e JOIN users u ON e.author_id=u.id
                     WHERE story_id=? ORDER BY e.id""", (story[0],))
        rows = c.fetchall()
        conn.close()
        for r in rows:
            st.write(f"[{r[1]}] {r[2]}")
            st.divider()


# -----------------------------
# 로그인/회원가입
# -----------------------------
def login_box():
    st.subheader("🔑 로그인")
    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
        user = get_user(username)
        if user and user[2] == hash_pw(password):
            st.session_state["user"] = user
            st.success("로그인 성공")
            st.rerun()
        else:
            st.error("로그인 실패")

    st.divider()
    st.subheader("📝 회원가입")
    new_user = st.text_input("새 아이디")
    new_pw = st.text_input("새 비밀번호", type="password")
    email = st.text_input("이메일")
    if st.button("회원가입"):
        if get_user(new_user):
            st.error("이미 존재하는 아이디")
        else:
            conn = sqlite3.connect("app.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username,password,email) VALUES (?,?,?)",
                      (new_user, hash_pw(new_pw), email))
            conn.commit()
            conn.close()
            st.success("회원가입 성공! 로그인 해주세요.")


def get_user_by_id(uid):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    u = c.fetchone()
    conn.close()
    return u


# -----------------------------
# 메인
# -----------------------------
def main():
    st.title("📓 멀티 일기장 & 릴레이 소설")

    if "user" not in st.session_state:
        login_box()
        return

    user = st.session_state["user"]
    st.sidebar.write(f"안녕하세요, **{user[1]}** 님")
    choice = st.sidebar.radio("메뉴", ["개인 일기", "공유 일기", "릴레이 소설", "로그아웃"])

    if choice == "개인 일기":
        page_personal(user[0])
    elif choice == "공유 일기":
        page_shared(user[0])
    elif choice == "릴레이 소설":
        page_relay(user[0])
    elif choice == "로그아웃":
        st.session_state.pop("user")
        st.rerun()


if __name__ == "__main__":
    init_db()
    main()

import streamlit as st
import sqlite3
from datetime import datetime, date
import json
import hashlib
from typing import List, Optional, Tuple

DB_PATH = 'app.db'

# -----------------------------
# Utilities
# -----------------------------

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def hash_password(password: str, salt: str) -> str:
    return sha256(password + ':' + salt)


def verify_password(password: str, salt: str, hashed: str) -> bool:
    return hash_password(password, salt) == hashed


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# DB Init
# -----------------------------

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # users
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS users (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT UNIQUE NOT NULL,
               password_hash TEXT NOT NULL,
               salt TEXT NOT NULL,
               email TEXT
           )'''
    )

    # personal diaries
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS diaries (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER NOT NULL,
               d_date TEXT NOT NULL,
               content TEXT NOT NULL,
               tags TEXT,
               created_at TEXT NOT NULL,
               updated_at TEXT NOT NULL,
               UNIQUE(user_id, d_date),
               FOREIGN KEY(user_id) REFERENCES users(id)
           )'''
    )

    # shared diaries (meta)
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS shared_diaries (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title TEXT NOT NULL,
               owner_id INTEGER NOT NULL,
               created_at TEXT NOT NULL,
               FOREIGN KEY(owner_id) REFERENCES users(id)
           )'''
    )

    # shared members
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS shared_members (
               diary_id INTEGER NOT NULL,
               user_id INTEGER NOT NULL,
               role TEXT DEFAULT 'member',
               PRIMARY KEY(diary_id, user_id),
               FOREIGN KEY(diary_id) REFERENCES shared_diaries(id),
               FOREIGN KEY(user_id) REFERENCES users(id)
           )'''
    )

    # shared entries
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS shared_entries (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               diary_id INTEGER NOT NULL,
               author_id INTEGER NOT NULL,
               d_datetime TEXT NOT NULL,
               content TEXT NOT NULL,
               FOREIGN KEY(diary_id) REFERENCES shared_diaries(id),
               FOREIGN KEY(author_id) REFERENCES users(id)
           )'''
    )

    # relay stories (meta)
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS relay_stories (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title TEXT NOT NULL,
               owner_id INTEGER NOT NULL,
               current_turn_user_id INTEGER,
               created_at TEXT NOT NULL,
               is_public INTEGER DEFAULT 0,
               FOREIGN KEY(owner_id) REFERENCES users(id),
               FOREIGN KEY(current_turn_user_id) REFERENCES users(id)
           )'''
    )

    # relay participants
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS relay_participants (
               story_id INTEGER NOT NULL,
               user_id INTEGER NOT NULL,
               turn_order INTEGER NOT NULL,
               PRIMARY KEY(story_id, user_id),
               FOREIGN KEY(story_id) REFERENCES relay_stories(id),
               FOREIGN KEY(user_id) REFERENCES users(id)
           )'''
    )

    # relay entries
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS relay_entries (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               story_id INTEGER NOT NULL,
               author_id INTEGER NOT NULL,
               part_order INTEGER NOT NULL,
               content TEXT NOT NULL,
               created_at TEXT NOT NULL,
               FOREIGN KEY(story_id) REFERENCES relay_stories(id),
               FOREIGN KEY(author_id) REFERENCES users(id)
           )'''
    )

    conn.commit()
    conn.close()


# -----------------------------
# User / Auth
# -----------------------------

def create_user(username: str, email: str, password: str) -> Tuple[bool, str]:
    username = username.strip()
    if len(username) < 2:
        return False, '유저명은 2글자 이상으로 해줘.'
    if len(password) < 6:
        return False, '비밀번호는 6자 이상으로 해줘.'

    salt = sha256(username + str(datetime.utcnow().timestamp()))[:16]
    pw_hash = hash_password(password, salt)
    try:
        conn = get_conn()
        conn.execute(
            'INSERT INTO users(username, email, password_hash, salt) VALUES (?, ?, ?, ?)',
            (username, email, pw_hash, salt)
        )
        conn.commit()
        return True, '회원가입 완료! 로그인해줘.'
    except sqlite3.IntegrityError:
        return False, '이미 존재하는 유저명이야.'
    finally:
        conn.close()


def get_user(username: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cur.fetchone()
    conn.close()
    return row


def authenticate(username: str, password: str) -> Optional[sqlite3.Row]:
    user = get_user(username)
    if not user:
        return None
    if verify_password(password, user['salt'], user['password_hash']):
        return user
    return None


# -----------------------------
# Personal Diary
# -----------------------------

def upsert_personal_entry(user_id: int, d: date, content: str, tags: str = '') -> None:
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    cur = conn.cursor()
    d_str = d.isoformat()
    cur.execute('SELECT id FROM diaries WHERE user_id = ? AND d_date = ?', (user_id, d_str))
    exists = cur.fetchone()
    if exists:
        cur.execute('UPDATE diaries SET content=?, tags=?, updated_at=? WHERE id=?',
                    (content, tags, now, exists['id']))
    else:
        cur.execute('INSERT INTO diaries(user_id, d_date, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, d_str, content, tags, now, now))
    conn.commit()
    conn.close()


def load_personal_entry(user_id: int, d: date) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM diaries WHERE user_id=? AND d_date=?', (user_id, d.isoformat()))
    row = cur.fetchone()
    conn.close()
    return row


def search_personal_entries(user_id: int, keyword: str) -> List[sqlite3.Row]:
    kw = f"%{keyword}%"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM diaries
                   WHERE user_id=? AND (content LIKE ? OR tags LIKE ?)
                   ORDER BY d_date DESC''', (user_id, kw, kw))
    rows = cur.fetchall()
    conn.close()
    return rows


# -----------------------------
# Shared Diaries
# -----------------------------

def create_shared_diary(title: str, owner_id: int, member_usernames: List[str]) -> Tuple[bool, str]:
    member_usernames = [u.strip() for u in member_usernames if u.strip()]
    if len(member_usernames) < 1:
        return False, '최소 2명 이상이어야 해(너 포함). 초대 대상 1명 이상 입력해줘.'
    if len(member_usernames) > 4:
        return False, '최대 인원은 5명이야(너 포함). 초대는 최대 4명까지만.'

    conn = get_conn()
    cur = conn.cursor()
    try:
        now = datetime.utcnow().isoformat()
        cur.execute('INSERT INTO shared_diaries(title, owner_id, created_at) VALUES (?, ?, ?)',
                    (title.strip() or '무제 공유일기', owner_id, now))
        diary_id = cur.lastrowid
        # owner is member + owner role
        cur.execute('INSERT INTO shared_members(diary_id, user_id, role) VALUES (?, ?, ?)', (diary_id, owner_id, 'owner'))

        # resolve usernames to ids
        for uname in member_usernames:
            user = get_user(uname)
            if not user:
                conn.rollback()
                return False, f'유저 {uname} 를 찾을 수 없어.'
            cur.execute('INSERT INTO shared_members(diary_id, user_id, role) VALUES (?, ?, ?)', (diary_id, user['id'], 'member'))
        conn.commit()
        return True, f'공유 일기장 생성 완료 (ID: {diary_id})'
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, '멤버 추가 중 문제 발생. 이미 멤버로 추가된 유저가 있는지 확인해줘.'
    finally:
        conn.close()


def my_shared_diaries(user_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT sd.* FROM shared_diaries sd
                   JOIN shared_members sm ON sd.id = sm.diary_id
                   WHERE sm.user_id = ?
                   ORDER BY sd.created_at DESC''', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def add_shared_entry(diary_id: int, author_id: int, content: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO shared_entries(diary_id, author_id, d_datetime, content) VALUES (?, ?, ?, ?)',
                (diary_id, author_id, datetime.utcnow().isoformat(), content))
    conn.commit()
    conn.close()


def get_shared_entries(diary_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT se.*, u.username AS author
                   FROM shared_entries se JOIN users u ON se.author_id = u.id
                   WHERE diary_id = ?
                   ORDER BY d_datetime DESC''', (diary_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def shared_diary_member_count(diary_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) AS c FROM shared_members WHERE diary_id=?', (diary_id,))
    c = cur.fetchone()['c']
    conn.close()
    return c


def is_member(diary_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM shared_members WHERE diary_id=? AND user_id=?', (diary_id, user_id))
    ok = cur.fetchone() is not None
    conn.close()
    return ok


# -----------------------------
# Relay Stories
# -----------------------------

def create_relay_story(title: str, owner_id: int, participant_usernames: List[str], is_public: bool) -> Tuple[bool, str, Optional[int]]:
    participant_usernames = [u.strip() for u in participant_usernames if u.strip()]
    if len(participant_usernames) < 1:
        return False, '최소 2명 이상이어야 해(너 포함). 초대 대상 1명 이상 입력해줘.', None

    # include owner as first slot by default if not listed
    if participant_usernames[0] != get_usernames_by_ids([owner_id])[0]:
        pass  # ordering will be set explicitly below

    conn = get_conn()
    cur = conn.cursor()
    try:
        now = datetime.utcnow().isoformat()
        cur.execute('INSERT INTO relay_stories(title, owner_id, current_turn_user_id, created_at, is_public) VALUES (?, ?, ?, ?, ?)',
                    (title.strip() or '무제 릴레이', owner_id, None, now, 1 if is_public else 0))
        story_id = cur.lastrowid

        # Build participant list with explicit order; owner first, then listed usernames (excluding duplicates/owner)
        ordered_user_ids: List[int] = []
        ordered_user_ids.append(owner_id)
        for uname in participant_usernames:
            user = get_user(uname)
            if not user:
                conn.rollback()
                return False, f'유저 {uname} 를 찾을 수 없어.', None
            if user['id'] not in ordered_user_ids:
                ordered_user_ids.append(user['id'])

        # insert participants
        for i, uid in enumerate(ordered_user_ids):
            cur.execute('INSERT INTO relay_participants(story_id, user_id, turn_order) VALUES (?, ?, ?)', (story_id, uid, i))

        # set first turn
        cur.execute('UPDATE relay_stories SET current_turn_user_id=? WHERE id=?', (ordered_user_ids[0], story_id))
        conn.commit()
        return True, f'릴레이 소설 생성 완료 (ID: {story_id})', story_id
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, '참가자 추가 중 문제 발생.', None
    finally:
        conn.close()


def get_usernames_by_ids(user_ids: List[int]) -> List[str]:
    if not user_ids:
        return []
    conn = get_conn()
    cur = conn.cursor()
    q = 'SELECT username FROM users WHERE id IN (%s)' % ','.join('?'*len(user_ids))
    cur.execute(q, user_ids)
    rows = cur.fetchall()
    conn.close()
    return [r['username'] for r in rows]


def list_my_relay_stories(user_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT DISTINCT rs.* FROM relay_stories rs
                   LEFT JOIN relay_participants rp ON rs.id = rp.story_id
                   WHERE rs.owner_id = ? OR rp.user_id = ?
                   ORDER BY rs.created_at DESC''', (user_id, user_id))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_relay_participants(story_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT rp.*, u.username FROM relay_participants rp
                   JOIN users u ON rp.user_id = u.id
                   WHERE rp.story_id=? ORDER BY rp.turn_order ASC''', (story_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_relay_entries(story_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM relay_entries WHERE story_id=? ORDER BY part_order ASC', (story_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def who_is_next(story_id: int) -> Optional[int]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT current_turn_user_id FROM relay_stories WHERE id=?', (story_id,))
    row = cur.fetchone()
    conn.close()
    return row['current_turn_user_id'] if row else None


def advance_turn(story_id: int):
    parts = get_relay_participants(story_id)
    if not parts:
        return
    uid_list = [p['user_id'] for p in parts]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT current_turn_user_id FROM relay_stories WHERE id=?', (story_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return
    curr = row['current_turn_user_id']
    try:
        idx = uid_list.index(curr)
    except ValueError:
        idx = -1
    nxt = uid_list[(idx + 1) % len(uid_list)]
    cur.execute('UPDATE relay_stories SET current_turn_user_id=? WHERE id=?', (nxt, story_id))
    conn.commit()
    conn.close()


def add_relay_entry(story_id: int, author_id: int, content: str) -> Tuple[bool, str]:
    # check turn
    turn_uid = who_is_next(story_id)
    if turn_uid is not None and turn_uid != author_id:
        return False, '네 차례가 아니야. 다음 순서를 기다려줘.'

    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COALESCE(MAX(part_order), -1) AS m FROM relay_entries WHERE story_id=?', (story_id,))
    m = cur.fetchone()['m']
    next_order = (m + 1)
    now = datetime.utcnow().isoformat()
    cur.execute('INSERT INTO relay_entries(story_id, author_id, part_order, content, created_at) VALUES (?, ?, ?, ?, ?)',
                (story_id, author_id, next_order, content, now))
    conn.commit()
    conn.close()

    # advance turn after successful insert
    advance_turn(story_id)
    return True, '작성 완료! 다음 참가자 차례로 넘어갔어.'


# -----------------------------
# UI Helpers
# -----------------------------

def ensure_session_state():
    defaults = {
        'user': None,
        'page': '로그인'
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def login_box():
    st.header('로그인')
    with st.form('login_form', clear_on_submit=False):
        username = st.text_input('유저명')
        password = st.text_input('비밀번호', type='password')
        submitted = st.form_submit_button('로그인')
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = dict(user)
            st.session_state.page = '개인 일기'
            st.success(f"환영해, {user['username']}!")
            st.experimental_rerun()
        else:
            st.error('로그인 실패. 유저명/비밀번호 확인해줘.')

    with st.expander('처음이야? 회원가입'):  # Register
        with st.form('register_form', clear_on_submit=True):
            r_username = st.text_input('유저명(2자 이상)')
            r_email = st.text_input('이메일(선택)')
            r_password = st.text_input('비밀번호(6자 이상)', type='password')
            r_submit = st.form_submit_button('가입')
        if r_submit:
            ok, msg = create_user(r_username, r_email, r_password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def sidebar_nav():
    st.sidebar.title('메뉴')
    if st.session_state.user:
        st.sidebar.markdown(f"**{st.session_state.user['username']}** 로 접속중")
        choice = st.sidebar.radio('이동', ['개인 일기', '공유 일기', '릴레이 소설', '로그아웃'])
        if choice == '로그아웃':
            st.session_state.user = None
            st.session_state.page = '로그인'
            st.experimental_rerun()
        else:
            st.session_state.page = choice
    else:
        st.session_state.page = '로그인'


def page_personal():
    st.header('개인 비밀 일기장')
    user_id = st.session_state.user['id']

    col1, col2 = st.columns([1,1])
    with col1:
        d = st.date_input('날짜 선택', value=date.today())
    with col2:
        tags = st.text_input('태그 (쉼표로 구분)')

    row = load_personal_entry(user_id, d)
    content = st.text_area('내용', value=row['content'] if row else '', height=250)

    if st.button('저장/수정'):
        upsert_personal_entry(user_id, d, content, tags)
        st.success('저장했어!')

    st.divider()
    st.subheader('검색')
    keyword = st.text_input('키워드로 검색')
    if keyword:
        results = search_personal_entries(user_id, keyword)
        for r in results:
            with st.container(border=True):
                st.markdown(f"**{r['d_date']}**  ")
                st.write(r['content'])
                if r['tags']:
                    st.caption(f"태그: {r['tags']}")


def page_shared():
    st.header('공유 일기장')
    user_id = st.session_state.user['id']

    with st.expander('새 공유 일기장 만들기'):
        with st.form('shared_create_form'):
            title = st.text_input('제목', value='우리들의 일기')
            invite = st.text_input('초대 유저명 (쉼표로 구분, 최소 1명, 최대 4명)')
            submitted = st.form_submit_button('생성')
        if submitted:
            members = [u.strip() for u in invite.split(',') if u.strip()]
            ok, msg = create_shared_diary(title, user_id, members)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.subheader('내가 속한 공유 일기장')
    diaries = my_shared_diaries(user_id)
    if not diaries:
        st.info('아직 속한 공유 일기장이 없어.')
        return

    labels = [f"[{d['id']}] {d['title']}" for d in diaries]
    selected = st.selectbox('열기', options=labels)
    diary_id = int(selected.split(']')[0][1:])

    # member count guard (2~5)
    mcount = shared_diary_member_count(diary_id)
    st.caption(f'멤버 수: {mcount}명 (최소 2, 최대 5)')

    if not is_member(diary_id, user_id):
        st.error('멤버만 접근 가능해.')
        return

    st.markdown('---')
    st.subheader('글 작성')
    content = st.text_area('내용', height=200, key=f'shared_write_{diary_id}')
    if st.button('작성하기', key=f'write_btn_{diary_id}'):
        if content.strip():
            add_shared_entry(diary_id, user_id, content.strip())
            st.success('작성 완료!')
        else:
            st.warning('내용을 입력해줘.')

    st.subheader('타임라인')
    entries = get_shared_entries(diary_id)
    if not entries:
        st.info('아직 글이 없어.')
    else:
        for e in entries:
            with st.container(border=True):
                t = datetime.fromisoformat(e['d_datetime'])
                st.markdown(f"**{e['author']}** · {t.strftime('%Y-%m-%d %H:%M')} (ID: {e['id']})")
                st.write(e['content'])


def page_relay():
    st.header('릴레이 소설')
    user_id = st.session_state.user['id']

    with st.expander('새 릴레이 소설 만들기'):
        with st.form('relay_create_form'):
            title = st.text_input('제목', value='우리들의 소설')
            participants = st.text_input('참가 유저명 (쉼표로 구분, 나 제외 최소 1명)')
            is_public = st.checkbox('전체 공개 블로그로 보기 허용', value=False)
            r_submit = st.form_submit_button('생성')
        if r_submit:
            usernames = [u.strip() for u in participants.split(',') if u.strip()]
            ok, msg, story_id = create_relay_story(title, user_id, usernames, is_public)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.subheader('내 릴레이 목록')
    stories = list_my_relay_stories(user_id)
    if not stories:
        st.info('참여 중인 릴레이가 없어.')
        return

    labels = [f"[{s['id']}] {s['title']}" for s in stories]
    selected = st.selectbox('열기', options=labels, key='relay_select')
    story_id = int(selected.split(']')[0][1:])

    parts = get_relay_participants(story_id)
    st.caption('참가자 순서: ' + ' → '.join([p['username'] for p in parts]))

    turn_uid = who_is_next(story_id)
    if turn_uid:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT username FROM users WHERE id=?', (turn_uid,))
        who = cur.fetchone()['username']
        conn.close()
        st.info(f'현재 차례: {who}')

    st.markdown('---')
    st.subheader('이어쓰기')
    content = st.text_area('이번 차례 내용', height=200, key=f'relay_write_{story_id}')
    if st.button('작성', key=f'relay_btn_{story_id}'):
        ok, msg = add_relay_entry(story_id, user_id, content.strip())
        if ok:
            st.success(msg)
        else:
            st.warning(msg)

    st.subheader('소설 본문')
    entries = get_relay_entries(story_id)
    if not entries:
        st.info('아직 본문이 없어. 첫 문장을 시작해봐!')
    else:
        for e in entries:
            with st.container(border=True):
                user = get_usernames_by_ids([e['author_id']])[0]
                st.markdown(f"**{e['part_order']+1}화 · {user}** · {e['created_at']}")
                st.write(e['content'])


# -----------------------------
# Main App
# -----------------------------

def main():
    st.set_page_config(page_title='비밀 일기 · 공유 · 릴레이', page_icon='📚', layout='wide')
    init_db()
    ensure_session_state()
    sidebar_nav()

    page = st.session_state.page
    if page == '로그인' or not st.session_state.user:
        login_box()
    elif page == '개인 일기':
        page_personal()
    elif page == '공유 일기':
        page_shared()
    elif page == '릴레이 소설':
        page_relay()
    else:
        st.write('페이지를 찾을 수 없어.')


if __name__ == '__main__':
    main()

%%writefile app.py
import streamlit as st
import google.generativeai as genai
import requests
import sqlite3
import threading
import schedule
import time
from datetime import date

# --- [1. 설정 및 키 입력] ---
NASA_KEY = '실제_키_abcd123...'
GEMINI_KEY = '실제_키_xyz987...'

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest')

# --- [2. DB 함수] ---
def get_db_connection():
    return sqlite3.connect('space_base.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS space_logs (
            date TEXT PRIMARY KEY,
            title TEXT,
            explanation TEXT,
            ai_message TEXT,
            url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- [3. 스케줄러] ---
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if 'scheduler_started' not in st.session_state:
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    st.session_state['scheduler_started'] = True

# --- [4. UI 디자인] ---
st.set_page_config(page_title="우주 기지: Zero to Hero", page_icon="🚀", layout="wide")

st.title("🌌 우주 기지 컨트롤 센터")

# 📍 [수정 핵심] 날짜 선택기를 아주 단순하고 명확하게 바꿨습니다!
# 사이드바가 아니라, 잘 보이는지 확인하기 위해 우선 '본문 상단'에 배치해볼까요?
# 아니요, 사이드바를 고집하되 표준형으로 넣겠습니다.

st.sidebar.title("📅 날짜 설정") # 큰 제목
st.sidebar.info("👇 아래 달력 아이콘을 눌러보세요")

# label_visibility 옵션을 삭제하여 기본 모양으로 되돌렸습니다.
selected_date = st.sidebar.date_input(
    "날짜를 선택하세요", 
    date.today()
)

st.sidebar.write(f"선택된 날짜: **{selected_date}**") # 잘 선택됐는지 눈으로 확인하는 텍스트

st.sidebar.markdown("---")
st.sidebar.header("🎨 에디터 모드")
force_refresh = st.sidebar.checkbox("🔄 저장된 문구 무시하고 다시 쓰기")

# --- [5. 메인 로직] ---
# 버튼을 더 크게 만들어서 눈에 띄게 합니다.
if st.button('🚀 우주 기지와 통신 시작 (Click Me)', use_container_width=True, type="primary"):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cached = None
    if not force_refresh:
        cursor.execute("SELECT title, ai_message, url FROM space_logs WHERE date = ?", (str(selected_date),))
        cached = cursor.fetchone()
    
    if cached:
        st.success("📦 [DB] 창고에서 데이터를 꺼내왔습니다!")
        title, ai_message, url = cached
    else:
        with st.spinner('🛰️ NASA와 통신 중...'):
            try:
                nasa_url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&date={selected_date}'
                res = requests.get(nasa_url).json()
                
                if 'url' in res:
                    title = res.get('title', '무제')
                    explanation = res.get('explanation', '')
                    url = res.get('url')
                    
                    prompt = f"""
                    너는 마케터야. 
                    [사진 설명]: {explanation}
                    이걸 보고 20대에게 'Zero to Hero'의 영감을 주는 인스타 글을 써줘.
                    """
                    ai_message = model.generate_content(prompt).text
                    
                    cursor.execute("INSERT OR REPLACE INTO space_logs (date, title, explanation, ai_message, url) VALUES (?, ?, ?, ?, ?)",
                                   (str(selected_date), title, explanation, ai_message, url))
                    conn.commit()
                else:
                    st.error("해당 날짜의 데이터가 없습니다.")
                    st.stop()
            except Exception as e:
                st.error(f"오류: {e}")
                st.stop()
    
    conn.close()

    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(url, caption=title, use_container_width=True)
    with col2:
        st.info("💌 AI의 메시지")
        st.write(ai_message)

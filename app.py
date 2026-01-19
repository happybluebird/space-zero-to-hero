import streamlit as st
import google.generativeai as genai
import requests
import sqlite3
import threading
import schedule
import time
from datetime import date

# --- [1. 설정 및 키 입력] ---
try:
    NASA_KEY = st.secrets["NASA_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
except FileNotFoundError:
    st.error("설정된 키가 없습니다. Streamlit Secrets에 키를 등록해주세요.")
    st.stop()

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
# 1. 페이지 설정 (이게 가장 먼저 나와야 합니다!)
st.set_page_config(page_title="우주 기지: Zero to Hero", page_icon="🚀", layout="wide")

# 2. 유성우 테마 디자인 적용 (CSS)
st.markdown("""
<style>
    /* 배경 및 전체 폰트 설정 */
    .stApp {
        background-image: linear-gradient(rgba(0, 8, 20, 0.8), rgba(0, 8, 20, 0.8)), url('https://i.imgur.com/8Z9gG2j.jpg');
        background-size: cover;
        background-attachment: fixed;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #E0E0E0;
    }
    
    /* 제목 스타일 */
    h1 {
        color: #FFFFFF;
        text-align: center;
        font-weight: 800;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: rgba(10, 25, 48, 0.9);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* 버튼 스타일 (로켓 발사) */
    div.stButton > button {
        background: linear-gradient(135deg, #FF4500, #FFD700);
        color: #000814;
        border: none;
        border-radius: 980px;
        padding: 15px 30px;
        font-size: 1.2rem;
        font-weight: 800;
        box-shadow: 0 4px 15px rgba(255, 69, 0, 0.4);
        width: 100%;
    }
    div.stButton > button:hover {
        transform: translateY(-3px);
        filter: brightness(1.1);
    }
    div.stButton > button::before {
        content: "🚀 ";
        margin-right: 8px;
    }

    /* 메시지 박스 스타일 */
    div[data-testid="stAlert"] {
        background-color: rgba(10, 25, 48, 0.6);
        border-left: 5px solid #FFD700;
        border-radius: 18px;
        backdrop-filter: blur(10px);
        color: #E0E0E0;
    }
</style>
""", unsafe_allow_html=True)

# 3. 화면 구성 요소 (날짜 선택기 등)
st.title("🌌 우주 기지 컨트롤 센터")

st.sidebar.title("📅 날짜 설정")
st.sidebar.info("👇 아래 달력 아이콘을 눌러보세요")

# 날짜 선택 기능 (이게 있어야 작동합니다!)
selected_date = st.sidebar.date_input(
    "날짜를 선택하세요", 
    date.today()
)

st.sidebar.write(f"선택된 날짜: **{selected_date}**")
st.sidebar.markdown("---")
st.sidebar.header("🎨 에디터 모드")
force_refresh = st.sidebar.checkbox("🔄 저장된 문구 무시하고 다시 쓰기")

# --- [5. 메인 로직] ---
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
                
                # [수정된 부분] 응답을 먼저 받고 상태를 확인합니다.
                response = requests.get(nasa_url)
                res = response.json()
                
                # 정상적으로 이미지 URL이 있는 경우
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
                    
                # [여기가 핵심] 데이터가 없을 때 진짜 이유를 화면에 보여줍니다.
                else:
                    st.error(f"🚨 NASA 통신 에러! 상태 코드: {response.status_code}")
                    st.write("▼ 아래 메시지를 복사해서 알려주세요:")
                    st.code(res) # 에러 내용을 그대로 보여줌
                    st.stop()

            except Exception as e:
                st.error(f"시스템 오류 발생: {e}")
                st.stop()
    
    conn.close()

    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(url, caption=title, use_container_width=True)
    with col2:
        st.info("💌 AI의 메시지")
        st.write(ai_message)

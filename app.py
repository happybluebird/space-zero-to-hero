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

# --- [4. UI 디자인: Space Library Theme] ---
# 1. 페이지 설정
st.set_page_config(page_title="우주도서관: Deep Space Archive", page_icon="🏛️", layout="wide")

# 2. 도서관 테마 디자인 적용 (CSS)
st.markdown("""
<style>
    /* 1. 배경 및 전체 폰트 설정 (Deep Space & Antique) */
    .stApp {
        /* 배경: 어두운 우주 이미지 */
        background-image: linear-gradient(rgba(5, 10, 20, 0.9), rgba(5, 10, 20, 0.9)), url('https://cdn.pixabay.com/photo/2016/10/20/18/35/earth-1756274_1280.jpg');
        background-size: cover;
        background-attachment: fixed;
        color: #e0e0e0; /* 오래된 종이 느낌의 미색 텍스트 */
        font-family: "Times New Roman", Times, serif; /* 지적인 명조체 계열 */
    }
    
    /* 2. 제목 스타일 (우주도서관 간판) */
    h1 {
        font-family: 'Times New Roman', serif;
        color: #d4af37; /* 앤틱 골드 (금박 느낌) */
        text-align: center;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.8);
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
    
    /* 3. 사이드바 스타일 (서재 느낌) */
    [data-testid="stSidebar"] {
        background-color: #0b1016; /* 아주 짙은 네이비/블랙 */
        border-right: 1px solid #2c3e50;
    }
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
        color: #a8b2c1;
        text-align: left;
    }

    /* 4. 버튼 스타일 (기록 열람) */
    div.stButton > button {
        background-color: #1c2833; /* 차분한 딥 네이비 */
        color: #d4af37; /* 금색 글씨 */
        border: 1px solid #d4af37; /* 금색 테두리 */
        border-radius: 5px; /* 둥글지 않고 각진 단말기 느낌 */
        padding: 15px 30px;
        font-size: 1.1rem;
        font-family: sans-serif; /* 가독성 위해 버튼은 고딕 */
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #d4af37;
        color: #0b1016;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
    }

    /* 5. 리포트 박스 스타일 (문서 느낌) */
    div[data-testid="stAlert"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-left: 3px solid #d4af37;
        color: #f0f0f0;
    }
    
    /* 6. 이미지 캡션 */
    div[data-testid="stImage"] > div {
        border: 1px solid #333;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

# 3. 화면 구성
st.title("🏛️ 우주도서관 (Space Library)")
st.markdown("<div style='text-align: center; color: #aaa; margin-bottom: 30px;'>세상에서 가장 큰 서재, 우주도서관에 오신 것을 환영합니다.</div>", unsafe_allow_html=True)

st.sidebar.title("🗂️ 아카이브 접근")
st.sidebar.info("열람하고자 하는 과거의 날짜를 선택하십시오.")

selected_date = st.sidebar.date_input(
    "열람 희망 날짜 (Access Date)", 
    date.today()
)

st.sidebar.write(f"선택된 좌표: **{selected_date}**")
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 관리자 모드")
force_refresh = st.sidebar.checkbox("🔄 데이터 재수신 (Cache Clear)")

# --- [5. 메인 로직: 사서 브리핑] ---
if st.button('📖 아카이브 기록 열람 (Retrieve Record)', use_container_width=True):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cached = None
    if not force_refresh:
        cursor.execute("SELECT title, ai_message, url FROM space_logs WHERE date = ?", (str(selected_date),))
        cached = cursor.fetchone()
    
    if cached:
        st.success("✅ [ARCHIVE] 보관소에서 기록을 찾았습니다.")
        title, ai_message, url = cached
    else:
        with st.spinner('📡 심우주 통신망 접속 중...'):
            try:
                nasa_url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&date={selected_date}'
                response = requests.get(nasa_url)
                res = response.json()
                
                if 'url' in res:
                    title = res.get('title', '무제')
                    explanation = res.get('explanation', '')
                    url = res.get('url')
                    
                    # [프롬프트 수정] 도서관 사서 페르소나 적용
                    prompt = f"""
                    당신은 '우주도서관'의 수석 사서입니다. 
                    사용자가 요청한 날짜의 천체 사진 정보를 브리핑해야 합니다.
                    
                    [사진 데이터]: {explanation}
                    
                    위 내용을 바탕으로 아래 3가지 형식에 맞춰 정중하고 지적인 어조(경어체, ~습니다)로 리포트를 작성해 주세요.
                    불필요한 이모지나 해시태그는 절대 사용하지 마십시오.
                    
                    1. [헤드라인 뉴스]: 내용을 관통하는 한 문장의 강렬한 제목
                    2. [지식의 서사]: 사진에 담긴 천문학적 현상과 의미를 깊이 있게 설명하는 에세이 (3~4문장)
                    3. [데이터 로그]: 관측 대상, 추정 거리, 별자리 위치 등 핵심 과학적 사실 요약 (글머리 기호 사용)
                    """
                    
                    ai_message = model.generate_content(prompt).text
                    
                    cursor.execute("INSERT OR REPLACE INTO space_logs (date, title, explanation, ai_message, url) VALUES (?, ?, ?, ?, ?)",
                                   (str(selected_date), title, explanation, ai_message, url))
                    conn.commit()
                    
                else:
                    st.error(f"🚨 통신 실패 (Status: {response.status_code})")
                    st.code(res)
                    st.stop()

            except Exception as e:
                st.error(f"⚠️ 시스템 오류: {e}")
                st.stop()
    
    conn.close()

    st.divider()
    
    # [레이아웃 변경] 왼쪽: 이미지 / 오른쪽: 리포트
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.image(url, caption=f"Figure 1. {title}", use_container_width=True)
        
    with col2:
        st.info("📜 사서의 브리핑 리포트")
        st.write(ai_message)
        
        st.markdown("---")
        st.caption("이 기록을 스크랩하시겠습니까?")
        # [신규 기능] 리포트 내용 복사하기 (st.code를 쓰면 우측 상단에 복사 버튼이 생깁니다)
        st.code(ai_message, language="text")

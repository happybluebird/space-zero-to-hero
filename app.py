import streamlit as st
import google.generativeai as genai
import requests
import sqlite3
import random  # 랜덤 추출을 위해 추가
from datetime import date

# ⚡ [핵심] 설정은 무조건 맨 위!
st.set_page_config(page_title="우주도서관: Deep Space Archive", layout="wide")

# --- [1. 메타 데이터 및 스타일 설정] ---
# 로봇들이 잘 읽어가도록 메타 태그 강제 주입
st.markdown(
    f'<head><title>우주도서관: Deep Space Archive</title>'
    f'<meta property="og:title" content="우주도서관: Deep Space Archive">'
    f'<meta property="og:description" content="NASA 데이터를 기반으로 한 우주 기록 보관소입니다.">'
    f'</head>', 
    unsafe_allow_html=True
)

st.markdown("""
<style>
    /* 전체 배경: 깊은 우주 느낌 */
    .stApp {
        background-image: linear-gradient(rgba(5, 10, 20, 0.95), rgba(5, 10, 20, 0.9)), url('https://cdn.pixabay.com/photo/2016/10/20/18/35/earth-1756274_1280.jpg');
        background-size: cover;
        background-attachment: fixed;
        color: #e0e0e0;
        font-family: "Times New Roman", serif;
    }
    
    /* 제목 스타일 */
    h1 {
        color: #d4af37; /* Gold */
        text-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
        font-weight: 700;
        letter-spacing: 1.5px;
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #0b1016;
        border-right: 1px solid #333;
    }
    
    /* 버튼 커스텀 */
    div.stButton > button {
        background-color: #15202b;
        color: #d4af37;
        border: 1px solid #d4af37;
        padding: 15px;
        font-size: 1rem;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #d4af37;
        color: #000;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
    }
    
    /* 정보 카드 */
    .info-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 8px;
        border-left: 3px solid #d4af37;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- [2. API 키 및 DB 설정] ---
try:
    NASA_KEY = st.secrets["NASA_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
except FileNotFoundError:
    st.error("🚨 보안 키(Secrets)가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

# DB 연결 함수
def get_db_connection():
    return sqlite3.connect('space_library_v2.db', check_same_thread=False)

# DB 초기화 (테이블 없으면 생성)
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 로그 테이블: 날짜/키워드, 제목, 설명, AI해석, 이미지URL
    c.execute('''
        CREATE TABLE IF NOT EXISTS library_logs (
            id TEXT PRIMARY KEY, 
            type TEXT,
            title TEXT,
            original_desc TEXT,
            ai_brief TEXT,
            img_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- [3. 사이드바: 탐사 통제실] ---
st.sidebar.title("🚀 탐사 통제실")
st.sidebar.markdown("---")

# 검색 모드 선택 (라디오 버튼)
search_mode = st.sidebar.radio(
    "탐사 방식 선택:",
    ("📅 날짜별 기록 (Date)", "🌌 테마별 탐사 (Category)")
)

st.sidebar.markdown("---")

# 변수 초기화
selected_date = None
selected_keyword = None
nasa_data = None

# 모드별 입력 UI
if search_mode == "📅 날짜별 기록 (Date)":
    st.sidebar.info("과거의 특정 날짜에 기록된 우주 사진을 인양합니다.")
    selected_date = st.sidebar.date_input("날짜 선택", date.today())
    query_id = str(selected_date) # DB 저장용 ID
    
else: # 테마별 탐사
    st.sidebar.info("NASA 데이터베이스에서 주제별 최고의 사진을 발굴합니다.")
    
    # 📌 [핵심] 카테고리 - 키워드 매핑 (NASA API가 확실히 주는 것들만 엄선)
    category_map = {
        "🌌 은하 (Galaxies)": "galaxy",
        "✨ 성운 (Nebula)": "nebula",
        "🪐 태양계 (Solar System)": "solar system",
        "🌑 블랙홀 (Black Hole)": "black hole",
        "🚀 우주 미션 (Missions)": "space launch",
        "👨‍🚀 우주비행사 (Astronauts)": "astronaut"
    }
    
    selected_category = st.sidebar.selectbox("주제 선택", list(category_map.keys()))
    selected_keyword = category_map[selected_category]
    query_id = f"CAT_{selected_keyword}_{date.today()}" # DB 저장용 ID (오늘 날짜 + 키워드)

# --- [4. 메인 로직: 데이터 인양] ---
st.title("🏛️ 우주도서관 (Space Library)")
st.caption("Universal Archive System powered by NASA & Gemini AI")

# 실행 버튼
btn_label = "🔭 기록 열람 (Retrieve)" if search_mode == "📅 날짜별 기록 (Date)" else "🛰️ 탐사 시작 (Explore)"

if st.button(btn_label, use_container_width=True):
    
    # UI 구획 나누기
    col_img, col_text = st.columns([1, 1.2])
    
    # 데이터 담을 변수들
    img_url, title, desc, ai_text = "", "", "", ""
    
    try:
        with st.spinner("📡 심우주 데이터 수신 중..."):
            
            # [시나리오 A] 날짜 검색 (APOD API)
            if search_mode == "📅 날짜별 기록 (Date)":
                url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&date={selected_date}"
                res = requests.get(url).json()
                
                if 'url' not in res:
                    st.error("해당 날짜의 데이터가 없습니다.")
                    st.stop()
                    
                img_url = res.get('hdurl', res.get('url'))
                title = res.get('title', '무제')
                desc = res.get('explanation', '')
                
            # [시나리오 B] 카테고리 검색 (NASA Image API)
            else:
                # NASA 검색 API (키워드로 이미지 100개 요청)
                search_url = f"https://images-api.nasa.gov/search?q={selected_keyword}&media_type=image"
                res = requests.get(search_url).json()
                
                items = res.get('collection', {}).get('items', [])
                
                if not items:
                    st.warning("해당 카테고리의 데이터가 없습니다.")
                    st.stop()
                
                # 🎲 [Pro 기능] 매번 똑같은 게 나오면 재미없으니 '랜덤'으로 하나 뽑음
                selected_item = random.choice(items[:50]) # 상위 50개 중 랜덤 1개
                
                data_core = selected_item['data'][0]
                link_core = selected_item['links'][0]
                
                title = data_core.get('title', '무제')
                desc = data_core.get('description', '상세 설명 없음')
                img_url = link_core.get('href')

            # --- [AI 사서의 브리핑 (공통 로직)] ---
            # DB에 저장된 분석이 있는지 확인 (API 비용 절약)
            # 여기서는 '랜덤 탐사'의 재미를 위해 카테고리 모드는 매번 새로 생성하게 할 수도 있음.
            # 일단은 매번 생성하는 구조로 갑니다.
            
            prompt = f"""
            당신은 '우주도서관'의 지적인 수석 사서입니다.
            아래 우주 사진 정보를 바탕으로 방문객에게 브리핑 리포트를 작성해주세요.
            
            [제목]: {title}
            [데이터]: {desc}
            
            [작성 형식]
            1. 📰 **헤드라인**: 호기심을 자극하는 한 문장 제목
            2. 📖 **지식의 서사**: 이 천체가 무엇인지, 왜 중요한지 인문학적이고 과학적으로 설명 (약 3~4문장)
            3. 🧬 **데이터 로그**: 
               - 관측 대상:
               - 핵심 특징:
            
            *어조: 정중하고 지적이며, 경이로움을 담아서.*
            *절대 해시태그(#)를 넣지 마시오.*
            """
            
            ai_response = model.generate_content(prompt)
            ai_text = ai_response.text
            
            # 화면 출력
            with col_img:
                st.image(img_url, use_container_width=True)
                st.markdown(f"""
                <div class="info-card">
                    <strong>📂 아카이브 태그</strong><br>
                    {selected_date if selected_date else selected_category}<br>
                    <span style='color:#888; font-size:0.8em;'>NASA Official Data</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 원본 보기 링크
                st.link_button("🔭 원본 고해상도 이미지", img_url, use_container_width=True)

            with col_text:
                st.subheader(f"📜 {title}")
                st.write(ai_text)
                
    except Exception as e:
        st.error(f"데이터 통신 중 오류 발생: {e}")

# --- [5. Footer] ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8rem;'>
    <strong>Space Library Project</strong> | Chief Librarian: Si eon Kim<br>
    Powered by NASA Open API & Google Gemini
</div>
""", unsafe_allow_html=True)

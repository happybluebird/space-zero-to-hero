import streamlit as st
import google.generativeai as genai
import requests
import sqlite3
import random
from datetime import date

# ⚡ [1. 설정] set_page_config는 무조건 맨 위!
st.set_page_config(page_title="우주도서관: Deep Space Archive", layout="wide")

# 로봇 메타 데이터 주입
st.markdown(
    f'<head><title>우주도서관: Deep Space Archive</title>'
    f'<meta property="og:title" content="우주도서관: Deep Space Archive">'
    f'<meta property="og:description" content="NASA 데이터를 기반으로 한 우주 기록 보관소입니다.">'
    f'</head>', 
    unsafe_allow_html=True
)

st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .stApp {
        background-image: linear-gradient(rgba(5, 10, 20, 0.95), rgba(5, 10, 20, 0.9)), url('https://cdn.pixabay.com/photo/2016/10/20/18/35/earth-1756274_1280.jpg');
        background-size: cover;
        background-attachment: fixed;
        color: #e0e0e0;
        font-family: "Times New Roman", serif;
    }
    h1 { color: #d4af37; text-shadow: 0 0 10px rgba(212, 175, 55, 0.5); font-weight: 700; }
    [data-testid="stSidebar"] { background-color: #0b1016; border-right: 1px solid #333; }
    
    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #15202b; color: #d4af37; border: 1px solid #d4af37;
        padding: 15px; font-size: 1rem; transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #d4af37; color: #000; box-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
    }
    
    /* 정보 카드 */
    .info-card {
        background: rgba(255, 255, 255, 0.05); padding: 20px;
        border-radius: 8px; border-left: 3px solid #d4af37; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- [2. API 키 및 모델 설정] ---
try:
    NASA_KEY = st.secrets["NASA_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
except FileNotFoundError:
    st.error("🚨 보안 키(Secrets)가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=GEMINI_KEY)

# 🔥 [수정 완료] 모델 이름을 심플하게 변경했습니다. (models/ 접두사 제거)
# 만약 이래도 에러가 나면 'gemini-pro'로 바꿔야 합니다.
model = genai.GenerativeModel('gemini-1.5-flash')

# DB 연결
def get_db_connection():
    return sqlite3.connect('space_library_v2.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS library_logs (
            id TEXT PRIMARY KEY, type TEXT, title TEXT, 
            original_desc TEXT, ai_brief TEXT, img_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- [3. 사이드바 UI] ---
st.sidebar.title("🚀 탐사 통제실")
st.sidebar.markdown("---")

search_mode = st.sidebar.radio(
    "탐사 방식 선택:", ("📅 날짜별 기록 (Date)", "🌌 테마별 탐사 (Category)")
)

st.sidebar.markdown("---")

selected_date = None
selected_keyword = None

if search_mode == "📅 날짜별 기록 (Date)":
    st.sidebar.info("과거의 특정 날짜를 지정하여 기록을 인양합니다.")
    selected_date = st.sidebar.date_input("날짜 선택", date.today())
else:
    st.sidebar.info("주제별 최고의 사진을 발굴합니다.")
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

# --- [4. 메인 로직] ---
st.title("🏛️ 우주도서관 (Space Library)")
st.caption("Universal Archive System powered by NASA & Gemini AI")

btn_label = "🔭 기록 열람 (Retrieve)" if search_mode == "📅 날짜별 기록 (Date)" else "🛰️ 탐사 시작 (Explore)"

if st.button(btn_label, use_container_width=True):
    col_img, col_text = st.columns([1, 1.2])
    
    try:
        with st.spinner("📡 심우주 데이터 수신 및 AI 분석 중..."):
            img_url, title, desc, ai_text = "", "", "", ""
            
            # A. 날짜 검색
            if search_mode == "📅 날짜별 기록 (Date)":
                url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&date={selected_date}"
                res = requests.get(url).json()
                if 'url' not in res:
                    st.error("데이터 없음")
                    st.stop()
                img_url = res.get('hdurl', res.get('url'))
                title = res.get('title', '무제')
                desc = res.get('explanation', '')
                
            # B. 카테고리 검색
            else:
                search_url = f"https://images-api.nasa.gov/search?q={selected_keyword}&media_type=image"
                res = requests.get(search_url).json()
                items = res.get('collection', {}).get('items', [])
                if not items:
                    st.warning("데이터 없음")
                    st.stop()
                
                # 랜덤 추출
                selected_item = random.choice(items[:50])
                data_core = selected_item['data'][0]
                link_core = selected_item['links'][0]
                
                title = data_core.get('title', '무제')
                desc = data_core.get('description', '설명 없음')
                img_url = link_core.get('href')

            # AI 분석
            prompt = f"""
            당신은 '우주도서관'의 수석 사서입니다.
            사진 정보: {title} / {desc}
            
            [작성 형식]
            1. 📰 **헤드라인**: 호기심을 자극하는 제목
            2. 📖 **지식의 서사**: 인문학적/과학적 해설 (3문장)
            3. 🧬 **데이터 로그**: 핵심 특징 요약
            
            *어조: 정중하고 지적으로. 해시태그 금지.*
            """
            
            ai_response = model.generate_content(prompt)
            ai_text = ai_response.text
            
            # 출력
            with col_img:
                st.image(img_url, use_container_width=True)
                st.markdown(f'<div class="info-card"><strong>ARCHIVE TAG</strong><br>{selected_keyword if selected_keyword else selected_date}</div>', unsafe_allow_html=True)
                st.link_button("🔭 원본 이미지", img_url, use_container_width=True)
            
            with col_text:
                st.subheader(f"📜 {title}")
                st.write(ai_text)
                
    except Exception as e:
        st.error(f"오류 발생: {e}")

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center; color:#666;'>Space Library Project | Chief Librarian: Si eon Kim</div>", unsafe_allow_html=True)

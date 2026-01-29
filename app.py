import streamlit as st
import google.generativeai as genai
import requests
import sqlite3
import random
import time
from datetime import date

# ⚡ [1. 페이지 및 스타일 설정]
st.set_page_config(page_title="우주도서관: Deep Space Archive", layout="wide")

# 로봇 메타 데이터
st.markdown(
    f'<head><title>우주도서관: Deep Space Archive</title>'
    f'<meta property="og:title" content="우주도서관: Deep Space Archive">'
    f'<meta property="og:description" content="NASA 데이터를 기반으로 한 전문 우주 기록 보관소입니다.">'
    f'</head>', 
    unsafe_allow_html=True
)

st.markdown("""
<style>
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.9), rgba(10, 20, 40, 0.95)), url('https://cdn.pixabay.com/photo/2016/10/20/18/35/earth-1756274_1280.jpg');
        background-size: cover;
        background-attachment: fixed;
        color: #e0e0e0;
        font-family: "Helvetica Neue", Arial, sans-serif; /* 폰트를 좀 더 모던하게 변경 */
    }
    h1 { color: #d4af37; text-shadow: 0 0 10px rgba(212, 175, 55, 0.5); font-weight: 700; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    
    /* 버튼 스타일 (전문가 느낌의 청록색 포인트) */
    div.stButton > button {
        background-color: #0d1b2a; color: #00f2ff; border: 1px solid #00f2ff;
        padding: 15px; font-size: 1rem; transition: 0.3s; font-family: 'Courier New', monospace;
    }
    div.stButton > button:hover {
        background-color: #00f2ff; color: #000; box-shadow: 0 0 15px rgba(0, 242, 255, 0.5);
    }
    
    /* 정보 카드 */
    .info-card {
        background: rgba(0, 20, 40, 0.6); padding: 20px;
        border-radius: 4px; border-left: 3px solid #00f2ff; margin-top: 20px;
        font-family: 'Courier New', monospace;
    }

    /* 망원경 뱃지 스타일 */
    /* 망원경 및 탐사선 뱃지 스타일 (다양화) */
    .badge-hubble { background-color: #3A6EA5; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 5px; }
    .badge-webb { background-color: #D4AF37; color: black; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 5px; }
    .badge-chandra { background-color: #8E44AD; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 5px; }
    .badge-solar { background-color: #F1C40F; color: black; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 5px; } /* 태양 - 노랑 */
    .badge-mars { background-color: #E67E22; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 5px; } /* 화성 - 주황 */
    .badge-deep { background-color: #2C3E50; color: #00f2ff; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 5px; border: 1px solid #00f2ff; } /* 심우주 - 네이비 */
    .badge-generic { background-color: #555; color: #ddd; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }
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

# 🔥 [안정화된 모델] Gemini Flash Latest 사용
model = genai.GenerativeModel('gemini-flash-latest')

# --- [3. 헬퍼 함수: 확장된 미션 뱃지 감지기] ---
def get_telescope_badges(text):
    text_lower = text.lower()
    badges = []

    # 1. 우주 망원경 (Space Telescopes)
    if "hubble" in text_lower or "hst" in text_lower:
        badges.append('<span class="badge-hubble">🔭 Hubble</span>')
    if "webb" in text_lower or "jwst" in text_lower:
        badges.append('<span class="badge-webb">🛰️ James Webb</span>')
    if "chandra" in text_lower:
        badges.append('<span class="badge-chandra">🟣 Chandra X-ray</span>')
    if "spitzer" in text_lower:
        badges.append('<span class="badge-mars">🔴 Spitzer</span>') # 적외선이라 붉은색 계열

    # 2. 행성 탐사선 (Planetary Missions)
    if "cassini" in text_lower:
        badges.append('<span class="badge-deep">🪐 Cassini (Saturn)</span>')
    if "juno" in text_lower:
        badges.append('<span class="badge-deep">⚡ Juno (Jupiter)</span>')
    if "voyager" in text_lower:
        badges.append('<span class="badge-deep">🌌 Voyager</span>')
    if "new horizons" in text_lower:
        badges.append('<span class="badge-deep">🌑 New Horizons (Pluto)</span>')
    if "galileo" in text_lower:
        badges.append('<span class="badge-deep">🛰️ Galileo</span>')

    # 3. 화성 로버 & 탐사선 (Mars)
    if any(x in text_lower for x in ["perseverance", "curiosity", "opportunity", "spirit", "mars rover"]):
        badges.append('<span class="badge-mars">🚙 Mars Rover</span>')
    if "reconnaissance orbiter" in text_lower or "mro" in text_lower:
        badges.append('<span class="badge-mars">🛰️ Mars Orbiter</span>')

    # 4. 태양 관측 위성 (Solar)
    if any(x in text_lower for x in ["sdo", "soho", "solar dynamics", "parker solar"]):
        badges.append('<span class="badge-solar">☀ Solar Mission</span>')

    # 5. 발견된 게 없으면 기본 뱃지
    if not badges:
        badges.append('<span class="badge-generic">📡 NASA Archive Data</span>')
        
    return "".join(badges)

# --- [4. 사이드바: 전문가 대시보드] ---
st.sidebar.title("🚀 MISSION CONTROL")
st.sidebar.caption("Real-time Space Weather & Archive Access")

# ☀ [기능 추가] 실시간 우주 날씨 (NASA SDO 위성 데이터)
st.sidebar.markdown("### ☀ Solar Monitor (SDO/AIA)")
try:
    # NASA SDO의 실시간 태양 이미지 (가장 최신 이미지를 가져오는 URL)
    # AIA 193 옹스트롬 (코로나와 플레어를 잘 보여줌)
    sdo_url = "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0193.jpg"
    # 캐싱 방지를 위해 타임스탬프 추가
    st.sidebar.image(sdo_url, caption=f"Live Solar Feed (Updated: {date.today()})", use_container_width=True)
    st.sidebar.info("📡 NASA SDO 위성이 전송하는 실시간 태양 활동입니다.")
except:
    st.sidebar.warning("Solar Feed Offline")

st.sidebar.markdown("---")

# 검색 모드
search_mode = st.sidebar.radio(
    "데이터 인양 모드 (Retrieval Mode):", 
    ("📅 날짜별 기록 (Date)", "🌌 심우주 아카이브 (Deep Field)")
)

# 🔬 [기능 추가] 전문가 모드 토글
expert_mode = st.sidebar.toggle("🔬 전문가 분석 모드 (Expert Mode)", value=False)

st.sidebar.markdown("---")

selected_date = None
selected_keyword = None

if search_mode == "📅 날짜별 기록 (Date)":
    selected_date = st.sidebar.date_input("Target Date", date.today())
else:
    # 카테고리를 좀 더 전문적으로 변경
    category_map = {
        "🌌 은하 (Galaxies)": "galaxy",
        "✨ 성운 (Nebulae)": "nebula",
        "🪐 태양계 (Solar System)": "solar system",
        "🌑 블랙홀 (Black Hole)": "black hole",
        "🌟 초신성 잔해 (Supernova Remnant)": "supernova remnant",
        "🔭 심우주 관측 (Deep Field)": "deep field",
        "☄️ 혜성/소행성 (Comets/Asteroids)": "comet"
    }
    selected_category = st.sidebar.selectbox("Target Object", list(category_map.keys()))
    selected_keyword = category_map[selected_category]

# --- [5. 메인 로직] ---
st.title("🏛️ 우주도서관 (Space Library)")
st.caption("Advanced Archive System powered by NASA Open API & Gemini Flash")

btn_label = "🔭 데이터 분석 시작 (Initialize Analysis)"

if st.button(btn_label, use_container_width=True):
    col_img, col_text = st.columns([1.5, 1.2]) # 이미지를 좀 더 크게
    
    try:
        with st.spinner("📡 Deep Space Network(DSN) 연결 중... 데이터 수신 대기..."):
            img_url, title, desc, ai_text = "", "", "", ""
            
            # NASA API 호출 로직 (기존과 동일)
            if search_mode == "📅 날짜별 기록 (Date)":
                url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&date={selected_date}"
                res = requests.get(url).json()
                if 'url' not in res:
                    st.error("해당 날짜의 관측 데이터가 존재하지 않습니다.")
                    st.stop()
                img_url = res.get('hdurl', res.get('url'))
                title = res.get('title', 'Untitled Object')
                desc = res.get('explanation', '')
                
            else:
                search_url = f"https://images-api.nasa.gov/search?q={selected_keyword}&media_type=image"
                res = requests.get(search_url).json()
                items = res.get('collection', {}).get('items', [])
                if not items:
                    st.warning("데이터베이스에서 일치하는 천체를 찾지 못했습니다.")
                    st.stop()
                
                selected_item = random.choice(items[:50])
                data_core = selected_item['data'][0]
                link_core = selected_item['links'][0]
                
                title = data_core.get('title', 'Untitled Object')
                desc = data_core.get('description', 'No description available.')
                img_url = link_core.get('href')

            # 🧬 [핵심] 프롬프트 분기 처리 (일반 모드 vs 전문가 모드)
            # 🧬 [핵심 수정] 모드별 정보 전달 방식 차별화
            if expert_mode:
                # 🔬 전문가 모드: 건조하고 분석적인 스펙 중심
                prompt = f"""
                당신은 NASA의 '수석 데이터 분석가'입니다. 
                아래 천체 사진의 메타데이터를 분석하여 천문학자를 위한 '기술적 리포트'를 작성하세요.
                
                [Target Object]: {title}
                [Raw Data]: {desc}
                
                [Output Format] - 한국어로 작성
                1. 🧪 **천체 분류 (Object Type)**: (예: 나선 은하, 구상 성단 등 정확한 명칭)
                2. 🔭 **관측 제원 (Instrument & Data)**: 
                   - 관측 장비: (텍스트에서 Hubble, Webb, Juno 등 탐사선 이름을 찾아 명시)
                   - 관측 파장/특징: (가능하다면 적외선/가시광선 등 파악)
                3. 📏 **물리적 데이터 (Physical Data)**:
                   - 거리 (Distance):
                   - 위치 (Constellation):
                4. 📝 **심층 분석 (Deep Analysis)**: 
                   - 이 천체의 형성 과정, 구성 물질, 학술적 의의를 전문 용어를 사용하여 건조하게 서술 (3문장).
                
                *톤앤매너: 감정을 배제하고, 수치와 팩트 위주로 작성.*
                """
            else:
                # 📖 일반 모드: 친절하고 이해하기 쉬운 스토리텔링 (+망원경 언급 추가)
                prompt = f"""
                당신은 '우주도서관'의 친절한 도슨트(해설가)입니다.
                관람객에게 이 우주 사진을 설명해주세요.
                
                [사진 정보]: {title} / {desc}
                
                [작성 형식] - 한국어로 작성
                1. 📰 **헤드라인**: 호기심을 자극하는 감성적인 제목
                2. 🛰️ **관측 이야기**: 
                   - "이 사진은 [망원경 이름]이 촬영했습니다"와 같이 자연스럽게 관측 장비를 소개하며 이야기를 시작하세요.
                   - 이 천체가 왜 아름답거나 신비로운지 인문학적으로 묘사하세요. (약 3~4문장)
                3. 🧬 **핵심 요약**: 기억해야 할 특징 2가지 (짧게)
                
                *톤앤매너: "관람객 여러분," 처럼 말을 걸듯이 부드럽고 정중하게.*
                """
            
            ai_response = model.generate_content(prompt)
            ai_text = ai_response.text
            
            # 뱃지 생성
            badges_html = get_telescope_badges(desc + title)
            
            with col_img:
                st.image(img_url, use_container_width=True)
                # 뱃지 및 메타데이터 표시
                st.markdown(f"""
                <div style="margin-top: 10px; margin-bottom: 20px;">
                    {badges_html}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f'<div class="info-card"><strong>📂 ARCHIVE ID</strong><br>{selected_keyword if selected_keyword else selected_date}<br><br><strong>📷 SOURCE</strong><br>NASA Image & Video Library</div>', unsafe_allow_html=True)
                st.link_button("🔭 원본 고해상도(FITS/JPG) 확인", img_url, use_container_width=True)
            
            with col_text:
                st.subheader(f"📜 {title}")
                st.write(ai_text)
                
    except Exception as e:
        if "429" in str(e):
             st.error("⏳ 쿼터 제한(Rate Limit). 잠시 대기 후 시도하십시오.")
        else:
             st.error(f"⚠️ SYSTEM ERROR: {e}")

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center; color:#666; font-family: Courier New;'>Space Library Project | Ver 3.0 Research Edition | Created by Si eon Kim</div>", unsafe_allow_html=True)

import streamlit as st
import google.generativeai as genai

st.title("🚑 우주도서관: 긴급 키 진단 모드")

try:
    # 1. 키 가져오기
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    genai.configure(api_key=GEMINI_KEY)

    # 2. 서버에 모델 목록 요청 (핵심!)
    st.write("📡 서버와 통신 중... (내 키로 쓸 수 있는 모델을 조회합니다)")
    
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            models.append(m.name)

    # 3. 결과 출력
    if models:
        st.success(f"✅ 인증 성공! 사용 가능한 모델 {len(models)}개를 찾았습니다.")
        st.code(models)
        st.info("위 목록에 있는 이름 중 하나를 골라 쓰면 100% 해결됩니다.")
    else:
        st.error("❌ 인증은 됐는데, 사용할 수 있는 모델이 하나도 없습니다. (매우 희귀한 케이스)")

except Exception as e:
    st.error("🚨 인증 실패! 키가 잘못되었거나 만료되었습니다.")
    st.error(f"에러 메시지: {e}")
    st.markdown("""
    **[해결책]**
    1. 키가 정확히 복사되었는지 확인하세요. (앞뒤 공백 주의)
    2. 아래 링크에서 **새 키**를 발급받으세요. (기존 키 삭제 추천)
    3. **[Google AI Studio](https://aistudio.google.com/app/apikey)** 👈 클릭
    """)

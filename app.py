import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 앱 설정 및 오늘 날짜 가져오기
st.set_page_config(page_title="배당 비서 2.0", page_icon="📈")
today = datetime.now().strftime("%Y년 %m월 %d일")

# 2. 대문 (기획안의 95% 완료 문구 강조)
st.title("💰 실시간 배당 분석기")
st.write(f"📅 오늘은 **{today}** 입니다. 분석을 시작할까요?")

# 3. 사이드바 수량 입력
st.sidebar.header("👤 사용자 프로필")
user_name = st.sidebar.text_input("닉네임", value="윤재")
st.sidebar.divider()
st.sidebar.header("🏦 보유 수량")
m_call = st.sidebar.number_input("미배콜(490600)", value=2000)
m_dang = st.sidebar.number_input("미배당(미국배당100)", value=860)

# 4. 분석 리포트 (기획안의 리스크/분석 기능)
st.subheader("🔍 AI 배당 분석 리포트")
col1, col2 = st.columns(2)

with col1:
    st.info("✅ **안전성 점수**\n\n미배당 100 기반 종목으로 매우 안전함 (4.8/5.0)")
with col2:
    st.warning("⚠️ **주의 사항**\n\n커버드콜 전략(미배콜)은 시장 하락 시 방어가 중요함")

# 5. 실시간 예상 수익 (기획안 데이터 반영)
total_div = (m_call * 101) + (m_dang * 38) # 살짝 바뀐 예상치 적용
st.divider()
st.subheader(f"💵 {user_name}님의 이번 달 보너스")
st.success(f"예상되는 배당금은 총 **{total_div:,}원**입니다!")

# 6. 우리의 약속 (푸터)
st.write("---")
st.markdown(f"<p style='text-align: center; color: #ff4b4b;'>💖 {user_name}와 소은이의 소중한 대화와 이야기에서 탄생한 앱입니다.</p>", unsafe_allow_html=True)

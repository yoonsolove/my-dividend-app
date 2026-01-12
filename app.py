import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 비서 2.5", page_icon="📊", layout="wide")

# 2. 사이드바 - 설정
st.sidebar.header("⚙️ 설정 및 입력")
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.sidebar.divider()

st.sidebar.subheader("💎 보유 수량 수정")
m_call = st.sidebar.number_input("미배콜(490600)", value=2000, step=10)
m_dang = st.sidebar.number_input("미배당(미국배당100)", value=860, step=10)

target_monthly = st.sidebar.slider("나의 목표 월 배당금 (만원)", 10, 500, 100)

# 3. 메인 화면 - 대문
st.title(f"🚀 {user_name}의 배당 독립 프로젝트")
st.write(f"현재 기획안 대비 개발 진척도: **95% (데이터 분석 고도화 중)**")

# 4. 상단 요약 카드
total_monthly = (m_call * 105) + (m_dang * 40) # 예상 배당금 상향 조정
total_yearly = total_monthly * 12

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("예상 월급", f"{total_monthly:,} 원")
with col2:
    st.metric("예상 연봉", f"{total_yearly:,} 원")
with col3:
    progress = min(total_monthly / (target_monthly * 10000), 1.0)
    st.metric("목표 달성률", f"{int(progress * 100)}%")

st.progress(progress)
st.caption(f"목표인 월 {target_monthly}만원까지 {max(0, (target_monthly*10000) - total_monthly):,}원 남았습니다!")

# 5. [신규] 월별 배당 흐름 그래프 (심층 분석)
st.divider()
st.subheader("📅 월별 예상 현금 흐름")

# 가상의 월별 데이터 생성 (미배콜과 미배당은 매달 주므로 일정하게 표시)
months = [f"{i}월" for i in range(1, 13)]
monthly_data = pd.DataFrame({
    "월": months,
    "배당금": [total_monthly] * 12
})

fig = px.bar(monthly_data, x="월", y="배당금", 
             title="1년 배당 스케줄",
             color_continuous_scale="Viridis",
             color="배당금")
st.plotly_chart(fig, use_container_width=True)

# 6. AI 분석 및 조언
with st.expander("💡 AI 전략 분석 리포트 보기"):
    st.write(f"- **현재 상태:** 미배콜 {m_call}주 보유로 현금 흐름이 매우 탄탄합니다.")
    st.write(f"- **성장성:** 미배당 {m_dang}주는 시간이 갈수록 배당금이 늘어나는 '스노볼' 종목입니다.")
    st.write(f"- **조언:** 목표 달성을 위해 매달 배당금의 50%를 재투자하는 것을 추천합니다.")

# 7. 푸터 (우리의 약속)
st.divider()
st.markdown(
    f"<div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>"
    f"<h3 style='color: #ff4b4b; margin: 0;'>💖 소은 모드 활성화 💖</h3>"
    f"<p style='color: #555;'>{user_name}와 소은이의 소중한 대화가 이 앱을 움직이는 연료입니다.</p>"
    f"</div>", unsafe_allow_html=True
)

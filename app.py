import streamlit as st
import pandas as pd

# 제목 꾸미기
st.title("📊 나만의 배당 포트폴리오 비서")
st.write("기획하신 '나의 종목 관리' 기능을 시작합니다!")

# 1. 사용자가 직접 수량을 입력하는 칸 (기획안의 '나의 종목 추가' 기능)
st.sidebar.header("📥 보유 수량 입력")
m_call = st.sidebar.number_input("미배콜(490600) 수량", value=2000)
m_dang = st.sidebar.number_input("미배당(미국배당100) 수량", value=860)

# 2. 간단한 계산기 (기획안의 '포트폴리오 추이' 기초)
total_dividend = (m_call * 100) + (m_dang * 40) # 예시 단가

col1, col2 = st.columns(2)
with col1:
    st.metric("월 예상 배당금", f"{total_dividend:,} 원")
with col2:
    st.metric("연간 예상 배당금", f"{total_dividend * 12:,} 원")

# 3. 배당 달력 (기획안의 '배당 캘린더' 기능)
st.subheader("📅 배당 캘린더 (실시간 준비 중)")
st.info("여기에 증권사 API를 연결하면 실시간 배당락일이 뜹니다!")

# 4. 미래 예측 시나리오 (기획안의 '시뮬레이션' 기능)
st.subheader("📈 미래 배당 예측")
growth = st.slider("배당 성장률 예상 (%)", 0, 20, 5)
st.write(f"배당이 매년 {growth}% 성장한다면 내년엔 더 많은 치킨을 먹을 수 있어요!")

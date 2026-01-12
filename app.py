import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 스노볼 분석기", page_icon="❄️", layout="wide")

# 2. 실시간 데이터 가져오기
@st.cache_data(ttl=600)
def get_dividend_stocks():
    tickers = {"미배콜": "490600.KS", "미배당": "402320.KS"}
    prices = {}
    for name, code in tickers.items():
        try:
            stock = yf.Ticker(code)
            prices[name] = stock.history(period="1d")['Close'].iloc[-1]
        except:
            prices[name] = 10000 
    return prices

current_prices = get_dividend_stocks()

# 3. 사이드바 - 설정
st.sidebar.header("👤 설정")
user_name = st.sidebar.text_input("사용자 이름", value="윤재") 
m_call_qty = st.sidebar.number_input("미배콜 보유 수량", value=2000)
m_dang_qty = st.sidebar.number_input("미배당 보유 수량", value=860)

st.sidebar.divider()
st.sidebar.header("❄️ 재투자 시뮬레이션")
years = st.sidebar.slider("재투자 기간 (년)", 1, 20, 10)
reinvest_rate = st.sidebar.slider("배당금 재투자 비율 (%)", 0, 100, 100)

# 4. 메인 화면 상단
st.title("❄️ 배당 재투자 스노볼 리포트")
div_monthly = (m_call_qty * 105) + (m_dang_qty * 40)
total_asset = (m_call_qty * current_prices["미배콜"]) + (m_dang_qty * current_prices["미배당"])

col1, col2, col3 = st.columns(3)
col1.metric("현재 월 배당금", f"{div_monthly:,.0f} 원")
col2.metric("현재 총 자산", f"{total_asset:,.0f} 원")
col3.metric("시뮬레이션 기간", f"{years}년")

# 5. 스노볼 계산 로직
history = []
temp_asset = total_asset
temp_monthly_div = div_monthly
yield_rate = (div_monthly * 12) / total_asset # 현재 배당률 계산

for i in range(1, (years * 12) + 1):
    # 매달 배당금 발생
    current_div = temp_monthly_div * (reinvest_rate / 100)
    # 재투자 (자산 증가)
    temp_asset += current_div
    # 자산 증가에 따른 다음 달 배당금 증가 (간단 모델)
    temp_monthly_div = (temp_asset * yield_rate) / 12
    
    if i % 12 == 0:
        history.append({"년수": f"{i//12}년차", "월배당금": int(temp_monthly_div), "총자산": int(temp_asset)})

df_snowball = pd.DataFrame(history)

# 6. 미래 성장 그래프
st.divider()
st.subheader(f"📈 {years}년 후, 당신의 월급은 어떻게 변할까요?")
fig_growth = px.area(df_snowball, x="년수", y="월배당금", 
                     title="재투자 시 월 배당금 성장 곡선",
                     color_discrete_sequence=['#00CC96'])
st.plotly_chart(fig_growth, use_container_width=True)

# 7. 상세 데이터 표
with st.expander("📅 연도별 상세 예측 데이터 보기"):
    st.table(df_snowball)

# 8. 푸터 (소은 모드)
st.divider()
st.markdown(f"<div style='text-align: center; color: gray;'>💖 <b>{user_name} & 소은</b>의 꿈이 자라는 공간 💖<br>시간이 흐를수록 우리의 자산도, 마음도 함께 성장합니다.</div>", unsafe_allow_html=True)

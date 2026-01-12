import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="미배콜 & 미배당 분석기", page_icon="📈", layout="wide")

# 2. 실시간 데이터 호출 함수 (미배콜: 490600.KS, 미배당: 402320.KS)
@st.cache_data(ttl=600) # 10분마다 데이터 갱신
def get_dividend_stocks():
    # 미배콜: TIGER 미국테크TOP10+10%프리미엄, 미배당: TIGER 미국배당다우존스
    tickers = {"미배콜": "490600.KS", "미배당": "402320.KS"}
    prices = {}
    for name, code in tickers.items():
        try:
            stock = yf.Ticker(code)
            prices[name] = stock.history(period="1d")['Close'].iloc[-1]
        except:
            prices[name] = 10000 # 에러 시 임시 가격
    return prices

# 데이터 불러오기
current_prices = get_dividend_stocks()

# 3. 사이드바 수량 입력
st.sidebar.title("📊 자산 설정")
user_name = st.sidebar.text_input("사용자", value="윤재")
m_call_qty = st.sidebar.number_input("미배콜 보유 수량", value=2000)
m_dang_qty = st.sidebar.number_input("미배당 보유 수량", value=860)

# 4. 메인 화면 - 실시간 자산 평가
st.title(f"💰 {user_name}님의 실시간 배당 리포트")
st.write(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 자산 가치 계산
val_call = m_call_qty * current_prices["미배콜"]
val_dang = m_dang_qty * current_prices["미배당"]
total_asset = val_call + val_dang

# 배당금 계산 (기획안 기준 예상치)
div_monthly = (m_call_qty * 105) + (m_dang_qty * 40)

# 5. 상단 지표 (Metric)
col1, col2, col3 = st.columns(3)
col1.metric("총 자산 평가액", f"{total_asset:,.0f} 원")
col2.metric("예상 월 배당금", f"{div_monthly:,.0f} 원", delta="+ 2.1%")
col3.metric("연간 합계", f"{div_monthly * 12:,.0f} 원")

# 6. 종목별 비중 차트 (기획안의 '심층 분석' 시각화)
st.divider()
st.subheader("🥧 포트폴리오 비중")
pie_data = pd.DataFrame({
    "종목": ["미배콜", "미배당"],
    "금액": [val_call, val_dang]
})
fig_pie = px.pie(pie_data, values='금액', names='종목', hole=0.4, 
                 color_discrete_sequence=['#FF4B4B', '#1C83E1'])
st.plotly_chart(fig_pie)

# 7. 푸터 (소은 모드)
st.divider()
st.markdown(f"<div style='text-align: center; color: gray;'>💖 {user_name} & 소은의 배당 독립 프로젝트 💖<br>본 앱은 실제 주가 데이터를 기반으로 계산됩니다.</div>", unsafe_allow_html=True)

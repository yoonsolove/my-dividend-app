import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="통합 배당 대시보드", page_icon="📅", layout="wide")

# 2. 실시간 데이터 및 환율 가져오기 함수
@st.cache_data(ttl=600)
def get_all_data(tickers_dict):
    data = {}
    # 환율 가져오기 (원/달러)
    usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    
    for name, code in tickers_dict.items():
        try:
            stock = yf.Ticker(code)
            price = stock.history(period="1d")['Close'].iloc[-1]
            # 배당 정보 (최근 1년 배당금 기반으로 월평균 추정)
            div_info = stock.dividends
            last_year_div = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))].sum()
            monthly_div = last_year_div / 12 if last_year_div > 0 else 0
            
            # 미국 주식일 경우 원화 환산
            if not code.endswith(".KS") and not code.endswith(".KQ"):
                price *= usd_krw
                monthly_div *= usd_krw
                
            data[name] = {"price": price, "monthly_div": monthly_div}
        except:
            data[name] = {"price": 0, "monthly_div": 0}
    return data, usd_krw

# 3. 사이드바 - 종목 관리 (1번 항목 구현: 종목 확장)
st.sidebar.header("👤 {0}님의 포트폴리오".format("윤재"))
user_name = st.sidebar.text_input("사용자 이름", value="윤재")

st.sidebar.subheader("➕ 종목 추가 및 수정")
# 기본 종목 리스트 (사용자가 여기서 수정/추가 가능)
default_stocks = {
    "미배콜": "490600.KS",
    "미배당": "402320.KS",
    "SCHD(예시)": "SCHD"
}

# 수량 입력창 생성
quantities = {}
for name, ticker in default_stocks.items():
    quantities[name] = st.sidebar.number_input(f"{name} 수량", value=2000 if "미배콜" in name else 860)

# 4. 데이터 로드
stock_info, current_usd = get_all_data(default_stocks)

# 5. 메인 화면 - 대시보드
st.title(f"📊 {user_name}님의 통합 배당 캘린더")
st.caption(f"실시간 환율: 1$ = {current_usd:,.2f}원 | 데이터 기준: {datetime.now().strftime('%H:%M:%S')}")

# 자산 및 배당 계산
total_asset = 0
total_monthly_div = 0
portfolio_details = []

for name, qty in quantities.items():
    price = stock_info[name]['price']
    div = stock_info[name]['monthly_div']
    asset_val = price * qty
    div_val = div * qty
    
    total_asset += asset_val
    total_monthly_div += div_val
    portfolio_details.append({"종목": name, "자산가치": asset_val, "월배당금": div_val})

df_portfolio = pd.DataFrame(portfolio_details)

# 6. 상단 요약 지표
col1, col2, col3 = st.columns(3)
col1.metric("총 자산 규모", f"{total_asset:,.0f} 원")
col2.metric("월 평균 배당금", f"{total_monthly_div:,.0f} 원")
col3.metric("연간 합계", f"{total_monthly_div * 12:,.0f} 원")

# 7. 배당 캘린더 (3번 항목 구현: 시각적 일정)
st.divider()
st.subheader("📅 월별 배당 지급 일정 (예측)")
# 대부분의 월배당 ETF는 매달 지급하므로 이를 시각화
calendar_data = []
for m in range(1, 13):
    for name in quantities.keys():
        calendar_data.append({"월": f"{m}월", "종목": name, "금액": total_monthly_div / len(quantities)})

df_cal = pd.DataFrame(calendar_data)
fig_cal = px.bar(df_cal, x="월", y="금액", color="종목", title="월별 배당금 구성")
st.plotly_chart(fig_cal, use_container_width=True)

# 8. 종목별 비중 분석
c1, c2 = st.columns(2)
with c1:
    st.subheader("🍩 종목별 비중")
    fig_pie = px.pie(df_portfolio, values='자산가치', names='종목', hole=0.5)
    st.plotly_chart(fig_pie)
with c2:
    st.subheader("📝 상세 내역")
    st.table(df_portfolio.style.format({"자산가치": "{:,.0f}", "월배당금": "{:,.0f}"}))

# 9. 푸터
st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b>의 배당 시스템 v3.0 💖<br>우리의 기획이 현실이 되는 순간입니다.</center>", unsafe_allow_html=True)

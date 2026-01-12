import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="통합 배당 대시보드", page_icon="📅", layout="wide")

# 2. 실시간 데이터 가져오기 (안전장치 강화)
@st.cache_data(ttl=600)
def get_all_data(tickers_dict):
    data = {}
    # 환율 가져오기
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    except:
        usd_krw = 1450.0 # 환율 실패 시 기본값
    
    for name, code in tickers_dict.items():
        try:
            stock = yf.Ticker(code)
            # 주가 가져오기
            hist = stock.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else 10000.0 # 주가 실패 시 1만원
            
            # 배당금 계산 (야후 데이터가 없으면 우리가 정한 수치 사용)
            div_info = stock.dividends
            if not div_info.empty:
                last_year_div = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))].sum()
                monthly_div = last_year_div / 12
            else:
                # 야후 파이낸스에 배당 정보가 없을 때의 종목별 기본값
                defaults = {"미배콜": 105, "미배당": 40, "SCHD(예시)": 0.2} 
                monthly_div = defaults.get(name, 0)

            # 미국 주식일 경우 원화 환산
            if not (code.endswith(".KS") or code.endswith(".KQ")):
                price *= usd_krw
                monthly_div *= usd_krw
                
            data[name] = {"price": price, "monthly_div": monthly_div}
        except:
            data[name] = {"price": 10000.0, "monthly_div": 50.0}
    return data, usd_krw

# 3. 사이드바 설정
st.sidebar.header("👤 포트폴리오 설정")
user_name = st.sidebar.text_input("사용자 이름", value="윤재")

# 종목 리스트
default_stocks = {
    "미배콜": "490600.KS",
    "미배당": "402320.KS",
    "SCHD(예시)": "SCHD"
}

quantities = {}
for name in default_stocks.keys():
    default_val = 2000 if "미배콜" in name else 860
    quantities[name] = st.sidebar.number_input(f"{name} 수량", value=default_val)

# 데이터 로드
stock_info, current_usd = get_all_data(default_stocks)

# 4. 메인 화면
st.title(f"📊 {user_name}님의 통합 배당 캘린더")
st.caption(f"실시간 환율: 1$ = {current_usd:,.2f}원 | 기준 시각: {datetime.now().strftime('%H:%M:%S')}")

# 계산 로직
portfolio_details = []
total_asset = 0
total_monthly_div = 0

for name, qty in quantities.items():
    info = stock_info.get(name, {"price": 0, "monthly_div": 0})
    asset_val = info['price'] * qty
    div_val = info['monthly_div'] * qty
    
    total_asset += asset_val
    total_monthly_div += div_val
    portfolio_details.append({"종목": name, "자산가치": asset_val, "월배당금": div_val})

df_portfolio = pd.DataFrame(portfolio_details)

# 5. 요약 지표
col1, col2, col3 = st.columns(3)
col1.metric("총 자산 규모", f"{total_asset:,.0f} 원")
col2.metric("월 평균 배당금", f"{total_monthly_div:,.0f} 원")
col3.metric("연간 합계", f"{total_monthly_div * 12:,.0f} 원")

# 6. 월별 배당 그래프
st.divider()
st.subheader("📅 월별 배당 지급 예측")
months = [f"{i}월" for i in range(1, 13)]
cal_list = []
for m in months:
    for _, row in df_portfolio.iterrows():
        cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당금"]})
df_cal = pd.DataFrame(cal_list)

fig_cal = px.bar(df_cal, x="월", y="금액", color="종목", 
                 color_discrete_sequence=px.colors.qualitative.Pastel)
st.plotly_chart(fig_cal, use_container_width=True)

# 7. 비중 분석 및 상세 표
c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("🍩 종목별 비중")
    fig_pie = px.pie(df_portfolio, values='자산가치', names='종목', hole=0.5)
    st.plotly_chart(fig_pie)
with c2:
    st.subheader("📝 상세 내역")
    st.dataframe(df_portfolio.style.format({"자산가치": "{:,.0f}", "월배당금": "{:,.0f}"}), use_container_width=True)

# 8. 푸터
st.divider()
st.markdown(f"<center>💖 {user_name} & 소은의 배당 시스템 v3.1 💖</center>", unsafe_allow_html=True)

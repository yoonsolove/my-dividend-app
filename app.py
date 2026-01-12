import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 스노볼 시뮬레이터", page_icon="❄️", layout="wide")

# 2. 데이터 가져오기 함수
@st.cache_data(ttl=300)
def get_stock_details(ticker_code):
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0}
    price = price_map.get(ticker_code, 10000.0)
    monthly_div = div_map.get(ticker_code, 50.0)
    
    try:
        stock = yf.Ticker(ticker_code)
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent_divs.empty:
                monthly_div = recent_divs.sum() / 12
        return price, monthly_div
    except:
        return price, monthly_div

# 3. 세션 상태 관리
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 UI
st.sidebar.header("👤 사용자 설정")
user_name = st.sidebar.text_input("이름", value="윤재")

st.sidebar.divider()
st.sidebar.subheader("📈 적립식 투자 설정")
add_monthly = st.sidebar.slider("매달 추가 투자금 (만원)", 0, 500, 50, step=10)
reinvest_rate = st.sidebar.slider("배당금 재투자 비율 (%)", 0, 100, 100)
sim_years = st.sidebar.slider("시뮬레이션 기간 (년)", 1, 40, 20)

st.sidebar.divider()
with st.sidebar.expander("📦 보유 종목 수정"):
    for i, stock in enumerate(st.session_state.stock_list):
        new_qty = st.number_input(f"{stock['name']} 수량", value=stock['qty'], key=f"q_{i}")
        st.session_state.stock_list[i]['qty'] = new_qty

# 5. 현재 데이터 계산
portfolio_data = []
total_asset = 0
current_monthly_div = 0
for s in st.session_state.stock_list:
    p, d = get_stock_details(s['ticker'])
    asset_val = p * s['qty']
    div_val = d * s['qty']
    total_asset += asset_val
    current_monthly_div += div_val
    portfolio_data.append({"종목": s['name'], "자산": asset_val, "배당": div_val})

# 6. 스노볼 시뮬레이션 로직 (핵심!)
sim_data = []
temp_asset = total_asset
# 현재 포트폴리오의 평균 배당수익률 계산
avg_yield = (current_monthly_div * 12) / total_asset if total_asset > 0 else 0.12 

for month in range(1, (sim_years * 12) + 1):
    # 1. 배당금 발생
    monthly_dividend = (temp_asset * avg_yield) / 12
    # 2. 재투자액 계산 (배당 재투자 + 매달 추가 적립액)
    reinvest_amount = (monthly_dividend * (reinvest_rate / 100)) + (add_monthly * 10000)
    # 3. 자산 증식
    temp_asset += reinvest_amount
    
    if month % 12 == 0:
        year = month // 12
        sim_data.append({
            "경과년수": f"{year}년차",
            "총자산": int(temp_asset),
            "월배당금": int((temp_asset * avg_yield) / 12)
        })

df_sim = pd.DataFrame(sim_data)

# 7. 메인 화면 출력
st.title(f"🚀 {user_name}님의 인생 역전 스노볼 시뮬레이션")
st.info(f"매달 **{add_monthly}만원**씩 추가 투자하고, 배당금을 **{reinvest_rate}%** 재투자할 경우의 시나리오입니다.")

c1, c2, c3 = st.columns(3)
final_asset = df_sim.iloc[-1]['총자산'] if not df_sim.empty else 0
final_div = df_sim.iloc[-1]['월배당금'] if not df_sim.empty else 0

c1.metric(f"{sim_years}년 후 총 자산", f"{final_asset:,.0f} 원")
c2.metric(f"{sim_years}년 후 월 배당금", f"{final_div:,.0f} 원")
c3.metric("현재 대비 성장률", f"{(final_asset/total_asset*100):,.0f}%" if total_asset > 0 else "0%")

# 그래프
st.divider()
st.subheader("📈 미래 자산 성장 곡선")
fig_asset = px.area(df_sim, x="경과년수", y="총자산", title="시간이 흐를수록 가팔라지는 자산의 속도",
                    color_discrete_sequence=['#1C83E1'])
st.plotly_chart(fig_asset, use_container_width=True)

st.subheader("💰 미래 월급(배당금) 변화")
fig_div = px.line(df_sim, x="경과년수", y="월배당금", title="나의 제2의 월급 성장기",
                  markers=True, color_discrete_sequence=['#FF4B4B'])
st.plotly_chart(fig_div, use_container_width=True)

# 상세 데이터
with st.expander("📅 연도별 상세 예측 지표 보기"):
    st.table(df_sim)

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b>의 미래 설계 시스템 v4.0 💖<br>꾸준함이 마법을 만듭니다.</center>", unsafe_allow_html=True)

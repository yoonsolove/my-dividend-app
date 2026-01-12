import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 통합 관리 시스템", page_icon="📈", layout="wide")

# 2. 데이터 가져오기 함수 (배당락일 포함)
@st.cache_data(ttl=300)
def get_stock_details(ticker_code):
    # 서버 응답 없을 때를 대비한 기본값
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0}
    
    price = price_map.get(ticker_code, 10000.0)
    monthly_div = div_map.get(ticker_code, 50.0)
    ex_date_str = "매월 말일경"
    
    try:
        stock = yf.Ticker(ticker_code)
        # 주가
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
        
        # 배당락일
        try:
            ex_div_raw = stock.info.get('exDividendDate')
            if ex_div_raw:
                ex_date_str = datetime.fromtimestamp(ex_div_raw).strftime('%Y-%m-%d')
            elif ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"):
                ex_date_str = "매월 말일경"
        except:
            ex_date_str = "매월/분기말"

        # 배당금
        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent_divs.empty:
                monthly_div = recent_divs.sum() / 12
        
        return price, monthly_div, ex_date_str
    except:
        return price, monthly_div, ex_date_str

# 3. 세션 상태 초기화 (종목 리스트)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 UI
user_name = st.sidebar.text_input("사용자 이름", value="윤재")

st.sidebar.divider()
st.sidebar.subheader("➕ 새 종목 추가")
with st.sidebar.container():
    new_name = st.text_input("종목명 (예: 슈드)")
    new_ticker = st.text_input("티커 (예: SCHD)")
    new_qty = st.number_input("수량 설정", min_value=0, value=100)
    if st.button("포트폴리오에 추가"):
        if new_name and new_ticker:
            st.session_state.stock_list.append({"name": new_name, "ticker": new_ticker, "qty": new_qty})
            st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📦 보유 종목 관리")
for i, stock in enumerate(st.session_state.stock_list):
    with st.sidebar.expander(f"{stock['name']} ({stock['ticker']})"):
        # 수량 수정
        u_qty = st.number_input(f"수량 변경", value=stock['qty'], key=f"q_{i}")
        if u_qty != stock['qty']:
            st.session_state.stock_list[i]['qty'] = u_qty
            st.rerun()
        # 삭제 버튼
        if st.button(f"🗑️ 삭제하기", key=f"del_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📊 시뮬레이션 설정")
add_monthly = st.sidebar.slider("매달 추가 투자금 (만원)", 0, 500, 50, step=10)
reinvest_rate = st.sidebar.slider("배당금 재투자 비율 (%)", 0, 100, 100)
sim_years = st.sidebar.slider("시뮬레이션 기간 (년)", 1, 40, 20)

# 5. 데이터 계산
portfolio_data = []
total_asset = 0
current_monthly_div = 0
for s in st.session_state.stock_list:
    p, d, ex = get_stock_details(s['ticker'])
    val = p * s['qty']
    div_val = d * s['qty']
    total_asset += val
    current_monthly_div += div_val
    portfolio_data.append({"종목": s['name'], "현재가": p, "배당락일": ex, "자산가치": val, "월배당": div_val})

df_portfolio = pd.DataFrame(portfolio_data)

# 6. 상단 섹션: 현재 현황
st.title(f"💰 {user_name}님의 배당 대시보드")
c1, c2, c3 = st.columns(3)
c1.metric("현재 총 자산", f"{total_asset:,.0f} 원")
c2.metric("월 예상 배당", f"{current_monthly_div:,.0f} 원")
c3.metric("연 예상 배당", f"{current_monthly_div*12:,.0f} 원")

st.divider()
t1, t2 = st.tabs(["📋 종목 상세 (배당락일 포함)", "📅 배당 캘린더"])
with t1:
    sc1, sc2 = st.columns([1.8, 1])
    with sc1:
        st.dataframe(df_portfolio.style.format({"현재가": "{:,.0f}", "자산가치": "{:,.0f}", "월배당": "{:,.0f}"}), use_container_width=True)
    with sc2:
        st.plotly_chart(px.pie(df_portfolio, values='자산가치', names='종목', hole=0.4, title="자산 비중"), use_container_width=True)

with t2:
    months = [f"{i}월" for i in range(1, 13)]
    cal_list = []
    for m in months:
        for _, row in df_portfolio.iterrows():
            cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="연간 배당 흐름"), use_container_width=True)

# 7. 하단 섹션: 시뮬레이션
st.divider()
st.subheader("❄️ 미래 성장 시뮬레이션")
sim_data = []
temp_asset = total_asset
avg_yield = (current_monthly_div * 12) / total_asset if total_asset > 0 else 0.12 

for month in range(1, (sim_years * 12) + 1):
    monthly_dividend = (temp_asset * avg_yield) / 12
    reinvest_amount = (monthly_dividend * (reinvest_rate / 100)) + (add_monthly * 10000)
    temp_asset += reinvest_amount
    if month % 12 == 0:
        sim_data.append({"경과년수": f"{month//12}년", "총자산": int(temp_asset), "월배당금": int((temp_asset * avg_yield) / 12)})

df_sim = pd.DataFrame(sim_data)
sc1, sc2 = st.columns(2)
with sc1:
    st.plotly_chart(px.area(df_sim, x="경과년수", y="총자산", title="자산 성장 곡선"), use_container_width=True)
with sc2:
    st.plotly_chart(px.line(df_sim, x="경과년수", y="월배당금", title="월 배당금 성장 곡선", markers=True), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b>의 통합 배당 시스템 v4.3 💖</center>", unsafe_allow_html=True)

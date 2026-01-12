import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 대시보드 v5.9", page_icon="💰", layout="wide")

# 2. 데이터 함수 (캐시 적용)
@st.cache_data(ttl=300)
def get_stock_details(ticker_code):
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0}
    price, monthly_div = price_map.get(ticker_code, 10000.0), div_map.get(ticker_code, 50.0)
    try:
        stock = yf.Ticker(ticker_code)
        hist = stock.history(period="1d")
        if not hist.empty: price = hist['Close'].iloc[-1]
        div_info = stock.dividends
        if not div_info.empty:
            recent = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent.empty: monthly_div = recent.sum() / 12
        return price, monthly_div
    except:
        return price, monthly_div

# 3. 세션 상태
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 데이터 계산
portfolio_data, total_asset, total_div_pre = [], 0, 0
for s in st.session_state.stock_list:
    p, d = get_stock_details(s['ticker'])
    val, div_pre = p * s['qty'], d * s['qty']
    total_asset += val
    total_div_pre += div_pre
    portfolio_data.append({"종목": s['name'], "자산가치": val, "월배당(세전)": div_pre, "세후": div_pre * 0.846})
df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846

# 5. 메인 화면 상단
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.title(f"📊 {user_name}님의 배당 리포트")

c1, c2 = st.columns(2)
c1.metric("총 자산", f"{total_asset:,.0f}원")
c2.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

chicken_p = st.sidebar.number_input("치킨 가격", value=30000, step=1000)
st.info(f"✨ 현재 배당금으로 **치킨 {total_div_post//chicken_p:,.0f}마리** 가능!")

st.divider()

# 6. 상세 내역 탭
t1, t2 = st.tabs(["📋 상세 내역", "📅 배당 캘린더"])
with t1: st.dataframe(df, use_container_width=True)
with t2:
    cal_list = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, row in df.iterrows(): cal_list.append({"월": m, "종목": row["종목"], "금액": row["세후"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목"), use_container_width=True)

# 7. [수정됨] 투자 시나리오 설정 (슬라이더 -> 수동 기입)
st.divider()
st.subheader("⚙️ 투자 시나리오 설정 (수동 기입)")
col_set1, col_set2, col_set3 = st.columns(3)

with col_set1:
    add_m = st.number_input("매달 추가 투자금 (만원)", min_value=0, value=100, step=1, key="v59_add_m")
with col_set2:
    reinvest_rate = st.number_input("배당금 재투자 비율 (%)", min_value=0, max_value=100, value=100, step=1, key="v59_reinvest")
with col_set3:
    sim_y = st.number_input("시뮬레이션 기간 (년)", min_value=1, max_value=50, value=20, step=1, key="v59_sim_y")

# 8. 미래 성장 시뮬레이션
sim_results = []
temp_asset = total_asset
annual_yield_post = (total_div_post * 12) / total_asset if total_asset > 0 else 0.1

for m in range(1, (sim_y * 12) + 1):
    invest_amt = ((temp_asset * annual_yield_post / 12) * (reinvest_rate / 100)) + (add_m * 10000)
    temp_asset += invest_amt
    # 5년 단위 또는 마지막 연도 기록
    if m % (5 * 12) == 0 or m == (sim_y * 12):
        y = m // 12
        sim_results.append({
            "년수": f"{y}년 후", 
            "자산(억)": round(temp_asset / 100000000, 2), 
            "월배당(만원)": int((temp_asset * annual_yield_post / 12) / 10000)
        })

st.plotly_chart(px.area(pd.DataFrame(sim_results), x="년수", y="자산(억)"), use_container_width=True)

for row in sim_results:
    with st.container():
        sc1, sc2, sc3 = st.columns([1, 2, 2])
        sc1.write(f"📅 **{row['년수']}**")
        sc2.metric("자산", f"{row['자산(억)']}억")
        sc3.metric("월급", f"{row['월배당(만원)']}만")
        st.write("---")

# 9. 종목 관리
st.divider()
st.subheader("📦 보유 종목 수정 및 추가")
with st.container():
    st.write("➕ **새 종목 추가**")
    new_col1, new_col2 = st.columns(2)
    n_name = new_col1.text_input("종목명", key="v59_nn")
    n_ticker = new_col2.text_input("티커", key="v59_nt")
    n_qty = st.number_input("수량", min_value=0, value=100, key="v59_nq")
    if st.button("🚀 추가", use_container_width=True):
        if n_name and n_ticker:
            st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
            st.rerun()

st.write("📋 **보유 종목**")
for i, stock in enumerate(st.session_state.stock_list):
    with st.container():
        name_col, del_col = st.columns([4, 1])
        name_col.markdown(f"**{i+1}. {stock['name']}**")
        if del_col.button("❌", key=f"v59_del_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()
        st.session_state.stock_list[i]['qty'] = st.number_input(f"수량 수정", value=stock['qty'], key=f"v59_q_{i}", label_visibility="collapsed")

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b> v5.9</center>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 대시보드 v5.5", page_icon="💰", layout="wide")

# 2. 데이터 함수
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

# 4. 사이드바 설정 (물가 및 투자금)
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.sidebar.divider()
st.sidebar.subheader("🍔 물가 설정")
chicken_p = st.sidebar.number_input("치킨 가격", value=30000, step=1000)
coffee_p = st.sidebar.number_input("커피 가격", value=5000, step=500)
st.sidebar.divider()
st.sidebar.subheader("📈 시뮬레이션 설정")
add_m = st.sidebar.slider("매달 추가 투자(만원)", 0, 1000, 100, step=10)
sim_y = st.sidebar.slider("시뮬레이션 기간(년)", 5, 40, 20, step=5)

# 5. 데이터 계산
portfolio_data, total_asset, total_div_pre = [], 0, 0
for s in st.session_state.stock_list:
    p, d = get_stock_details(s['ticker'])
    val, div_pre = p * s['qty'], d * s['qty']
    total_asset += val
    total_div_pre += div_pre
    portfolio_data.append({
        "종목": s['name'], "자산가치": val, "월배당(세전)": div_pre, "세후": div_pre * 0.846
    })
df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846

# 6. 메인 대시보드 출력
st.title(f"📊 {user_name}님의 배당 리포트")

# 상단 지표
c1, c2 = st.columns(2)
c1.metric("총 자산", f"{total_asset:,.0f}원")
c2.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

# 치킨/커피 지수 안내
st.info(f"✨ 이번 달 배당금은 **치킨 {total_div_post//chicken_p:,.0f}마리** 또는 **커피 {total_div_post//coffee_p:,.0f}잔** 분량입니다!")
st.divider()

# 7. 상세 리스트 및 캘린더 (복구 완료!)
t1, t2 = st.tabs(["📋 종목 상세", "📅 배당 캘린더"])
with t1:
    st.dataframe(df.style.format({"자산가치": "{:,.0f}", "월배당(세전)": "{:,.0f}", "세후": "{:,.0f}"}), use_container_width=True)

with t2:
    cal_list = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, row in df.iterrows():
            cal_list.append({"월": m, "종목": row["종목"], "금액": row["세후"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="연간 세후 배당 흐름"), use_container_width=True)

# 8. 시뮬레이션 섹션 (개선된 버전 유지)
st.divider()
st.subheader("❄️ 미래 성장 시뮬레이션")
sim_results = []
temp_asset = total_asset
avg_yield_post = (total_div_post * 12) / total_asset if total_asset > 0 else 0.1

for m in range(1, (sim_y * 12) + 1):
    temp_asset += (temp_asset * avg_yield_post / 12) + (add_m * 10000)
    if m % (10 * 12) == 0 or m == (sim_y * 12):
        y = m // 12
        sim_results.append({
            "년수": f"{y}년 후", 
            "자산(억)": round(temp_asset / 100000000, 2),
            "월배당(만원)": int((temp_asset * avg_yield_post / 12) / 10000)
        })

st.plotly_chart(px.area(pd.DataFrame(sim_results), x="년수", y="자산(억)", text="자산(억)", title="자산 성장 (억 단위)"), use_container_width=True)

# 주요 지점 수치 카드
for row in sim_results:
    with st.container():
        sc1, sc2, sc3 = st.columns([1, 2, 2])
        sc1.write(f"📅 **{row['년수']}**")
        sc2.metric("예상 자산", f"{row['자산(억)']} 억")
        sc3.metric("예상 월급", f"{row['월배당(만원)']} 만원")
        st.write("---")

# 9. 종목 관리 (하단 배치)
with st.expander("📝 종목 관리 및 추가"):
    n_name = st.text_input("종목명")
    n_ticker = st.text_input("티커")
    n_qty = st.number_input("수량", min_value=0, value=100)
    if st.button("목록에 추가"):
        st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
        st.rerun()
    
    for i, stock in enumerate(st.session_state.stock_list):
        ec1, ec2, ec3 = st.columns([2, 2, 1])
        ec1.write(stock['name'])
        st.session_state.stock_list[i]['qty'] = ec2.number_input("수량", value=stock['qty'], key=f"q_v55_{i}", label_visibility="collapsed")
        if ec3.button("삭제", key=f"d_v55_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

st.markdown(f"<center>💖 <b>{user_name} & 소은</b> 통합 관리 v5.5 💖</center>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 대시보드 v5.4", page_icon="💰", layout="wide")

# 2. 데이터 함수 (기존 유지)
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
total_asset, total_div_pre = 0, 0
for s in st.session_state.stock_list:
    p, d = get_stock_details(s['ticker'])
    total_asset += p * s['qty']
    total_div_pre += d * s['qty']
total_div_post = total_div_pre * 0.846

# 5. 메인 대시보드
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.title(f"💰 {user_name}님의 배당 리포트")

# 상단 지표
c1, c2 = st.columns(2)
c1.metric("총 자산", f"{total_asset:,.0f}원")
c2.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

st.divider()

# 6. 미래 성장 시뮬레이션 (모바일 최적화 섹션)
st.subheader("❄️ 미래 성장 예측 (세후)")

# 사이드바 설정값
add_m = st.sidebar.slider("매달 추가 투자(만원)", 0, 1000, 100, step=10)
sim_y = st.sidebar.slider("시뮬레이션 기간(년)", 5, 40, 20, step=5)

# 계산 로직
sim_data = []
temp_asset = total_asset
avg_yield_post = (total_div_post * 12) / total_asset if total_asset > 0 else 0.1

for m in range(1, (sim_y * 12) + 1):
    # 월 복리 계산: (현재자산 * 월수익률) + 추가투자금
    temp_asset += (temp_asset * avg_yield_post / 12) + (add_m * 10000)
    if m % (10 * 12) == 0 or m == (sim_y * 12): # 10년 단위 또는 최종 년도 저장
        y = m // 12
        sim_data.append({
            "년수": f"{y}년 후", 
            "자산(억)": round(temp_asset / 100000000, 2),
            "월배당(만원)": int((temp_asset * avg_yield_post / 12) / 10000)
        })

# 그래프 표시 (가독성을 위해 단순화)
df_sim = pd.DataFrame(sim_data)
st.plotly_chart(px.area(df_sim, x="년수", y="자산(억)", text="자산(억)", title="자산 성장 추이"), use_container_width=True)

# 핵심 수치 카드 (모바일에서 보기 편한 텍스트 방식)
st.write("🔍 **주요 시점 목표치**")
for _, row in df_sim.iterrows():
    with st.container():
        sc1, sc2, sc3 = st.columns([1, 2, 2])
        sc1.write(f"📅 **{row['년수']}**")
        sc2.metric("예상 자산", f"{row['자산(억)']} 억원")
        sc3.metric("예상 월급", f"{row['월배당(만원)']} 만원")
        st.write("---")

st.divider()

# 7. 종목 관리 (간결하게 유지)
with st.expander("📝 종목 관리 및 추가"):
    n_name = st.text_input("종목명")
    n_ticker = st.text_input("티커")
    n_qty = st.number_input("수량", min_value=0, value=100)
    if st.button("추가"):
        st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
        st.rerun()
    
    for i, stock in enumerate(st.session_state.stock_list):
        ec1, ec2, ec3 = st.columns([2, 2, 1])
        ec1.write(stock['name'])
        st.session_state.stock_list[i]['qty'] = ec2.number_input("수량", value=stock['qty'], key=f"q_{i}", label_visibility="collapsed")
        if ec3.button("X", key=f"d_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

st.markdown(f"<center>💖 <b>{user_name} & 소은</b> v5.4</center>", unsafe_allow_html=True)

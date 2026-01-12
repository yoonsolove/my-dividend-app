import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="통합 배당 & 세금 관리", page_icon="💸", layout="wide")

# 2. 데이터 가져오기 함수 (기존 유지)
@st.cache_data(ttl=300)
def get_stock_details(ticker_code):
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0}
    price, monthly_div = price_map.get(ticker_code, 10000.0), div_map.get(ticker_code, 50.0)
    ex_date_str, d_day_msg = "확인중", "-"
    try:
        stock = yf.Ticker(ticker_code)
        hist = stock.history(period="1d")
        if not hist.empty: price = hist['Close'].iloc[-1]
        try:
            ex_div_raw = stock.info.get('exDividendDate')
            if ex_div_raw:
                ex_date = datetime.fromtimestamp(ex_div_raw).date()
                ex_date_str = ex_date.strftime('%Y-%m-%d')
                days_left = (ex_date - date.today()).days
                d_day_msg = f"D-{days_left}" if days_left > 0 else ("오늘" if days_left == 0 else "경과")
            elif ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"):
                ex_date_str = "매월 말일경"
        except: pass
        div_info = stock.dividends
        if not div_info.empty:
            recent = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent.empty: monthly_div = recent.sum() / 12
        return price, monthly_div, ex_date_str, d_day_msg
    except:
        return price, monthly_div, ex_date_str, d_day_msg

# 3. 세션 상태 초기화
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 UI
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.sidebar.divider()
with st.sidebar.expander("➕ 새 종목 추가"):
    n_name = st.text_input("종목명")
    n_ticker = st.text_input("티커")
    n_qty = st.number_input("수량", min_value=0, value=100)
    if st.button("추가"):
        if n_name and n_ticker:
            st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
            st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🍔 물가 설정 (배당 체감용)")
chicken_p = st.sidebar.number_input("치킨 한 마리 가격", value=30000, step=1000)
coffee_p = st.sidebar.number_input("커피 한 잔 가격", value=5000, step=500)

st.sidebar.divider()
add_monthly = st.sidebar.slider("매달 추가 투자금 (만원)", 0, 500, 50, step=10)
sim_years = st.sidebar.slider("시뮬레이션 기간 (년)", 1, 40, 20)

# 5. 데이터 계산
portfolio_data = []
total_asset, total_div_pre = 0, 0
for s in st.session_state.stock_list:
    p, d, ex, dday = get_stock_details(s['ticker'])
    val, div_pre = p * s['qty'], d * s['qty']
    tax = div_pre * 0.154
    total_asset += val
    total_div_pre += div_pre
    portfolio_data.append({"종목": s['name'], "배당락일": ex, "D-Day": dday, "자산가치": val, "월배당(세전)": div_pre, "예상세금": tax, "월배당(세후)": div_pre-tax})

df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * (1 - 0.154)

# 6. 메인 화면 출력 (★ 요청하신 수정 구간!)
st.title(f"📊 {user_name}님의 배당 리포트")

# 체감 지수 계산
chickens = total_div_post // chicken_p
coffees = total_div_post // coffee_p

# 지표 섹션
c1, c2, c3, c4 = st.columns(4)
c1.metric("총 자산", f"{total_asset:,.0f} 원")
c2.metric("월 수령액(세후)", f"{total_div_post:,.0f} 원")
c3.metric("월 예상 세금", f"{total_div_pre*0.154:,.0f} 원", delta_color="inverse")
c4.metric("연 예상 세금", f"{total_div_pre*12*0.154:,.0f} 원", delta_color="inverse")

# 감성 한 줄 추가
st.info(f"✨ 이번 달 배당금은 **치킨 {chickens:,.0f}마리** 또는 **커피 {coffees:,.0f}잔**의 가치가 있습니다! (물가 반영)")
st.divider()

# --- 이하 7, 8번 섹션(탭, 그래프 등)은 기존과 동일 ---
t1, t2 = st.tabs(["📋 종목 상세", "📅 캘린더"])
with t1: st.dataframe(df.style.format({"자산가치": "{:,.0f}", "월배당(세전)": "{:,.0f}", "예상세금": "{:,.0f}", "월배당(세후)": "{:,.0f}"}), use_container_width=True)
with t2:
    cal_df = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, r in df.iterrows(): cal_df.append({"월": m, "종목": r["종목"], "금액": r["월배당(세후)"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_df), x="월", y="금액", color="종목"), use_container_width=True)

st.subheader("❄️ 미래 성장 시뮬레이션")
sim_data = []
temp_asset, avg_yield_post = total_asset, (total_div_post * 12) / total_asset if total_asset > 0 else 0.1
for m in range(1, (sim_years * 12) + 1):
    temp_asset += (temp_asset * avg_yield_post / 12) + (add_monthly * 10000)
    if m % 12 == 0: sim_data.append({"년수": f"{m//12}년", "자산": int(temp_asset), "월배당": int(temp_asset * avg_yield_post / 12)})
st.plotly_chart(px.area(pd.DataFrame(sim_data), x="년수", y="자산"), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b> 통합 관리 v4.8 💖</center>", unsafe_allow_html=True)

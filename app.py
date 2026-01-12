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
        
        # 배당락일 추출
        try:
            ex_div_raw = stock.info.get('exDividendDate')
            if ex_div_raw:
                ex_date_str = datetime.fromtimestamp(ex_div_raw).strftime('%Y-%m-%d')
            elif ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"):
                ex_date_str = "매월 말일경"
        except:
            ex_date_str = "확인중"

        # 배당금
        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent_divs.empty:
                monthly_div = recent_divs.sum() / 12
        
        return price, monthly_div, ex_date_str
    except:
        return price, monthly_div, ex_date_str

# 3. 세션 상태 관리
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 UI
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.sidebar.divider()
st.sidebar.subheader("📈 미래 적립 설정")
add_monthly = st.sidebar.slider("매달 추가 투자금 (만원)", 0, 500, 50, step=10)
reinvest_rate = st.sidebar.slider("배당금 재투자 비율 (%)", 0, 100, 100)
sim_years = st.sidebar.slider("시뮬레이션 기간 (년)", 1, 40, 20)

st.sidebar.divider()
with st.sidebar.expander("📦 보유 종목 수량 수정"):
    for i, stock in enumerate(st.session_state.stock_list):
        new_qty = st.number_input(f"{stock['name']} 수량", value=stock['qty'], key=f"q_{i}")
        st.session_state.stock_list[i]['qty'] = new_qty

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
    portfolio_data.append({
        "종목": s['name'], 
        "현재가": p, 
        "배당락일": ex, 
        "자산가치": val, 
        "월배당": div_val
    })

df_portfolio = pd.DataFrame(portfolio_data)

# ==========================================
# 6. 상단 섹션: 현재 포트폴리오 현황
# ==========================================
st.title(f"💰 {user_name}님의 배당 대시보드")

col1, col2, col3 = st.columns(3)
col1.metric("현재 총 자산", f"{total_asset:,.0f} 원")
col2.metric("월 예상 배당", f"{current_monthly_div:,.0f} 원")
col3.metric("연 예상 배당", f"{current_monthly_div*12:,.0f} 원")

st.divider()

tab1, tab2 = st.tabs(["📋 종목 상세 (배당락일)", "📅 월별 배당 캘린더"])

with tab1:
    c1, c2 = st.columns([1.8, 1])
    with c1:
        st.write("**[보유 종목 상세 리스트]**")
        # 배당락일 컬럼 포함하여 출력
        st.dataframe(df_portfolio.style.format({
            "현재가": "{:,.0f}원", 
            "자산가치": "{:,.0f}원", 
            "월배당": "{:,.0f}원"
        }), use_container_width=True)
    with c2:
        fig_pie = px.pie(df_portfolio, values='자산가치', names='종목', hole=0.4, title="자산 비중")
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    months = [f"{i}월" for i in range(1, 13)]
    cal_list = []
    for m in months:
        for _, row in df_portfolio.iterrows():
            cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당"]})
    fig_cal = px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="연간 배당 흐름")
    st.plotly_chart(fig_cal, use_container_width=True)

# ==========================================
# 7. 하단 섹션: 미래 스노볼 시뮬레이션
# ==========================================
st.write("")
st.subheader("❄️ 미래 성장 시뮬레이션")
st.info(f"💡 {add_monthly}만원 적립 + 배당금 {reinvest_rate}% 재투자 시나리오")

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

# 8. 푸터
st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b>의 배당 시스템 v4.2 💖</center>", unsafe_allow_html=True)

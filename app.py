import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="나만의 배당 관리자", page_icon="🏦", layout="wide")

# 2. 실시간 데이터 가져오기 함수 (안전장치 포함)
@st.cache_data(ttl=600)
def get_stock_info(ticker_code):
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        stock = yf.Ticker(ticker_code)
        hist = stock.history(period="1d")
        price = hist['Close'].iloc[-1] if not hist.empty else 10000.0
        
        div_info = stock.dividends
        if not div_info.empty:
            last_year_div = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))].sum()
            monthly_div = last_year_div / 12
        else:
            defaults = {"490600.KS": 105, "402320.KS": 40, "SCHD": 0.2, "JEPI": 0.4, "O": 0.26}
            monthly_div = defaults.get(ticker_code, 50)

        is_usd = not (ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"))
        if is_usd:
            price *= usd_krw
            monthly_div *= usd_krw
            
        return price, monthly_div, usd_krw
    except:
        return 10000.0, 50.0, 1450.0

# 3. 세션 상태 초기화 (종목 리스트 저장)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 - 종목 관리자
st.sidebar.header("👤 사용자 설정")
user_name = st.sidebar.text_input("이름", value="윤재")

st.sidebar.divider()
st.sidebar.subheader("📂 종목 편집기")

# 종목 추가 기능
with st.sidebar.expander("➕ 새 종목 추가"):
    new_name = st.text_input("종목명")
    new_ticker = st.text_input("티커 (예: O, 005930.KS)")
    new_qty = st.number_input("초기 수량", min_value=0, value=100)
    if st.button("포트폴리오에 추가"):
        if new_name and new_ticker:
            st.session_state.stock_list.append({"name": new_name, "ticker": new_ticker, "qty": new_qty})
            st.rerun()

# 기존 종목 수정 및 삭제 (수정 즉시 반영 로직)
st.sidebar.write("**현재 보유 종목**")
for i, stock in enumerate(st.session_state.stock_list):
    with st.sidebar.expander(f"📦 {stock['name']} ({stock['ticker']})"):
        # 수량을 세션 상태에 직접 연결
        new_qty = st.number_input(f"수량 변경", value=stock['qty'], key=f"qty_input_{i}")
        if new_qty != stock['qty']:
            st.session_state.stock_list[i]['qty'] = new_qty
            st.rerun() # 값이 바뀌면 즉시 화면 갱신
            
        if st.button(f"삭제", key=f"del_btn_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

# 5. 데이터 계산 (메인 로직)
portfolio_data = []
total_asset = 0
total_monthly_div = 0
current_usd = 1450.0

for s in st.session_state.stock_list:
    p, d, usd = get_stock_info(s['ticker'])
    current_usd = usd
    asset_val = p * s['qty']
    div_val = d * s['qty']
    
    total_asset += asset_val
    total_monthly_div += div_val
    portfolio_data.append({"종목": s['name'], "자산가치": asset_val, "월배당금": div_val})

df_portfolio = pd.DataFrame(portfolio_data)

# 6. 메인 화면 출력
st.title(f"💰 {user_name}님의 실시간 자산 리포트")
st.caption(f"실시간 환율: 1$ = {current_usd:,.2f}원")

# 요약 카드
c1, c2, c3 = st.columns(3)
c1.metric("총 평가금액", f"{total_asset:,.0f} 원")
c2.metric("예상 월 배당금", f"{total_monthly_div:,.0f} 원")
c3.metric("예상 연 배당금", f"{total_monthly_div*12:,.0f} 원")

# 그래프 섹션
st.divider()
tab1, tab2 = st.tabs(["📅 배당 캘린더", "🍩 자산 비중"])

with tab1:
    if not df_portfolio.empty:
        months = [f"{i}월" for i in range(1, 13)]
        cal_list = []
        for m in months:
            for _, row in df_portfolio.iterrows():
                cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당금"]})
        fig_cal = px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목")
        st.plotly_chart(fig_cal, use_container_width=True)

with tab2:
    if not df_portfolio.empty:
        fig_pie = px.pie(df_portfolio, values='자산가치', names='종목', hole=0.4)
        st.plotly_chart(fig_pie)

# 상세 표
st.subheader("📋 포트폴리오 상세 내역")
st.dataframe(df_portfolio.style.format({"자산가치": "{:,.0f}", "월배당금": "{:,.0f}"}), use_container_width=True)

# 푸터
st.divider()
st.markdown(f"<center>💖 {user_name} & 소은의 배당 엔진 v3.6 💖</center>", unsafe_allow_html=True)

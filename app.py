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
        # 환율 정보
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        
        stock = yf.Ticker(ticker_code)
        hist = stock.history(period="1d")
        price = hist['Close'].iloc[-1] if not hist.empty else 0
        
        # 배당 정보 추출
        div_info = stock.dividends
        if not div_info.empty:
            last_year_div = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))].sum()
            monthly_div = last_year_div / 12
        else:
            # 배당 정보가 없을 경우 종목별 추정치 (알려진 종목들 위주)
            defaults = {"490600.KS": 105, "402320.KS": 40, "SCHD": 0.2, "JEPI": 0.4, "O": 0.26}
            monthly_div = defaults.get(ticker_code, 0)

        # 미국 주식(환율 적용)
        is_usd = not (ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"))
        if is_usd:
            price *= usd_krw
            monthly_div *= usd_krw
            
        return price, monthly_div, usd_krw
    except:
        return 0, 0, 1450.0

# 3. 사이드바 - 종목 관리자
st.sidebar.header("👤 사용자 설정")
user_name = st.sidebar.text_input("이름", value="윤재")

st.sidebar.divider()
st.sidebar.subheader("📂 종목 편집기")

# 세션 상태(Session State)를 사용해 종목 리스트 유지
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 종목 추가 폼
with st.sidebar.expander("➕ 새 종목 추가"):
    new_name = st.text_input("종목명 (예: 리얼티인컴)")
    new_ticker = st.text_input("티커 (예: O 또는 005930.KS)")
    new_qty = st.number_input("보유 수량", min_value=0, value=100)
    if st.button("포트폴리오에 추가"):
        st.session_state.stock_list.append({"name": new_name, "ticker": new_ticker, "qty": new_qty})
        st.rerun()

# 기존 종목 수정 및 삭제
st.sidebar.write("---")
st.sidebar.write("**현재 보유 종목**")
updated_list = []
for i, stock in enumerate(st.session_state.stock_list):
    with st.sidebar.expander(f"📦 {stock['name']} ({stock['ticker']})"):
        u_qty = st.number_input(f"수량 변경", value=stock['qty'], key=f"qty_{i}")
        if st.button(f"삭제", key=f"del_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()
        updated_list.append({"name": stock['name'], "ticker": stock['ticker'], "qty": u_qty})
st.session_state.stock_list = updated_list

# 4. 데이터 계산
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

# 5. 메인 화면 출력
st.title(f"💰 {user_name}님의 커스텀 배당 대시보드")
st.caption(f"실시간 환율: 1$ = {current_usd:,.2f}원 | 종목 수: {len(df_portfolio)}개")

# 요약 카드
c1, c2, c3 = st.columns(3)
c1.metric("총 평가금액", f"{total_asset:,.0f} 원")
c2.metric("예상 월급", f"{total_monthly_div:,.0f} 원")
c3.metric("예상 연봉", f"{total_monthly_div*12:,.0f} 원")

# 그래프 섹션
st.divider()
tab1, tab2 = st.tabs(["📅 배당 캘린더", "🍩 자산 비중"])

with tab1:
    months = [f"{i}월" for i in range(1, 13)]
    cal_data = []
    for m in months:
        for _, row in df_portfolio.iterrows():
            cal_data.append({"월": m, "종목": row["종목"], "금액": row["월배당금"]})
    if cal_data:
        fig_cal = px.bar(pd.DataFrame(cal_data), x="월", y="금액", color="종목", barmode='stack')
        st.plotly_chart(fig_cal, use_container_width=True)

with tab2:
    if not df_portfolio.empty:
        fig_pie = px.pie(df_portfolio, values='자산가치', names='종목', hole=0.4)
        st.plotly_chart(fig_pie)

# 상세 표
st.subheader("📋 포트폴리오 상세 내역")
st.dataframe(df_portfolio.style.format({"자산가치": "{:,.0f}", "월배당금": "{:,.0f}"}), use_container_width=True)

# 6. 푸터
st.divider()
st.markdown(f"<center>💖 {user_name} & 소은의 배당 엔진 v3.5 💖</center>", unsafe_allow_html=True)

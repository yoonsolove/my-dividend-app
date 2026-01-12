import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 캘린더 & 실시간 자산", page_icon="📈", layout="wide")

# 2. 데이터 가져오기 함수 (안전장치 및 기본값 강화)
@st.cache_data(ttl=300) # 5분마다 갱신
def get_stock_details(ticker_code):
    # 기본값 설정 (서버 응답 없을 때를 대비한 든든한 기초값)
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0, "SCHD": 80.0, "O": 60.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0, "SCHD": 0.2, "O": 0.26}
    
    price = price_map.get(ticker_code, 10000.0)
    monthly_div = div_map.get(ticker_code, 50.0)
    ex_date_str = "매월 말일경"
    usd_krw = 1450.0
    
    try:
        # 환율 가져오기
        rate_ticker = yf.Ticker("USDKRW=X")
        rate_hist = rate_ticker.history(period="1d")
        if not rate_hist.empty:
            usd_krw = rate_hist['Close'].iloc[-1]
        
        stock = yf.Ticker(ticker_code)
        
        # 주가 가져오기
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
        
        # 배당금 및 배당락일
        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent_divs.empty:
                monthly_div = recent_divs.sum() / 12
        
        # 미국 주식 환율 적용
        if not (ticker_code.endswith(".KS") or ticker_code.endswith(".KQ")):
            price *= usd_krw
            monthly_div *= usd_krw
        else:
            ex_date_str = "매월 말일경" # 한국 월배당주 고정 안내
            
        return price, monthly_div, ex_date_str, usd_krw
    except:
        return price, monthly_div, ex_date_str, usd_krw

# 3. 세션 상태 관리
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 UI
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.sidebar.divider()
with st.sidebar.expander("➕ 종목 추가"):
    n_name = st.text_input("종목명")
    n_ticker = st.text_input("티커")
    n_qty = st.number_input("수량", min_value=0, value=100)
    if st.button("추가하기"):
        st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
        st.rerun()

for i, stock in enumerate(st.session_state.stock_list):
    with st.sidebar.expander(f"📦 {stock['name']}"):
        new_qty = st.number_input(f"수량", value=stock['qty'], key=f"q_{i}")
        if new_qty != stock['qty']:
            st.session_state.stock_list[i]['qty'] = new_qty
            st.rerun()
        if st.button(f"삭제", key=f"d_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

# 5. 데이터 계산
portfolio_data = []
total_asset = 0
total_monthly_div = 0
for s in st.session_state.stock_list:
    p, d, ex, usd = get_stock_details(s['ticker'])
    val = p * s['qty']
    div_val = d * s['qty']
    portfolio_data.append({"종목": s['name'], "현재가": p, "배당락일": ex, "자산가치": val, "월배당": div_val})
    total_asset += val
    total_monthly_div += div_val

df = pd.DataFrame(portfolio_data)

# 6. 메인 화면 출력
st.title(f"📈 {user_name}님의 배당 대시보드")
st.success(f"현재 환율: 1$ = {usd:,.2f}원")

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{total_asset:,.0f} 원")
c2.metric("월 예상 배당", f"{total_monthly_div:,.0f} 원")
c3.metric("연 예상 배당", f"{total_monthly_div*12:,.0f} 원")

# 표 출력
st.subheader("📋 포트폴리오 현황")
st.dataframe(df, use_container_width=True)

# 그래프 (데이터가 있을 때만 출력하는 조건 삭제하여 강제 출력)
st.divider()
months = [f"{i}월" for i in range(1, 13)]
cal_list = []
for m in months:
    for _, row in df.iterrows():
        cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당"]})

# 캘린더 그래프
fig_cal = px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="월별 배당 예측 (연간)")
st.plotly_chart(fig_cal, use_container_width=True)

# 비중 그래프
fig_pie = px.pie(df, values='자산가치', names='종목', title="자산 비중", hole=0.4)
st.plotly_chart(fig_pie, use_container_width=True)

st.divider()
st.markdown(f"<center>💖 {user_name} & 소은 배당 엔진 v3.9.1 💖</center>", unsafe_allow_html=True)

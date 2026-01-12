import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 캘린더 & 실시간 자산", page_icon="🔔", layout="wide")

# 2. 데이터 가져오기 함수 (주가 연동 보강)
@st.cache_data(ttl=600) # 주가는 10분마다 갱신
def get_stock_details(ticker_code):
    price, monthly_div, ex_date_str = 0.0, 0.0, "확인불가"
    usd_krw = 1450.0
    
    try:
        # 환율 가져오기
        rate_ticker = yf.Ticker("USDKRW=X")
        usd_krw = rate_ticker.fast_info.last_price if rate_ticker.fast_info.last_price else 1450.0
        
        stock = yf.Ticker(ticker_code)
        
        # 주가 가져오기 (fast_info 사용으로 속도 및 안정성 향상)
        price = stock.fast_info.last_price
        
        # 만약 실시간가가 0이면 최근 1일치 기록에서 가져오기
        if price is None or price <= 0:
            hist = stock.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                # 최후의 보단: 기본 가격 설정
                defaults_price = {"490600.KS": 10500, "402320.KS": 11500}
                price = defaults_price.get(ticker_code, 0.0)
        
        # 배당금 및 배당락일 (이전 로직 유지 및 보강)
        try:
            ex_div_raw = stock.info.get('exDividendDate')
            if ex_div_raw:
                ex_date_str = datetime.fromtimestamp(ex_div_raw).strftime('%Y-%m-%d')
            elif ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"):
                ex_date_str = "매월 말일경"
        except:
            ex_date_str = "매월/분기말"

        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            monthly_div = recent_divs.sum() / 12 if not recent_divs.empty else 0
        
        # 야후 데이터 부족 시 보조 데이터
        if monthly_div == 0:
            defaults_div = {"490600.KS": 105, "402320.KS": 40}
            monthly_div = defaults_div.get(ticker_code, 0)

        # 미국 주식 환율 적용
        if not (ticker_code.endswith(".KS") or ticker_code.endswith(".KQ")):
            price *= usd_krw
            monthly_div *= usd_krw
            
        return price, monthly_div, ex_date_str, usd_krw
    except:
        return 0.0, 0.0, "조회중", 1450.0

# 3. 세션 상태 관리 (동일)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 (동일)
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

# 5. 계산 및 출력
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

st.title(f"📈 {user_name}님의 실시간 자산 관리")
st.success(f"현재 환율: 1$ = {usd:,.2f}원")

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{total_asset:,.0f} 원")
c2.metric("월 예상 배당", f"{total_monthly_div:,.0f} 원")
c3.metric("연 예상 배당", f"{total_monthly_div*12:,.0f} 원")

st.subheader("📋 포트폴리오 현황")
st.dataframe(df[["종목", "현재가", "배당락일", "자산가치", "월배당"]].style.format({"현재가": "{:,.0f}원", "자산가치": "{:,.0f}원", "월배당": "{:,.0f}원"}), use_container_width=True)

# 그래프 (연간 흐름)
st.divider()
months = [f"{i}월" for i in range(1, 13)]
cal_list = []
for m in months:
    for _, row in df.iterrows():
        cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당"]})
st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="월별 배당 예측"), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 {user_name} & 소은 배당 엔진 v3.9 💖</center>", unsafe_allow_html=True)

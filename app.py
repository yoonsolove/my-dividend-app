import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 캘린더 & 배당락", page_icon="🔔", layout="wide")

# 2. 데이터 가져오기 함수 (배당락일 추가)
@st.cache_data(ttl=3600) # 배당락일은 자주 안 변하므로 1시간 캐시
def get_stock_details(ticker_code):
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        stock = yf.Ticker(ticker_code)
        
        # 주가 및 배당금
        price = stock.history(period="1d")['Close'].iloc[-1]
        info = stock.info
        
        # 배당락일 가져오기 시도
        ex_div_date = info.get('exDividendDate')
        if ex_div_date:
            ex_date_str = datetime.fromtimestamp(ex_div_date).strftime('%Y-%m-%d')
        else:
            ex_date_str = "데이터 확인필요" # 한국 종목은 주로 월말/분기말

        # 배당금 추정
        div_info = stock.dividends
        if not div_info.empty:
            monthly_div = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))].sum() / 12
        else:
            defaults = {"490600.KS": 105, "402320.KS": 40, "SCHD": 0.2, "O": 0.26}
            monthly_div = defaults.get(ticker_code, 50)

        # 환율 적용
        is_usd = not (ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"))
        if is_usd:
            price *= usd_krw
            monthly_div *= usd_krw
            
        return price, monthly_div, ex_date_str, usd_krw
    except:
        return 10000.0, 50.0, "연동오류", 1450.0

# 3. 세션 상태 관리
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 사이드바 UI
st.sidebar.header("👤 {0}님의 설정".format(st.session_state.get('user_name', '윤재')))
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.session_state.user_name = user_name

st.sidebar.divider()
st.sidebar.subheader("📂 포트폴리오 관리")

with st.sidebar.expander("➕ 종목 추가"):
    new_name = st.text_input("종목명")
    new_ticker = st.text_input("티커")
    new_qty = st.number_input("수량", min_value=0, value=100)
    if st.button("추가하기"):
        st.session_state.stock_list.append({"name": new_name, "ticker": new_ticker, "qty": new_qty})
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

# 5. 계산 및 메인 화면
portfolio_data = []
total_monthly_div = 0
current_usd = 1450.0

for s in st.session_state.stock_list:
    p, d, ex_date, usd = get_stock_details(s['ticker'])
    current_usd = usd
    portfolio_data.append({
        "종목": s['name'],
        "티커": s['ticker'],
        "현재가": p,
        "보유수량": s['qty'],
        "자산가치": p * s['qty'],
        "월예상배당": d * s['qty'],
        "배당락일(예정)": ex_date
    })
    total_monthly_div += d * s['qty']

df = pd.DataFrame(portfolio_data)

st.title(f"🔔 {user_name}님의 배당락 알리미")
st.info(f"💡 대부분의 월배당 ETF는 **매달 말일**이 배당락일입니다. (미배콜/미배당 포함)")

# 상단 대시보드
c1, c2, c3 = st.columns(3)
c1.metric("월 예상 배당", f"{total_monthly_div:,.0f} 원")
c2.metric("실시간 환율", f"{current_usd:,.2f} 원")
c3.metric("총 종목 수", f"{len(df)} 개")

# 6. 배당락 상세 리스트 (가장 중요한 부분)
st.subheader("📅 종목별 배당락 정보")
st.dataframe(df[["종목", "티커", "배당락일(예정)", "월예상배당"]].style.set_properties(**{'background-color': '#fff4f4'}, subset=['배당락일(예정)']), use_container_width=True)

# 7. 월별 그래프
st.divider()
months = [f"{i}월" for i in range(1, 13)]
cal_list = []
for m in months:
    for _, row in df.iterrows():
        cal_list.append({"월": m, "종목": row["종목"], "금액": row["월예상배당"]})
st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="연간 배당 흐름"), use_container_width=True)

# 푸터
st.divider()
st.markdown(f"<center>💖 {user_name} & 소은의 배당 엔진 v3.7 💖</center>", unsafe_allow_html=True)

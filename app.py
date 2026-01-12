import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="배당 캘린더 & 배당락", page_icon="🔔", layout="wide")

# 2. 데이터 가져오기 함수 (안전장치 강화 버전)
@st.cache_data(ttl=3600)
def get_stock_details(ticker_code):
    # 기본값 설정
    price, monthly_div, ex_date_str = 0.0, 0.0, "데이터 확인필요"
    usd_krw = 1450.0 # 환율 실패 시 기본값
    
    try:
        # 환율 가져오기
        rate_data = yf.Ticker("USDKRW=X").history(period="1d")
        if not rate_data.empty:
            usd_krw = rate_data['Close'].iloc[-1]
        
        stock = yf.Ticker(ticker_code)
        
        # 1. 주가 가져오기
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
        
        # 2. 배당락일 가져오기 (가장 에러가 많은 부분 분리)
        try:
            ex_div_raw = stock.info.get('exDividendDate')
            if ex_div_raw:
                ex_date_str = datetime.fromtimestamp(ex_div_raw).strftime('%Y-%m-%d')
            else:
                # 한국 ETF(미배콜 등)는 보통 매달 마지막 영업일이 배당락일
                if ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"):
                    ex_date_str = "매월 말일경"
                else:
                    ex_date_str = "분기/월말"
        except:
            ex_date_str = "조회불가(점검중)"

        # 3. 배당금 가져오기
        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent_divs.empty:
                monthly_div = recent_divs.sum() / 12
            else:
                monthly_div = 0
        else:
            # 야후에 데이터 없을 때만 사용하는 보조 데이터베이스
            defaults = {"490600.KS": 105, "402320.KS": 40, "SCHD": 0.2, "O": 0.26}
            monthly_div = defaults.get(ticker_code, 0)

        # 4. 환율 적용
        is_usd = not (ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"))
        if is_usd:
            price *= usd_krw
            monthly_div *= usd_krw
            
        return price, monthly_div, ex_date_str, usd_krw
    except Exception as e:
        # 어떤 오류가 나도 앱은 돌아가게 함
        return 0.0, 0.0, "확인불가", usd_krw

# 3. 세션 상태 및 사이드바 (이전과 동일)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

st.sidebar.header("👤 {0}님의 설정".format(st.session_state.get('user_name', '윤재')))
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.session_state.user_name = user_name

st.sidebar.divider()
st.sidebar.subheader("📂 포트폴리오 관리")

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

# 4. 데이터 계산 및 메인 화면
portfolio_data = []
total_monthly_div = 0
current_usd = 1450.0

for s in st.session_state.stock_list:
    p, d, ex_date, usd = get_stock_details(s['ticker'])
    current_usd = usd
    val = p * s['qty']
    div_val = d * s['qty']
    portfolio_data.append({
        "종목": s['name'],
        "현재가": f"{p:,.0f}원",
        "자산가치": val,
        "배당락일": ex_date,
        "월배당": div_val
    })
    total_monthly_div += div_val

df = pd.DataFrame(portfolio_data)

st.title(f"🔔 {user_name}님의 배당락 & 캘린더")
st.success(f"현재 환율: 1$ = {current_usd:,.2f}원")

# 메인 지표
col1, col2 = st.columns(2)
col1.metric("월 예상 배당 합계", f"{total_monthly_div:,.0f} 원")
col2.metric("연 예상 배당 합계", f"{total_monthly_div * 12:,.0f} 원")

# 상세 표
st.subheader("📋 종목별 상세 정보")
st.table(df[["종목", "현재가", "배당락일", "월배당"]])

# 그래프
st.divider()
months = [f"{i}월" for i in range(1, 13)]
cal_list = []
for m in months:
    for _, row in df.iterrows():
        cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당"]})
st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="월별 배당 현황"), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 {user_name} & 소은의 배당 엔진 v3.8 💖</center>", unsafe_allow_html=True)

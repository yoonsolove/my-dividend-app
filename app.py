import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 실전 관리 시스템", page_icon="💰", layout="wide")

# 2. 데이터 가져오기 함수 (D-Day 및 세금 로직 추가)
@st.cache_data(ttl=300)
def get_stock_details(ticker_code):
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0}
    
    price = price_map.get(ticker_code, 10000.0)
    monthly_div = div_map.get(ticker_code, 50.0)
    ex_date_str = "매월 말일경"
    d_day_msg = "-"
    
    try:
        stock = yf.Ticker(ticker_code)
        # 주가
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
        
        # 배당락일 및 D-Day 계산
        try:
            ex_div_raw = stock.info.get('exDividendDate')
            if ex_div_raw:
                ex_date = datetime.fromtimestamp(ex_div_raw).date()
                ex_date_str = ex_date.strftime('%Y-%m-%d')
                days_left = (ex_date - date.today()).days
                if days_left > 0:
                    d_day_msg = f"D-{days_left}"
                elif days_left == 0:
                    d_day_msg = "오늘(배당락일)"
                else:
                    d_day_msg = "경과"
            elif ticker_code.endswith(".KS") or ticker_code.endswith(".KQ"):
                ex_date_str = "매월 말일경"
                d_day_msg = "월말 대기"
        except:
            ex_date_str = "확인중"

        # 배당금
        div_info = stock.dividends
        if not div_info.empty:
            recent_divs = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent_divs.empty:
                monthly_div = recent_divs.sum() / 12
        
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
st.sidebar.subheader("➕ 새 종목 추가")
new_name = st.sidebar.text_input("종목명")
new_ticker = st.sidebar.text_input("티커")
new_qty = st.sidebar.number_input("수량", min_value=0, value=100)
if st.sidebar.button("포트폴리오에 추가"):
    if new_name and new_ticker:
        st.session_state.stock_list.append({"name": new_name, "ticker": new_ticker, "qty": new_qty})
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📦 보유 종목 관리")
for i, stock in enumerate(st.session_state.stock_list):
    with st.sidebar.expander(f"{stock['name']} ({stock['ticker']})"):
        u_qty = st.number_input(f"수량 변경", value=stock['qty'], key=f"q_{i}")
        if u_qty != stock['qty']:
            st.session_state.stock_list[i]['qty'] = u_qty
            st.rerun()
        if st.button(f"🗑️ 삭제하기", key=f"del_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

st.sidebar.divider()
add_monthly = st.sidebar.slider("매달 추가 투자금 (만원)", 0, 500, 50, step=10)
sim_years = st.sidebar.slider("시뮬레이션 기간 (년)", 1, 40, 20)

# 5. 데이터 계산
portfolio_data = []
total_asset = 0
total_div_pre_tax = 0 # 세전

for s in st.session_state.stock_list:
    p, d, ex, dday = get_stock_details(s['ticker'])
    val = p * s['qty']
    div_pre = d * s['qty']
    div_post = div_pre * (1 - 0.154) # 세후 계산
    
    total_asset += val
    total_div_pre_tax += div_pre
    
    portfolio_data.append({
        "종목": s['name'],
        "현재가": p,
        "배당락일": ex,
        "D-Day": dday,
        "자산가치": val,
        "월 배당(세전)": div_pre,
        "월 배당(세후)": div_post
    })

df = pd.DataFrame(portfolio_data)
total_div_post_tax = total_div_pre_tax * (1 - 0.154)

# 6. 메인 화면 출력
st.title(f"💰 {user_name}님의 스마트 배당 리포트")

# 주요 지표 (Metric)
m1, m2, m3 = st.columns(3)
m1.metric("총 자산 가치", f"{total_asset:,.0f} 원")
m2.metric("월 예상 수령액 (세후)", f"{total_div_post_tax:,.0f} 원", f"세전 {total_div_pre_tax:,.0f}원")
m3.metric("연간 합계 (세후)", f"{total_div_post_tax*12:,.0f} 원")

st.divider()

# 상세 현황 탭
t1, t2 = st.tabs(["📊 실전 투자 상세", "📅 월별 캘린더"])
with t1:
    st.write("**[종목별 배당락 D-Day 및 세후 배당금]**")
    st.dataframe(df.style.format({
        "현재가": "{:,.0f}원",
        "자산가치": "{:,.0f}원",
        "월 배당(세전)": "{:,.0f}원",
        "월 배당(세후)": "{:,.0f}원"
    }), use_container_width=True)
    
    st.caption("💡 세후 금액은 배당소득세 15.4%를 적용한 예상치입니다.")

with t2:
    months = [f"{i}월" for i in range(1, 13)]
    cal_list = []
    for m in months:
        for _, row in df.iterrows():
            cal_list.append({"월": m, "종목": row["종목"], "금액": row["월 배당(세후)"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="연간 세후 배당 흐름"), use_container_width=True)

# 7. 하단 시뮬레이션
st.divider()
st.subheader("❄️ 장기 스노볼 예측 (세후 기준)")
sim_data = []
temp_asset = total_asset
avg_yield_post = (total_div_post_tax * 12) / total_asset if total_asset > 0 else 0.10

for month in range(1, (sim_years * 12) + 1):
    monthly_dividend_post = (temp_asset * avg_yield_post) / 12
    temp_asset += monthly_dividend_post + (add_monthly * 10000)
    if month % 12 == 0:
        sim_data.append({"경과년수": f"{month//12}년", "총자산": int(temp_asset), "세후 월배당": int((temp_asset * avg_yield_post) / 12)})

st.plotly_chart(px.area(pd.DataFrame(sim_data), x="경과년수", y="총자산", title="적립식 투자 시 자산 성장"), use_container_width=True)

# 8. 푸터
st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b>의 투자 시스템 v4.5 💖</center>", unsafe_allow_html=True)

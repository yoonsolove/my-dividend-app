import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="통합 배당 & 세금 관리", page_icon="💸", layout="wide")

# 2. 데이터 가져오기 함수
@st.cache_data(ttl=300)
def get_stock_details(ticker_code):
    price_map = {"490600.KS": 10500.0, "402320.KS": 11500.0}
    div_map = {"490600.KS": 105.0, "402320.KS": 40.0}
    price = price_map.get(ticker_code, 10000.0)
    monthly_div = div_map.get(ticker_code, 50.0)
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

# 4. 사이드바 UI (메뉴 복구 및 순서 조정)
st.sidebar.header(f"👤 {st.session_state.get('user_name', '윤재')}님의 포트폴리오")
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.session_state.user_name = user_name

st.sidebar.divider()
st.sidebar.subheader("➕ 새 종목 추가")
with st.sidebar.container():
    n_name = st.text_input("종목명 (예: 슈드)")
    n_ticker = st.text_input("티커 (예: SCHD)")
    n_qty = st.number_input("수량 설정", min_value=0, value=100)
    if st.sidebar.button("포트폴리오에 추가"):
        if n_name and n_ticker:
            st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
            st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📦 보유 종목 관리")
for i, stock in enumerate(st.session_state.stock_list):
    with st.sidebar.expander(f"{stock['name']} ({stock['ticker']})"):
        u_qty = st.number_input(f"수량 변경", value=stock['qty'], key=f"q_edit_{i}")
        st.session_state.stock_list[i]['qty'] = u_qty
        if st.button(f"🗑️ 삭제하기", key=f"del_btn_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📊 시뮬레이션 설정")
add_monthly = st.sidebar.slider("매달 추가 투자금 (만원)", 0, 500, 50, step=10)
reinvest_rate = st.sidebar.slider("배당금 재투자 비율 (%)", 0, 100, 100)
sim_years = st.sidebar.slider("시뮬레이션 기간 (년)", 1, 40, 20)

# 5. 데이터 계산
portfolio_data = []
total_asset = 0
total_div_pre = 0

for s in st.session_state.stock_list:
    p, d, ex, dday = get_stock_details(s['ticker'])
    val = p * s['qty']
    div_pre = d * s['qty']
    tax = div_pre * 0.154
    div_post = div_pre - tax
    
    total_asset += val
    total_div_pre += div_pre
    
    portfolio_data.append({
        "종목": s['name'], "배당락일": ex, "D-Day": dday,
        "자산가치": val, "월배당(세전)": div_pre, "예상세금": tax, "월배당(세후)": div_post
    })

df = pd.DataFrame(portfolio_data)
total_tax_monthly = total_div_pre * 0.154
total_div_post = total_div_pre - total_tax_monthly

# 6. 메인 화면 출력
st.title(f"📊 {user_name}님의 배당 & 세금 리포트")

# 금융소득종합과세 경고
if total_div_pre * 12 > 20000000:
    st.warning(f"⚠️ 주의: 연간 세전 배당금({total_div_pre*12:,.0f}원)이 2,000만 원을 초과합니다.")

# 지표 섹션
c1, c2, c3, c4 = st.columns(4)
c1.metric("총 자산", f"{total_asset:,.0f} 원")
c2.metric("월 수령액(세후)", f"{total_div_post:,.0f} 원")
c3.metric("월 예상 세금", f"{total_tax_monthly:,.0f} 원", delta_color="inverse")
c4.metric("연 예상 세금", f"{total_tax_monthly*12:,.0f} 원", delta_color="inverse")

st.divider()

# 탭 구성
t1, t2 = st.tabs(["📋 종목 상세 내역", "📅 세후 배당 캘린더"])
with t1:
    st.dataframe(df.style.format({
        "자산가치": "{:,.0f}원", "월배당(세전)": "{:,.0f}원", 
        "예상세금": "{:,.0f}원", "월배당(세후)": "{:,.0f}원"
    }), use_container_width=True)

with t2:
    months = [f"{i}월" for i in range(1, 13)]
    cal_list = []
    for m in months:
        for _, row in df.iterrows():
            cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당(세후)"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", title="연간 세후 배당 흐름"), use_container_width=True)

# 7. 하단 시뮬레이션 섹션
st.divider()
st.subheader("❄️ 미래 성장 시뮬레이션 (세후 기준)")
sim_data = []
temp_asset = total_asset
avg_yield_post = (total_div_post * 12) / total_asset if total_asset > 0 else 0.1

for month in range(1, (sim_years * 12) + 1):
    # (세후 배당금 * 재투자율) + 추가 적립금
    reinvest_amt = (temp_asset * avg_yield_post / 12) * (reinvest_rate / 100) + (add_monthly * 10000)
    temp_asset += reinvest_amt
    if month % 12 == 0:
        sim_data.append({"년수": f"{month//12}년", "자산": int(temp_asset), "세후월배당": int(temp_asset * avg_yield_post / 12)})

sc1, sc2 = st.columns(2)
with sc1:
    st.plotly_chart(px.area(pd.DataFrame(sim_data), x="년수", y="자산", title="장기 자산 성장"), use_container_width=True)
with sc2:
    st.plotly_chart(px.line(pd.DataFrame(sim_data), x="년수", y="세후월배당", title="미래 월급 변화", markers=True), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b> 통합 관리 v4.7 💖</center>", unsafe_allow_html=True)

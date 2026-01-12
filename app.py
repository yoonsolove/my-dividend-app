import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 대시보드 v5.3", page_icon="💸", layout="wide")

# 2. 데이터 함수 (기존 유지)
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
                ex_date_str = "매월 말일"
        except: pass
        div_info = stock.dividends
        if not div_info.empty:
            recent = div_info[div_info.index > (datetime.now() - pd.Timedelta(days=365))]
            if not recent.empty: monthly_div = recent.sum() / 12
        return price, monthly_div, ex_date_str, d_day_msg
    except:
        return price, monthly_div, ex_date_str, d_day_msg

# 3. 세션 상태
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860}
    ]

# 4. 데이터 계산
portfolio_data, total_asset, total_div_pre = [], 0, 0
for s in st.session_state.stock_list:
    p, d, ex, dday = get_stock_details(s['ticker'])
    val, div_pre = p * s['qty'], d * s['qty']
    total_asset += val
    total_div_pre += div_pre
    portfolio_data.append({
        "종목": s['name'], "배당락": ex, "D-Day": dday, 
        "자산가치": val, "월배당(세전)": div_pre, "세후": div_pre * 0.846
    })
df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846

# 5. 메인 대시보드
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.title(f"💰 {user_name}님의 배당 리포트")

c1, c2 = st.columns(2)
c1.metric("총 자산", f"{total_asset:,.0f}원")
c2.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

st.divider()

# 6. [중요] 깨짐 없는 포트폴리오 관리 (Expander 제거)
st.subheader("📝 종목 관리")

# (1) 종목 추가 카드
with st.container():
    st.markdown("### ➕ 새 종목 추가")
    add_c1, add_c2, add_c3 = st.columns([1, 1, 1])
    n_name = add_c1.text_input("종목명", key="final_n")
    n_ticker = add_c2.text_input("티커", key="final_t")
    n_qty = add_c3.number_input("수량", min_value=0, value=100, key="final_q")
    if st.button("🚀 포트폴리오에 즉시 추가", use_container_width=True):
        if n_name and n_ticker:
            st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
            st.rerun()

st.write("") # 간격

# (2) 보유 종목 리스트 수정/삭제 카드
with st.container():
    st.markdown("### 📦 보유 종목 수정 및 삭제")
    for i, stock in enumerate(st.session_state.stock_list):
        # 모바일에서도 보기 좋게 3분할
        edit_c1, edit_c2, edit_c3 = st.columns([2, 2, 1])
        with edit_c1:
            st.write(f"**{stock['name']}**")
        with edit_c2:
            st.session_state.stock_list[i]['qty'] = st.number_input("수량", value=stock['qty'], key=f"fq_{i}", label_visibility="collapsed")
        with edit_c3:
            if st.button("삭제", key=f"fd_{i}", use_container_width=True):
                st.session_state.stock_list.pop(i)
                st.rerun()
        st.write("---")

# 7. 상세 내역 및 그래프
t1, t2 = st.tabs(["종목 상세", "배당 흐름"])
with t1:
    st.dataframe(df, use_container_width=True)
with t2:
    cal_list = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, row in df.iterrows(): cal_list.append({"월": m, "종목": row["종목"], "금액": row["세후"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목"), use_container_width=True)

# 8. 시뮬레이션
st.divider()
st.subheader("❄️ 미래 성장 시뮬레이션")
add_m = st.sidebar.slider("매달 추가 투자(만원)", 0, 500, 50)
sim_y = st.sidebar.slider("시나리오 기간(년)", 1, 40, 20)

sim_data = []
temp_asset, avg_yield_post = total_asset, (total_div_post * 12) / total_asset if total_asset > 0 else 0.1
for m in range(1, (sim_y * 12) + 1):
    temp_asset += (temp_asset * avg_yield_post / 12) + (add_m * 10000)
    if m % 12 == 0: sim_data.append({"년수": f"{m//12}년", "자산(억)": round(temp_asset/100000000, 2)})

st.plotly_chart(px.area(pd.DataFrame(sim_data), x="년수", y="자산(억)", title="자산 성장 (단위: 억)"), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b> 통합 관리 v5.3 💖</center>", unsafe_allow_html=True)

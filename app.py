import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 대시보드 v5.1", page_icon="💸", layout="wide")

# 아이콘 깨짐 방지용 스타일 강제 주입
st.markdown("""
    <style>
    span[data-testid="stExpanderIcon"] { display: none; } /* 화살표 텍스트 깨짐 방지 */
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 가져오기 함수 (캐시 적용)
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

# 3. 세션 상태 초기화
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
        "자산가치": val, "월배당(세전)": div_pre, "세금": div_pre * 0.154, "월배당(세후)": div_pre * 0.846
    })
df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846

# 5. 메인 화면 상단 리포트
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.title(f"📊 {user_name}님의 배당 리포트")

# 지표 섹션 (한 줄에 2개씩 모바일 배치 유도)
m_col1, m_col2 = st.columns(2)
m_col1.metric("총 자산", f"{total_asset:,.0f}원")
m_col2.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

m_col3, m_col4 = st.columns(2)
m_col3.metric("월 예상 세금", f"{total_div_pre*0.154:,.0f}원")
m_col4.metric("연 예상 세금", f"{total_div_pre*12*0.154:,.0f}원")

# 물가 설정 (사이드바 메뉴)
chicken_p = st.sidebar.number_input("🍗 치킨 가격 설정", value=30000, step=1000)
st.info(f"✨ 이번 달 배당금은 치킨 **{total_div_post//chicken_p:,.0f}마리** 분량입니다!")

st.divider()

# 6. 종목 관리 메뉴 (이모지로 텍스트 깨짐 해결)
st.subheader("🛠️ 포트폴리오 관리")
add_tab, edit_tab = st.columns(2)

with add_tab:
    with st.expander("➕ 새 종목 추가하기", expanded=False):
        n_name = st.text_input("종목명", key="add_n")
        n_ticker = st.text_input("티커", key="add_t")
        n_qty = st.number_input("수량", min_value=0, value=100, key="add_q")
        if st.button("포트폴리오 추가"):
            if n_name and n_ticker:
                st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": n_qty})
                st.rerun()

with edit_tab:
    with st.expander("📦 종목 수정/삭제", expanded=False):
        for i, stock in enumerate(st.session_state.stock_list):
            edit_c1, edit_c2 = st.columns([3, 1])
            with edit_c1:
                new_q = st.number_input(f"{stock['name']}", value=stock['qty'], key=f"edit_q_{i}")
                st.session_state.stock_list[i]['qty'] = new_q
            with edit_c2:
                if st.button("🗑️", key=f"edit_d_{i}"):
                    st.session_state.stock_list.pop(i)
                    st.rerun()

st.divider()

# 7. 상세 내역 (가로 스크롤 허용)
t1, t2 = st.tabs(["📋 종목 상세", "📅 캘린더"])
with t1:
    st.dataframe(df.style.format({
        "자산가치": "{:,.0f}", "월배당(세전)": "{:,.0f}", 
        "세금": "{:,.0f}", "월배당(세후)": "{:,.0f}"
    }), use_container_width=True)

with t2:
    cal_list = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, row in df.iterrows(): cal_list.append({"월": m, "종목": row["종목"], "금액": row["월배당(세후)"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_list), x="월", y="금액", color="종목", barmode="stack"), use_container_width=True)

# 8. 미래 시뮬레이션 (그래프 가독성 개선)
st.divider()
st.subheader("❄️ 미래 스노볼 시뮬레이션")
add_monthly = st.sidebar.slider("매달 추가 투자(만원)", 0, 500, 50)
sim_years = st.sidebar.slider("시뮬레이션 기간(년)", 1, 40, 20)

sim_data = []
temp_asset, avg_yield_post = total_asset, (total_div_post * 12) / total_asset if total_asset > 0 else 0.1
for m in range(1, (sim_years * 12) + 1):
    temp_asset += (temp_asset * avg_yield_post / 12) + (add_monthly * 10000)
    if m % 12 == 0:
        sim_data.append({"년수": f"{m//12}년", "자산(억)": round(temp_asset/100000000, 2)})

# 모바일에서 숫자가 겹치지 않게 '억' 단위로 표시
st.plotly_chart(px.area(pd.DataFrame(sim_data), x="년수", y="자산(억)", title="장기 자산 성장 (단위: 억)"), use_container_width=True)

st.divider()
st.markdown(f"<center>💖 <b>{user_name} & 소은</b> 통합 관리 v5.1 💖</center>", unsafe_allow_html=True)

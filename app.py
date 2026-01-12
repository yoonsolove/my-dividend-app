import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 리포트 v6.0", page_icon="💰", layout="wide")

# 2. 가격 자동 호출 함수 (보조용)
@st.cache_data(ttl=300)
def fetch_auto_price(ticker_code):
    try:
        stock = yf.Ticker(ticker_code)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        return 0.0
    except:
        return 0.0

# 3. 세션 상태 (평단가 'avg_price'와 현재가 'cur_price' 추가)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000, "avg_price": 10500.0, "cur_price": 12930.0},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860, "avg_price": 11000.0, "cur_price": 11500.0}
    ]

# 4. 데이터 계산
portfolio_data = []
total_asset, total_div_pre, total_invest = 0, 0, 0

for s in st.session_state.stock_list:
    # 계산: 평가금액, 배당금(임시 1% 가정/자동화 가능), 수익률
    val = s['cur_price'] * s['qty']
    invest_val = s['avg_price'] * s['qty']
    profit_rate = ((s['cur_price'] / s['avg_price']) - 1) * 100 if s['avg_price'] > 0 else 0
    
    # 배당금 호출 (기존 로직 유지)
    _, div_per_share = (0, 105.0) if s['name'] == "미배콜" else (0, 40.0) 
    div_pre = div_per_share * s['qty']
    
    total_asset += val
    total_invest += invest_val
    total_div_pre += div_pre
    
    portfolio_data.append({
        "종목": s['name'], "수량": s['qty'], "평단": s['avg_price'], "현재가": s['cur_price'],
        "수익률": f"{profit_rate:.2f}%", "평가금액": val, "월배당(세후)": div_pre * 0.846
    })

df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846
total_profit_rate = ((total_asset / total_invest) - 1) * 100 if total_invest > 0 else 0

# 5. 메인 화면 상단 지표
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
st.title(f"📊 {user_name}님의 실시간 리포트")

# 지표 섹션 (수익률 추가)
c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{total_asset:,.0f}원", f"{total_asset - total_invest:,.0f}원")
c2.metric("수익률", f"{total_profit_rate:.2f}%")
c3.metric("월 수령액", f"{total_div_post:,.0f}원")

st.divider()

# 6. 종목 관리 (평단가 및 현재가 수정 레이아웃)
st.subheader("📦 보유 종목 및 가격 관리")

for i, stock in enumerate(st.session_state.stock_list):
    with st.container():
        col_n, col_d = st.columns([4, 1])
        col_n.markdown(f"**{i+1}. {stock['name']}** ({stock['ticker']})")
        if col_d.button("삭제", key=f"v6_del_{i}"):
            st.session_state.stock_list.pop(i)
            st.rerun()
        
        # 3열 배치 (수량, 평단가, 현재가)
        edit_c1, edit_c2, edit_c3 = st.columns(3)
        st.session_state.stock_list[i]['qty'] = edit_c1.number_input("수량", value=stock['qty'], key=f"v6_q_{i}")
        st.session_state.stock_list[i]['avg_price'] = edit_c2.number_input("내 평단가", value=stock['avg_price'], key=f"v6_a_{i}")
        
        # 현재가 입력창 (자동 불러오기 버튼 옆에 배치)
        new_cur = edit_c3.number_input("현재가(수정)", value=stock['cur_price'], key=f"v6_c_{i}")
        st.session_state.stock_list[i]['cur_price'] = new_cur
        
        st.write("---")

# 7. 종목 추가
with st.expander("➕ 새 종목 추가"):
    ac1, ac2 = st.columns(2)
    new_name = ac1.text_input("종목명")
    new_ticker = ac2.text_input("티커(ex. 005930.KS)")
    new_q = st.number_input("초기 수량", value=100)
    if st.button("포트폴리오에 추가"):
        auto_p = fetch_auto_price(new_ticker) if new_ticker else 10000.0
        st.session_state.stock_list.append({
            "name": new_name, "ticker": new_ticker, "qty": new_q, 
            "avg_price": auto_p, "cur_price": auto_p
        })
        st.rerun()

# 8. 시뮬레이션 및 나머지 (기존 버전과 동일하게 유지)
# ... (중략: 이전 버전의 시뮬레이션 및 캘린더 코드 삽입 가능) ...

st.markdown(f"<center>💖 <b>{user_name} & 소은</b> v6.0</center>", unsafe_allow_html=True)

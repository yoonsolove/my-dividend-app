import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# 1. 앱 설정
st.set_page_config(page_title="배당 리포트 v6.2", page_icon="💰", layout="wide")

# 2. 세션 상태 (평단가 및 현재가 초기값)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000, "avg_price": 10500.0, "cur_price": 12930.0},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860, "avg_price": 11000.0, "cur_price": 11500.0}
    ]

# --- [수정 포인트] 가격 수정 입력창을 상단으로 배치하여 즉시 반영되도록 함 ---

# 3. 사용자 및 물가 설정 (사이드바)
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
chicken_p = st.sidebar.number_input("치킨 가격", value=30000, step=1000)

st.title(f"📊 {user_name}님의 실시간 리포트")

# 4. 종목 관리 및 가격 수정 (계산 전에 배치)
with st.expander("📦 보유 종목 수량/가격 수정", expanded=False):
    for i, stock in enumerate(st.session_state.stock_list):
        with st.container():
            mc1, mc2 = st.columns([4, 1])
            mc1.write(f"**{i+1}. {stock['name']}**")
            if mc2.button("삭제", key=f"del_{i}"):
                st.session_state.stock_list.pop(i)
                st.rerun()
            
            ec1, ec2, ec3 = st.columns(3)
            # 수동 입력값이 즉시 세션에 저장됨
            st.session_state.stock_list[i]['qty'] = ec1.number_input(f"{stock['name']} 수량", value=stock['qty'], key=f"q_{i}")
            st.session_state.stock_list[i]['avg_price'] = ec2.number_input(f"{stock['name']} 평단가", value=stock['avg_price'], key=f"a_{i}")
            st.session_state.stock_list[i]['cur_price'] = ec3.number_input(f"{stock['name']} 현재가", value=stock['cur_price'], key=f"c_{i}")
            st.write("---")

# 5. 데이터 계산 로직 (수정된 값을 바탕으로 계산)
portfolio_data = []
total_asset, total_invest, total_div_pre = 0, 0, 0

for s in st.session_state.stock_list:
    val = s['cur_price'] * s['qty']
    invest_val = s['avg_price'] * s['qty']
    div_per_share = 105.0 if "미배콜" in s['name'] else 40.0
    div_pre = div_per_share * s['qty']
    
    total_asset += val
    total_invest += invest_val
    total_div_pre += div_pre
    
    portfolio_data.append({
        "종목": s['name'], "수량": s['qty'], "평단": s['avg_price'], "현재가": s['cur_price'],
        "평가금액": val, "수익률": f"{((s['cur_price']/s['avg_price'])-1)*100:.2f}%" if s['avg_price']>0 else "0%",
        "월배당(세후)": div_pre * 0.846
    })

df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846
total_profit_rate = ((total_asset / total_invest) - 1) * 100 if total_invest > 0 else 0

# 6. 대시보드 지표 표시
c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{total_asset:,.0f}원", f"{total_asset - total_invest:,.0f}원")
c2.metric("전체 수익률", f"{total_profit_rate:.2f}%")
c3.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

st.info(f"✨ 현재 배당금으로 매달 **치킨 {total_div_post//chicken_p:,.0f}마리** 가능!")
st.divider()

# 7. 상세 내역 및 캘린더 탭
tab1, tab2 = st.tabs(["📋 상세 내역", "📅 배당 캘린더"])
with tab1:
    st.dataframe(df, use_container_width=True)
with tab2:
    cal_data = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, row in df.iterrows():
            cal_data.append({"월": m, "종목": row["종목"], "금액": row["월배당(세후)"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_data), x="월", y="금액", color="종목"), use_container_width=True)

# 8. 투자 시나리오 및 시뮬레이션
st.divider()
st.subheader("⚙️ 미래 투자 시나리오 (수동 입력)")
col_s1, col_s2, col_s3 = st.columns(3)
add_m = col_s1.number_input("매달 추가 투자 (만원)", value=100, step=1)
reinvest_r = col_s2.number_input("배당 재투자 비율 (%)", value=100, min_value=0, max_value=100)
sim_y = col_s3.number_input("예측 기간 (년)", value=20, min_value=1)

sim_results = []
curr_sim_asset = total_asset
ann_yield = (total_div_post * 12) / total_asset if total_asset > 0 else 0.1

for m in range(1, (sim_y * 12) + 1):
    m_div = (curr_sim_asset * ann_yield / 12)
    curr_sim_asset += (m_div * (reinvest_r / 100)) + (add_m * 10000)
    if m % (5 * 12) == 0 or m == (sim_y * 12):
        y = m // 12
        sim_results.append({
            "년수": f"{y}년 후", 
            "자산(억)": round(curr_sim_asset / 100000000, 2),
            "월배당(만원)": int((curr_sim_asset * ann_yield / 12) / 10000)
        })

st.plotly_chart(px.area(pd.DataFrame(sim_results), x="년수", y="자산(억)", text="자산(억)"), use_container_width=True)

# 주요 수치 요약
for row in sim_results:
    with st.container():
        sc1, sc2, sc3 = st.columns([1, 2, 2])
        sc1.write(f"📅 **{row['년수']}**")
        sc2.metric("자산", f"{row['자산(억)']}억")
        sc3.metric("월급", f"{row['월배당(만원)']}만")
        st.write("---")

# 9. 새 종목 추가
with st.expander("➕ 새 종목 추가"):
    nc1, nc2 = st.columns(2)
    n_name = nc1.text_input("종목명", key="new_n")
    n_ticker = nc2.text_input("티커", key="new_t")
    if st.button("추가하기"):
        st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": 100, "avg_price": 10000.0, "cur_price": 10000.0})
        st.rerun()

st.markdown(f"<center>💖 <b>{user_name} & 소은</b> v6.2</center>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# 1. 앱 설정
st.set_page_config(page_title="배당 리포트 v6.5", page_icon="💰", layout="wide")

# 2. 세션 상태 (기본 데이터 설정)
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = [
        {"name": "미배콜", "ticker": "490600.KS", "qty": 2000, "avg_price": 10500.0, "cur_price": 12930.0},
        {"name": "미배당", "ticker": "402320.KS", "qty": 860, "avg_price": 11000.0, "cur_price": 11500.0}
    ]

# 3. 사용자 및 물가 설정 (사이드바)
user_name = st.sidebar.text_input("사용자 이름", value="윤재")
chicken_p = st.sidebar.number_input("치킨 가격", value=30000, step=1000)

st.title(f"📊 {user_name}님의 실시간 리포트")

# 4. [중요] 가격 수정 및 종목 관리 (최상단 배치로 즉시 반영)
with st.expander("📦 보유 종목 수량/가격 수정 (평단가 & 현재가)", expanded=False):
    for i, stock in enumerate(st.session_state.stock_list):
        with st.container():
            mc1, mc2 = st.columns([4, 1])
            mc1.write(f"**{i+1}. {stock['name']}**")
            if mc2.button("삭제", key=f"del_{i}"):
                st.session_state.stock_list.pop(i)
                st.rerun()
            
            ec1, ec2, ec3 = st.columns(3)
            st.session_state.stock_list[i]['qty'] = ec1.number_input(f"{stock['name']} 수량", value=stock['qty'], key=f"q_{i}")
            st.session_state.stock_list[i]['avg_price'] = ec2.number_input(f"{stock['name']} 내 평단가", value=stock['avg_price'], key=f"a_{i}")
            st.session_state.stock_list[i]['cur_price'] = ec3.number_input(f"{stock['name']} 현재가(수정)", value=stock['cur_price'], key=f"c_{i}")
            st.write("---")

# 5. 데이터 계산 로직
portfolio_data = []
total_asset, total_invest, total_div_pre = 0, 0, 0

for s in st.session_state.stock_list:
    val = s['cur_price'] * s['qty']
    invest_val = s['avg_price'] * s['qty']
    # 배당금 산정 (임시 기준값)
    div_per_share = 105.0 if "미배콜" in s['name'] else 40.0
    div_pre = div_per_share * s['qty']
    
    total_asset += val
    total_invest += invest_val
    total_div_pre += div_pre
    
    portfolio_data.append({
        "종목": s['name'], "수량": s['qty'], "평단": f"{s['avg_price']:,.0f}", 
        "현재가": f"{s['cur_price']:,.0f}", "평가금액": val, 
        "수익률": f"{((s['cur_price']/s['avg_price'])-1)*100:.2f}%" if s['avg_price']>0 else "0%",
        "월배당(세후)": div_pre * 0.846
    })

df = pd.DataFrame(portfolio_data)
total_div_post = total_div_pre * 0.846
total_profit_rate = ((total_asset / total_invest) - 1) * 100 if total_invest > 0 else 0

# 6. 상단 대시보드 지표
c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{total_asset:,.0f}원", f"{total_asset - total_invest:,.0f}원")
c2.metric("전체 수익률", f"{total_profit_rate:.2f}%")
c3.metric("월 수령액(세후)", f"{total_div_post:,.0f}원")

st.info(f"✨ 현재 배당금으로 매달 **치킨 {total_div_post//chicken_p:,.0f}마리**를 드실 수 있습니다!")
st.divider()

# 7. 상세 내역 및 캘린더 탭
tab1, tab2 = st.tabs(["📋 실시간 상세내역", "📅 월별 배당현황"])
with tab1:
    st.dataframe(df, use_container_width=True)
with tab2:
    cal_data = []
    for m in [f"{i}월" for i in range(1, 13)]:
        for _, row in df.iterrows():
            cal_data.append({"월": m, "종목": row["종목"], "금액": row["월배당(세후)"]})
    st.plotly_chart(px.bar(pd.DataFrame(cal_data), x="월", y="금액", color="종목", barmode="group"), use_container_width=True)

# 8. 투자 시나리오 및 배당 성장 시뮬레이션
st.divider()
st.subheader("⚙️ 미래 투자 시나리오 (배당 성장 반영)")
sc1, sc2, sc3, sc4 = st.columns(4)

with sc1: add_m = st.number_input("매달 추가 투자 (만원)", value=100, step=10)
with sc2: reinvest_r = st.number_input("배당 재투자 비율 (%)", value=100, max_value=100)
with sc3: div_growth = st.number_input("연 배당 성장률 (%)", value=5, help="기업이 매년 배당금을 올리는 비율")
with sc4: sim_y = st.number_input("예측 기간 (년)", value=20, step=5)

# 복리 계산 엔진
sim_list = []
curr_sim_asset = total_asset
# 현재 자산 대비 연 배당률 산출
annual_yield = (total_div_post * 12) / total_asset if total_asset > 0 else 0.1

for m in range(1, (sim_y * 12) + 1):
    # 매년 초(13개월, 25개월...)에 배당금 자체를 성장시킴
    if m % 12 == 1 and m > 1:
        annual_yield *= (1 + (div_growth / 100))
        
    m_div = (curr_sim_asset * annual_yield / 12)
    # 투자금 = (발생 배당금 * 재투자율) + 추가 매수금
    curr_sim_asset += (m_div * (reinvest_r / 100)) + (add_m * 10000)
    
    if m % (5 * 12) == 0 or m == (sim_y * 12):
        y = m // 12
        sim_list.append({
            "년수": f"{y}년 후", 
            "자산(억)": round(curr_sim_asset / 100000000, 2),
            "월급(만원)": int((curr_sim_asset * annual_yield / 12) / 10000)
        })

# 결과 시각화
df_sim = pd.DataFrame(sim_list)
st.plotly_chart(px.area(df_sim, x="년수", y="자산(억)", text="자산(억)", title="배당 성장이 반영된 자산 흐름"), use_container_width=True)

# 요약 카드
for row in sim_list:
    with st.container():
        res1, res2, res3 = st.columns([1, 2, 2])
        res1.write(f"📅 **{row['년수']}**")
        res2.metric("예상 자산", f"{row['자산(억)']}억")
        res3.metric("예상 월급", f"{row['월급(만원)']}만")
        st.write("---")

# 9. 새 종목 추가
with st.expander("➕ 새 종목 추가"):
    nc1, nc2 = st.columns(2)
    n_name = nc1.text_input("종목명", key="n_name")
    n_ticker = nc2.text_input("티커", key="n_tick")
    if st.button("포트폴리오에 추가"):
        st.session_state.stock_list.append({"name": n_name, "ticker": n_ticker, "qty": 100, "avg_price": 10000.0, "cur_price": 10000.0})
        st.rerun()

st.markdown(f"<center>💖 <b>{user_name} & 소은</b> v6.5</center>", unsafe_allow_html=True)

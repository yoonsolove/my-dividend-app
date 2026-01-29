import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v5.0", layout="wide", page_icon="🚀")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "투자액", "배당률", "배당성장률", "배당락일", "유형"])

# --- 사이드바: 1. 종목 관리 ---
st.sidebar.title("➕ 종목 추가/수정")
with st.sidebar.form("add_form"):
    name = st.text_input("종목명(코드)", value="441640").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    amount = st.number_input("현재 보유금액 (원)", min_value=0, value=20000000, step=100000)
    yield_rate = st.number_input("현재 배당률 (%)", min_value=0.0, value=3.5, step=0.1)
    default_growth = 10.0 if category == "배당성장주" else 0.5
    growth_rate = st.number_input("연간 배당성장률 (%)", value=default_growth, step=0.1)
    ex_date = st.date_input("차기 배당락일", value=date.today())
    
    submitted = st.form_submit_button("포트폴리오 반영")
    if submitted:
        new_row = pd.DataFrame([[name, amount, yield_rate, growth_rate, ex_date, category]], 
                               columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
        st.success(f"{name} 등록 완료!")

# --- 사이드바: 2. 재투자 및 적립 설정 (중요 핵심!) ---
st.sidebar.title("⚙️ 재투자 및 적립 설정")
reinvest = st.sidebar.checkbox("배당금 전액 재투자", value=True)
monthly_add = st.sidebar.number_input("매달 추가 투자액 (원)", min_value=0, value=1000000, step=100000)

# --- 메인 화면 ---
st.title("📈 초복리 배당 성장 분석 (재투자+추가적립)")

if st.session_state.portfolio.empty:
    st.info("왼쪽에서 종목을 등록하고 투자 설정을 마쳐주세요.")
else:
    # 1. 상단 요약
    total_invest_now = st.session_state.portfolio['투자액'].sum()
    st.metric("현재 총 자산", f"{total_invest_now:,.0f}원")

    st.divider()

    # 2. 10개년 복리 예측 수치 계산
    st.subheader("🚀 재투자 및 추가 적립 시뮬레이션 (10년)")
    
    years = list(range(1, 11))
    
    # 각 종목별/연도별 데이터를 담을 리스트
    forecast_data = []
    
    # 전체 포트폴리오를 하나의 덩어리로 계산 (비중 유지 가정)
    # 실제 정밀 계산을 위해 각 종목별 비중을 계산
    portfolio_yield = (st.session_state.portfolio['투자액'] * st.session_state.portfolio['배당률'] / 100).sum() / total_invest_now
    portfolio_growth = (st.session_state.portfolio['투자액'] * st.session_state.portfolio['배당성장률'] / 100).sum() / total_invest_now

    for _, row in st.session_state.portfolio.iterrows():
        stock_name = row['종목명']
        current_principal = row['투자액']
        stock_yield = row['배당률'] / 100
        stock_growth = row['배당성장률'] / 100
        
        # 포트폴리오 내 비중 계산 (추가 적립금을 나눌 기준)
        weight = row['투자액'] / total_invest_now
        
        row_stats = {"종목명": stock_name}
        
        for y in years:
            # 1년간 받을 배당금 계산 (세후 15.4% 가정)
            annual_div = current_principal * stock_yield * 0.846
            
            # 수치 기록 (해당 연도 시작 시점의 연 배당금)
            row_stats[f"{y}년차"] = int(current_principal * stock_yield)
            
            # --- 자산 업데이트 (다음 연도를 위해) ---
            # 1. 배당 성장 (기업이 주는 배당금 자체가 늘어남)
            stock_yield = stock_yield * (1 + stock_growth)
            
            # 2. 배당금 재투자 (원금이 늘어남)
            if reinvest:
                current_principal += annual_div
            
            # 3. 추가 투자액 적립 (매달 monthly_add 만큼 원금에 추가)
            # 해당 종목 비중만큼 추가 적립
            current_principal += (monthly_add * 12 * weight)
            
        forecast_data.append(row_stats)

    # 데이터프레임 생성
    df_result = pd.DataFrame(forecast_data)
    
    # 합계 계산
    sum_row = {"종목명": "📊 연도별 총합계"}
    for y in years:
        sum_row[f"{y}년차"] = df_result[f"{y}년차"].sum()
    df_result = pd.concat([df_result, pd.DataFrame([sum_row])], ignore_index=True)

    # 표 출력
    st.write(f"### [매월 {monthly_add:,.0f}원 추가 투자 + 배당 재투자 시 예상 배당금]")
    st.dataframe(
        df_result.style.format({f"{y}년차": "{:,.0f}원" for y in years}),
        use_container_width=True
    )

    st.divider()

    # 3. 추가 정보 제공
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"""
        **복리의 원리 적용 내역:**
        1. **배당 성장:** 기업이 배당금을 매년 {portfolio_growth*100:.1f}%씩 늘림.
        2. **재투자:** 받은 배당금(세후 15.4% 제외)으로 주식을 더 삼.
        3. **추가 적립:** 매달 {monthly_add:,.0f}원씩 새 주식을 더 삼.
        """)
    with c2:
        # 10년 뒤 총 자산 추정치 (마지막 계산된 principal 합계)
        st.success(f"**10년 뒤 예상 연간 배당금:** 약 {sum_row['10년차']:,.0f}원")
        st.caption("※ 이 수치는 주가 상승을 제외한 '배당금'의 성장만을 계산한 보수적인 수치입니다.")

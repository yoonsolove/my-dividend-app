import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="월 배당 마스터 v5.5", layout="wide", page_icon="🌙")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "투자액", "배당률", "배당성장률", "배당락일", "유형"])

# --- 사이드바: 설정 ---
st.sidebar.title("➕ 종목 및 투자 설정")
with st.sidebar.form("add_form"):
    name = st.text_input("종목명(코드)", value="441640").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    amount = st.number_input("현재 보유금액 (원)", min_value=0, value=20000000, step=100000)
    yield_rate = st.number_input("현재 배당률 (%)", min_value=0.0, value=3.5, step=0.1)
    growth_rate = st.number_input("연간 배당성장률 (%)", value=10.0 if category == "배당성장주" else 0.5, step=0.1)
    ex_date = st.date_input("차기 배당락일", value=date.today())
    
    submitted = st.form_submit_button("포트폴리오 반영")
    if submitted:
        new_row = pd.DataFrame([[name, amount, yield_rate, growth_rate, ex_date, category]], 
                               columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)

st.sidebar.markdown("---")
reinvest = st.sidebar.checkbox("배당금 전액 재투자", value=True)
monthly_add = st.sidebar.number_input("매달 추가 투자액 (원)", min_value=0, value=1000000, step=100000)

# --- 메인 화면 ---
st.title("🌙 월간 배당금 성장 시뮬레이션")
st.caption("재투자 + 매달 적립식 투자를 반영한 '월급' 변화 수치입니다.")

if st.session_state.portfolio.empty:
    st.info("왼쪽 사이드바에서 종목을 먼저 등록해주세요.")
else:
    # 데이터 계산 로직
    total_now = st.session_state.portfolio['투자액'].sum()
    years = list(range(1, 11))
    forecast_rows = []

    for _, row in st.session_state.portfolio.iterrows():
        current_principal = row['투자액']
        stock_yield = row['배당률'] / 100
        stock_growth = row['배당성장률'] / 100
        weight = row['투자액'] / total_now
        
        row_stats = {"종목명": row['종목명']}
        
        for y in years:
            # 해당 연도의 '월 평균 배당금' (세전 기준)
            monthly_div = (current_principal * stock_yield) / 12
            row_stats[f"{y}년차"] = int(monthly_div)
            
            # 다음 연도를 위한 복리 계산 (세후 재투자 반영)
            annual_div_after_tax = (current_principal * stock_yield) * 0.846
            stock_yield *= (1 + stock_growth) # 배당금 자체의 성장
            
            if reinvest:
                current_principal += annual_div_after_tax # 배당 재투자
            
            current_principal += (monthly_add * 12 * weight) # 매달 추가 적립
            
        forecast_rows.append(row_stats)

    # 테이블 생성
    df_monthly = pd.DataFrame(forecast_rows)
    
    # 합계 행 추가
    sum_row = {"종목명": "📊 월 배당 합계(세전)"}
    for y in years:
        sum_row[f"{y}년차"] = df_monthly[f"{y}년차"].sum()
    df_monthly = pd.concat([df_monthly, pd.DataFrame([sum_row])], ignore_index=True)

    # 결과 출력
    st.write(f"### 📅 연도별 예상 '월평균' 수령액")
    st.dataframe(
        df_monthly.style.format({f"{y}년차": "{:,.0f}원" for y in years}),
        use_container_width=True
    )

    # 요약 정보
    st.divider()
    final_monthly = sum_row['10년차']
    st.success(f"🚀 현재 페이스 유지 시, **10년 후 당신의 월 배당금은 {final_monthly:,.0f}원**이 됩니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**실수령액 기준 (세후 15.4%):**\n\n"
                f"- 1년차 월 세후: {int(sum_row['1년차'] * 0.846):,.0f}원\n"
                f"- 10년차 월 세후: {int(sum_row['10년차'] * 0.846):,.0f}원")
    with col2:
        # 간단한 목표 설정 (예: 월 300만원 목표)
        target = 3000000
        progress = min(sum_row['1년차'] / target, 1.0)
        st.write(f"**목표 월 배당({target:,.0f}원) 달성률**")
        st.progress(progress)
        st.caption(f"현재 목표의 {progress*100:.1f}% 지점을 지나고 있습니다.")

import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="배당 마스터 v6.0", layout="wide", page_icon="📈")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])

# --- 사이드바: 1. 종목 상세 입력 (수량/주가 기반) ---
st.sidebar.title("➕ 종목 상세 등록")
with st.sidebar.form("add_form"):
    name = st.text_input("종목명(코드)", value="441640").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    
    # 주가와 수량 입력 (이게 들어가야 정확한 재투자 계산이 가능합니다)
    count = st.number_input("현재 보유 수량 (주)", min_value=0, value=100)
    price = st.number_input("현재 주가 (원)", min_value=0, value=100000)
    dps = st.number_input("연간 주당 배당금 (원)", min_value=0, value=3500)
    
    growth_rate = st.number_input("연간 배당성장률 (%)", value=10.0 if category == "배당성장주" else 0.5)
    
    submitted = st.form_submit_button("포트폴리오 반영")
    if submitted:
        new_row = pd.DataFrame([[name, count, price, dps, growth_rate, category]], 
                               columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)

st.sidebar.markdown("---")
st.sidebar.title("⚙️ 투자 환경 설정")
monthly_add = st.sidebar.number_input("매달 추가 투자액 (원)", min_value=0, value=1000000)
price_growth = st.sidebar.slider("연간 주가 상승률 예측 (%)", 0, 15, 3) # 주가 상승 시 주식을 덜 사게 되는 효과 반영

# --- 메인 화면 ---
st.title("📈 주식 수 기반 월 배당 성장 시뮬레이션")

if st.session_state.portfolio.empty:
    st.info("사이드바에서 현재 주가와 보유 수량을 입력해주세요.")
else:
    # 계산 로직
    years = list(range(1, 11))
    forecast_rows = []

    for _, row in st.session_state.portfolio.iterrows():
        current_shares = row['보유수량']
        current_price = row['현재주가']
        current_dps = row['주당배당금']
        stock_growth = row['배당성장률'] / 100
        
        row_stats = {"종목명": row['종목명']}
        
        for y in years:
            # 해당 연도 월 배당금 계산 (수량 * 주당배당금 / 12)
            monthly_div = (current_shares * current_dps) / 12
            row_stats[f"{y}년차"] = int(monthly_div)
            
            # --- 복리 엔진 가동 ---
            # 1. 기업의 배당금 인상 (DPS 증가)
            current_dps *= (1 + stock_growth)
            
            # 2. 추가 매수 (추가 투자금 + 세후 배당금)
            annual_div_net = (current_shares * (current_dps / (1+stock_growth))) * 0.846
            total_fresh_cash = annual_div_net + (monthly_add * 12 * (1/len(st.session_state.portfolio)))
            
            # 주가도 상승한다고 가정 (주가가 오르면 같은 돈으로 살 수 있는 주식 수는 줄어듦)
            current_price *= (1 + (price_growth / 100))
            new_shares = total_fresh_cash / current_price
            current_shares += new_shares
            
        forecast_rows.append(row_stats)

    # 데이터 출력
    df_monthly = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 배당 합계(세전)"}
    for y in years:
        sum_row[f"{y}년차"] = df_monthly[f"{y}년차"].sum()
    df_monthly = pd.concat([df_monthly, pd.DataFrame([sum_row])], ignore_index=True)

    st.write("### 📅 연도별 예상 '월평균' 수령액")
    st.dataframe(df_monthly.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)

    # 시각적 피드백
    st.success(f"💡 주가가 매년 {price_growth}% 상승한다고 가정할 때, 재투자로 불어나는 **주식 수**를 포함한 수치입니다.")

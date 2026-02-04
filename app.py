import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v7.5", layout="wide", page_icon="🚀")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])

# --- 사이드바: 1. 종목 등록 ---
st.sidebar.title("➕ 종목 실시간 등록")
with st.sidebar.form("add_form"):
    ticker = st.text_input("티커/종목코드 (예: 441640.KS, SCHD)", value="441640.KS").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    count = st.number_input("현재 보유 수량 (주)", min_value=0, value=2080)
    
    # ⚠️ 중요: 주가가 원화면 배당금도 '원'으로 입력해야 합니다.
    dps = st.number_input("연간 주당 배당금 (원/달러 단위통일 필수)", min_value=0.0, value=1200.0, step=10.0)
    growth_rate = st.number_input("연간 배당성장률 (%)", value=10.0, step=0.1)
    
    submitted = st.form_submit_button("실시간 주가로 등록")
    
    if submitted:
        try:
            stock_data = yf.Ticker(ticker)
            current_price = stock_data.history(period="1d")['Close'].iloc[-1]
            
            new_row = pd.DataFrame([[ticker, count, current_price, dps, growth_rate, category]], 
                                   columns=st.session_state.portfolio.columns)
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
            st.success(f"✅ {ticker} 등록! 현재가: {current_price:,.0f}원 / 주당배당금: {dps:,.0f}원")
        except:
            st.error("티커를 확인해 주세요. (한국주식은 뒤에 .KS 또는 .KQ를 붙여야 합니다)")

# --- 사이드바: 2. 환경 설정 ---
st.sidebar.markdown("---")
st.sidebar.title("⚙️ 투자 환경 설정")
monthly_add = st.sidebar.number_input("매달 추가 투자액 (원)", min_value=0, value=1000000, step=100000)
price_growth = st.sidebar.slider("연간 주가 상승률 (%)", 0, 15, 3)

# --- 메인 화면 ---
st.title("📈 초정밀 배당 월급 시뮬레이션 v7.5")

if st.session_state.portfolio.empty:
    st.info("왼쪽에서 종목을 먼저 등록해주세요.")
else:
    # 1. 상단 요약
    total_val = (st.session_state.portfolio['보유수량'] * st.session_state.portfolio['현재주가']).sum()
    st.metric("현재 포트폴리오 평가액", f"{total_val:,.0f}원")

    # 2. 복리 시뮬레이션
    years = list(range(1, 11))
    forecast_rows = []

    for _, row in st.session_state.portfolio.iterrows():
        cur_shares = float(row['보유수량'])
        cur_price = float(row['현재주가'])
        cur_dps = float(row['주당배당금'])
        dgr = row['배당성장률'] / 100
        pgr = price_growth / 100
        
        stock_forecast = {"종목명": row['종목명']}
        
        for y in years:
            # 월 평균 배당금 기록 (세전)
            monthly_income = (cur_shares * cur_dps) / 12
            stock_forecast[f"{y}년차"] = int(monthly_income)
            
            # 다음 연도 데이터 업데이트
            # 1. 배당 성장
            cur_dps *= (1 + dgr)
            
            # 2. 가용 자금 (세후 배당금 + 12개월 추가 적립액)
            # 전년도 DPS 기준으로 배당금 계산
            annual_div_net = (cur_shares * (cur_dps / (1 + dgr))) * 0.846
            fresh_cash = annual_div_net + (monthly_add * 12)
            
            # 3. 주가 상승 및 수량 증가
            cur_price *= (1 + pgr)
            cur_shares += (fresh_cash / cur_price)
            
        forecast_rows.append(stock_forecast)

    df_res = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 배당 합계(세전)"}
    for y in years:
        sum_row[f"{y}년차"] = df_res[f"{y}년차"].sum()
    df_res = pd.concat([df_res, pd.DataFrame([sum_row])], ignore_index=True)

    st.write("### 📅 연도별 예상 '월평균' 수령액")
    st.dataframe(df_res.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)

    st.success(f"🚀 **10년 후 예상 월 배당금:** {sum_row['10년차']:,.0f}원 (세전)")

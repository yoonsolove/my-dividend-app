import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v7.0", layout="wide", page_icon="🚀")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])

# --- 사이드바: 1. 종목 등록 (실시간 주가 연동) ---
st.sidebar.title("➕ 종목 실시간 등록")
with st.sidebar.form("add_form"):
    ticker = st.text_input("티커/종목코드 (예: SCHD, 441640.KS)", value="SCHD").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    count = st.number_input("현재 보유 수량 (주)", min_value=0, value=100)
    
    # 주당 배당금은 종목마다 정책이 다르므로 수동 입력이 가장 정확합니다.
    dps = st.number_input("연간 주당 배당금 (원/달러)", min_value=0.0, value=3.5, step=0.1)
    growth_rate = st.number_input("연간 배당성장률 (%)", value=10.0 if category == "배당성장주" else 0.5)
    
    submitted = st.form_submit_button("실시간 주가로 등록")
    
    if submitted:
        try:
            # yfinance로 실시간 주가 가져오기
            stock_data = yf.Ticker(ticker)
            current_price = stock_data.history(period="1d")['Close'].iloc[-1]
            
            new_row = pd.DataFrame([[ticker, count, current_price, dps, growth_rate, category]], 
                                   columns=st.session_state.portfolio.columns)
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
            st.success(f"✅ {ticker} 등록 완료! (현재가: {current_price:,.2f})")
        except:
            st.error("⚠️ 주가를 가져올 수 없습니다. 티커를 확인해 주세요. (한국주식 예: 005930.KS)")

# --- 사이드바: 2. 환경 설정 ---
st.sidebar.markdown("---")
st.sidebar.title("⚙️ 투자 환경 설정")
monthly_add = st.sidebar.number_input("매달 추가 투자액 (원/달러)", min_value=0, value=1000000, step=100000)
price_growth = st.sidebar.slider("연간 주가 상승률 예측 (%)", 0, 15, 3)

# --- 메인 화면 ---
st.title("📈 초정밀 배당 월급 시뮬레이션")
st.caption("실시간 주가와 주식 수 증가를 반영한 10년 로드맵입니다.")

if st.session_state.portfolio.empty:
    st.info("왼쪽 사이드바에서 종목 티커를 입력하고 '실시간 주가로 등록'을 눌러주세요.")
else:
    # 1. 상단 현재 상태 요약
    total_value = (st.session_state.portfolio['보유수량'] * st.session_state.portfolio['현재주가']).sum()
    st.metric("현재 포트폴리오 평가액", f"{total_value:,.0f}")

    st.divider()

    # 2. 복리 시뮬레이션 계산
    years = list(range(1, 11))
    forecast_rows = []

    for _, row in st.session_state.portfolio.iterrows():
        cur_shares = row['보유수량']
        cur_price = row['현재주가']
        cur_dps = row['주당배당금']
        dgr = row['배당성장률'] / 100
        pgr = price_growth / 100
        
        stock_monthly_forecast = {"종목명": row['종목명']}
        
        for y in years:
            # y년차 월 평균 배당금 기록
            monthly_income = (cur_shares * cur_dps) / 12
            stock_monthly_forecast[f"{y}년차"] = int(monthly_income)
            
            # --- 자산 증식 로직 (연말 기준 업데이트) ---
            # A. 배당금 자체의 성장
            cur_dps *= (1 + dgr)
            
            # B. 재투자 및 추가 매수 가능 금액 (세후 배당금 + 12개월 적립금)
            net_div = (cur_shares * (cur_dps / (1+dgr))) * 0.846
            fresh_cash = net_div + (monthly_add * 12 * (1/len(st.session_state.portfolio)))
            
            # C. 주가 상승 반영 및 주식 수 업데이트
            cur_price *= (1 + pgr)
            new_shares_bought = fresh_cash / cur_price
            cur_shares += new_shares_bought
            
        forecast_rows.append(stock_monthly_forecast)

    # 결과 테이블 구성
    df_result = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 배당 합계(세전)"}
    for y in years:
        sum_row[f"{y}년차"] = df_result[f"{y}년차"].sum()
    df_result = pd.concat([df_result, pd.DataFrame([sum_row])], ignore_index=True)

    st.write("### 📅 연도별 예상 '월평균' 수령액")
    st.dataframe(df_result.style.format({f"{y}년차": "{:,.0f}" for y in years}), use_container_width=True)

    # 3. 분석 가이드
    st.divider()
    st.subheader("💡 투자 포인트 분석")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**왜 숫자가 이렇게 늘어나나요?**")
        st.write(f"1. **배당 성장**: 기업이 매년 배당을 늘림")
        st.write(f"2. **수량 증가**: 받은 배당금으로 주식을 더 삼")
        st.write(f"3. **적립 효과**: 매달 추가로 {monthly_add:,.0f}원치 주식을 삼")
    with col2:
        final_monthly = sum_row['10년차']
        st.success(f"현재 전략 유지 시, **10년 후 월 배당금은 약 {final_monthly:,.0f}원**입니다.")
        st.caption("※ 주가 상승률이 높을수록 재투자 시 매수되는 주식 수는 줄어듭니다.")

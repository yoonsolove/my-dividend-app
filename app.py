import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz  # 시간대 처리를 위해 필요

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v8.1", layout="wide", page_icon="🤖")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])

# --- 사이드바: 종목 등록 ---
st.sidebar.title("🤖 종목 자동 분석 및 등록")
with st.sidebar.form("add_form"):
    ticker_input = st.text_input("티커 (예: SCHD, 441640.KS)", value="441640.KS").upper()
    count = st.number_input("현재 보유 수량 (주)", min_value=0, value=2080)
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    analyze_btn = st.form_submit_button("실시간 데이터 분석 및 추가")

if analyze_btn:
    try:
        with st.spinner('데이터를 분석 중입니다...'):
            stock = yf.Ticker(ticker_input)
            
            # 1. 현재 주가
            price_data = stock.history(period="1d")
            if price_data.empty:
                raise ValueError("주가 데이터를 찾을 수 없습니다.")
            price = price_data['Close'].iloc[-1]
            
            # 2. 배당금 분석 (에러 수정 포인트: 시간대 통일)
            div_history = stock.dividends
            if not div_history.empty:
                # 데이터의 시간대 확인 후 '현재 시간'에도 동일한 시간대 적용
                tz = div_history.index.tz
                now_with_tz = datetime.now(tz)
                
                # 최근 1년 배당금 합계
                last_year_divs = div_history[div_history.index > (now_with_tz - timedelta(days=365))]
                auto_dps = last_year_divs.sum()
                
                # 배당성장률 계산 (최근 3년)
                yearly_divs = div_history.resample('YE').sum()
                avg_growth = yearly_divs.pct_change().tail(3).mean() * 100 if len(yearly_divs) >= 2 else 0.5
            else:
                auto_dps = 0.0
                avg_growth = 0.5

            # 미배콜 예외 처리
            if category == "미배콜/고배당" and avg_growth > 5: avg_growth = 1.0
            if pd.isna(avg_growth): avg_growth = 0.5

            new_row = pd.DataFrame([[ticker_input, count, price, auto_dps, avg_growth, category]], 
                                   columns=st.session_state.portfolio.columns)
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
            st.sidebar.success(f"분석 완료: {ticker_input}")
            
    except Exception as e:
        st.sidebar.error(f"오류 발생: {e}")

# --- 사이드바: 환경 설정 ---
st.sidebar.markdown("---")
monthly_add = st.sidebar.number_input("매달 추가 투자액", min_value=0, value=1000000)
price_growth = st.sidebar.slider("연간 주가 상승률 예측 (%)", 0, 15, 3)

# --- 메인 화면 ---
st.title("📊 자동화된 월 배당 성장 시뮬레이션")

if st.session_state.portfolio.empty:
    st.warning("종목을 등록해주세요.")
else:
    # 1. 요약
    total_val = (st.session_state.portfolio['보유수량'] * st.session_state.portfolio['현재주가']).sum()
    st.metric("현재 포트폴리오 평가액", f"{total_val:,.0f}원")

    # 2. 시뮬레이션
    years = list(range(1, 11))
    forecast_rows = []
    for _, row in st.session_state.portfolio.iterrows():
        cur_shares, cur_price, cur_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        stock_forecast = {"종목명": row['종목명'], "적용성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            stock_forecast[f"{y}년차"] = int((cur_shares * cur_dps) / 12)
            cur_dps *= (1 + dgr)
            # 재투자/적립 로직
            net_div = (cur_shares * (cur_dps / (1+dgr))) * 0.846
            fresh_cash = net_div + (monthly_add * 12)
            cur_price *= (1 + pgr)
            cur_shares += (fresh_cash / cur_price)
        forecast_rows.append(stock_forecast)

    df_res = pd.DataFrame(forecast_rows)
    # 합계 계산
    sum_row = {"종목명": "📊 월 합계", "적용성장률": "-"}
    for y in years: sum_row[f"{y}년차"] = df_res[f"{y}년차"].sum()
    df_res = pd.concat([df_res, pd.DataFrame([sum_row])], ignore_index=True)

    st.dataframe(df_res.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🚀 10년 후 예상 월급: {sum_row['10년차']:,.0f}원")

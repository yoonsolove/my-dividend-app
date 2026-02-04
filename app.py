import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, date, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v8.0", layout="wide", page_icon="🤖")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])

# --- 사이드바: 종목 등록 (자동 계산 엔진 탑재) ---
st.sidebar.title("🤖 종목 자동 분석 및 등록")
with st.sidebar.form("add_form"):
    ticker_input = st.text_input("티커/종목코드 (예: SCHD, 441640.KS)", value="SCHD").upper()
    count = st.number_input("현재 보유 수량 (주)", min_value=0, value=2080)
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    
    st.markdown("---")
    st.caption("아래 버튼을 누르면 최근 데이터를 기반으로 자동 계산됩니다.")
    analyze_btn = st.form_submit_button("실시간 데이터 분석 및 추가")

if analyze_btn:
    try:
        with st.spinner(f'{ticker_input} 데이터를 분석 중...'):
            stock = yf.Ticker(ticker_input)
            
            # 1. 현재 주가 가져오기
            price = stock.history(period="1d")['Close'].iloc[-1]
            
            # 2. 최근 1년(365일) 배당금 합계 계산 (실제 지급액 기준)
            div_history = stock.dividends
            last_year_divs = div_history[div_history.index > (datetime.now() - timedelta(days=365))]
            auto_dps = last_year_divs.sum()
            
            # 3. 최근 3년 평균 배당성장률 계산
            yearly_divs = div_history.resample('YE').sum()
            if len(yearly_divs) >= 3:
                # 최근 3~5년 성장률 평균
                avg_growth = yearly_divs.pct_change().tail(3).mean() * 100
            else:
                avg_growth = 0.5 # 데이터 부족 시 기본값 (미배콜 등)
            
            # 미배콜/고배당 유형일 경우 성장률 보정 (과거 데이터가 튀는 경우 방지)
            if category == "미배콜/고배당" and avg_growth > 5:
                avg_growth = 1.0
            
            # 데이터프레임 저장
            new_row = pd.DataFrame([[ticker_input, count, price, auto_dps, avg_growth, category]], 
                                   columns=st.session_state.portfolio.columns)
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
            
            st.sidebar.success(f"분석 완료!\n- 주당배당금: {auto_dps:,.1f}\n- 평균성장률: {avg_growth:.1f}%")
    except Exception as e:
        st.sidebar.error(f"데이터를 가져오지 못했습니다: {e}\n(팁: 국내 ETF는 '종목코드.KS' 형식을 확인하세요)")

# --- 사이드바: 2. 환경 설정 ---
st.sidebar.markdown("---")
st.sidebar.title("⚙️ 투자 환경 설정")
monthly_add = st.sidebar.number_input("매달 추가 투자액 (원/달러)", min_value=0, value=1000000, step=100000)
price_growth = st.sidebar.slider("연간 주가 상승률 예측 (%)", 0, 15, 3)

# --- 메인 화면 ---
st.title("📊 자동화된 월 배당 성장 시뮬레이션")
st.info("데이터 출처: 실시간 야후 파이낸스 (최근 1년 배당금 및 3년 평균 성장률 반영)")

if st.session_state.portfolio.empty:
    st.warning("왼쪽 사이드바에서 종목을 등록해주세요. 자동으로 과거 평균치를 계산합니다.")
else:
    # 1. 현재 상태 요약
    total_val = (st.session_state.portfolio['보유수량'] * st.session_state.portfolio['현재주가']).sum()
    st.metric("현재 포트폴리오 평가액", f"{total_val:,.0f} (통화단위 무관)")

    st.divider()

    # 2. 복리 시뮬레이션 (수량 기반)
    years = list(range(1, 11))
    forecast_rows = []

    for _, row in st.session_state.portfolio.iterrows():
        cur_shares = float(row['보유수량'])
        cur_price = float(row['현재주가'])
        cur_dps = float(row['주당배당금'])
        dgr = row['배당성장률'] / 100
        pgr = price_growth / 100
        
        stock_forecast = {"종목명": row['종목명'], "적용성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            # 월 평균 배당금 기록
            monthly_income = (cur_shares * cur_dps) / 12
            stock_forecast[f"{y}년차"] = int(monthly_income)
            
            # 연말 업데이트 (다음 연도용)
            cur_dps *= (1 + dgr) # 배당 성장
            annual_div_net = (cur_shares * (cur_dps / (1 + dgr))) * 0.846 # 세후 배당
            fresh_cash = annual_div_net + (monthly_add * 12) # 적립액 추가
            
            cur_price *= (1 + pgr) # 주가 상승
            cur_shares += (fresh_cash / cur_price) # 수량 증가
            
        forecast_rows.append(stock_forecast)

    # 테이블 구성
    df_res = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 합계(세전)", "적용성장률": "-"}
    for y in years:
        sum_row[f"{y}년차"] = df_res[f"{y}년차"].sum()
    df_res = pd.concat([df_res, pd.DataFrame([sum_row])], ignore_index=True)

    st.write("### 📅 연도별 예상 '월평균' 수령액 (재투자+적립 반영)")
    st.dataframe(df_res.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)

    st.success(f"🚀 **10년 후 예상 월급:** {sum_row['10년차']:,.0f}원")

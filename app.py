import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v9.0", layout="wide", page_icon="⚖️")

# 세션 상태 초기화 (입력값 보관용)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])
if 'temp_data' not in st.session_state:
    st.session_state.temp_data = {"price": 0.0, "dps": 0.0, "growth": 0.0}

# --- 사이드바: 종목 분석 및 등록 ---
st.sidebar.title("🤖 1단계: 데이터 분석")
ticker_input = st.sidebar.text_input("티커 입력 (예: 402970.KS, SCHD)", value="402970.KS").upper()

if st.sidebar.button("실시간 데이터 불러오기"):
    try:
        with st.spinner('데이터 추출 중...'):
            stock = yf.Ticker(ticker_input)
            # 주가 추출
            p_data = stock.history(period="1d")
            st.session_state.temp_data['price'] = p_data['Close'].iloc[-1] if not p_data.empty else 0.0
            
            # 배당금 및 성장률 추출
            divs = stock.dividends
            if not divs.empty:
                tz = divs.index.tz
                now_tz = datetime.now(tz)
                st.session_state.temp_data['dps'] = divs[divs.index > (now_tz - timedelta(days=365))].sum()
                
                yearly = divs.resample('YE').sum()
                growth = yearly.pct_change().tail(3).mean() * 100 if len(yearly) >= 2 else 5.0
                st.session_state.temp_data['growth'] = max(growth, 0.0) # 마이너스 방지 기본값
            else:
                st.session_state.temp_data['dps'] = 0.0
                st.session_state.temp_data['growth'] = 5.0
            st.sidebar.success("데이터를 불러왔습니다. 아래에서 수정 후 등록하세요!")
    except Exception as e:
        st.sidebar.error(f"오류: {e}")

st.sidebar.markdown("---")
st.sidebar.title("✍️ 2단계: 수동 수정 및 등록")

# 불러온 데이터를 기본값으로 설정하되 사용자가 수정 가능하게 함
with st.sidebar.form("manual_edit_form"):
    count = st.number_input("보유 수량 (주)", value=2080)
    # 분석된 값이 있으면 그 값을, 없으면 0을 표시
    final_price = st.number_input("현재 주가", value=float(st.session_state.temp_data['price']), format="%.2f")
    final_dps = st.number_input("연간 주당 배당금 (수정 가능)", value=float(st.session_state.temp_data['dps']), format="%.2f")
    final_growth = st.number_input("배당 성장률 (%) (수정 가능)", value=float(st.session_state.temp_data['growth']), format="%.1f")
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    
    submit_btn = st.form_submit_button("포트폴리오에 최종 추가")

if submit_btn:
    new_data = pd.DataFrame([[ticker_input, count, final_price, final_dps, final_growth, category]], 
                            columns=st.session_state.portfolio.columns)
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_data]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
    st.success(f"{ticker_input} 등록 완료!")

# --- 메인 화면: 환경 설정 및 결과 ---
st.sidebar.markdown("---")
monthly_add = st.sidebar.number_input("매달 추가 투자금", value=1000000)
price_growth = st.sidebar.slider("연간 주가 상승률 (%)", 0, 15, 3)

st.title("📈 맞춤형 배당 성장 시뮬레이터")

if st.session_state.portfolio.empty:
    st.info("왼쪽에서 종목 티커를 입력하고 데이터를 분석한 뒤 등록해주세요.")
else:
    # 계산 로직 (수량 기반 복리)
    years = list(range(1, 11))
    forecast_rows = []
    
    for _, row in st.session_state.portfolio.iterrows():
        c_shares, c_price, c_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        row_forecast = {"종목명": row['종목명'], "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            row_forecast[f"{y}년차"] = int((c_shares * c_dps) / 12)
            # 복리 업데이트
            c_dps *= (1 + dgr)
            net_div = (c_shares * (c_dps / (1+dgr))) * 0.846
            c_price *= (1 + pgr)
            c_shares += (net_div + (monthly_add * 12 / len(st.session_state.portfolio))) / c_price
        forecast_rows.append(row_forecast)

    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 합계", "성장률": "-"}
    for y in years: sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    st.write("### 📅 연도별 예상 월 수령액")
    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🚀 10년 후 예상 월 배당금: {sum_row['10년차']:,.0f}원")

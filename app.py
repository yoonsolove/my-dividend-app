import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v15.7", layout="wide", page_icon="⚖️")

# --- 세션 상태 초기화 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기"])

if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"ticker": "", "ticker_original": None, "count": 100, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당"}

# --- [메인 상단] ---
st.title("📈 배당 마스터 v15.7 (정밀 시뮬레이션)")

col_sel, col_del = st.columns([3, 1])
with col_sel:
    stock_list = ["새 종목 추가"] + list(st.session_state.portfolio["종목명"])
    selected_stock = st.selectbox("📝 관리할 종목 선택:", stock_list, key="stock_selector")
    
    if selected_stock != "새 종목 추가":
        t = st.session_state.portfolio[st.session_state.portfolio["종목명"] == selected_stock].iloc[0]
        if st.session_state.edit_data.get("ticker_original") != selected_stock:
            st.session_state.edit_data = {
                "ticker": t["종목명"], "ticker_original": selected_stock,
                "count": int(t["보유수량"]), "price": float(t["현재주가"]),
                "dps": float(t["주당배당금"]), "growth": float(t["배당성장률"]),
                "cat": t["유형"], "cycle": t.get("지급주기", "월배당")
            }
            st.rerun()
    elif st.session_state.edit_data.get("ticker_original") is not None:
        st.session_state.edit_data = {"ticker": "", "ticker_original": None, "count": 100, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당"}
        st.rerun()

with col_del:
    st.write(" ")
    st.write(" ")
    if selected_stock != "새 종목 추가" and st.button("❌ 삭제", use_container_width=True):
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
        st.rerun()

# --- [사이드바 설정] ---
st.sidebar.title("🤖 데이터 설정")
ticker_input = st.sidebar.text_input("티커 입력", value=st.session_state.edit_data.get("ticker", "")).upper()

if st.sidebar.button("🔍 데이터 불러오기"):
    try:
        stock = yf.Ticker(ticker_input)
        p_data = stock.history(period="1d")
        st.session_state.edit_data['price'] = p_data['Close'].iloc[-1] if not p_data.empty else 0.0
        divs = stock.dividends
        if not divs.empty:
            st.session_state.edit_data['dps'] = divs[divs.index > (datetime.now(divs.index.tz) - timedelta(days=365))].sum()
        st.session_state.edit_data['ticker'] = ticker_input
        st.rerun()
    except: st.sidebar.error("데이터 로드 실패")

with st.sidebar.form("edit_form"):
    f_count = st.number_input("보유 수량", value=int(st.session_state.edit_data.get("count", 100)))
    f_price = st.number_input("현재 주가", value=float(st.session_state.edit_data.get("price", 0.0)))
    f_cycle = st.selectbox("지급 주기", ["월배당", "분기배당", "연배당"], index=["월배당", "분기배당", "연배당"].index(st.session_state.edit_data.get("cycle", "월배당")))
    divisor = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    f_dps_input = st.number_input(f"{f_cycle} 1회 배당금", value=float(st.session_state.edit_data.get("dps", 0.0)/divisor))
    f_growth = st.number_input("배당 성장률 (%)", value=float(st.session_state.edit_data.get("growth", 5.0)))
    f_cat = st.selectbox("유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    save_btn = st.form_submit_button("💾 저장/수정")

if save_btn:
    multiplier = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    new_data = [ticker_input, f_count, f_price, f_dps_input * multiplier, f_growth, f_cat, f_cycle]
    if selected_stock != "새 종목 추가":
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock]
    new_row = pd.DataFrame([new_data], columns=st.session_state.portfolio.columns)
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).reset_index(drop=True)
    st.rerun()

# --- [시뮬레이션 로직 보정] ---
if not st.session_state.portfolio.empty:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    with c1: target_years = st.slider("📅 분석 기간 (년)", 1, 30, 10)
    with c2: monthly_add = st.number_input("💵 매달 총 추가 투자금", value=500000)
    with c3: price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 3)
    with c4: 
        is_reinvest = st.checkbox("🔄 배당 재투자", value=True)
        is_tax = st.checkbox("💸 세금 공제(15.4%)", value=True)

    years = list(range(1, target_years + 1))
    forecast_rows = []
    
    # 각 종목별로 시뮬레이션 수행
    for _, row in st.session_state.portfolio.iterrows():
        # 초기값 설정
        shares = float(row['보유수량'])
        price = float(row['현재주가'])
        annual_dps = float(row['주당배당금'])
        d_growth = row['배당성장률'] / 100
        p_growth = price_growth / 100
        tax = 0.846 if is_tax else 1.0
        
        # 종목별 할당 투자금 (매달)
        item_monthly_fund = monthly_add / len(st.session_state.portfolio)
        
        stock_forecast = {"종목명": row['종목명'], "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            # 1. 현재 주식 수 기준 연간 배당금 (세전 월평균으로 기록)
            monthly_income = (shares * annual_dps) / 12
            stock_forecast[f"{y}년차"] = int(monthly_income)
            
            # 2. 연말 정산 (1년 단위 시뮬레이션 업데이트)
            # 배당금 재투자 액수 계산
            reinvest_amount = (shares * annual_dps * tax) if is_reinvest else 0
            # 1년간의 총 투자금 (재투자 + 매달 적립금)
            total_annual_investment = reinvest_amount + (item_monthly_fund * 12)
            
            # 주가와 주당 배당금 업데이트 (연초 대비 기말 기준)
            price *= (1 + p_growth)
            annual_dps *= (1 + d_growth)
            
            # 추가 매수 주식 수 (평균 주가 적용 - 간략화하여 기말 주가 적용)
            new_shares = total_annual_investment / max(price, 1.0)
            shares += new_shares
            
        forecast_rows.append(stock_forecast)

    # 결과 데이터프레임 생성 및 합계 계산
    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 합계", "성장률": "-"}
    for y in years:
        sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    st.subheader(f"🗓️ {target_years}개년 예상 월 평균 배송금 (세전)")
    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🎯 **{target_years}년 후 총 예상 월 수령액은 {sum_row[f'{target_years}년차']:,.0f}원입니다.**")

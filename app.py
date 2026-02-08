import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v15.9", layout="wide", page_icon="⚖️")

# --- [보정 로직] 세션 상태 초기화 및 규격 맞춤 ---
# 우리가 사용할 표준 컬럼 리스트
STANDARD_COLUMNS = ["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기", "재투자여부"]

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=STANDARD_COLUMNS)
else:
    # ⚠️ 중요: 기존 데이터에 '재투자여부' 칸이 없으면 강제로 만들어줌 (ValueError 방지)
    for col in STANDARD_COLUMNS:
        if col not in st.session_state.portfolio.columns:
            st.session_state.portfolio[col] = True if col == "재투자여부" else ""

if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {
        "ticker": "", "ticker_original": None, "count": 100, "price": 0.0, 
        "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당", "is_reinvest": True
    }

# --- [메인 상단] ---
st.title("📈 배당 마스터 v15.9 (오류 복구 및 규격화)")

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
                "cat": t["유형"], "cycle": t.get("지급주기", "월배당"),
                "is_reinvest": t.get("재투자여부", True)
            }
            st.rerun()
    elif st.session_state.edit_data.get("ticker_original") is not None:
        st.session_state.edit_data = {
            "ticker": "", "ticker_original": None, "count": 100, "price": 0.0, 
            "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당", "is_reinvest": True
        }
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
    f_reinvest = st.checkbox("🔄 이 종목 배당금 재투자", value=st.session_state.edit_data.get("is_reinvest", True))
    f_cat = st.selectbox("유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    save_btn = st.form_submit_button("💾 저장/수정")

if save_btn:
    multiplier = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    # 💡 컬럼 순서에 맞춰서 정확히 매칭
    new_data = {
        "종목명": ticker_input, 
        "보유수량": f_count, 
        "현재주가": f_price, 
        "주당배당금": f_dps_input * multiplier, 
        "배당성장률": f_growth, 
        "유형": f_cat, 
        "지급주기": f_cycle, 
        "재투자여부": f_reinvest
    }
    
    if selected_stock != "새 종목 추가":
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock]
    
    new_row = pd.DataFrame([new_data])
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
    st.rerun()

# --- [시뮬레이션 로직] ---
if not st.session_state.portfolio.empty:
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    with c1: target_years = st.slider("📅 분석 기간 (년)", 1, 30, 10)
    with c2: monthly_add = st.number_input("💵 매달 총 추가 투자금", value=500000)
    with c3: price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 3)
    with c4: is_tax = st.checkbox("💸 세금 공제(15.4%)", value=True)

    years = list(range(1, target_years + 1))
    forecast_rows = []
    
    for _, row in st.session_state.portfolio.iterrows():
        shares = float(row['보유수량'])
        price = float(row['현재주가'])
        annual_dps = float(row['주당배당금'])
        d_growth = row['배당성장률'] / 100
        p_growth = price_growth / 100
        tax = 0.846 if is_tax else 1.0
        
        stock_reinvest = row.get('재투자여부', True)
        item_monthly_fund = monthly_add / len(st.session_state.portfolio)
        
        stock_forecast = {"종목명": row['종목명'], "재투자": "O" if stock_reinvest else "X"}
        
        for y in years:
            stock_forecast[f"{y}년차"] = int((shares * annual_dps) / 12)
            reinvest_fund = (shares * annual_dps * tax) if stock_reinvest else 0
            total_fund = reinvest_fund + (item_monthly_fund * 12)
            price *= (1 + p_growth)
            annual_dps *= (1 + d_growth)
            shares += (total_fund / max(price, 1.0))
            
        forecast_rows.append(stock_forecast)

    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 합계", "재투자": "-"}
    for y in years: sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    st.subheader(f"🗓️ {target_years}개년 예상 월 평균 배당금 (세전)")
    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
else:
    st.info("💡 종목을 추가해 주세요.")

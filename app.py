import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v15.6", layout="wide", page_icon="📈")

# --- 세션 상태 초기화 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기"])

if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"ticker": "", "ticker_original": None, "count": 100, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당"}

# --- [메인 상단 관리 로직] ---
st.title("📈 배당 마스터 v15.6 (오버플로 방지 버전)")

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
    if selected_stock != "새 종목 추가" and st.button("❌ 선택 종목 삭제", use_container_width=True):
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
        st.rerun()

# --- [사이드바 입력] ---
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

# --- [결과 출력 영역] ---
if not st.session_state.portfolio.empty:
    st.divider()
    set_c1, set_c2, set_c3, set_c4 = st.columns(4)
    with set_c1: target_years = st.slider("📅 분석 기간 (년)", 1, 30, 10)
    with set_c2: monthly_add = st.number_input("💵 매달 추가 투자금", value=1000000)
    with set_c3: price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 3)
    with set_c4: 
        is_reinvest = st.checkbox("🔄 재투자", value=True)
        is_tax = st.checkbox("💸 세금(15.4%)", value=True)

    years = list(range(1, target_years + 1))
    forecast_rows = []
    MAX_VAL = 1e15 # 💡 숫자가 너무 커지는 것을 방지 (천조 단위 제한)

    for _, row in st.session_state.portfolio.iterrows():
        c_shares, c_price, c_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        row_f = {"종목명": row['종목명'], "주기": row.get('지급주기', '월배당'), "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            monthly_div = min((c_shares * c_dps) / 12, MAX_VAL) # 💡 오버플로 방지
            row_f[f"{y}년차"] = monthly_div
            c_dps = min(c_dps * (1 + dgr), MAX_VAL)
            if is_reinvest:
                net_div = (c_shares * (c_dps / (1+dgr))) * (0.846 if is_tax else 1.0)
                invest_fund = net_div + (monthly_add * 12 / len(st.session_state.portfolio))
            else:
                invest_fund = (monthly_add * 12 / len(st.session_state.portfolio))
            c_price = min(c_price * (1 + pgr), MAX_VAL)
            c_shares = min(c_shares + (invest_fund / max(c_price, 1.0)), 1e12) # 주식수도 1조주 제한
            
        forecast_rows.append(row_f)

    res_df = pd.DataFrame(forecast_rows)
    # 합계 계산 시에도 숫자 타입 확인
    sum_row = {"종목명": "📊 월 합계", "주기": "-", "성장률": "-"}
    for y in years:
        sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    # 💡 데이터프레임 표시 전 최종 타입 변환 (안전하게 float로 통일)
    for y in years:
        res_df[f"{y}년차"] = res_df[f"{y}년차"].apply(lambda x: float(x) if x < MAX_VAL else MAX_VAL)

    st.write(f"### 🗓️ {target_years}개년 예상 월 평균 배당금")
    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🎯 **{target_years}년 후 월 수령액: {sum_row[f'{target_years}년차']:,.0f}원**")
else:
    st.info("💡 종목을 추가해 주세요.")

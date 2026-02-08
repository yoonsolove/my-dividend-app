import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v17.0", layout="wide", page_icon="⚖️")

# --- 세션 상태 초기화 ---
STANDARD_COLUMNS = ["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기", "재투자여부", "월적립금"]

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=STANDARD_COLUMNS)

if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {
        "ticker": "", "ticker_original": None, "count": 100, "price": 0.0, 
        "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당", "is_reinvest": True, "monthly_pay": 0
    }

# --- [메인 상단] ---
st.title("📈 배당 마스터 v17.0 (배당금 몰아주기 전략)")
st.info("💡 전략: 441640의 배당금과 매달 50만원을 전부 402970 매수에 집중 투자합니다.")

col_sel, col_del = st.columns([3, 1])
with col_sel:
    stock_list = ["새 종목 추가"] + list(st.session_state.portfolio["종목명"])
    selected_stock = st.selectbox("📝 종목 관리:", stock_list, key="stock_selector")
    
    if selected_stock != "새 종목 추가":
        t = st.session_state.portfolio[st.session_state.portfolio["종목명"] == selected_stock].iloc[0]
        if st.session_state.edit_data.get("ticker_original") != selected_stock:
            st.session_state.edit_data = {
                "ticker": t["종목명"], "ticker_original": selected_stock,
                "count": int(t["보유수량"]), "price": float(t["현재주가"]),
                "dps": float(t["주당배당금"]), "growth": float(t["배당성장률"]),
                "cat": t["유형"], "cycle": t.get("지급주기", "월배당"),
                "is_reinvest": t.get("재투자여부", True),
                "monthly_pay": int(t.get("월적립금", 0))
            }
            st.rerun()

with col_del:
    st.write(" ")
    st.write(" ")
    if selected_stock != "새 종목 추가" and st.button("❌ 삭제", use_container_width=True):
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
        st.rerun()

# --- [사이드바 설정] ---
st.sidebar.title("🤖 종목 설정")
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
    f_cycle = st.selectbox("지급 주기", ["월배당", "분기배당", "연배당"], index=0)
    multiplier = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    f_dps_input = st.number_input(f"{f_cycle} 1회 배당금", value=float(st.session_state.edit_data.get("dps", 0.0)/multiplier))
    f_growth = st.number_input("배당 성장률 (%)", value=float(st.session_state.edit_data.get("growth", 5.0)))
    f_monthly_pay = st.number_input("💵 매달 추가 적립금", value=int(st.session_state.edit_data.get("monthly_pay", 0)))
    f_reinvest = st.checkbox("🔄 배당 재투자 여부", value=st.session_state.edit_data.get("is_reinvest", True))
    f_cat = st.selectbox("유형", ["배당성장주", "미배콜", "일반"])
    save_btn = st.form_submit_button("💾 저장/수정")

if save_btn:
    new_data = {
        "종목명": ticker_input, "보유수량": f_count, "현재주가": f_price, 
        "주당배당금": f_dps_input * multiplier, "배당성장률": f_growth, 
        "유형": f_cat, "지급주기": f_cycle, "재투자여부": f_reinvest, "월적립금": f_monthly_pay
    }
    if selected_stock != "새 종목 추가":
        st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock]
    new_row = pd.DataFrame([new_data])
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
    st.rerun()

# --- [전략적 시뮬레이션 로직] ---
if not st.session_state.portfolio.empty:
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: target_years = st.slider("📅 분석 기간 (년)", 1, 30, 15)
    with c2: price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 5)
    with c3: is_tax = st.checkbox("💸 세금 공제(15.4%) 적용", value=True)

    years = list(range(1, target_years + 1))
    
    # 시뮬레이션용 데이터 복사
    sim_data = st.session_state.portfolio.copy()
    for col in ['보유수량', '현재주가', '주당배당금']:
        sim_data[col] = sim_data[col].astype(float)
        
    history = []
    tax_rate = 0.846 if is_tax else 1.0

    for y in years:
        total_monthly_div = 0
        yearly_cash_flow = 0
        
        # 1. 먼저 각 종목에서 발생하는 배당금(현금흐름) 계산
        stock_incomes = {}
        for idx, row in sim_data.iterrows():
            monthly_div = (row['보유수량'] * row['주당배당금']) / 12
            total_monthly_div += monthly_div
            stock_incomes[row['종목명']] = int(monthly_div)
            
            # 재투자용 현금 모으기 (재투자 설정된 종목의 배당금 + 모든 종목의 월 적립금)
            yearly_cash_flow += (row['보유수량'] * row['주당배당금'] * tax_rate) if row['재투자여부'] else 0
            yearly_cash_flow += (row['월적립금'] * 12)

        # 2. 모인 현금(yearly_cash_flow)을 '재투자'가 체크된 종목에 몰아주기
        # 만약 여러 종목이 재투자라면 나눠서 들어가겠지만, 윤재님 전략에선 402970만 체크하면 됩니다.
        reinvest_targets = sim_data[sim_data['재투자여부'] == True]
        if not reinvest_targets.empty:
            fund_per_target = yearly_cash_flow / len(reinvest_targets)
            for idx in reinvest_targets.index:
                # 기말 주가로 매수한다고 가정
                future_price = sim_data.at[idx, '현재주가'] * (1 + (price_growth/100))
                sim_data.at[idx, '보유수량'] += (fund_per_target / max(future_price, 1.0))

        # 3. 주가 및 배당금 성장 반영
        for idx in sim_data.index:
            sim_data.at[idx, '현재주가'] *= (1 + (price_growth/100))
            sim_data.at[idx, '주당배당금'] *= (1 + (sim_data.at[idx, '배당성장률']/100))

        # 기록
        history_row = {"연도": f"{y}년차"}
        history_row.update(stock_incomes)
        history_row["합계"] = int(total_monthly_div)
        history.append(history_row)

    res_df = pd.DataFrame(history)
    st.subheader(f"📊 윤재님 맞춤 전략 시뮬레이션 ({target_years}년)")
    st.dataframe(res_df.set_index("연도").style.format("{:,}원"), use_container_width=True)
    
    st.success(f"🎯 **{target_years}년 후 예상 월 수령액: {history[-1]['합계']:,}원**")
    st.caption("※ 441640은 재투자 체크 해제 / 402970은 재투자 체크 및 월적립금 50만원 설정 시 정확한 결과가 나옵니다.")

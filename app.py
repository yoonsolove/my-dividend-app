import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v11.0", layout="wide", page_icon="🗑️")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])
if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"ticker": "", "count": 100, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반"}

# --- [메인 화면 상단] 관리 제어판 ---
st.title("📈 배당 마스터 v11.0 (종목 삭제/관리 기능)")

col_header1, col_header2 = st.columns([3, 1])

with col_header1:
    if not st.session_state.portfolio.empty:
        selected_stock = st.selectbox("📝 관리할 종목 선택 (수정은 왼쪽, 삭제는 오른쪽 버튼):", 
                                     ["새 종목 추가"] + list(st.session_state.portfolio["종목명"]))
        
        # 선택 시 데이터 동기화
        if selected_stock != "새 종목 추가":
            target = st.session_state.portfolio[st.session_state.portfolio["종목명"] == selected_stock].iloc[0]
            st.session_state.edit_data = {
                "ticker": target["종목명"], "count": int(target["보유수량"]),
                "price": float(target["현재주가"]), "dps": float(target["주당배당금"]),
                "growth": float(target["배당성장률"]), "cat": target["유형"]
            }
        else:
            st.session_state.edit_data = {"ticker": "", "count": 100, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반"}
    else:
        selected_stock = "새 종목 추가"
        st.info("포트폴리오가 비어 있습니다. 왼쪽에서 종목을 추가하세요.")

with col_header2:
    st.write(" ") # 간격 조절
    st.write(" ")
    # 🔥 [삭제 기능] 선택된 종목 삭제 버튼
    if selected_stock != "새 종목 추가":
        if st.button("❌ 선택 종목 삭제", use_container_width=True):
            st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
            st.toast(f"{selected_stock} 종목이 삭제되었습니다.")
            st.rerun()

# --- [사이드바] 등록 및 수정 로직 ---
st.sidebar.title("🤖 1단계: 데이터 분석")
ticker_input = st.sidebar.text_input("티커 입력", value=st.session_state.edit_data["ticker"]).upper()

if st.sidebar.button("실시간 데이터 불러오기"):
    try:
        with st.spinner('데이터 분석 중...'):
            stock = yf.Ticker(ticker_input)
            p_data = stock.history(period="1d")
            st.session_state.edit_data['price'] = p_data['Close'].iloc[-1] if not p_data.empty else 0.0
            divs = stock.dividends
            if not divs.empty:
                tz = divs.index.tz
                st.session_state.edit_data['dps'] = divs[divs.index > (datetime.now(tz) - timedelta(days=365))].sum()
                yearly = divs.resample('YE').sum()
                st.session_state.edit_data['growth'] = max(yearly.pct_change().tail(3).mean() * 100, 0.0) if len(yearly) >= 2 else 5.0
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"오류: {e}")

st.sidebar.markdown("---")
st.sidebar.title("✍️ 2단계: 저장 및 수정")
with st.sidebar.form("edit_form"):
    f_count = st.number_input("보유 수량 (주)", value=st.session_state.edit_data["count"])
    f_price = st.number_input("현재 주가", value=st.session_state.edit_data["price"], format="%.2f")
    f_dps = st.number_input("연간 주당 배당금", value=st.session_state.edit_data["dps"], format="%.2f")
    f_growth = st.number_input("배당 성장률 (%)", value=st.session_state.edit_data["growth"], format="%.1f")
    f_cat = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"], 
                        index=["배당성장주", "미배콜/고배당", "리츠", "일반"].index(st.session_state.edit_data["cat"]))
    save_btn = st.form_submit_button("💾 포트폴리오에 저장/수정")

if save_btn:
    if f_price <= 0:
        st.sidebar.error("⚠️ 주가는 0보다 커야 합니다.")
    else:
        new_row = pd.DataFrame([[ticker_input, f_count, f_price, f_dps, f_growth, f_cat]], columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
        st.rerun()

# --- 시뮬레이션 환경 설정 ---
st.sidebar.markdown("---")
target_years = st.sidebar.slider("분석 기간 (년)", 1, 30, 10)
monthly_add = st.sidebar.number_input("매달 추가 투자금", value=1000000)
price_growth = st.sidebar.slider("연간 주가 상승률 (%)", 0, 15, 3)

# --- 결과 출력 ---
if not st.session_state.portfolio.empty:
    years = list(range(1, target_years + 1))
    forecast_rows = []
    
    for _, row in st.session_state.portfolio.iterrows():
        c_shares, c_price, c_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        row_f = {"종목명": row['종목명'], "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            row_f[f"{y}년차"] = int((c_shares * c_dps) / 12)
            c_dps *= (1 + dgr)
            # 재투자 로직 (주가 0 방지)
            net_div = (c_shares * (c_dps / (1+dgr))) * 0.846
            c_price *= (1 + pgr)
            c_shares += (net_div + (monthly_add * 12 / len(st.session_state.portfolio))) / max(c_price, 1.0)
            
        forecast_rows.append(row_f)

    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 합계", "성장률": "-"}
    for y in years: sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🚀 {target_years}년 후 예상 월급: **{sum_row[f'{target_years}년차']:,.0f}원**")

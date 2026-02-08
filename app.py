import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v15.2", layout="wide", page_icon="📈")

# --- 세션 상태 초기화 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기"])

if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"ticker": "", "count": 2080, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당"}

# --- [사이드바] 1단계: 데이터 분석 ---
st.sidebar.title("🤖 1단계: 데이터 분석")
ticker_input = st.sidebar.text_input("티커 입력", value=st.session_state.edit_data.get("ticker", "")).upper()

if st.sidebar.button("🔍 실시간 데이터 불러오기"):
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
            st.session_state.edit_data['ticker'] = ticker_input
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"로드 실패: {e}")

st.sidebar.markdown("---")
st.sidebar.title("✍️ 2단계: 저장 및 수정")
with st.sidebar.form("edit_form"):
    f_count = st.number_input("보유 수량 (주)", value=int(st.session_state.edit_data.get("count", 100)))
    f_price = st.number_input("현재 주가", value=float(st.session_state.edit_data.get("price", 0.0)), format="%.2f")
    
    cycle_list = ["월배당", "분기배당", "연배당"]
    curr_cycle = st.session_state.edit_data.get("cycle", "월배당")
    f_cycle = st.selectbox("지급 주기", cycle_list, index=cycle_list.index(curr_cycle) if curr_cycle in cycle_list else 0)
    
    divisor = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    f_dps_input = st.number_input(f"{f_cycle} 1회당 배당금", value=float(st.session_state.edit_data.get("dps", 0.0) / divisor), format="%.2f")
    f_growth = st.number_input("배당 성장률 (%)", value=float(st.session_state.edit_data.get("growth", 5.0)), format="%.1f")
    
    cat_list = ["배당성장주", "미배콜/고배당", "리츠", "일반"]
    curr_cat = st.session_state.edit_data.get("cat", "일반")
    f_cat = st.selectbox("종목 유형", cat_list, index=cat_list.index(curr_cat) if curr_cat in cat_list else 3)
    save_btn = st.form_submit_button("💾 포트폴리오에 저장/수정")

if save_btn:
    multiplier = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    new_row = pd.DataFrame([[ticker_input, f_count, f_price, f_dps_input * multiplier, f_growth, f_cat, f_cycle]], 
                            columns=st.session_state.portfolio.columns)
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
    st.rerun()

# --- [사이드바 하단: 백업] ---
st.sidebar.markdown("---")
if not st.session_state.portfolio.empty:
    csv = st.session_state.portfolio.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(label="📥 포트폴리오 다운로드", data=csv, file_name="my_portfolio.csv", mime="text/csv", use_container_width=True)

uploaded_file = st.sidebar.file_uploader("📂 파일 불러오기", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if "지급주기" not in df.columns: df["지급주기"] = "월배당"
    st.session_state.portfolio = df
    st.rerun()

# --- [메인 화면] ---
st.title("📈 배당 마스터 v15.2 (시뮬레이션 복구 완료)")

if not st.session_state.portfolio.empty:
    # 종목 선택 및 삭제
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        selected_stock = st.selectbox("📝 수정할 종목 선택:", ["새 종목 추가"] + list(st.session_state.portfolio["종목명"]))
        if selected_stock != "새 종목 추가":
            t = st.session_state.portfolio[st.session_state.portfolio["종목명"] == selected_stock].iloc[0]
            st.session_state.edit_data = {"ticker": t["종목명"], "count": t["보유수량"], "price": t["현재주가"], "dps": t["주당배당금"], "growth": t["배당성장률"], "cat": t["유형"], "cycle": t.get("지급주기", "월배당")}
    with col_del:
        st.write(" ")
        st.write(" ")
        if selected_stock != "새 종목 추가" and st.button("❌ 선택 종목 삭제"):
            st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
            st.rerun()

    # 🔥 [복구 및 강화된 설정 영역]
    st.divider()
    st.subheader("⚙️ 시뮬레이션 상세 설정")
    set_c1, set_c2, set_c3, set_c4 = st.columns(4)
    with set_c1:
        target_years = st.slider("📅 분석 기간 (년)", 1, 30, 10)
    with set_c2:
        monthly_add = st.number_input("💵 매달 추가 투자금", value=1000000, step=100000)
    with set_c3:
        price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 3)
    with set_c4:
        is_reinvest = st.checkbox("🔄 배당금 재투자", value=True)
        is_tax = st.checkbox("💸 세금 공제 (15.4%)", value=True)

    # 시뮬레이션 계산
    years = list(range(1, target_years + 1))
    forecast_rows = []
    tax_rate = 0.846 if is_tax else 1.0
    
    for _, row in st.session_state.portfolio.iterrows():
        c_shares, c_price, c_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        row_f = {"종목명": row['종목명'], "주기": row.get('지급주기', '월배당'), "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            row_f[f"{y}년차"] = int((c_shares * c_dps) / 12)
            c_dps *= (1 + dgr)
            
            # 재투자 및 추가 매수 로직
            if is_reinvest:
                net_div = (c_shares * (c_dps / (1+dgr))) * tax_rate
                invest_fund = net_div + (monthly_add * 12 / len(st.session_state.portfolio))
            else:
                invest_fund = (monthly_add * 12 / len(st.session_state.portfolio))
            
            c_price *= (1 + pgr)
            c_shares += (invest_fund / max(c_price, 1.0))
            
        forecast_rows.append(row_f)

    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 배당 합계", "주기": "-", "성장률": "-"}
    for y in years: sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    st.write(f"### 🗓️ {target_years}개년 예상 월 평균 배당금 (세전)")
    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🎯 **{target_years}년 후 예상 월 수령액: {sum_row[f'{target_years}년차']:,.0f}원**")
else:
    st.info("👈 왼쪽 사이드바에서 종목을 추가하여 시뮬레이션을 시작하세요!")

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v15.1", layout="wide", page_icon="🛡️")

# --- 세션 상태 초기화 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기"])

# edit_data 초기화 (안전하게 기본값 설정)
if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {
        "ticker": "", "count": 100, "price": 0.0, 
        "dps": 0.0, "growth": 5.0, "cat": "일반", "cycle": "월배당"
    }

# --- [사이드바] 데이터 분석 ---
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
                now_tz = datetime.now(tz)
                st.session_state.edit_data['dps'] = divs[divs.index > (now_tz - timedelta(days=365))].sum()
                yearly = divs.resample('YE').sum()
                st.session_state.edit_data['growth'] = max(yearly.pct_change().tail(3).mean() * 100, 0.0) if len(yearly) >= 2 else 5.0
            
            st.session_state.edit_data['ticker'] = ticker_input
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"데이터 로드 실패: {e}")

st.sidebar.markdown("---")
st.sidebar.title("✍️ 2단계: 저장 및 수정")

# --- 에러 방지 핵심 로직: .get()을 사용하여 데이터가 없으면 기본값 적용 ---
with st.sidebar.form("edit_form"):
    f_count = st.number_input("보유 수량 (주)", value=int(st.session_state.edit_data.get("count", 100)))
    f_price = st.number_input("현재 주가", value=float(st.session_state.edit_data.get("price", 0.0)), format="%.2f")
    
    # 주기 정보가 없을 경우 '월배당'을 기본값으로 사용
    current_cycle = st.session_state.edit_data.get("cycle", "월배당")
    cycle_list = ["월배당", "분기배당", "연배당"]
    default_cycle_idx = cycle_list.index(current_cycle) if current_cycle in cycle_list else 0
    
    f_cycle = st.selectbox("지급 주기", cycle_list, index=default_cycle_idx)
    
    # 주기별 1회당 배당금 표시 (연간 배당금을 주기에 맞춰 나눔)
    divisor = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
    f_dps_input = st.number_input(f"{f_cycle} 1회당 배당금", 
                                 value=float(st.session_state.edit_data.get("dps", 0.0) / divisor), 
                                 format="%.2f")
    
    f_growth = st.number_input("배당 성장률 (%)", value=float(st.session_state.edit_data.get("growth", 5.0)), format="%.1f")
    
    current_cat = st.session_state.edit_data.get("cat", "일반")
    cat_list = ["배당성장주", "미배콜/고배당", "리츠", "일반"]
    default_cat_idx = cat_list.index(current_cat) if current_cat in cat_list else 3
    
    f_cat = st.selectbox("종목 유형", cat_list, index=default_cat_idx)
    
    save_btn = st.form_submit_button("💾 포트폴리오에 저장/수정")

# 연환산 배당금 계산
multiplier = 12 if f_cycle == "월배당" else 4 if f_cycle == "분기배당" else 1
final_annual_dps = f_dps_input * multiplier

if save_btn:
    if f_price <= 0:
        st.sidebar.error("⚠️ 주가는 0보다 커야 합니다.")
    else:
        new_row = pd.DataFrame([[ticker_input, f_count, f_price, final_annual_dps, f_growth, f_cat, f_cycle]], 
                                columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형", "지급주기"])
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
        st.rerun()

# --- [사이드바 하단: 저장/불러오기] ---
st.sidebar.markdown("---")
if not st.session_state.portfolio.empty:
    csv = st.session_state.portfolio.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(label="📥 포트폴리오 다운로드", data=csv, file_name="dividend_v15_1.csv", mime="text/csv", use_container_width=True)

uploaded_file = st.sidebar.file_uploader("📂 파일 불러오기", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # 구버전 파일(지급주기 컬럼 없음) 대응
    if "지급주기" not in df.columns:
        df["지급주기"] = "월배당" 
    st.session_state.portfolio = df
    st.rerun()

# --- [메인 화면] ---
st.title("📈 배당 마스터 v15.1 (시스템 안정화)")

if not st.session_state.portfolio.empty:
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        selected_stock = st.selectbox("📝 수정할 종목 선택:", ["새 종목 추가"] + list(st.session_state.portfolio["종목명"]))
        if selected_stock != "새 종목 추가":
            target = st.session_state.portfolio[st.session_state.portfolio["종목명"] == selected_stock].iloc[0]
            # 안전하게 데이터 로드
            st.session_state.edit_data = {
                "ticker": target["종목명"], "count": target["보유수량"], "price": target["현재주가"], 
                "dps": target["주당배당금"], "growth": target["배당성장률"], 
                "cat": target["유형"], "cycle": target.get("지급주기", "월배당")
            }
    with col_del:
        st.write(" ")
        st.write(" ")
        if selected_stock != "새 종목 추가" and st.button("❌ 선택 종목 삭제"):
            st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
            st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: target_years = st.slider("📅 분석 기간 (년)", 1, 30, 10)
    with c2: monthly_add = st.number_input("💵 매달 추가 투자금", value=1000000)
    with c3: price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 3)

    # 시뮬레이션 계산
    years = list(range(1, target_years + 1))
    forecast_rows = []
    
    for _, row in st.session_state.portfolio.iterrows():
        c_shares, c_price, c_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        row_f = {"종목명": row['종목명'], "주기": row.get('지급주기', '월배당'), "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            row_f[f"{y}년차"] = int((c_shares * c_dps) / 12)
            c_dps *= (1 + dgr)
            net_div = (c_shares * (c_dps / (1+dgr))) * 0.846
            c_price *= (1 + pgr)
            c_shares += (net_div + (monthly_add * 12 / len(st.session_state.portfolio))) / max(c_price, 1.0)
        forecast_rows.append(row_f)

    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 배당 합계", "주기": "-", "성장률": "-"}
    for y in years: sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    st.success(f"🎯 **{target_years}년 후 예상 월 평균 수령액은 {sum_row[f'{target_years}년차']:,.0f}원 입니다.**")
else:
    st.info("👈 왼쪽에서 종목을 추가해 주세요.")

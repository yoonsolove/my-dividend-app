import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import io

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v14.0", layout="wide", page_icon="💰")

# --- 세션 상태 초기화 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "보유수량", "현재주가", "주당배당금", "배당성장률", "유형"])

if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"ticker": "", "count": 100, "price": 0.0, "dps": 0.0, "growth": 5.0, "cat": "일반"}

# --- [사이드바] 데이터 분석 및 설정 ---
st.sidebar.title("🤖 1단계: 데이터 분석")
ticker_input = st.sidebar.text_input("티커 입력 (예: 402970.KS, SCHD)", value=st.session_state.edit_data["ticker"]).upper()

if st.sidebar.button("🔍 실시간 데이터 불러오기"):
    try:
        with st.spinner('데이터 분석 중...'):
            stock = yf.Ticker(ticker_input)
            # 주가 데이터
            p_data = stock.history(period="1d")
            st.session_state.edit_data['price'] = p_data['Close'].iloc[-1] if not p_data.empty else 0.0
            
            # 배당 데이터
            divs = stock.dividends
            if not divs.empty:
                tz = divs.index.tz
                now_tz = datetime.now(tz)
                # 최근 1년 배당금 합계
                st.session_state.edit_data['dps'] = divs[divs.index > (now_tz - timedelta(days=365))].sum()
                # 최근 3년 평균 성장률 계산
                yearly = divs.resample('YE').sum()
                st.session_state.edit_data['growth'] = max(yearly.pct_change().tail(3).mean() * 100, 0.0) if len(yearly) >= 2 else 5.0
            
            st.session_state.edit_data['ticker'] = ticker_input
            st.sidebar.success("분석 완료! 아래 2단계에서 확인 후 저장하세요.")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"데이터 로드 실패: {e}")

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
        st.sidebar.error("⚠️ 주가는 0보다 커야 계산이 가능합니다.")
    else:
        new_row = pd.DataFrame([[ticker_input, f_count, f_price, f_dps, f_growth, f_cat]], columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("💾 데이터 백업")
# CSV 저장 기능
if not st.session_state.portfolio.empty:
    csv = st.session_state.portfolio.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(label="📥 현재 포트폴리오 다운로드", data=csv, file_name="my_dividend_data.csv", mime="text/csv", use_container_width=True)

# CSV 불러오기 기능
uploaded_file = st.sidebar.file_uploader("📂 파일 불러오기", type=["csv"])
if uploaded_file:
    st.session_state.portfolio = pd.read_csv(uploaded_file)
    st.sidebar.success("데이터 복구 완료!")

# --- [메인 화면] ---
st.title("📈 초정밀 배당 마스터 시뮬레이터 v14.0")

# 1. 상단 관리 바
if not st.session_state.portfolio.empty:
    col_sel, col_del = st.columns([3, 1])
    with col_sel:
        selected_stock = st.selectbox("📝 수정할 종목 선택 (선택 시 왼쪽 입력창 자동 동기화):", ["새 종목 추가"] + list(st.session_state.portfolio["종목명"]))
        if selected_stock != "새 종목 추가":
            target = st.session_state.portfolio[st.session_state.portfolio["종목명"] == selected_stock].iloc[0]
            st.session_state.edit_data = {"ticker": target["종목명"], "count": int(target["보유수량"]), "price": float(target["현재주가"]), "dps": float(target["주당배당금"]), "growth": float(target["배당성장률"]), "cat": target["유형"]}
    with col_del:
        st.write(" ")
        st.write(" ")
        if selected_stock != "새 종목 추가" and st.button("❌ 선택 종목 삭제", use_container_width=True):
            st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio["종목명"] != selected_stock].reset_index(drop=True)
            st.rerun()

    # 2. 시뮬레이션 설정 슬라이더
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: target_years = st.slider("📅 분석 기간 (년)", 1, 30, 10)
    with c2: monthly_add = st.number_input("💵 매달 추가 투자금", value=1000000, step=100000)
    with c3: price_growth = st.slider("📈 연간 주가 상승률 (%)", 0, 15, 3)

    # 3. 시뮬레이션 계산 로직
    years = list(range(1, target_years + 1))
    forecast_rows = []
    
    for _, row in st.session_state.portfolio.iterrows():
        c_shares, c_price, c_dps = float(row['보유수량']), float(row['현재주가']), float(row['주당배당금'])
        dgr, pgr = row['배당성장률'] / 100, price_growth / 100
        row_f = {"종목명": row['종목명'], "성장률": f"{row['배당성장률']:.1f}%"}
        
        for y in years:
            row_f[f"{y}년차"] = int((c_shares * c_dps) / 12)
            c_dps *= (1 + dgr)
            # 재투자 로직 (세금 15.4% 제외)
            net_div = (c_shares * (c_dps / (1+dgr))) * 0.846
            c_price *= (1 + pgr)
            # 월 적립금은 전체 종목에 균등 배분한다고 가정
            c_shares += (net_div + (monthly_add * 12 / len(st.session_state.portfolio))) / max(c_price, 1.0)
        forecast_rows.append(row_f)

    res_df = pd.DataFrame(forecast_rows)
    sum_row = {"종목명": "📊 월 배당 합계", "성장률": "-"}
    for y in years: sum_row[f"{y}년차"] = res_df[f"{y}년차"].sum()
    res_df = pd.concat([res_df, pd.DataFrame([sum_row])], ignore_index=True)

    # 4. 결과 출력
    st.write(f"### 🗓️ {target_years}개년 예상 월 평균 배당금 (세전)")
    st.dataframe(res_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}), use_container_width=True)
    
    st.success(f"🎯 **{target_years}년 후 당신의 매달 배당금은 {sum_row[f'{target_years}년차']:,.0f}원 입니다.**")
    
    # 배당락일 정보 (간이)
    st.divider()
    st.subheader("🔔 종목별 참고 정보")
    info_cols = st.columns(len(st.session_state.portfolio))
    for i, ticker in enumerate(st.session_state.portfolio["종목명"]):
        with info_cols[i]:
            st.caption(f"**{ticker}**")
            try:
                cal = yf.Ticker(ticker).calendar
                st.write(f"배당예정일: {cal.get('Dividend Date')}")
            except:
                st.write("일정 정보 없음")

else:
    st.info("👈 왼쪽 사이드바에서 종목을 분석하고 추가하여 시뮬레이션을 시작하세요!")

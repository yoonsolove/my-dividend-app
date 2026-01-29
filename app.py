import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# 1. 앱 설정 및 스타일
st.set_page_config(page_title="배당 통합 관리 v3.5", layout="wide", page_icon="📈")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "투자액", "배당률", "배당성장률", "배당락일", "유형"])

# --- 사이드바: 종목 등록 (2.0 로직: 개별 설정) ---
st.sidebar.title("➕ 종목 관리")
with st.sidebar.form("add_form"):
    name = st.text_input("종목명", value="SCHD").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    amount = st.number_input("투자금액 ($)", min_value=0, value=10000)
    yield_rate = st.number_input("현재 배당률 (%)", min_value=0.0, value=3.5)
    
    # 2.0 핵심: 미배콜은 0~1%, 성장주는 10% 등 개별 지정
    growth_rate = st.number_input("연간 배당성장률 (%)", value=10.0 if category == "배당성장주" else 0.5)
    ex_date = st.date_input("차기 배당락일", value=date.today())
    
    submitted = st.form_submit_button("포트폴리오 반영")
    if submitted:
        new_row = pd.DataFrame([[name, amount, yield_rate, growth_rate, ex_date, category]], 
                               columns=st.session_state.portfolio.columns)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last')
        st.success(f"{name} 등록 완료!")

# --- 메인 화면: 3.0 로직 (통합 대시보드) ---
st.title("📊 통합 배당 대시보드")

if st.session_state.portfolio.empty:
    st.warning("왼쪽 사이드바에서 종목을 먼저 등록해주세요!")
else:
    # 1. 상단 요약 (3.0 자동화 로직)
    total_invest = st.session_state.portfolio['투자액'].sum()
    total_annual_div = (st.session_state.portfolio['투자액'] * st.session_state.portfolio['배당률'] / 100).sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 투자액", f"${total_invest:,.0f}")
    m2.metric("예상 연 배당금(세전)", f"${total_annual_div:,.2f}")
    m3.metric("실제 수령액(세후 15%)", f"${total_annual_div * 0.85:,.2f}")

    st.divider()

    # 2. 배당락일 D-Day 알림 (3.0 자동 반영)
    st.subheader("📅 배당락일 캘린더 (D-Day)")
    today = date.today()
    cal_df = st.session_state.portfolio.copy()
    cal_df['남은일수'] = cal_df['배당락일'].apply(lambda x: (x - today).days)
    cal_df['상태'] = cal_df['남은일수'].apply(lambda x: f"D-{x}" if x >= 0 else "종료")
    
    # D-3 이내 종목 강조
    def highlight_urgent(val):
        color = 'red' if 'D-0' in str(val) or 'D-1' in str(val) or 'D-2' in str(val) or 'D-3' in str(val) else 'black'
        return f'color: {color}; font-weight: bold'

    st.table(cal_df[['종목명', '유형', '배당락일', '상태']].sort_values('배당락일').style.applymap(highlight_urgent, subset=['상태']))

    # 3. 미래 시뮬레이션 (2.0 + 3.0 조합)
    st.divider()
    st.subheader("🚀 10개년 복리 배당 성장 예측")
    
    years = list(range(1, 11))
    sim_results = []
    
    for _, row in st.session_state.portfolio.iterrows():
        base_div = row['투자액'] * (row['배당률'] / 100)
        for y in years:
            # 종목별로 다른 성장률(growth_rate) 적용
            future_val = base_div * ((1 + row['배당성장률'] / 100) ** (y - 1))
            sim_results.append({"연도": f"{y}년", "종목": row['종목명'], "배당금": future_val})
    
    fig = px.bar(pd.DataFrame(sim_results), x="연도", y="배당금", color="종목", 
                 title="종목별 성장률이 적용된 누적 배당수익", barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    st.info("💡 **조합 분석:** 미배콜은 현재 높은 배당을 주지만 10년 뒤에도 동일하며, 배당성장주는 현재는 적지만 10년 뒤 막대가 훨씬 높아지는 것을 볼 수 있습니다.")

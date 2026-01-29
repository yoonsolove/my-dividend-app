import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 통합 관리 v3.8", layout="wide", page_icon="📈")

# 세션 상태 초기화
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "투자액", "배당률", "배당성장률", "배당락일", "유형"])

# --- 사이드바: 종목 관리 ---
st.sidebar.title("➕ 종목 관리")
with st.sidebar.form("add_form"):
    name = st.text_input("종목명(코드)", value="441640").upper()
    category = st.selectbox("종목 유형", ["배당성장주", "미배콜/고배당", "리츠", "일반"])
    amount = st.number_input("총 투자금액 (원)", min_value=0, value=20000000, step=100000)
    yield_rate = st.number_input("현재 배당률 (%)", min_value=0.0, value=3.5, step=0.1)
    
    default_growth = 10.0 if category == "배당성장주" else 0.5
    growth_rate = st.number_input("연간 배당성장률 (%)", value=default_growth, step=0.1)
    ex_date = st.date_input("차기 배당락일", value=date.today())
    
    submitted = st.form_submit_button("포트폴리오 반영")
    if submitted:
        new_row = pd.DataFrame([[name, amount, yield_rate, growth_rate, ex_date, category]], 
                               columns=st.session_state.portfolio.columns)
        # ⚠️ 수정 포인트: 중복 제거 후 인덱스를 완전히 새로 고침 (오류 방지 핵심)
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
        st.success(f"{name} 등록 완료!")

# --- 메인 화면: 통합 대시보드 ---
st.title("📊 통합 배당 대시보드 (₩)")

if st.session_state.portfolio.empty:
    st.info("왼쪽에서 종목을 등록해주세요. 원화 단위로 계산됩니다.")
else:
    # 1. 상단 요약
    total_invest = st.session_state.portfolio['투자액'].sum()
    total_div = (st.session_state.portfolio['투자액'] * st.session_state.portfolio['배당률'] / 100).sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 투자액", f"{total_invest:,.0f}원")
    col2.metric("예상 연 배당금(세전)", f"{total_div:,.0f}원")
    col3.metric("실제 수령액(세후 15%)", f"{total_div * 0.85:,.0f}원")

    st.divider()

    # 2. 배당락일 캘린더 (중복 인덱스 오류 해결 버전)
    st.subheader("📅 배당락일 캘린더 (D-Day)")
    try:
        today = date.today()
        # 데이터 복사 시 인덱스 초기화 확인
        cal_df = st.session_state.portfolio.copy().reset_index(drop=True)
        
        cal_df['상태'] = cal_df['배당락일'].apply(lambda x: (x - today).days)
        cal_df['D-Day'] = cal_df['상태'].apply(lambda x: f"D-{x}" if x >= 0 else "종료")
        
        # 표시할 열 선택 및 정렬
        display_df = cal_df[['종목명', '유형', '배당락일', 'D-Day']].sort_values('배당락일').reset_index(drop=True)

        def highlight_dday(val):
            if any(target in str(val) for target in ['D-0', 'D-1', 'D-2', 'D-3']):
                return 'color: red; font-weight: bold;'
            return ''

        # 스타일 적용 시 열 이름 정확히 매칭
        st.table(display_df.style.applymap(highlight_dday, subset=['D-Day']))
        
    except Exception as e:
        st.error(f"캘린더 로딩 중 오류가 발생했습니다. (사유: {e})")

    # 3. 미래 시뮬레이션
    st.divider()
    st.subheader("🚀 10개년 복리 배당 성장 예측 (원)")
    
    years = list(range(1, 11))
    sim_data = []
    for _, row in st.session_state.portfolio.iterrows():
        base = row['투자액'] * (row['배당률'] / 100)
        for y in years:
            val = base * ((1 + row['배당성장률'] / 100) ** (y - 1))
            sim_data.append({"연도": f"{y}년차", "종목": row['종목명'], "배당금": val})
            
    fig = px.bar(pd.DataFrame(sim_data), x="연도", y="배당금", color="종목", 
                 title="종목별 성장률 반영 미래 배당금", barmode='group')
    st.plotly_chart(fig, use_container_width=True)

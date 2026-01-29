import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 통합 관리 v4.0", layout="wide", page_icon="📈")

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
        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row]).drop_duplicates('종목명', keep='last').reset_index(drop=True)
        st.success(f"{name} 등록 완료!")

# --- 메인 화면 ---
st.title("📊 배당 수치 분석 대시보드 (₩)")

if st.session_state.portfolio.empty:
    st.info("왼쪽 사이드바에서 종목을 등록해주세요. 모든 수치는 원화(₩) 기준입니다.")
else:
    # 1. 상단 핵심 요약
    total_invest = st.session_state.portfolio['투자액'].sum()
    total_div = (st.session_state.portfolio['투자액'] * st.session_state.portfolio['배당률'] / 100).sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 투자 자산", f"{total_invest:,.0f}원")
    col2.metric("1년 차 총 배당금(세전)", f"{total_div:,.0f}원")
    col3.metric("1년 차 실수령액(세후)", f"{total_div * 0.85:,.0f}원")

    st.divider()

    # 2. 배당락일 캘린더 (D-Day)
    st.subheader("📅 배당락일 일정")
    today = date.today()
    cal_df = st.session_state.portfolio.copy().reset_index(drop=True)
    cal_df['남은일수'] = cal_df['배당락일'].apply(lambda x: (x - today).days)
    cal_df['D-Day'] = cal_df['남은일수'].apply(lambda x: f"D-{x}" if x >= 0 else "종료")
    
    display_cal = cal_df[['종목명', '유형', '배당락일', 'D-Day']].sort_values('배당락일').reset_index(drop=True)
    
    # 강조 스타일 함수
    def style_urgent(val):
        if any(t in str(val) for t in ['D-0', 'D-1', 'D-2', 'D-3']):
            return 'color: #d32f2f; font-weight: bold;'
        return ''
    
    st.table(display_cal.style.applymap(style_urgent, subset=['D-Day']))

    st.divider()

    # 3. 10개년 복리 배당금 수치 테이블 (그래프 제외 핵심 섹션)
    st.subheader("🚀 10개년 복리 배당 예측 데이터")
    st.caption("※ 매년 설정된 배당성장률이 복리로 적용된 수치입니다.")
    
    years = list(range(1, 11))
    table_rows = []

    for _, row in st.session_state.portfolio.iterrows():
        base_annual_div = row['투자액'] * (row['배당률'] / 100)
        row_data = {"종목명": row['종목명'], "성장률": f"{row['배당성장률']}%"}
        
        for y in years:
            # 복리 계산: 초기배당금 * (1 + 성장률)^(n-1)
            future_amount = base_annual_div * ((1 + row['배당성장률'] / 100) ** (y - 1))
            row_data[f"{y}년차"] = int(future_amount)
        
        table_rows.append(row_data)
            
    # 데이터프레임 생성
    forecast_df = pd.DataFrame(table_rows)
    
    # 합계 행 계산 및 추가
    sum_data = {"종목명": "📊 연도별 총합계", "성장률": "-"}
    for y in years:
        sum_data[f"{y}년차"] = forecast_df[f"{y}년차"].sum()
    
    forecast_df = pd.concat([forecast_df, pd.DataFrame([sum_data])], ignore_index=True)

    # 수치 테이블 출력 (가독성을 위한 포맷팅)
    st.dataframe(
        forecast_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}),
        use_container_width=True,
        height=400
    )

    # 4. 세후 수치 간편 확인
    with st.expander("📝 세후(15.4%) 금액으로 보기"):
        st.write("소득세 15.4%를 제외한 실제 통장에 꽂히는 예상 금액입니다.")
        after_tax_df = forecast_df.copy()
        for y in years:
            # 합계 행 포함 모든 수치에 0.846 곱함
            after_tax_df[f"{y}년차"] = after_tax_df[f"{y}년차"].apply(lambda x: int(x * 0.846) if isinstance(x, (int, float)) else x)
        
        st.dataframe(
            after_tax_df.style.format({f"{y}년차": "{:,.0f}원" for y in years}),
            use_container_width=True
        )

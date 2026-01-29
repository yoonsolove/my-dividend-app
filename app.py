import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# 1. 앱 설정
st.set_page_config(page_title="배당 마스터 v3.1", layout="wide", page_icon="💰")

# 세션 상태 초기화 (데이터 휘발 방지)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["종목명", "투자액", "배당률", "배당성장률", "배당락일"])

st.title("💰 맞춤형 배당 관리 시스템 v3.1")
st.markdown("---")

# 2. 종목 입력 및 관리 섹션
with st.container():
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.subheader("📌 종목 기본 정보")
        name = st.text_input("종목명 (예: JEPI, SCHD, O)", value="SCHD").upper()
        invest_amt = st.number_input("현재 총 투자액 ($)", min_value=0, value=10000, step=1000)
        
    with col2:
        st.subheader("📈 배당 정책 설정")
        yield_rate = st.number_input("현재 시가배당률 (%)", min_value=0.0, value=3.4, step=0.1)
        # 미배콜은 0~1%, 배당성장주는 10% 이상으로 입력 유도
        growth_rate = st.number_input("연간 배당성장률 (%)", min_value=0.0, value=10.0, 
                                     help="미배콜(JEPI 등)은 0%에 가깝게, 배당성장주(SCHD 등)는 10% 내외를 권장합니다.")
        
    with col3:
        st.subheader("📅 배당 일정 관리")
        ex_date = st.date_input("다가오는 배당락일", value=date.today())
        add_btn = st.button("💾 포트폴리오에 추가/업데이트", use_container_width=True)

if add_btn:
    new_stock = pd.DataFrame([[name, invest_amt, yield_rate, growth_rate, ex_date]], 
                             columns=["종목명", "투자액", "배당률", "배당성장률", "배당락일"])
    # 기존 종목이 있으면 업데이트, 없으면 추가
    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_stock]).drop_duplicates('종목명', keep='last')
    st.success(f"✅ {name} 종목이 성공적으로 반영되었습니다.")

# 3. 배당락일 캘린더 (D-Day 알림)
st.markdown("---")
st.subheader("📅 실시간 배당락일 캘린더")
if not st.session_state.portfolio.empty:
    today = date.today()
    cal_list = []
    
    for _, row in st.session_state.portfolio.iterrows():
        d_day = (row['배당락일'] - today).days
        status = f"D-{d_day}" if d_day >= 0 else "종료"
        cal_list.append({
            "종목": row['종목명'],
            "배당락일": row['배당락일'],
            "남은 일정": status,
            "성격": "미배콜/고배당" if row['배당성장률'] < 3 else "배당성장주"
        })
    
    cal_df = pd.DataFrame(cal_list).sort_values(by="배당락일")
    
    # 가독성을 위한 조건부 서식 (D-3 이내 강조)
    def style_dday(val):
        color = 'red' if 'D-0' in str(val) or 'D-1' in str(val) or 'D-2' in str(val) or 'D-3' in str(val) else 'black'
        return f'color: {color}; font-weight: bold'

    st.table(cal_df.style.applymap(style_dday, subset=['남은 일정']))
else:
    st.info("먼저 종목을 추가해 주세요.")

# 4. [개별 성장률 반영] 미래 배당금 시뮬레이션
st.markdown("---")
st.subheader("🚀 10년 후 나의 월급(배당금) 변화")
if not st.session_state.portfolio.empty:
    years = list(range(1, 11))
    sim_results = []
    
    for _, row in st.session_state.portfolio.iterrows():
        annual_div = row['투자액'] * (row['배당률'] / 100)
        for y in years:
            # 복리 배당성장률 적용 (row['배당성장률'] 사용)
            future_div = annual_div * ((1 + row['배당성장률'] / 100) ** (y - 1))
            sim_results.append({
                "연도": f"{y}년차",
                "종목": row['종목명'],
                "예상배당금": round(future_div, 2)
            })
    
    sim_df = pd.DataFrame(sim_results)
    
    # 시각화: 누적 막대 차트
    fig = px.bar(sim_df, x="연도", y="예상배당금", color="종목", 
                 title="종목별 배당성장률이 반영된 장기 배당 흐름",
                 labels={"예상배당금": "연간 예상 배당금 ($)"},
                 barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    # 전문가적 분석 피드백
    st.info("""
    **💡 분석 팁:** - **미배콜 종목:** 초기 배당금은 높지만 시간이 흘러도 막대의 높이가 거의 일정합니다.
    - **배당성장주:** 초기 높이는 낮지만 시간이 갈수록 막대가 가파르게 높아지는 'J-커브'를 그리게 됩니다.
    """)

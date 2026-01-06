import streamlit as st
import pandas as pd

# 1. 앱 대문 꾸미기
st.title("🚀 내 마음대로 바꾸는 배당 앱")
st.write("왼쪽 메뉴(화살표)를 눌러서 종목 이름과 수량을 바꿔보세요!")

# 2. 왼쪽 사이드바(서랍장)에 입력칸 만들기
st.sidebar.header("📋 종목 설정")

# 첫 번째 종목 설정
stock_name_1 = st.sidebar.text_input("첫 번째 종목 이름", value="미배콜")
count_1 = st.sidebar.number_input(f"{stock_name_1} 수량", value=2000)
div_1 = st.sidebar.number_input(f"{stock_name_1} 1주당 배당금(원)", value=100)

st.sidebar.markdown("---") # 줄 긋기

# 두 번째 종목 설정
stock_name_2 = st.sidebar.text_input("두 번째 종목 이름", value="미배당")
count_2 = st.sidebar.number_input(f"{stock_name_2} 수량", value=860)
div_2 = st.sidebar.number_input(f"{stock_name_2} 1주당 배당금(원)", value=40)

# 3. 계산하기
total_1 = count_1 * div_1
total_2 = count_2 * div_2
grand_total = total_1 + total_2

# 4. 화면에 예쁘게 보여주기
st.subheader("💰 이번 달 예상 보물상자")

col1, col2 = st.columns(2)
with col1:
    st.metric(stock_name_1, f"{total_1:,} 원")
with col2:
    st.metric(stock_name_2, f"{total_2:,} 원")

st.divider()
st.header(f"✨ 총 합계: {grand_total:,} 원")

# 5. 배당 달력 (입력한 이름이 자동으로 들어감)
st.subheader("📅 배당 일정")
calendar_data = {
    '종목': [stock_name_1, stock_name_2],
    '입금예정일': ['매월 초', '매월 초'],
    '받을 금액': [f"{total_1:,}원", f"{total_2:,}원"]
}
st.table(pd.DataFrame(calendar_data))

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정 (모바일 최적화)
st.set_page_config(page_title="가족 가계부", layout="centered")

# Google Sheets 연결
url = "https://docs.google.com/spreadsheets/d/19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w/edit#gid=0"

conn = st.connection("gsheets", type=GSheetsConnection)


# 데이터 로드
def load_data():
    targets = conn.read(worksheet="Target")
    actuals = conn.read(worksheet="Data")
    return targets, actuals

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# --- 모드 선택 (입력 vs 대시보드) ---
menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드"])

# 1. 소비 입력 섹션
with menu[0]:
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("날짜", datetime.now())
        category = st.selectbox("소비 내역(항목)", targets_df["Category"].unique())
        card = st.selectbox("사용 카드", ["현대카드", "국민카드", "현금", "기타"])
        amount = st.number_input("액수 (원)", min_value=0, step=1000)
        installment = st.selectbox("할부 상세", ["일시불", "2개월", "3개월", "6개월", "12개월"])
        
        submit = st.form_submit_button("기록하기")
        
        if submit:
            new_data = pd.DataFrame([{
                "Date": date.strftime("%Y-%m-%d"),
                "Category": category,
                "Card": card,
                "Amount": amount,
                "Installment": installment
            }])
            updated_df = pd.concat([actuals_df, new_data], ignore_index=True)
            conn.update(worksheet="Data", data=updated_df)
            st.success("입력 완료!")
            st.rerun()

# 2. 대시보드 섹션
with menu[1]:
    # 이번 달 데이터 필터링
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'])
    this_month = datetime.now().month
    current_actuals = actuals_df[actuals_df['Date'].dt.month == this_month]
    
    # 항목별 집계
    summary = current_actuals.groupby("Category")["Amount"].sum().reset_index()
    summary = pd.merge(targets_df, summary, on="Category", how="left").fillna(0)
    
    # 계산 및 출력
    for index, row in summary.iterrows():
        goal = row["Monthly_Goal"]
        actual = row["Amount"]
        # 절감율 계산: LaTeX 적용
        # $$ \text{절감율} = \frac{\text{목표} - \text{누적}}{\text{목표}} \times 100 $$
        diff = goal - actual
        saving_rate = (diff / goal) * 100 if goal > 0 else 0
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{row['Category']}**")
            st.progress(min(max(actual / goal, 0.0), 1.0) if goal > 0 else 0.0)
        with col2:
            if diff >= 0:
                st.metric("절감액", f"{int(diff):,}원", f"{saving_rate:.1f}%")
            else:
                st.metric("초과액", f"{int(abs(diff)):,}원", f"{saving_rate:.1f}%", delta_color="inverse")
    
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(summary['Amount'].sum()):,} 원")

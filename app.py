import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

# 페이지 설정 (모바일 최적화)
st.set_page_config(page_title="가족 가계부", layout="centered")

# 본인의 구글 시트 ID
SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"

def get_csv_url(sheet_id, sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

def load_data():
    try:
        # Target 시트와 Data 시트 로드
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        return targets, actuals
    except Exception as e:
        st.error("구글 시트를 읽어오는데 실패했습니다. 시트 ID나 탭 이름을 확인해주세요.")
        st.stop()

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# 2026년 4월 기준 설정
this_year, this_month, today_day = 2026, 4, 6

menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# -------------------------------------------
# 1. 소비 입력
# -------------------------------------------
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=650, scrolling=True)

# -------------------------------------------
# 2. 실시간 대시보드 (수정 핵심 구역)
# -------------------------------------------
with menu[1]:
    # 날짜 처리
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'], errors='coerce')
    total_days = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days
    
    # [중요] 모든 카테고리명에서 공백을 제거하여 매칭 확률을 높임
    targets_df['Category'] = targets_df['Category'].astype(str).str.strip()
    actuals_df['Category(big)'] = actuals_df['Category(big)'].astype(str).str.strip()
    
    # 이번 달 데이터 필터링
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    # 💡 1단계: Data 시트에서 'Category(big)'별로 금액 합산
    summary_data = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    
    # 💡 2단계: Target 시트(기준)에 summary_data(금액)를 붙임
    # Target의 'Category' 열과 Data의 'Category(big)' 열을 매칭
    final_summary = pd.merge(
        targets_df, 
        summary_data, 
        left_on="Category", 
        right_on="Category(big)", 
        how="left"
    ).fillna(0)
    
    st.subheader("📊 대분류별 누적 사용 금액")
    # 바 차트 범례를 Target 시트의 Category 이름으로 강제 지정
    st.bar_chart(final_summary.set_index("Category")["Amount"])
    
    st.divider()
    st.subheader(f"🎯 오늘({this_month}/{today_day}) 기준 누적 현황")
    
    total_spent = 0
    for _, row in final_summary.iterrows():
        cat_name = row["Category"]  # '식재료', '생필품(쿠팡 포함)' 등
        goal = row["Monthly_Goal"]
        actual = row["Amount"]
        total_spent += actual
        
        cum_target = goal * elapsed_ratio
        diff = cum_target - actual
        
        col1, col2 = st.columns([1.8, 1.2])
        with col1:
            st.write(f"**{cat_name}**")
            prog = min(max(float(actual / goal), 0.0), 1.0) if goal > 0 else 0.0
            st.progress(prog)
            st.caption(f"예산: {int(goal):,}원 / 오늘권장: {int(cum_target):,}원")
        with col2:
            if diff >= 0:
                st.metric("누적 사용액", f"{int(actual):,}원", f"-{int(diff):,}원 (안정)")
            else:
                st.metric("누적 사용액", f"{int(actual):,}원", f"+{int(abs(diff)):,}원 (위험)", delta_color="inverse")
                
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(total_spent):,} 원")

# -------------------------------------------
# 3. 전체 내역 및 관리
# -------------------------------------------
with menu[2]:
    st.subheader("📜 이번 달 소비 상세")
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    
    # 7대 범례 출력
    show_cols = ["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]
    st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)
    
    st.divider()
    st.link_button("🗑️ 구글 시트에서 내역 수정/삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

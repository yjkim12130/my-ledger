import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

# 페이지 설정 (모바일 최적화)
st.set_page_config(page_title="가족 가계부", layout="centered")

# 본인의 구글 시트 ID
SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"

# 링크 공개 방식의 다운로드 URL 생성 함수
def get_csv_url(sheet_id, sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

def load_data():
    try:
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        return targets, actuals
    except Exception as e:
        st.error("구글 시트를 읽어오는데 실패했습니다. 시트 ID나 탭 이름을 확인해주세요.")
        st.stop()

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# --- 모드 선택 ---
menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# 1. 소비 입력 섹션
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=650, scrolling=True)

# 2. 대시보드 섹션
with menu[1]:
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'])
    
    # 현재 날짜 기준 정보 계산
    now = datetime.now()
    this_year = now.year
    this_month = now.month
    today_day = now.day
    
    # 이번 달의 총 일수 계산 (예: 4월이면 30일)
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    
    # 일할 계산 비율 (예: 30일 중 10일째면 10/30 = 0.333)
    elapsed_ratio = today_day / total_days_in_month
    
    current_actuals = actuals_df[actuals_df['Date'].dt.month == this_month]
    
    # 항목별 집계
    st.subheader("📊 항목별 누적 사용 금액")
    summary = current_actuals.groupby("Category")["Amount"].sum().reset_index()
    summary = pd.merge(targets_df, summary, on="Category", how="left").fillna(0)
    
    # 바 차트로 시각화
    st.bar_chart(summary.set_index("Category")["Amount"])
    
    st.divider()
    
    # 🎯 요청하신 일할 계산 기준 목표 대비 소비 현황
    st.subheader(f"🎯 오늘({this_month}/{today_day}) 기준 소비 현황")
    st.caption(f"💡 이번 달 총 {total_days_in_month}일 중 {today_day}일째 경과 (진행률: {elapsed_ratio*100:.1f}%)")
    
    for index, row in summary.iterrows():
        monthly_goal = row["Monthly_Goal"]
        actual = row["Amount"]
        
        # 오늘 기준 목표액 = 한달 목표액 * (오늘 날짜 / 이번 달 총 일수)
        today_goal = monthly_goal * elapsed_ratio
        
        # 오늘 기준 절감/초과액 계산
        diff = today_goal - actual
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{row['Category']}**")
            # 게이지 바는 '한 달 전체 예산' 대비 현재 얼마 썼는지를 직관적으로 보여줍니다.
            progress_val = min(max(float(actual / monthly_goal), 0.0), 1.0) if monthly_goal > 0 else 0.0
            st.progress(progress_val)
            st.caption(f"한달 예산 {int(monthly_goal):,}원 중 {int(actual):,}원 사용")
            
        with col2:
            if diff >= 0:
                st.metric("오늘 기준 절약", f"{int(diff):,}원")
            else:
                st.metric("오늘 기준 초과", f"{int(abs(diff)):,}원", delta_color="inverse")
    
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(summary['Amount'].sum()):,} 원")

# 3. 전체 내역 및 삭제 관리 섹션
with menu[2]:
    st.subheader("📜 이번 달 소비 건별 상세 내역")
    
    display_df = actuals_df[actuals_df['Date'].dt.month == this_month].copy()
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    show_table = display_df[["Date", "Category", "Amount", "누적 총액", "Card", "Installment"]]
    
    st.dataframe(show_table, use_container_width=True, hide_index=True)
    
    st.divider()
    st.warning("⚠️ 앱에서는 구글 시트의 데이터를 직접 삭제할 수 없습니다. 잘못 입력된 내역은 아래 버튼을 눌러 구글 시트에서 직접 해당 행을 삭제해주세요.")
    st.link_button("🗑️ 구글 시트 열어서 내역 삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

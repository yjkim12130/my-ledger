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

# 2026년 4월 6일 기준 하드코딩 (날짜 불일치 방지)
this_year = 2026
this_month = 4
today_day = 6

# ==========================================
# 1. 소비 입력 섹션
# ==========================================
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=650, scrolling=True)


# ==========================================
# 2. 대시보드 섹션
# ==========================================
with menu[1]:
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'], errors='coerce')
    
    # 일할 계산 비율 산출
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days_in_month
    
    # 텍스트 매칭 실패 방지 (공백 제거)
    actuals_df['Category(big)'] = actuals_df['Category(big)'].astype(str).str.strip()
    targets_df['Category'] = targets_df['Category'].astype(str).str.strip()
    
    # 이번 달 데이터만 필터링 (3번째 탭과 완벽 동일)
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    st.subheader("📊 대분류별 누적 사용 금액")
    
    # 7대 범례 중 'Category(big)' 원본 데이터로 그룹화
    summary = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    
    # Target 시트의 'Category'와 1:1 매칭하여 병합
    summary = pd.merge(targets_df, summary, left_on="Category", right_on="Category(big)", how="left").fillna(0)
    
    # 바 차트로 시각화
    st.bar_chart(summary.set_index("Category")["Amount_y" if "Amount_y" in summary.columns else "Amount"])
    
    st.divider()
    
    st.subheader(f"🎯 오늘({this_month}/{today_day})까지의 누적 소비 현황")
    st.caption(f"💡 이번 달 총 {total_days_in_month}일 중 {today_day}일 경과 (진행률: {elapsed_ratio*100:.1f}%)")
    
    total_spent = 0
    
    for index, row in summary.iterrows():
        monthly_goal = row["Monthly_Goal"]
        actual = row["Amount_y"] if "Amount_y" in row else row["Amount"]
        category_name = row["Category"]
        
        total_spent += actual
        
        # 누적 권장 예산 및 차액 계산
        cumulative_target = monthly_goal * elapsed_ratio
        diff = cumulative_target - actual
        
        col1, col2 = st.columns([1.8, 1.2])
        with col1:
            st.write(f"**{category_name}**")
            progress_val = min(max(float(actual / monthly_goal), 0.0), 1.0) if monthly_goal > 0 else 0.0
            st.progress(progress_val)
            st.caption(f"한달 예산: {int(monthly_goal):,}원 / 오늘까지 권장: {int(cumulative_target):,}원")
            
        with col2:
            if diff >= 0:
                st.metric(
                    label="누적 사용액", 
                    value=f"{int(actual):,}원", 
                    delta=f"-{int(diff):,}원 (안정)"
                )
            else:
                st.metric(
                    label="누적 사용액", 
                    value=f"{int(actual):,}원", 
                    delta=f"+{int(abs(diff)):,}원 (위험)", 
                    delta_color="inverse"
                )
    
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(total_spent):,} 원")


# ==========================================
# 3. 전체 내역 및 관리 섹션
# ==========================================
with menu[2]:
    st.subheader("📜 이번 달 소비 건별 상세 내역")
    
    # 대시보드와 완벽히 동일한 조건으로 데이터 필터링
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    
    # 날짜 순 정렬 및 누적 총액 계산
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    
    # 요청하신 7가지 상세 열 노출
    show_table = display_df[["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]]
    
    st.dataframe(show_table, use_container_width=True, hide_index=True)
    
    st.divider()
    st.warning("⚠️ 앱에서는 구글 시트의 데이터를 직접 삭제할 수 없습니다. 잘못 입력된 내역은 아래 버튼을 눌러 구글 시트에서 직접 해당 행을 삭제해주세요.")
    st.link_button("🗑️ 구글 시트 열어서 내역 삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

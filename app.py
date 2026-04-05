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

# 2. 대시보드 섹션 (★로직 대폭 수정)
with menu[1]:
    # 날짜 데이터 변환 및 오류 방지 (errors='coerce'로 잘못된 날짜는 NaT 처리)
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'], errors='coerce')
    
    # 현재 날짜 기준 정보 계산 (2026년 4월 기준)
    this_year = 2026
    this_month = 4
    today_day = 6  # 오늘 날짜
    
    # 이번 달의 총 일수 계산
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days_in_month
    
    # 1. 이번 달 데이터만 정확하게 필터링
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    # 2. 텍스트 매칭 오류 방지를 위해 카테고리명 앞뒤 공백 제거
    current_actuals['Category(big)'] = current_actuals['Category(big)'].astype(str).str.strip()
    targets_df['Category'] = targets_df['Category'].astype(str).str.strip()
    
    st.subheader("📊 대분류별 누적 사용 금액")
    
    # 3. 이번 달 데이터만으로 그룹화 합산
    summary = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    
    # 4. Target 시트 기준으로 데이터 병합 (결측치는 0원 처리)
    summary = pd.merge(targets_df, summary, left_on="Category", right_on="Category(big)", how="left").fillna(0)
    
    # 바 차트로 시각화
    st.bar_chart(summary.set_index("Category")["Amount_y" if "Amount_y" in summary.columns else "Amount"])
    
    st.divider()
    
    # 🎯 누적 기준 목표 대비 소비 현황
    st.subheader(f"🎯 오늘({this_month}/{today_day})까지의 누적 소비 현황")
    st.caption(f"💡 이번 달 총 {total_days_in_month}일 중 {today_day}일 경과 (진행률: {elapsed_ratio*100:.1f}%)")
    
    total_spent = 0
    
    for index, row in summary.iterrows():
        monthly_goal = row["Monthly_Goal"]
        
        # 병합 후 Amount 컬럼 이름이 중복되었을 경우를 대비한 방어 코드
        if "Amount_y" in row:
            actual = row["Amount_y"]
        elif "Amount" in row:
            actual = row["Amount"]
        else:
            actual = 0
            
        category_name = row["Category"]
        total_spent += actual
        
        # 오늘까지 썼어야 할 '누적 권장 예산'
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
                st.metric(label="누적 사용액", value=f"{int(actual):,}원", delta=f"-{int(diff):,}원 (안정)")
            else:
                st.metric(label="누적 사용액", value=f"{int(actual):,}원", delta=f"+{int(abs(diff)):,}원 (위험)", delta_color="inverse")
    
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(total_spent):,} 원")

# 3. 전체 내역 및 삭제 관리 섹션
with menu[2]:
    st.subheader("📜 이번 달 소비 건별 상세 내역")
    
    # 전체 내역 탭도 대시보드와 동일한 기준으로 필터링하여 일관성 유지
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    
    show_table = display_df[["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]]
    
    st.dataframe(show_table, use_container_width=True, hide_index=True)
    
    st.divider()
    st.warning("⚠️ 앱에서는 구글 시트의 데이터를 직접 삭제할 수 없습니다. 잘못 입력된 내역은 아래 버튼을 눌러 구글 시트에서 직접 해당 행을 삭제해주세요.")
    st.link_button("🗑️ 구글 시트 열어서 내역 삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

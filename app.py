import streamlit as st
import pandas as pd
from datetime import datetime

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
# 2. 대시보드 섹션
with menu[1]:
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'])
    this_month = datetime.now().month
    current_actuals = actuals_df[actuals_df['Date'].dt.month == this_month]
    
    # 항목별 집계
    st.subheader("📊 항목별 누적 사용 금액")
    summary = current_actuals.groupby("Category")["Amount"].sum().reset_index()
    summary = pd.merge(targets_df, summary, on="Category", how="left").fillna(0)
    
    # 바 차트로 시각화
    st.bar_chart(summary.set_index("Category")["Amount"])
    
    st.divider()
    
    # 기존 목표 대비 절감율 UI
    st.subheader("🎯 목표 대비 소비 현황")
    for index, row in summary.iterrows():
        goal = row["Monthly_Goal"]
        actual = row["Amount"]
        
        diff = goal - actual
        saving_rate = (diff / goal) * 100 if goal > 0 else 0
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{row['Category']}**")
            st.progress(min(max(float(actual / goal), 0.0), 1.0) if goal > 0 else 0.0)
            
        # ⚠️ 이 부분의 들여쓰기를 완벽하게 맞춰야 합니다!
        with col2:
            if diff >= 0:
                st.metric("절감액", f"{int(diff):,}원", f"{saving_rate:.1f}%")
            else:
                st.metric("초과액", f"{int(abs(diff)):,}원", f"{saving_rate:.1f}%", delta_color="inverse")
    
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(summary['Amount'].sum()):,} 원")

# 3. 0번 & 2번 요청: 전체 내역 및 삭제 관리 섹션
with menu[2]:
    st.subheader("📜 이번 달 소비 건별 상세 내역")
    
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'])
    this_month = datetime.now().month
    display_df = actuals_df[actuals_df['Date'].dt.month == this_month].copy()
    
    # 0번 요청: 소비 건별 누적 금액 계산 (날짜순 정렬 후 누적합)
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    # 사용자에게 보여줄 컬럼 정리 및 날짜 포맷팅
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    show_table = display_df[["Date", "Category", "Amount", "누적 총액", "Card", "Installment"]]
    
    # 테이블 출력
    st.dataframe(show_table, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 2번 요청에 대한 우회책 제공
    st.warning("⚠️ 앱에서는 구글 시트의 데이터를 직접 삭제할 수 없습니다. 잘못 입력된 내역은 아래 버튼을 눌러 구글 시트에서 직접 해당 행을 삭제해주세요.")
    st.link_button("🗑️ 구글 시트 열어서 내역 삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

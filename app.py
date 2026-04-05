import streamlit as st
import pandas as pd
from datetime import datetime

# 페이지 설정 (모바일 최적화)
st.set_page_config(page_title="가족 가계부", layout="centered")

# ⚠️ [필수 수정] 본인의 구글 시트 ID를 입력하세요.
# 주소창의 d/ 와 /edit 사이에 있는 길고 복잡한 문자열입니다.
SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"

# 링크 공개 방식의 다운로드 URL 생성 함수
def get_csv_url(sheet_id, sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

def load_data():
    try:
        # Target 시트와 Data 시트를 CSV 형태로 다이렉트 스트리밍
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        return targets, actuals
    except Exception as e:
        st.error("구글 시트를 읽어오는데 실패했습니다. 시트 ID나 탭 이름을 확인해주세요.")
        st.stop()

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# --- 모드 선택 (입력 vs 대시보드) ---
menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드"])

# 1. 소비 입력 섹션 (이 방식에서는 입력 시 구글 폼 링크나 시트 링크를 활용하는 것이 안정적입니다)
with menu[0]:
    st.info("💡 링크 공개 방식에서는 직접 입력보다 '구글 폼'을 연동하는 것이 훨씬 안정적입니다.")
    # 구글 시트 주소를 브라우저에서 바로 열 수 있도록 버튼 제공
    st.link_button("👉 구글 시트에서 직접 기록하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

# 2. 대시보드 섹션
with menu[1]:
    # 이번 달 데이터 필터링
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'])
    
    # 2026년 현재 기준으로 데이터 필터링
    this_month = datetime.now().month
    current_actuals = actuals_df[actuals_df['Date'].dt.month == this_month]
    
    # 항목별 집계
    summary = current_actuals.groupby("Category")["Amount"].sum().reset_index()
    summary = pd.merge(targets_df, summary, on="Category", how="left").fillna(0)
    
    # 계산 및 출력
    for index, row in summary.iterrows():
        goal = row["Monthly_Goal"]
        actual = row["Amount"]
        
        diff = goal - actual
        saving_rate = (diff / goal) * 100 if goal > 0 else 0
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{row['Category']}**")
            st.progress(min(max(float(actual / goal), 0.0), 1.0) if goal > 0 else 0.0)
        with col2:
            if diff >= 0:
                st.metric("절감액", f"{int(diff):,}원", f"{saving_rate:.1f}%")
            else:
                st.metric("초과액", f"{int(abs(diff)):,}원", f"{saving_rate:.1f}%", delta_color="inverse")
    
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(summary['Amount'].sum()):,} 원")

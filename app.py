import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

# 1. 페이지 설정 및 기본 정보
st.set_page_config(page_title="우리집 가계부", layout="centered")

SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"
this_year, this_month, today_day = 2026, 4, 6  # 기준 날짜

# 구글 시트 연결 함수
def get_csv_url(sheet_id, sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data(ttl=60)
def load_data():
    try:
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        # 공백 제거 및 타입 최적화
        targets['Category'] = targets['Category'].astype(str).str.strip()
        actuals['Category(big)'] = actuals['Category(big)'].astype(str).str.strip()
        actuals['Date'] = pd.to_datetime(actuals['Date'], errors='coerce')
        return targets, actuals
    except Exception as e:
        st.error("데이터 로드 중 오류가 발생했습니다.")
        st.stop()

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# 탭 구성
menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# ==========================================
# 탭 1: 소비 입력
# ==========================================
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=600, scrolling=True)

# ==========================================
# 탭 2: 실시간 대시보드
# ==========================================
with menu[1]:
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days_in_month

    summary_data = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    final_summary = pd.merge(targets_df, summary_data, left_on="Category", right_on="Category(big)", how="left").fillna(0)

    st.subheader("📊 카테고리별 사용금액")
    st.bar_chart(final_summary.set_index("Category")["Amount"])

    st.divider()
    
    total_spent = 0
    for _, row in final_summary.iterrows():
        cat_name, goal, actual = row["Category"], row["Monthly_Goal"], row["Amount"]
        total_spent += actual
        cum_target = goal * elapsed_ratio
        diff = cum_target - actual

        col1, col2 = st.columns([1.8, 1.2])
        with col1:
            st.write(f"**{cat_name}**")
            st.progress(min(max(float(actual / goal), 0.0), 1.0) if goal > 0 else 0.0)
            st.caption(f"예산: {int(goal):,} / 권장: {int(cum_target):,}")
        with col2:
            st.metric("사용액", f"{int(actual):,}원", f"{int(diff):,}원", delta_color="normal" if diff >= 0 else "inverse")

    st.divider()
    st.subheader(f"{this_month}월 총 지출: {int(total_spent):,} 원")

# ==========================================
# 탭 3: 전체 내역 및 관리
# ==========================================
with menu[2]:
    st.subheader("📜 이번 달 소비 상세 내역")
    
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    table_view = display_df.copy()
    table_view['Date'] = table_view['Date'].dt.strftime('%Y-%m-%d')
    cols = ["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]
    st.dataframe(table_view[cols], use_container_width=True, hide_index=True)

    st.divider()

    st.subheader(f"🗓️ {this_month}월 소비 캘린더")
    st.caption("단위: 만원 (예: 9.3만)")

    daily_totals = display_df.groupby(display_df['Date'].dt.day)['Amount'].sum()
    month_cal = calendar.monthcalendar(this_year, this_month)
    days = ["월", "화", "수", "목", "금", "토", "일"]

    cal_html = f"""
    <style>
        .cal-container {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; width: 100%; }}
        .cal-header {{ font-weight: bold; font-size: 0.7em; padding: 5px 0; background: #f0f2f6; border-radius: 3px; text-align: center; }}
        .cal-day {{ border: 1px solid #f0f2f6; border-radius: 3px; min-height: 42px; text-align: center; padding: 4px 0; background: white; display: flex; flex-direction: column; justify-content: center; }}
        .today {{ border: 1.5px solid #007bff; background: #e6f3ff; font-weight: bold; }}
        .day-num {{ font-size: 0.75em; color: #333; }}
        .amt {{ font-size: 0.62em; color: #ff4b4b; font-weight: bold; white-space: nowrap; margin-top: 1px; }}
        .empty-amt {{ font-size: 0.62em; color: #ccc; }}
    </style>
    <div class="cal-container">
    """
    for d in days: cal_html += f'<div class="cal-header">{d}</div>'

    for week in month_cal:
        for day in week:
            if day == 0:
                cal_html += '<div style="background:none;"></div>'
            else:
                amt = daily_totals.get(day, 0)
                is_today = "today" if day == today_day else ""
                
                if amt > 0:
                    # [에러 수정 포인트] :.1f 포맷으로 변경
                    amt_text = f"{amt / 10000:.1f}만".replace(".0만", "만")
                    amt_html = f'<span class="amt">{amt_text}</span>'
                else:
                    amt_html = '<span class="empty-amt">-</span>'
                
                cal_html += f'<div class="cal-day {is_today}"><span class="day-num">{day}</span>{amt_html}</div>'
    
    cal_html += "</div>"
    st.markdown(cal_html, unsafe_allow_html=True)

    st.divider()
    st.link_button("🗑️ 구글 시트에서 수정/삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

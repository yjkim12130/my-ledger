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
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        return targets, actuals
    except Exception as e:
        st.error("구글 시트를 읽어오는데 실패했습니다.")
        st.stop()

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# 2026년 4월 6일 기준 하드코딩 (필요시 수정)
this_year, this_month, today_day = 2026, 4, 6

menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# ===========================================
# 1. 소비 입력
# ===========================================
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=650, scrolling=True)

# ===========================================
# 2. 실시간 대시보드
# ===========================================
with menu[1]:
    actuals_df['Date'] = pd.to_datetime(actuals_df['Date'], errors='coerce')
    total_days = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days
    
    targets_df['Category'] = targets_df['Category'].astype(str).str.strip()
    actuals_df['Category(big)'] = actuals_df['Category(big)'].astype(str).str.strip()
    
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    summary_data = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    final_summary = pd.merge(targets_df, summary_data, left_on="Category", right_on="Category(big)", how="left").fillna(0)
    
    st.subheader("📊 대분류별 누적 사용 금액")
    st.bar_chart(final_summary.set_index("Category")["Amount"])
    
    st.divider()
    st.subheader(f"🎯 오늘({this_month}/{today_day}) 기준 누적 현황")
    
    total_spent = 0
    for _, row in final_summary.iterrows():
        cat_name, goal, actual = row["Category"], row["Monthly_Goal"], row["Amount"]
        total_spent += actual
        cum_target, diff = goal * elapsed_ratio, (goal * elapsed_ratio) - actual
        
        col1, col2 = st.columns([1.8, 1.2])
        with col1:
            st.write(f"**{cat_name}**")
            st.progress(min(max(float(actual / goal), 0.0), 1.0) if goal > 0 else 0.0)
            st.caption(f"예산: {int(goal):,}원 / 오늘권장: {int(cum_target):,}원")
        with col2:
            if diff >= 0:
                st.metric("누적 사용액", f"{int(actual):,}원", f"-{int(diff):,}원 (안정)")
            else:
                st.metric("누적 사용액", f"{int(actual):,}원", f"+{int(abs(diff)):,}원 (위험)", delta_color="inverse")
                
    st.divider()
    st.subheader("이번 달 총 소비")
    st.title(f"{int(total_spent):,} 원")

# ===========================================
# 3. 전체 내역 및 관리 (캘린더 최적화 포함)
# ===========================================
with menu[2]:
    st.subheader("📜 이번 달 소비 상세")
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    # 테이블 출력용 데이터 가공
    table_df = display_df.copy()
    table_df['Date'] = table_df['Date'].dt.strftime('%Y-%m-%d')
    show_cols = ["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]
    st.dataframe(table_df[show_cols], use_container_width=True, hide_index=True)
    
    st.divider()

    # 🗓️ [신규] 모바일 최적화 및 '만원' 단위 변경 캘린더
    st.subheader(f"🗓️ {this_month}월 소비 캘린더")
    st.caption("일자별 총 지출액 요약 (단위: 만원)")

    # 일자별 합계 데이터 준비
    daily_totals = display_df.groupby(display_df['Date'].dt.day)['Amount'].sum()

    # 캘린더 그리드 데이터 준비
    month_cal = calendar.monthcalendar(this_year, this_month)
    days = ["월", "화", "수", "목", "금", "토", "일"]
    
    # CSS Grid를 활용하여 모바일에서 7열 강제 유지
    cal_html = f"""
    <style>
        .calendar-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 4px;
            text-align: center;
            font-family: sans-serif;
        }}
        .calendar-header {{
            font-weight: bold;
            padding: 5px;
            background-color: #f0f2f6;
            border-radius: 5px;
            font-size: 0.8em;
        }}
        .calendar-day {{
            padding: 6px 1px;
            border: 1px solid #f0f2f6;
            border-radius: 5px;
            min-height: 45px;
            background-color: #ffffff;
        }}
        .today-mark {{
            background-color: #e6f3ff;
            font-weight: bold;
            border: 1px solid #007bff;
        }}
        .spent-text {{
            color: #ff4b4b;
            font-size: 0.75em;
            display: block;
            margin-top: 3px;
        }}
        .zero-text {{
            color: #ccc;
            font-size: 0.75em;
            display: block;
            margin-top: 3px;
        }}
    </style>
    <div class="calendar-grid">
    """

    # 요일 헤더 렌더링
    for d in days:
        cal_html += f'<div class="calendar-header">{d}</div>'

    # 날짜 및 소비 데이터 렌더링
    for week in month_cal:
        for day in week:
            if day == 0:
                cal_html += '<div class="calendar-day" style="border:none;background:none;"></div>'
            else:
                daily_val = daily_totals.get(day, 0)
                is_today = "today-mark" if day == today_day else ""
                
                # 금액이 있을 경우에만 포맷팅 (93,000원 -> 9.3만)
                if daily_val > 0:
                    amount_text = f"{daily_val / 10000:.1f}만"
                    amount_text = amount_text.replace(".0만", "만")
                    display_text = f'<span class="spent-text">{amount_text}</span>'
                else:
                    display_text = '<span class="zero-text">-</span>'
                
                cal_html += f"""
                <div class="calendar-day {is_today}">
                    <span style="font-size: 0.85em;">{day}</span>
                    {display_text}
                </div>
                """
    
    cal_html += "</div>"
    
    # 최종 HTML 출력
    st.markdown(cal_html, unsafe_allow_html=True)

    st.divider()
    st.link_button("🗑️ 구글 시트에서 내역 수정/삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

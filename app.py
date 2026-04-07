import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# 1. 페이지 설정 및 기본 정보
st.set_page_config(page_title="우리집 가계부", layout="centered")

SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"

# 💡 [날짜 자동화] 서버 시간에 의존하지 않고 무조건 한국 표준시(KST)로 오늘 날짜를 가져옵니다.
now_kst = datetime.utcnow() + timedelta(hours=9)
this_year, this_month, today_day = now_kst.year, now_kst.month, now_kst.day

# 구글 시트 연결 함수
def get_csv_url(sheet_id, sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data(ttl=60)
def load_data():
    try:
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        
        targets['Category'] = targets['Category'].astype(str).str.strip()
        actuals['소비 내역(분류)'] = actuals['소비 내역(분류)'].astype(str).str.strip()
        actuals['소비 날짜'] = pd.to_datetime(actuals['소비 날짜'], errors='coerce')
        
        actuals['액수'] = pd.to_numeric(actuals['액수'], errors='coerce').fillna(0)
        
        return targets, actuals
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        st.stop()

targets_df, actuals_df = load_data()

# 💡 [새로고침 기능] 제목 옆에 버튼을 배치하여 언제든 최신 시트 상태를 강제로 불러옵니다.
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.title("💸 우리집 가계부")
with col2:
    st.write("") # 간격 맞추기
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# ==========================================
# 탭 1: 소비 입력
# ==========================================
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=900, scrolling=True)

# ==========================================
# 탭 2: 실시간 대시보드
# ==========================================
with menu[1]:
    current_actuals = actuals_df[
        (actuals_df['소비 날짜'].dt.year == this_year) & 
        (actuals_df['소비 날짜'].dt.month == this_month)
    ]
    
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days_in_month

    summary_data = current_actuals.groupby("소비 내역(분류)")["액수"].sum().reset_index()
    final_summary = pd.merge(targets_df, summary_data, left_on="Category", right_on="소비 내역(분류)", how="left").fillna(0)

    st.subheader("📊 카테고리별 사용금액")
    st.bar_chart(final_summary.set_index("Category")["액수"])

    st.divider()
    st.subheader(f"🎯 오늘({this_month}/{today_day}) 기준 소비 성적표")
    
    total_spent = 0
    for i, (_, row) in enumerate(final_summary.iterrows(), start=1):
        cat_name, goal, actual = row["Category"], row["Monthly_Goal"], row["액수"]
        total_spent += actual
        
        cum_target = goal * elapsed_ratio
        diff = cum_target - actual

        if goal > 0:
            actual_ratio = (actual / goal) * 100
            target_ratio = (cum_target / goal) * 100
            
            if actual <= cum_target:
                green_bar_width = min(actual_ratio, 100)
                red_bar_width = 0
                status_color = "#28a745"
                bg_color = "#e8f5e9"
                text_color = "#2e7d32"
                status_text = "계획대비 절약중"
                detail_subtext = f"{int(diff):,}원 여유"
            else:
                green_bar_width = min(target_ratio, 100)
                red_bar_width = min(max(actual_ratio - target_ratio, 0.0), 120 - target_ratio)
                status_color = "#ff4b4b"
                bg_color = "#ffebee"
                text_color = "#c62828"
                status_text = "계획대비 과소비중"
                detail_subtext = f"{int(abs(diff)):,}원 초과"
        else:
            green_bar_width = red_bar_width = target_ratio = 0
            status_color, bg_color, text_color, status_text, detail_subtext = "#ccc", "#f0f2f6", "#555", "예산 미설정", "-"

        st.markdown(f"<span style='font-size: 1.15em; font-weight: bold;'>{i}. {cat_name}</span> <span style='font-size: 0.9em; color: #555;'>(전체예산: {int(goal):,})</span>", unsafe_allow_html=True)
        
        progress_card_html = f"""
        <div style="display: flex; align-items: center; gap: 8px; font-family: sans-serif; width: 100%;">
            <div style="flex: 1; position: relative; background-color: #f0f2f6; border-radius: 4px; height: 18px; overflow: visible;">
                <div style="position: absolute; left: 0; top: 0; width: {green_bar_width}%; background-color: #28a745; height: 100%; border-radius: 4px;"></div>
                <div style="position: absolute; left: {green_bar_width}%; top: 0; width: {red_bar_width}%; background-color: #ff4b4b; height: 100%; border-radius: 4px;"></div>
                <div style="position: absolute; left: {target_ratio}%; top: -2px; width: 2px; background-color: #007bff; height: 22px; z-index: 10; border-radius: 1px;"></div>
            </div>
            
            <div style="width: 155px; background-color: {bg_color}; padding: 8px 4px; border-radius: 6px; border: 1px solid {status_color}; text-align: center; display: flex; flex-direction: column; justify-content: center; height: 55px; flex-shrink: 0;">
                <span style="font-size: 12px; font-weight: bold; color: #111;">누적: {int(actual):,}원</span>
                <span style="font-size: 11px; color: #555; margin-top: 1px;">계획: {int(cum_target):,}원</span>
                <span style="font-size: 9px; font-weight: bold; color: {text_color}; white-space: nowrap; margin-top: 3px;">
                    {status_text}<br>({detail_subtext})
                </span>
            </div>
        </div>
        """
        st.components.v1.html(progress_card_html, height=75)
        st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    st.subheader(f"{this_month}월 총 지출: {int(total_spent):,} 원")

# ==========================================
# 탭 3: 전체 내역 및 관리
# ==========================================
with menu[2]:
    st.subheader("📜 이번 달 소비 상세 내역")
    
    display_df = actuals_df[
        (actuals_df['소비 날짜'].dt.year == this_year) & 
        (actuals_df['소비 날짜'].dt.month == this_month)
    ].copy()
    display_df = display_df.sort_values(by="소비 날짜")
    
    display_df["누적 총액"] = display_df["액수"].cumsum()
    
    table_view = display_df.copy()
    table_view['소비 날짜'] = table_view['소비 날짜'].dt.strftime('%Y-%m-%d')
    st.dataframe(table_view, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader(f"🗓️ {this_month}월 소비 캘린더")
    st.caption("단위: 만원 (예: 9.3만)")

    daily_totals = display_df.groupby(display_df['소비 날짜'].dt.day)['액수'].sum()
    month_cal = calendar.monthcalendar(this_year, this_month)
    days = ["월", "화", "수", "목", "금", "토", "일"]

    cal_html = f"""
    <div style="font-family: sans-serif;">
        <style>
            .cal-container {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; width: 100%; }}
            .cal-header {{ font-weight: bold; font-size: 11px; padding: 6px 0; background: #f0f2f6; border-radius: 3px; text-align: center; color: #555; }}
            .cal-day {{ border: 1px solid #f0f2f6; border-radius: 3px; min-height: 45px; text-align: center; padding: 4px 0; background: white; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
            .today {{ border: 1.5px solid #007bff; background: #e6f3ff; font-weight: bold; }}
            .day-num {{ font-size: 12px; color: #333; }}
            .amt {{ font-size: 10px; color: #ff4b4b; font-weight: bold; white-space: nowrap; margin-top: 2px; }}
            .empty-amt {{ font-size: 10px; color: #ccc; }}
        </style>
        <div class="cal-container">
    """
    for d in days: 
        cal_html += f'<div class="cal-header">{d}</div>'

    for week in month_cal:
        for day in week:
            if day == 0:
                cal_html += '<div style="background:none;"></div>'
            else:
                amt = daily_totals.get(day, 0)
                is_today = "today" if day == today_day else ""
                
                if amt > 0:
                    amt_text = f"{amt / 10000:.1f}만".replace(".0만", "만")
                    amt_html = f'<span class="amt">{amt_text}</span>'
                else:
                    amt_html = '<span class="empty-amt">-</span>'
                
                cal_html += f'<div class="cal-day {is_today}"><span class="day-num">{day}</span>{amt_html}</div>'
    
    cal_html += "</div></div>"
    st.components.v1.html(cal_html, height=320)
    st.divider()
    st.link_button("🗑️ 구글 시트에서 수정/삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

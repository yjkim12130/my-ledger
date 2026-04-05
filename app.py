import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

# 1. 페이지 설정 및 기본 정보
st.set_page_config(page_title="우리집 가계부", layout="centered")

SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"
this_year, this_month, today_day = 2026, 4, 6  # 기준 날짜 (2026년 4월 6일)

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

# 모드 선택 탭
menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# ==========================================
# 탭 1: 소비 입력
# ==========================================
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    # 영준님의 구글 폼 임베드 링크
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=600, scrolling=True)

# ==========================================
# 탭 2: 실시간 대시보드 (시각화 고도화 핵심)
# ==========================================
with menu[1]:
    # 이번 달 데이터 필터링 (2026년 4월 기준)
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    # 일할 계산 비율
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days_in_month  # 오늘까지 한 달 중 경과률

    # 카테고리별 합계 계산 및 병합
    summary_data = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    final_summary = pd.merge(targets_df, summary_data, left_on="Category", right_on="Category(big)", how="left").fillna(0)

    st.subheader("📊 카테고리별 지출 요약")
    st.bar_chart(final_summary.set_index("Category")["Amount"])

    st.divider()
    st.subheader(f"🎯 오늘({this_month}/{today_day}) 기준 소비 성적표")
    st.caption("💡 아래 바 그래프 설명: "
               "<span style='color:#ccc;'>회색(전체예산)</span>, "
               "<span style='color:#1E90FF; font-weight:bold;'>파란색(오늘까지 권장예산)</span>, "
               "<span style='color:#28a745; font-weight:bold;'>초록/빨강(실제지출)</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    total_spent = 0
    for i, (_, row) in enumerate(final_summary.iterrows(), start=1):
        cat_name, goal, actual = row["Category"], row["Monthly_Goal"], row["Amount"]
        total_spent += actual
        
        cum_target = goal * elapsed_ratio  # 오늘까지의 누적 권장 예산
        diff = cum_target - actual        # 권장 예산 대비 차액 (양수: 여유, 음수: 초과)
        spent_percent_of_goal = int((actual / goal) * 100) if goal > 0 else 0

        # UI 색상 및 문구 분기 로직
        if diff < 0:
            bar_color = "#ff4b4b"       # 실제 지출 바: 빨강 (과소비)
            bg_color = "#ffebee"        # 우측 카드 배경: 연빨강
            text_color = "#c62828"      # 우측 카드 텍스트: 딥레드
            status_text = f"계획대비 과소비중({spent_percent_of_goal}% 사용중, {int(abs(diff)):,} 초과)"
        else:
            bar_color = "#28a745"       # 실제 지출 바: 초록 (절약)
            bg_color = "#e8f5e9"        # 우측 카드 배경: 연초록
            text_color = "#2e7d32"      # 우측 카드 텍스트: 딥그린
            status_text = f"계획대비 절약중({spent_percent_of_goal}% 사용중, {int(diff):,} 여유)"

        # 그래프 계산용 비율 (0~100 사이로 클리핑)
        actual_progress = min(max(float(actual / goal), 0.0), 1.0) * 100 if goal > 0 else 0
        target_progress = min(max(float(cum_target / goal), 0.0), 1.0) * 100 if goal > 0 else 0

        # 모바일 가독성을 위한 컬럼 비율 조정
        col1, col2 = st.columns([1.0, 2.0]) 

        with col1:
            st.markdown(f"<span style='font-size: 1.1em; font-weight: bold;'>{i}. {cat_name}</span>", unsafe_allow_html=True)
            st.caption(f"예산: {int(goal):,}")
            
        with col2:
            # 💡 [핵심] 듀얼 프로그레스 바 + 우측 정보 카드 통합 HTML/CSS
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 20px;">
                    <div style="flex: 1; position: relative; background-color: #f0f2f6; border-radius: 4px; height: 18px;">
                        <div style="position: absolute; left: 0; top: 0; width: {target_progress}%; background-color: #1E90FF; height: 100%; border-radius: 4px; opacity: 0.6;"></div>
                        
                        <div style="position: absolute; left: 0; top: 0; width: {actual_progress}%; background-color: {bar_color}; height: 100%; border-radius: 4px; display: flex; align-items: center; justify-content: flex-end;">
                            <span style="color: white; font-size: 0.7em; font-weight: bold; margin-right: 3px; white-space: nowrap;">
                                {int(actual/1000):,}k
                            </span>
                        </div>
                    </div>
                    
                    <div style="width: 140px; background-color: {bg_color}; padding: 6px; border-radius: 6px; border: 1px solid {bar_color}; text-align: center; display: flex; flex-direction: column; justify-content: center; height: 45px;">
                        <span style="font-size: 0.9em; font-weight: bold; color: #111;">{int(actual):,}원</span>
                        <span style="font-size: 0.65em; font-weight: bold; color: {text_color}; white-space: nowrap; margin-top: 1px;">
                            {status_text}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # st.markdown("<br><br>", unsafe_allow_html=True) # 중복 개행 제거

    st.divider()
    st.subheader(f"{this_month}월 총 지출: {int(total_spent):,} 원")

# ==========================================
# 탭 3: 전체 내역 및 관리
# ==========================================
with menu[2]:
    st.subheader("📜 이번 달 소비 상세 내역")
    
    # 데이터 가공 (this_year, this_month 기준)
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    # 7대 범례 표 출력 포맷팅
    table_view = display_df.copy()
    table_view['Date'] = table_view['Date'].dt.strftime('%Y-%m-%d')
    cols = ["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]
    st.dataframe(table_view[cols], use_container_width=True, hide_index=True)

    st.divider()

    # 절대 깨지지 않는 모바일 7열 캘린더
    st.subheader(f"🗓️ {this_month}월 소비 캘린더")
    st.caption("단위: 만원 (예: 9.3만)")

    # 일자별 합계 데이터 준비
    daily_totals = display_df.groupby(display_df['Date'].dt.day)['Amount'].sum()
    month_cal = calendar.monthcalendar(this_year, this_month)
    days = ["월", "화", "수", "목", "금", "토", "일"]

    # CSS Grid 캘린더 HTML
    cal_html = f"""
    <style>
        .cal-container {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; width: 100%; }}
        .cal-header {{ font-weight: bold; font-size: 0.7em; padding: 5px 0; background: #f0f2f6; border-radius: 3px; text-align: center; }}
        .cal-day {{ border: 1px solid #f0f2f6; border-radius: 3px; min-height: 40px; text-align: center; padding: 4px 0; background: white; display: flex; flex-direction: column; justify-content: center; }}
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
                
                # 만원 단위 포맷팅 (9.3만)
                if amt > 0:
                    amt_text = f"{amt / 10000:.1f}만".replace(".0만", "만")
                    amt_html = f'<span class="amt">{amt_text}</span>'
                else:
                    amt_html = '<span class="empty-amt">-</span>'
                
                cal_html += f'<div class="cal-day {is_today}"><span class="day-num">{day}</span>{amt_html}</div>'
    
    cal_html += "</div>"
    st.markdown(cal_html, unsafe_allow_html=True)

    st.divider()
    # 구글 시트 직접 링크 버튼
    st.link_button("🗑️ 구글 시트에서 수정/삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

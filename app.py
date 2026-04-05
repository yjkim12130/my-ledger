import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

# 1. 페이지 설정 및 기본 정보
st.set_page_config(page_title="우리집 가계부", layout="centered")

SHEET_ID = "19wGTMH2bt6SZPQ5tbbwcOPVoCZYti1QTc7uYsPjty2w"
# 💡 하드코딩된 오늘 날짜 (2026년 4월 6일)
this_year, this_month, today_day = 2026, 4, 6

# 구글 시트 연결 함수
def get_csv_url(sheet_id, sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data(ttl=60) # 1분마다 데이터 갱신
def load_data():
    try:
        targets = pd.read_csv(get_csv_url(SHEET_ID, "Target"))
        actuals = pd.read_csv(get_csv_url(SHEET_ID, "Data"))
        # 공백 제거 및 데이터 타입 최적화
        targets['Category'] = targets['Category'].astype(str).str.strip()
        actuals['Category(big)'] = actuals['Category(big)'].astype(str).str.strip()
        actuals['Date'] = pd.to_datetime(actuals['Date'], errors='coerce')
        return targets, actuals
    except Exception as e:
        st.error("데이터 로드 중 오류가 발생했습니다. 시트 설정을 확인하세요.")
        st.stop()

targets_df, actuals_df = load_data()

st.title("💸 우리집 가계부")

# 탭 구성
menu = st.tabs(["💰 소비 입력", "📊 실시간 대시보드", "📜 전체 내역 및 관리"])

# ==========================================
# 탭 1: 소비 입력 (Google Forms 임베드)
# ==========================================
with menu[0]:
    st.subheader("💰 빠른 소비 입력")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScygQkv9LyeZmUMSE3kKdW1Nba2GvZ3UM3QlxKaHnO-wc8NFw/viewform?embedded=true"
    st.components.v1.iframe(form_url, height=600, scrolling=True)

# ==========================================
# 탭 2: 실시간 대시보드 (시각화 고도화 핵심)
# ==========================================
with menu[1]:
    # 이번 달 데이터 필터링
    current_actuals = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ]
    
    # 일할 계산 비율 (오늘/전체일수)
    total_days_in_month = calendar.monthrange(this_year, this_month)[1]
    elapsed_ratio = today_day / total_days_in_month

    # 카테고리별 합계 계산 및 병합 (Target 시트 기준)
    summary_data = current_actuals.groupby("Category(big)")["Amount"].sum().reset_index()
    final_summary = pd.merge(targets_df, summary_data, left_on="Category", right_on="Category(big)", how="left").fillna(0)

    st.subheader("📊 카테고리별 사용금액 (전체)")
    # 기본 바 차트 출력
    st.bar_chart(final_summary.set_index("Category")["Amount"])

    st.divider()
    
    st.subheader(f"🎯 오늘({this_month}/{today_day}) 기준 소비 성적표")
    # 💡 캘린더 범례 추가
    st.caption("💡 바 그래프 설명: "
               "<span style='color:#ccc;'>회색(전체예산)</span>, "
               "<span style='color:#28a745; font-weight:bold;'>초록색(안정지출)</span>, "
               "<span style='color:#ff4b4b; font-weight:bold;'>빨간색(초과지출)</span>, "
               "<span style='color:#007bff; font-weight:bold;'>파란선(오늘권장선)</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    total_spent = 0
    for i, (_, row) in enumerate(final_summary.iterrows(), start=1):
        cat_name, goal, actual = row["Category"], row["Monthly_Goal"], row["Amount"]
        total_spent += actual
        
        # 권장 예산 및 차액 계산
        cum_target = goal * elapsed_ratio
        diff = cum_target - actual

        # 💡 [시각화 핵심] 듀얼 프로그레스 바 연산 로직
        progress_goal = 100 # 회색 바탕 바 (전체 예산)

        if goal > 0:
            # 1. 실제 지출 비율 (예산 대비 %)
            actual_ratio = (actual / goal) * 100
            # 2. 오늘 권장 예산 비율 (예산 대비 %)
            target_ratio = (cum_target / goal) * 100
            
            if actual <= cum_target:
                # 💡 안정 상태: 초록색 바만 표시
                green_bar_width = min(actual_ratio, 100) # 예산 내에서 차오름
                red_bar_width = 0
                status_color = "#28a745" # 초록 (카드 테두리용)
                bg_color = "#e8f5e9"    # 연초록 (카드 배경용)
                text_color = "#2e7d32"  # 딥그린 (텍스트용)
                status_text = f"{int(diff):,} 여유"
            else:
                # 💡 초과 상태: 초록색 바(권장예산까지) + 빨간색 바(초과분) 스택
                green_bar_width = min(target_ratio, 100) # 권장예산까지는 초록
                # 초과한 금액만큼만 빨간색으로 표시 (너무 길어지면 화면 뚫으므로 최대 120% clip)
                red_bar_width = min(max(actual_ratio - target_ratio, 0.0), 120 - target_ratio) 
                status_color = "#ff4b4b" # 빨강 (카드 테두리용)
                bg_color = "#ffebee"    # 연빨강 (카드 배경용)
                text_color = "#c62828"  # 딥레드 (텍스트용)
                status_text = f"{int(abs(diff)):,} 초과"
        else:
            # 예산이 0원인 카테고리 예외처리
            green_bar_width = red_bar_width = target_ratio = 0
            status_color, bg_color, text_color, status_text = "#ccc", "#f0f2f6", "#555", "예산 미설정"

        col1, col2 = st.columns([1.1, 1.9]) # 모바일 최적화 비율
        with col1:
            st.markdown(f"<span style='font-size: 1.1em; font-weight: bold;'>{i}. {cat_name}</span>", unsafe_allow_html=True)
            st.caption(f"예산: {int(goal):,} / 권장: {int(cum_target):,}")
            
        with col2:
            # 💡 [핵심] HTML/CSS 기반의 커스텀 듀얼 스택형 프로그레스 바 구현
            st.markdown(f"""
                <div style="width: 100%; display: flex; align-items: center; gap: 8px;">
                    <div style="flex: 1; position: relative; background-color: #f0f2f6; border-radius: 4px; height: 16px; overflow: visible;">
                        <div style="position: absolute; left: 0; top: 0; width: {green_bar_width}%; background-color: #28a745; height: 100%; border-radius: 4px;"></div>
                        
                        <div style="position: absolute; left: {green_bar_width}%; top: 0; width: {red_bar_width}%; background-color: #ff4b4b; height: 100%; border-radius: 4px;"></div>
                        
                        <div style="position: absolute; left: {target_ratio}%; top: -2px; width: 2px; background-color: #007bff; height: 20px; z-index: 10; border-radius: 1px;"></div>
                    </div>
                    
                    <div style="width: 140px; background-color: {bg_color}; padding: 8px 6px; border-radius: 6px; border: 1px solid {status_color}; text-align: center; display: flex; flex-direction: column; justify-content: center; height: 40px; flex-shrink: 0;">
                        <span style="font-size: 1.05em; font-weight: bold; color: #111;">{int(actual):,}원 지출</span>
                        <span style="font-size: 0.75em; font-weight: bold; color: {text_color}; white-space: nowrap; margin-top: 2px;">
                            계획대비 {status_text}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)

    st.divider()
    st.subheader(f"{this_month}월 총 지출: {int(total_spent):,} 원")

# ==========================================
# 탭 3: 전체 내역 및 관리 (표 & 캘린더)
# ==========================================
with menu[2]:
    st.subheader("📜 이번 달 소비 상세 내역")
    
    # 데이터 가공
    display_df = actuals_df[
        (actuals_df['Date'].dt.year == this_year) & 
        (actuals_df['Date'].dt.month == this_month)
    ].copy()
    display_df = display_df.sort_values(by="Date")
    display_df["누적 총액"] = display_df["Amount"].cumsum()
    
    # 테이블 출력용 데이터 가공 (원본 Date 보존)
    table_df = display_df.copy()
    table_df['Date'] = table_view['Date'].dt.strftime('%Y-%m-%d')
    cols = ["Date", "Category(big)", "Category(small)", "Amount", "누적 총액", "Card", "Installment"]
    # hide_index=True로 스트림릿 자체 인덱스 숨김
    st.dataframe(table_view[cols], use_container_width=True, hide_index=True)

    st.divider()

    # 절대 깨지지 않는 모바일 7열 캘린더
    st.subheader(f"🗓️ {this_month}월 소비 캘린더")
    st.caption("단위: 만원 (예: 9.3만)")

    # 일자별 합계 데이터 준비
    daily_totals = display_df.groupby(display_df['Date'].dt.day)['Amount'].sum()

    # calendar 라이브러리를 활용해 한 달 달력 그리드 데이터 준비
    month_cal = calendar.monthcalendar(this_year, this_month)
    days = ["월", "화", "수", "목", "금", "토", "일"]
    
    # 💡 st.columns(7) 대신 HTML/CSS Grid를 사용하여 모바일에서도 레이아웃 고정
    cal_html = f"""
    <style>
        .calendar-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2px;
            text-align: center;
            font-family: sans-serif;
            width: 100%;
        }}
        .calendar-header {{
            font-weight: bold;
            padding: 5px 0;
            background-color: #f0f2f6;
            border-radius: 3px;
            font-size: 0.7em;
        }}
        .calendar-day {{
            padding: 4px 0;
            border: 1px solid #f0f2f6;
            border-radius: 3px;
            min-height: 40px;
            background-color: #ffffff;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        .today-mark {{
            background-color: #e6f3ff;
            font-weight: bold;
            border: 1px solid #007bff;
        }}
        .spent-text {{
            color: #ff4b4b;
            font-size: 0.65em;
            font-weight: bold;
            white-space: nowrap;
            margin-top: 1px;
        }}
        .zero-text {{
            color: #ccc;
            font-size: 0.65em;
            margin-top: 1px;
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
                    # .0만으로 끝나는 경우 소수점 제거 (예: 10.0만 -> 10만)
                    amount_text = amount_text.replace(".0만", "만")
                    display_text = f'<span class="spent-text">{amount_text}</span>'
                else:
                    display_text = '<span class="zero-text">-</span>'
                
                cal_html += f"""
                <div class="calendar-day {is_today}">
                    <span style="font-size: 0.75em; line-height: 1;">{day}</span>
                    {display_text}
                </div>
                """
    
    cal_html += "</div>"
    st.markdown(cal_html, unsafe_allow_html=True)

    st.divider()
    # 구글 시트 직접 링크 버튼
    st.link_button("🗑️ 구글 시트에서 수정/삭제하기", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

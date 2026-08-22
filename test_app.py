"""app.py 점검.

구글시트를 실제로 부르지 않도록 pandas.read_csv 를 표본 데이터로 바꿔 끼운다.
"""

import calendar
from datetime import datetime, timedelta

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

NOW_KST = datetime.utcnow() + timedelta(hours=9)
THIS_YEAR, THIS_MONTH = NOW_KST.year, NOW_KST.month

TARGETS = pd.DataFrame(
    [["교통비", 100000], ["운동비", 50000]], columns=["Category", "Monthly_Goal"]
)


def month_back(delta):
    index = THIS_YEAR * 12 + (THIS_MONTH - 1) - delta
    return index // 12, index % 12 + 1


def sheet_date(period, day):
    year, month = period
    return f"{month}/{day}/{year}"


# 이번 달 2건(합 90,000) / 지난달 1건(30,000) / 두 달 전 1건(15,000)
DATA = pd.DataFrame(
    [
        [sheet_date(month_back(0), 1), "교통비", "지하철", "영준 하나카드", 20000, "일시불"],
        [sheet_date(month_back(0), 2), "운동비", "헬스", "윤진 롯데카드", 70000, "일시불"],
        [sheet_date(month_back(1), 5), "교통비", "택시", "윤진 국민카드", 30000, "일시불"],
        [sheet_date(month_back(2), 9), "운동비", "필라테스", "영준 현대카드", 15000, "일시불"],
    ],
    columns=["소비 날짜", "소비 내역(분류)", "Category(small)", "사용 카드", "액수", "일시불,할부 여부"],
)


@pytest.fixture
def sheet(monkeypatch):
    def fake_read_csv(url, *args, **kwargs):
        return TARGETS.copy() if "Target" in url else DATA.copy()

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def run_app():
    app = AppTest.from_file("app.py", default_timeout=60)
    app.run()
    assert not app.exception, app.exception
    return app


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


def selectbox(app, label):
    return next(widget for widget in app.selectbox if widget.label == label)


def subheaders(app):
    return [element.value for element in app.subheader]


def show_month(app, year, month):
    app.session_state["sel_year"] = year
    app.session_state["sel_month"] = month
    app.run()
    return app


# --- 기존 화면은 그대로 ---


def test_the_three_tabs_are_unchanged(sheet):
    app = run_app()

    assert [tab.label for tab in app.tabs] == [
        "💰 소비 입력",
        "📊 실시간 대시보드",
        "📜 전체 내역 및 관리",
    ]


def test_the_refresh_button_is_still_there(sheet):
    app = run_app()

    assert button(app, "🔄 새로고침") is not None


def test_dashboard_tab_still_reports_this_month(sheet):
    app = run_app()

    assert f"{THIS_MONTH}월 총 지출: 90,000 원" in subheaders(app)


def test_dashboard_tab_ignores_the_month_picked_in_the_third_tab(sheet):
    app = show_month(run_app(), *month_back(1))

    assert f"{THIS_MONTH}월 총 지출: 90,000 원" in subheaders(app)


# --- 개선 3: 세 번째 탭에서 과거 월 조회 ---


def test_third_tab_opens_on_the_current_month(sheet):
    app = run_app()

    assert app.session_state["sel_year"] == THIS_YEAR
    assert app.session_state["sel_month"] == THIS_MONTH
    assert len(app.dataframe[0].value) == 2


def test_third_tab_shows_the_details_of_a_past_month(sheet):
    app = show_month(run_app(), *month_back(1))

    details = app.dataframe[0].value

    assert list(details["액수"]) == [30000]


def test_third_tab_headings_follow_the_selected_month(sheet):
    year, month = month_back(1)

    app = show_month(run_app(), year, month)

    assert f"📜 {year}년 {month}월 소비 상세 내역" in subheaders(app)
    assert f"🗓️ {year}년 {month}월 소비 캘린더" in subheaders(app)


def test_third_tab_switches_between_past_months(sheet):
    app = run_app()

    assert list(show_month(app, *month_back(2)).dataframe[0].value["액수"]) == [15000]
    assert list(show_month(app, *month_back(1)).dataframe[0].value["액수"]) == [30000]


def test_previous_month_button_steps_back_one_month(sheet):
    app = show_month(run_app(), 2026, 1)

    button(app, "◀").click().run()

    assert app.session_state["sel_year"] == 2025
    assert app.session_state["sel_month"] == 12


def test_next_month_button_steps_forward_one_month(sheet):
    app = show_month(run_app(), 2026, 12)

    button(app, "▶").click().run()

    assert app.session_state["sel_year"] == 2027
    assert app.session_state["sel_month"] == 1


def test_a_month_without_records_shows_an_empty_table_instead_of_crashing(sheet):
    기록된_달 = {month_back(delta)[1] for delta in (0, 1, 2)}
    빈_달 = next(m for m in range(1, 13) if m not in 기록된_달)

    app = show_month(run_app(), THIS_YEAR, 빈_달)

    assert app.dataframe[0].value.empty


def test_the_running_total_column_is_kept(sheet):
    app = run_app()

    assert list(app.dataframe[0].value["누적 총액"]) == [20000, 90000]


def test_year_dropdown_offers_the_years_that_have_records(sheet):
    app = run_app()

    assert f"{THIS_YEAR}년" in selectbox(app, "연도").options


def test_third_tab_shows_the_total_for_the_selected_month(sheet):
    app = run_app()

    assert f"💰 {THIS_YEAR}년 {THIS_MONTH}월 총 지출: 90,000 원" in subheaders(app)


def test_third_tab_total_follows_the_month_you_pick(sheet):
    year, month = month_back(1)

    app = show_month(run_app(), year, month)

    assert f"💰 {year}년 {month}월 총 지출: 30,000 원" in subheaders(app)


def test_third_tab_total_is_zero_for_a_month_without_records(sheet):
    기록된_달 = {month_back(delta)[1] for delta in (0, 1, 2)}
    빈_달 = next(m for m in range(1, 13) if m not in 기록된_달)

    app = show_month(run_app(), THIS_YEAR, 빈_달)

    assert f"💰 {THIS_YEAR}년 {빈_달}월 총 지출: 0 원" in subheaders(app)

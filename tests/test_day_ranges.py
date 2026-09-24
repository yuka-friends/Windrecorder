import datetime as dt

import pandas as pd
import pytest


@pytest.mark.parametrize("selected", [dt.date(2023, 12, 31), dt.date(2024, 2, 29), dt.date(2024, 1, 31)])
@pytest.mark.parametrize("minutes", [0, 30, 90, 360])
def test_day_bounds_are_one_full_day_across_month_and_year(monkeypatch, selected, minutes):
    from windrecorder import utils
    from windrecorder.config import config

    monkeypatch.setattr(config, "day_begin_minutes", minutes)
    start = dt.datetime.combine(selected, dt.time()) + dt.timedelta(minutes=minutes)
    for value in (selected, dt.datetime.combine(selected, dt.time(12))):
        assert utils.get_datetime_in_day_range_pole_by_config_day_begin(value, "start") == start
        assert utils.get_datetime_in_day_range_pole_by_config_day_begin(value, "end") == start + dt.timedelta(
            days=1, seconds=-1
        )


def test_oneday_date_and_datetime_have_identical_cross_year_search(db, make_rows, monkeypatch):
    from windrecorder import oneday
    from windrecorder.config import config

    monkeypatch.setattr(oneday, "db_manager", db)
    monkeypatch.setattr(config, "day_begin_minutes", 90)
    db.db_add_dataframe_to_db_process(
        make_rows("2023-12-31_01-29-59", "2023-12-31_01-30-00", "2024-01-01_01-29-59", "2024-01-01_01-30-00")
    )
    by_date = oneday.OneDay().search_day_data(dt.date(2023, 12, 31))
    by_datetime = oneday.OneDay().search_day_data(dt.datetime(2023, 12, 31, 12))
    assert len(by_date) == 2
    pd.testing.assert_frame_equal(by_date, by_datetime)


def test_activity_statistics_do_not_mutate_source_rows(make_rows):
    from windrecorder.record_wintitle import count_all_page_times_by_raw_dataframe

    source = make_rows("2024-01-01_12-00-10", "2024-01-01_12-00-00", title="(12) Editor")
    original = source.copy(deep=True)
    assert count_all_page_times_by_raw_dataframe(source) == {"Editor": 10}
    pd.testing.assert_frame_equal(source, original)


def test_empty_library_footer_has_no_invalid_timestamp(db, monkeypatch):
    from windrecorder import state

    monkeypatch.setattr(state, "db_manager", db)
    result = state.get_footer_state_data()
    assert result["first_record_time_str"] == "—"
    assert result["latest_record_time_str"] == "—"
    assert result["latest_db_records_num"] == 0

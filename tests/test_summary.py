import datetime as dt
import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def summary(db, monkeypatch):
    from windrecorder import state

    monkeypatch.setattr(state, "db_manager", db)
    return state


def test_absent_month_has_same_search_columns_as_empty_existing_month(db):
    start, end = dt.datetime(2024, 2, 1), dt.datetime(2024, 2, 29, 23, 59, 59)
    missing, count, pages = db.db_search_data("", start, end)
    assert (count, pages) == (0, 0)
    db.db_initialize(str(Path(db.db_path) / "default_2024-02_wind.db"))
    empty, _, _ = db.db_search_data("", start, end)
    assert list(missing.columns) == list(empty.columns)
    assert {"videofile_time", "thumbnail", "ocr_text", "win_title"} <= set(missing.columns)


@pytest.mark.parametrize(
    "method,rows,columns",
    [
        ("get_month_data_overview", 29, ["day", "data_count"]),
        ("get_month_day_overview_scatter", 29 * 24, ["day", "hours", "data_count"]),
        ("get_year_data_overview", 12, ["month", "data_count"]),
        ("get_year_data_overview_scatter", 366, ["month", "day", "data_count"]),
    ],
)
def test_absent_period_returns_complete_zero_calendar(summary, method, rows, columns):
    frame = getattr(summary, method)(dt.datetime(2024, 2, 15))
    assert list(frame.columns) == columns
    assert len(frame) == rows
    assert frame.data_count.sum() == 0


def test_midnight_hour_end_of_month_and_december_are_counted_once(summary, db, make_rows):
    db.db_add_dataframe_to_db_process(
        make_rows(
            "2023-12-31_23-59-59",
            "2024-01-01_00-00-00",
            "2024-01-01_00-59-59",
            "2024-01-01_01-00-00",
            "2024-01-31_23-59-59",
            "2024-02-01_00-00-00",
            "2024-02-29_23-59-59",
            "2024-12-31_23-59-59",
            "2025-01-01_00-00-00",
        )
    )
    month = summary.get_month_day_overview_scatter(dt.datetime(2024, 1, 1))
    assert month.data_count.sum() == 4
    assert month.query("day == 1 and hours == 1").data_count.item() == 2
    assert month.query("day == 1 and hours == 2").data_count.item() == 1
    assert month.query("day == 31 and hours == 24").data_count.item() == 1
    year = summary.get_year_data_overview_scatter(dt.datetime(2024, 1, 1))
    assert year.data_count.sum() == 7
    assert year.query("month == 12 and day == 31").data_count.item() == 1
    assert summary.get_year_data_overview(dt.datetime(2024, 1, 1)).data_count.sum() == 7
    assert summary.get_month_data_overview(dt.datetime(2024, 1, 1)).data_count.sum() == 4


def test_empty_period_consumers_do_not_crash(db, summary, monkeypatch, workspace):
    from windrecorder import record_wintitle, wordcloud
    from windrecorder.utils import datetime_to_seconds

    monkeypatch.setattr(record_wintitle, "db_manager", db)
    monkeypatch.setattr(wordcloud, "db_manager", db)
    start, end = dt.datetime(2024, 2, 1), dt.datetime(2024, 2, 29, 23, 59, 59)
    assert db.db_get_closest_row_around_by_datetime(start).empty
    assert all(pd.isna(value) for value in db.db_get_time_min_and_max_through_datetime(start))
    assert db.db_get_day_thumbnail_by_distributeavg(start, end, 10) is None
    assert db.db_get_day_thumbnail_by_timeavg(start, end, 10) is None
    assert not summary.generate_lightbox_from_datetime_range(start, end, img_saved_folder=str(workspace / "images"))
    assert record_wintitle.get_wintitle_stat_dict_in_month(start) == {}
    text = wordcloud.get_month_ocr_result(datetime_to_seconds(start), str(workspace / "new-cache/ocr.txt"))
    assert Path(text).read_text(encoding="utf-8") == ""


def test_record_bounds_skip_empty_shards_and_allow_empty_library(db, make_rows):
    from windrecorder.utils import dtstr_to_seconds

    assert db.db_first_earliest_record_time() is None
    assert db.db_latest_record_time() is None
    db.db_initialize(str(Path(db.db_path) / "default_2020-01_wind.db"))
    db.db_add_dataframe_to_db_process(make_rows("2024-02-29_12-00-00"))
    assert db.db_first_earliest_record_time() == dtstr_to_seconds("2024-02-29_12-00-00")
    assert db.db_latest_record_time() == dtstr_to_seconds("2024-02-29_12-00-00")


def test_summary_counts_read_legacy_table_without_schema_or_rowid_changes(summary, db):
    from windrecorder.utils import datetime_to_seconds

    path = Path(db.db_path) / "default_2020-02_wind.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE video_text (videofile_time INT, ocr_text TEXT, thumbnail TEXT)")
        conn.execute(
            "INSERT INTO video_text(rowid, videofile_time, ocr_text) VALUES (42, ?, 'old')",
            [datetime_to_seconds(dt.datetime(2020, 2, 29, 23, 59, 59))],
        )
    before = path.read_bytes()
    result = summary.get_month_day_overview_scatter(dt.datetime(2020, 2, 1))
    assert result.data_count.sum() == 1
    assert path.read_bytes() == before


def test_summary_cache_refreshes_after_backfill_and_rebuilds_bad_cache(summary, db, make_rows, workspace):
    from windrecorder.config import config

    selected = dt.datetime(2024, 2, 1)
    old_cache = Path(config.date_state_dir_ud) / "2024-02_month_data_state.csv"
    old_cache.parent.mkdir(parents=True, exist_ok=True)
    old_cache.write_text("legacy CSV remains untouched")
    assert summary.get_cached_calendar_overview(selected, "month").data_count.sum() == 0
    db.db_add_dataframe_to_db_process(make_rows("2024-02-29_23-59-59"))
    result = summary.get_cached_calendar_overview(selected, "month")
    assert result.data_count.sum() == 1
    pd.testing.assert_frame_equal(result, summary.get_cached_calendar_overview(selected, "month"))
    cache = next(old_cache.parent.glob("2024-02*calendar*.json"))
    cache.write_text('{"partial":', encoding="utf-8")
    assert summary.get_cached_calendar_overview(selected, "month").data_count.sum() == 1
    assert json.loads(cache.read_text(encoding="utf-8"))
    assert old_cache.read_text() == "legacy CSV remains untouched"


def test_summary_cache_hit_avoids_scanning_database(summary, db, monkeypatch):
    selected = dt.datetime(2024, 2, 1)
    expected = summary.get_cached_calendar_overview(selected, "month")

    def unexpected(*args):
        pytest.fail("Unchanged source should reuse the validated cache")

    monkeypatch.setattr(db, "db_get_record_counts", unexpected)
    pd.testing.assert_frame_equal(expected, summary.get_cached_calendar_overview(selected, "month"))


def test_summary_cache_sees_wal_commit_and_deletion(summary, db, make_rows):
    selected = dt.datetime(2024, 2, 1)
    db.db_add_dataframe_to_db_process(make_rows("2024-02-29_23-59-59"))
    path = Path(db.db_path) / "default_2024-02_wind.db"
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        assert summary.get_cached_calendar_overview(selected, "month").data_count.sum() == 1
        conn.execute("INSERT INTO video_text SELECT * FROM video_text")
        conn.commit()
        assert summary.get_cached_calendar_overview(selected, "month").data_count.sum() == 2
        conn.execute("DELETE FROM video_text")
        conn.commit()
        assert summary.get_cached_calendar_overview(selected, "month").data_count.sum() == 0
    finally:
        conn.close()


@pytest.fixture
def summary_page(summary, db, monkeypatch):
    from windrecorder import record_wintitle
    from windrecorder.config import config
    from windrecorder.ui import state as ui_state

    monkeypatch.setattr(ui_state, "db_manager", db)
    monkeypatch.setattr(record_wintitle, "db_manager", db)
    monkeypatch.setattr(config, "enable_ai_day_poem", False)
    monkeypatch.setattr(config, "enable_ai_extract_tag", False)
    from streamlit.testing.v1 import AppTest

    return AppTest.from_string("from windrecorder.ui.state import render\nrender()", default_timeout=45)


def test_summary_page_switches_to_empty_month_and_back(summary_page, db, make_rows):
    db.db_add_dataframe_to_db_process(make_rows("2024-01-01_00-00-00", "2024-12-31_23-59-59"))
    app = summary_page.run()
    assert not app.exception
    assert app.session_state.df_month_stat.data_count.sum() == 1
    app.number_input[1].set_value(6).run()
    assert not app.exception
    assert app.session_state.df_month_stat.data_count.sum() == 0
    assert app.session_state.df_year_stat.data_count.sum() == 2
    assert all(button.disabled for button in app.button)
    assert len(app.info) >= 1
    app.number_input[1].set_value(1).run()
    assert not app.exception
    assert app.session_state.df_month_stat.data_count.sum() == 1
    assert all(not button.disabled for button in app.button)


def test_summary_page_accepts_empty_library(summary_page):
    app = summary_page.run()
    assert not app.exception
    assert len(app.info) == 1
    assert not app.number_input

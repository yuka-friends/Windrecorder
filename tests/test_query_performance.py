import datetime as dt
import sqlite3
from pathlib import Path

import pandas as pd


def test_deferred_search_pages_match_full_results_across_months(db, make_rows):
    from windrecorder.config import config

    rows = make_rows("2024-01-31_23-59-59", "2024-02-01_00-00-00", "2024-02-02_12-00-00")
    rows["thumbnail"] = "x" * 100_000
    db.db_add_dataframe_to_db_process(rows)
    start, end = dt.datetime(2024, 1, 1), dt.datetime(2024, 3, 1)
    full, count, pages = db.db_search_data("hello", start, end)
    refs, ref_count, ref_pages = db.db_search_data("hello", start, end, defer_payload=True)
    assert (ref_count, ref_pages) == (count, pages)
    assert refs.memory_usage(deep=True).sum() < full.memory_usage(deep=True).sum() / 100
    db.db_max_page_result = 2
    materialized = pd.concat([db.db_search_data_page_turner(refs, page) for page in (1, 2)], ignore_index=True)
    pd.testing.assert_frame_equal(full, materialized)
    assert db.db_search_data_page_turner(refs, 3).empty
    assert config.max_page_result > 0


def test_search_reads_committed_wal_without_copying_month(db, make_rows, monkeypatch):
    path = Path(db.db_path) / "default_2024-01_wind.db"
    db.db_add_dataframe_to_db_process(make_rows("2024-01-01_12-00-00"))

    def no_snapshot(*args):
        raise AssertionError("Interactive search must not copy the database")

    monkeypatch.setattr(db, "get_temp_dbfilepath", no_snapshot)
    writer = sqlite3.connect(path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO video_text SELECT * FROM video_text")
        start, end = dt.datetime(2024, 1, 1), dt.datetime(2024, 2, 1)
        assert db.db_search_data("hello", start, end)[1] == 1
        writer.commit()
        assert db.db_search_data("hello", start, end)[1] == 2
    finally:
        writer.close()
    assert not list(path.parent.glob("*_TEMP_READ.db"))


def test_existing_time_index_is_additive_and_used_for_date_search(db, make_rows):
    path = Path(db.db_path) / "default_2024-01_wind.db"
    db.db_add_dataframe_to_db_process(make_rows("2024-01-01_12-00-00"))
    with sqlite3.connect(path) as conn:
        before = conn.execute("SELECT rowid, * FROM video_text").fetchall()
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM video_text WHERE videofile_time BETWEEN ? AND ?", (0, 1)
        ).fetchall()
    assert any("SEARCH" in str(row) and "INDEX" in str(row) for row in plan)
    db.db_update_table_product_routine()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT rowid, * FROM video_text").fetchall() == before


def test_deferred_page_skips_deleted_or_reused_record_id(db, make_rows):
    db.db_add_dataframe_to_db_process(make_rows("2024-01-01_12-00-00"))
    refs, _, _ = db.db_search_data("hello", dt.datetime(2024, 1, 1), dt.datetime(2024, 2, 1), defer_payload=True)
    path = Path(db.db_path) / "default_2024-01_wind.db"
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE video_text SET videofile_time=videofile_time+60")
    assert db.db_search_data_page_turner(refs, 1).empty


def test_vector_matches_keep_scores_attached_to_ids_and_skip_missing_rows(db, make_rows):
    db.db_add_dataframe_to_db_process(make_rows("2024-01-01_12-00-00", "2024-01-01_12-00-01", "2024-01-01_12-00-02"))
    result = db.db_get_rowid_and_similar_tuple_list_rows([(3, 0.9), (99, 0.8), (1, 0.7)], "default_2024-01_wind.db")
    assert result.videofile_name.tolist() == ["2024-01-01_12-00-02.mp4", "2024-01-01_12-00-00.mp4"]
    assert result.probs.tolist() == [0.9, 0.7]


def test_daily_histogram_preserves_half_open_buckets_and_original_rows(make_rows):
    from windrecorder.oneday import OneDay

    rows = make_rows("2024-01-01_00-00-00", "2024-01-01_00-05-59", "2024-01-01_00-06-00", "2024-01-01_00-18-00")
    original = rows.copy(deep=True)
    result = OneDay().get_day_statistic_chart_overview(rows, dt.datetime(2024, 1, 1), dt.datetime(2024, 1, 1, 0, 12))
    assert result.data.tolist() == [2, 1, 0]
    pd.testing.assert_frame_equal(rows, original)

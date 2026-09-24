import datetime as dt
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def search_db(db, make_rows):
    path = Path(db.db_path) / "default_2024-06_wind.db"
    for timestamp, text, title in [
        ("2024-06-01_12-00-00", "alpha beta", "editor"),
        ("2024-06-01_12-00-01", "alpha", "beta browser"),
        ("2024-06-01_12-00-02", "alpha", "editor"),
        ("2024-06-02_12-00-00", "alpha beta", "outside range"),
    ]:
        db.db_add_dataframe_to_db(str(path), make_rows(timestamp, text=text, title=title))
    db._db_filename_dict = db._init_db_filename_dict()
    return db


def search(db, keyword, exclude=""):
    return db.db_search_data(keyword, dt.datetime(2024, 6, 1), dt.datetime(2024, 6, 1, 23, 59, 59), exclude)


def test_empty_query_date_range_and_pagination(search_db):
    frame, count, pages = search(search_db, "")
    assert count == 3
    assert pages == 1
    search_db.db_max_page_result = 2
    assert len(search_db.db_search_data_page_turner(frame, 1)) == 2
    assert len(search_db.db_search_data_page_turner(frame, 2)) == 1


@pytest.mark.xfail(strict=True, reason="OR groups escape keyword AND and date constraints")
def test_all_keywords_and_date_constraints_apply(search_db):
    frame, count, _ = search(search_db, "alpha beta")
    assert count == 2
    assert set(frame.win_title) == {"editor", "beta browser"}


@pytest.mark.xfail(strict=True, reason="Excluded terms are interpolated into SQL")
def test_quotes_in_exclusion_are_literal(search_db):
    _, count, _ = search(search_db, "", "can't")
    assert count == 3


@pytest.mark.xfail(strict=True, reason="Copying SQLite file misses committed WAL data")
def test_read_snapshot_contains_committed_wal_rows(db):
    path = Path(db.db_path) / "default_2020-02_wind.db"
    with sqlite3.connect(path) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE video_text (ocr_text TEXT)")
        writer.execute("INSERT INTO video_text VALUES ('committed')")
        writer.commit()
        snapshot = db.get_temp_dbfilepath(str(path))
        with sqlite3.connect(snapshot) as reader:
            assert reader.execute("SELECT ocr_text FROM video_text").fetchall() == [("committed",)]
    writer.close()

import datetime as dt
import json
import sqlite3
from pathlib import Path

import pytest


def test_config_fills_missing_defaults_without_changing_user_values(workspace):
    from windrecorder import config as module

    path = Path(module.FILEPATH_CONFIG_USER)
    path.write_text(json.dumps({"lang": "ja", "user_name": "old_user"}), encoding="utf-8")
    result = module.get_config_json()
    assert result["lang"] == "ja"
    assert result["user_name"] == "old_user"
    assert "record_seconds" in result


@pytest.mark.xfail(strict=True, reason="Config upgrade drops fields belonging to extensions/future versions")
def test_config_preserves_unknown_fields(workspace):
    from windrecorder import config as module

    path = Path(module.FILEPATH_CONFIG_USER)
    path.write_text(json.dumps({"extension_settings": {"enabled": True}}), encoding="utf-8")
    assert module.get_config_json()["extension_settings"] == {"enabled": True}


@pytest.mark.parametrize("timestamp", ["1970-01-01_00-00-00", "2024-02-29_23-59-59", "2025-01-01_00-00-00"])
def test_persisted_wall_clock_timestamp_roundtrip(timestamp):
    from windrecorder import utils

    seconds = utils.dtstr_to_seconds(timestamp)
    assert utils.seconds_to_date(seconds) == timestamp
    assert utils.seconds_to_datetime(seconds) == dt.datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")
    assert utils.datetime_to_seconds(utils.seconds_to_datetime(seconds)) == seconds


def test_legacy_schema_upgrade_is_additive_and_repeatable(db):
    path = Path(db.db_path) / "default_2020-01_wind.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE video_text (videofile_name TEXT, picturefile_name TEXT, videofile_time INT, "
                     "ocr_text TEXT, is_videofile_exist BOOLEAN, is_picturefile_exist BOOLEAN, thumbnail TEXT)")
        conn.execute("INSERT INTO video_text VALUES ('old.mp4', '0.jpg', 123, '旧数据', 1, 0, 'image')")
    db._db_filename_dict = db._init_db_filename_dict()
    db.db_update_table_product_routine()
    db.db_update_table_product_routine()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT rowid, * FROM video_text").fetchone() == (
            1, "old.mp4", "0.jpg", 123, "旧数据", 1, 0, "image", None, None)


def test_dataframe_roundtrip_preserves_schema_and_rowids(db, make_rows):
    rows = make_rows("2024-06-01_12-00-00", "2024-06-01_12-00-01")
    path = Path(db.db_path) / "default_2024-06_wind.db"
    db.db_add_dataframe_to_db(str(path), rows)
    with sqlite3.connect(path) as conn:
        assert [c[1] for c in conn.execute("PRAGMA table_info(video_text)")] == list(rows.columns)
        assert conn.execute("SELECT rowid, ocr_text, deep_linking FROM video_text").fetchall() == [
            (1, "hello", "https://example.com"), (2, "hello", "https://example.com")]


@pytest.mark.xfail(strict=True, reason="Single-row batches are silently dropped")
def test_single_row_batch_is_saved(db, make_rows):
    rows = make_rows("2024-06-01_12-00-00")
    db.db_add_dataframe_to_db_process(rows)
    with sqlite3.connect(Path(db.db_path) / "default_2024-06_wind.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM video_text").fetchone()[0] == 1


@pytest.mark.xfail(strict=True, reason="Month split routes both halves to the older file and drops boundaries")
def test_batches_route_each_row_to_its_year_and_month(db, make_rows):
    rows = make_rows("2025-01-01_00-00-00", "2024-01-01_00-00-00", "2024-12-31_23-59-59")
    rows.index = [9, 3, 7]
    db.db_add_dataframe_to_db_process(rows)
    for timestamp in rows.videofile_name:
        with sqlite3.connect(Path(db.db_path) / f"default_{timestamp[:7]}_wind.db") as conn:
            assert conn.execute("SELECT videofile_name FROM video_text").fetchall() == [(timestamp,)]


def test_file_lock_rejects_contention_and_releases_on_exception(tmp_path):
    from windrecorder.exceptions import LockExistsException
    from windrecorder.lock import FileLock

    path = tmp_path / "lock"
    with pytest.raises(ValueError), FileLock(str(path), "123", timeout_s=None):
        assert path.read_text() == "123"
        with pytest.raises(LockExistsException):
            FileLock(str(path), timeout_s=None)
        raise ValueError("body failed")
    assert not path.exists()


@pytest.mark.xfail(strict=True, reason="Repeated release deletes a new owner's lock")
def test_repeated_release_does_not_remove_successor_lock(tmp_path):
    from windrecorder.lock import FileLock

    path = str(tmp_path / "lock")
    first = FileLock(path, timeout_s=None)
    first.release()
    with FileLock(path, "second", timeout_s=None):
        first.release()
        assert Path(path).read_text() == "second"

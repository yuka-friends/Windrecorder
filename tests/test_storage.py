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


def test_single_row_batch_is_saved(db, make_rows):
    rows = make_rows("2024-06-01_12-00-00")
    db.db_add_dataframe_to_db_process(rows)
    with sqlite3.connect(Path(db.db_path) / "default_2024-06_wind.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM video_text").fetchone()[0] == 1


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


def test_repeated_release_does_not_remove_successor_lock(tmp_path):
    from windrecorder.lock import FileLock

    path = str(tmp_path / "lock")
    first = FileLock(path, timeout_s=None)
    first.release()
    with FileLock(path, "second", timeout_s=None):
        first.release()
        assert Path(path).read_text() == "second"


def test_atomic_json_failure_preserves_original_and_cleans_temp(tmp_path, monkeypatch):
    from windrecorder import storage

    path = tmp_path / "settings.json"
    path.write_text('{"old": true}', encoding="utf-8")
    def fail(*args):
        raise PermissionError("file in use")
    monkeypatch.setattr(storage.os, "replace", fail)
    with pytest.raises(PermissionError):
        storage.atomic_write_json(path, {"new": True})
    assert json.loads(path.read_text()) == {"old": True}
    assert list(tmp_path.glob("settings.json.*.tmp")) == []


def test_config_reads_do_not_rewrite_and_single_setting_preserves_other_edits(workspace):
    from windrecorder import config as module

    path = Path(module.FILEPATH_CONFIG_USER)
    before = path.stat().st_mtime_ns
    module.get_config_json()
    assert path.stat().st_mtime_ns == before
    data = module.get_config_json()
    data["record_seconds"] = 123
    path.write_text(json.dumps(data), encoding="utf-8")
    current = module.Config(**module.get_config_json())
    current.record_seconds = 456  # stale unrelated in-memory state
    current.set_and_save_config("lang", "ja")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["record_seconds"] == 123
    assert saved["lang"] == "ja"
    assert "db_path_ud" not in saved


def test_legacy_migration_never_removes_small_current_database(workspace, monkeypatch):
    from windrecorder import upgrade_migration_routine as migration

    monkeypatch.setenv("APPDATA", str(workspace))
    monkeypatch.setattr(migration.utils, "is_file_already_in_startup", lambda name: False)
    current = workspace / "userdata" / "db"
    legacy = workspace / "db"
    current.mkdir()
    legacy.mkdir()
    (current / "small.db").write_bytes(b"current data")
    (legacy / "old.db").write_bytes(b"legacy data")
    old_config = workspace / "config"
    old_config.mkdir()
    (old_config / "custom.txt").write_text("custom")
    migration.main()
    migration.main()
    assert (current / "small.db").read_bytes() == b"current data"
    assert (legacy / "old.db").read_bytes() == b"legacy data"
    assert (old_config / "custom.txt").read_text() == "custom"


def test_database_discovery_ignores_backups_other_users_and_invalid_dates(db):
    for name in ["default_2020-03_wind.db", "default_2020-99_wind.db", "default2_2020-01_wind.db",
                 "default_2020-03_wind_TEMP_READ.db", "default_backup.db"]:
        (Path(db.db_path) / name).touch()
    names = db.get_db_filename_dict()
    assert "default_2020-03_wind.db" in names
    assert not any(name in names for name in ["default_2020-99_wind.db", "default_backup.db",
                                             "default2_2020-01_wind.db", "default_2020-03_wind_TEMP_READ.db"])


def test_database_manager_uses_its_own_directory_and_username(workspace):
    from windrecorder.db_manager import _DBManager

    manager = _DBManager(str(workspace / "separate"), 20, "another_user")
    assert len(manager.get_db_filename_dict()) == 1
    assert next(iter(manager.get_db_filename_dict())).startswith("another_user_")

import csv
import datetime as dt
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "extension/windrecorder-memory/scripts/query.py"


@pytest.fixture
def query(db, workspace):
    from windrecorder.query_service import RecordQuery

    return RecordQuery(workspace)


@pytest.mark.parametrize(
    "keyword,exclude", [("", ""), ("hello editor", ""), ("hello", "skip"), ("' OR 1=1 --", ""), ("project-plan", "")]
)
def test_agent_search_matches_application_and_paginates(query, db, make_rows, keyword, exclude):
    rows = make_rows("2024-01-31_23-59-59", "2024-02-01_00-00-00", "2024-02-02_01-00-00", title="editor")
    rows.loc[1, "ocr_text"] = "hello skip"
    rows.loc[2, "ocr_text"] = "project plan hello"
    rows["thumbnail"] = "x" * 200_000
    db.db_add_dataframe_to_db_process(rows)
    start, end = dt.datetime(2024, 1, 1), dt.datetime(2024, 3, 1)
    expected, count, _ = db.db_search_data(keyword, start, end - dt.timedelta(seconds=1), exclude)
    all_rows = []
    for offset in range(count + 1):
        result = query.search(start, end, keyword, exclude, limit=1, offset=offset)
        assert result["total_matches"] == count
        assert result["has_more"] == (offset + len(result["records"]) < count)
        all_rows.extend(result["records"])
    assert [row["ocr_text"] for row in all_rows] == expected.ocr_text.tolist()
    assert all("thumbnail" not in row for row in all_rows)


def test_agent_context_counts_and_detail_keep_boundaries_and_provenance(query, db, make_rows):
    db.db_add_dataframe_to_db_process(
        make_rows("2024-01-31_23-59-59", "2024-02-01_00-00-00", "2024-02-01_00-00-01", text="一二三四五六")
    )
    at = dt.datetime(2024, 2, 1)
    context = query.context(at, 1, text_limit=2)
    assert len(context["records"]) == 3
    record = context["records"][1]
    assert record["recorded_at"] == "2024-02-01 00:00:00"
    assert record["ocr_text"] == "一二" and record["text_truncated"]
    assert record["video_offset_seconds"] == 0
    detail = query.record(record["record_id"], text_offset=2)["record"]
    assert detail["ocr_text"] == "三四五六" and not detail["text_truncated"]
    counts = query.counts(at, at + dt.timedelta(days=1), "hour")
    assert counts["total_records"] == 2
    assert {row["time"]: row["count"] for row in counts["buckets"]} == db.db_get_record_counts(
        at, at + dt.timedelta(days=1), "hour"
    )
    with sqlite3.connect(Path(db.db_path) / record["database"]) as conn:
        conn.execute("UPDATE video_text SET videofile_time=videofile_time+100 WHERE rowid=?", [record["rowid"]])
    assert query.record(record["record_id"])["record"] is None
    assert query.record("../elsewhere.db:1:0")["record"] is None


def test_old_schema_and_missing_month_read_without_file_or_schema_changes(query, workspace):
    from windrecorder.query_service import seconds

    path = query.db_dir / "default_2020-02_wind.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE video_text(videofile_name TEXT, picturefile_name TEXT, videofile_time INT, ocr_text TEXT)")
        conn.execute(
            "INSERT INTO video_text(rowid, videofile_name, picturefile_name, videofile_time, ocr_text) VALUES (42, ?, ?, ?, ?)",
            ["2020-02-29_12-00-00.mp4", "0.jpg", seconds(dt.datetime(2020, 2, 29, 12)), "旧记录"],
        )
    before = {str(path.relative_to(workspace)): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    result = query.search(dt.datetime(2020, 2, 1), dt.datetime(2020, 3, 1), "旧记录")
    assert result["records"][0]["win_title"] is None
    assert result["records"][0]["deep_linking"] is None
    assert result["records"][0]["rowid"] == 42
    assert query.search(dt.datetime(2010, 1, 1), dt.datetime(2010, 2, 1))["records"] == []
    assert query.counts(dt.datetime(2020, 2, 1), dt.datetime(2020, 3, 1))["total_records"] == 1
    query.status()
    assert {str(path.relative_to(workspace)): path.read_bytes() for path in workspace.rglob("*") if path.is_file()} == before
    with query._open(path) as conn, pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM video_text")


def test_agent_queries_see_committed_wal_only(query, db, make_rows):
    db.db_add_dataframe_to_db_process(make_rows("2024-02-01_00-00-00"))
    writer = sqlite3.connect(query.db_dir / "default_2024-02_wind.db")
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO video_text SELECT * FROM video_text")
        assert query.context(dt.datetime(2024, 2, 1))["total_matches"] == 1
        writer.commit()
        assert query.context(dt.datetime(2024, 2, 1))["total_matches"] == 2
    finally:
        writer.close()


def test_flag_notes_omit_images_and_report_pagination(query):
    with query.notes_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["datetime", "note", "thumbnail"])
        writer.writeheader()
        for day in (1, 2):
            writer.writerow(dict(datetime=f"2024-02-0{day} 12:00:00", note="项目复盘" * 10, thumbnail="x" * 200_000))
    result = query.notes(dt.datetime(2024, 2, 1), dt.datetime(2024, 3, 1), "项目", limit=1, text_limit=4)
    assert result["total_matches"] == 2 and result["next_offset"] == 1
    assert result["records"][0]["text_truncated"]
    assert result["records"][0]["source_type"] == "flag_note"
    assert "thumbnail" not in result["records"][0]


@pytest.mark.parametrize("value", ["2024-02-01T00:00:00Z", "2024-02-01T00:00:00+08:00", "2024-02-01T00:00:00.1"])
def test_agent_rejects_ambiguous_timestamp_conversion(value):
    from windrecorder.query_service import parse_datetime

    with pytest.raises(ValueError):
        parse_datetime(value)


def test_cli_runs_with_standard_library_from_another_directory(query, db, make_rows, workspace):
    db.db_add_dataframe_to_db_process(make_rows("2024-02-01_12-00-00", text="项目回顾"))
    before = {str(path.relative_to(workspace)): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    process = subprocess.run(
        [
            sys.executable,
            "-S",
            str(CLI),
            "--root",
            str(workspace),
            "search",
            "--start",
            "2024-02-01",
            "--end",
            "2024-02-02",
            "--query",
            "项目",
        ],
        cwd=ROOT.parent,
        capture_output=True,
        encoding="utf-8",
        timeout=20,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["ok"] and result["result"]["records"][0]["ocr_text"] == "项目回顾"
    assert {str(path.relative_to(workspace)): path.read_bytes() for path in workspace.rglob("*") if path.is_file()} == before


def test_cli_failure_is_not_reported_as_no_matches(query, workspace):
    (query.db_dir / "default_2024-02_wind.db").write_bytes(b"not a database")
    process = subprocess.run(
        [sys.executable, "-S", str(CLI), "--root", str(workspace), "status"], capture_output=True, encoding="utf-8", timeout=20
    )
    assert process.returncode == 2
    assert not json.loads(process.stdout)["ok"]


def test_skill_cli_commands_and_copied_skill_use_explicit_installation(query, db, make_rows, workspace):
    db.db_add_dataframe_to_db_process(make_rows("2024-02-01_12-00-00", text="讨论项目甲"))
    with query.notes_path.open("w", encoding="utf-8", newline="") as stream:
        stream.write("datetime,note,thumbnail\n2024-02-01 12:00:00,项目甲已决定延期,unused\n")
    # Simulate an installed/copied skill, separate from the application code.
    copied_cli = workspace / "agent home/.agents/skills/windrecorder-memory/scripts/query.py"
    copied_cli.parent.mkdir(parents=True)
    shutil.copyfile(CLI, copied_cli)
    for name in ("__init__.py", "query_service.py", "query_sql.py"):
        shutil.copyfile(ROOT / "windrecorder" / name, workspace / "windrecorder" / name)
    record_id = query.context(dt.datetime(2024, 2, 1, 12))["records"][0]["record_id"]
    cases = [
        (["status"], "record_count", 1),
        (["counts", "--start", "2024-02-01", "--end", "2024-02-02"], "total_records", 1),
        (["context", "--at", "2024-02-01 12:00:00", "--seconds", "60"], "total_matches", 1),
        (["notes", "--start", "2024-02-01", "--end", "2024-02-02", "--query", "延期"], "total_matches", 1),
    ]
    before = {str(path.relative_to(workspace)): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    for arguments, key, expected in cases:
        process = subprocess.run(
            [sys.executable, "-S", str(copied_cli), "--root", str(workspace), *arguments],
            capture_output=True,
            encoding="utf-8",
            cwd=ROOT.parent,
            timeout=20,
        )
        assert process.returncode == 0, process.stdout + process.stderr
        assert json.loads(process.stdout)["result"][key] == expected
    process = subprocess.run(
        [sys.executable, "-S", str(copied_cli), "--root", str(workspace), "record", "--id", record_id],
        capture_output=True,
        encoding="utf-8",
        cwd=ROOT.parent,
        timeout=20,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(process.stdout)["result"]["record"]["ocr_text"] == "讨论项目甲"
    assert {str(path.relative_to(workspace)): path.read_bytes() for path in workspace.rglob("*") if path.is_file()} == before


def test_missing_library_does_not_create_it(workspace):
    from windrecorder.query_service import RecordQuery

    query = RecordQuery(workspace)
    result = query.status()
    assert result["record_count"] == 0 and not result["db_directory_exists"]
    assert not query.db_dir.exists()

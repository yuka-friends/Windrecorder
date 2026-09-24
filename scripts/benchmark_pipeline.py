"""Compare legacy eager search with indexed, deferred search on a disposable DB.

Pass --database to benchmark a read-only backup of an existing monthly shard.
The default fixture is synthetic; no desktop capture or model download occurs.
"""

import argparse
import datetime as dt
import json
import logging
import os
import re
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def benchmark(database=None, rows=10000):
    import pandas as pd

    original_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="windrecorder-benchmark-") as temporary:
        root = Path(temporary)
        shutil.copytree(ROOT / "windrecorder/config_src", root / "windrecorder/config_src")
        folder = root / "bench_db"
        folder.mkdir()
        month = re.search(r"\d{4}-\d{2}", database.name).group() if database else "2024-01"
        path = folder / f"benchmark_{month}_wind.db"
        if database:
            with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(path)) as target:
                    source.backup(target)
        else:
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute(
                    "CREATE TABLE video_text (videofile_name TEXT, picturefile_name TEXT, videofile_time INT, "
                    "ocr_text TEXT, is_videofile_exist BOOLEAN, is_picturefile_exist BOOLEAN, thumbnail TEXT, "
                    "win_title TEXT, deep_linking TEXT)"
                )
                conn.executemany(
                    "INSERT INTO video_text VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        (
                            "2024-01-01_00-00-00.mp4",
                            f"{i}.png",
                            1704067200 + i,
                            "benchmark text",
                            1,
                            0,
                            "x" * 4096,
                            "benchmark",
                            "",
                        )
                        for i in range(rows)
                    ),
                )
        start = dt.datetime.strptime(month, "%Y-%m")
        end = (start + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(seconds=1)
        params = ((start - dt.datetime(1970, 1, 1)).total_seconds(), (end - dt.datetime(1970, 1, 1)).total_seconds())
        query = "SELECT * FROM video_text WHERE ocr_text LIKE '%' AND videofile_time BETWEEN ? AND ? ORDER BY videofile_time, rowid"
        old_times = []
        for _ in range(3):
            began = time.perf_counter()
            with closing(sqlite3.connect(path)) as reader, closing(sqlite3.connect(root / "old-snapshot.db")) as snapshot:
                reader.backup(snapshot)
                full = pd.read_sql_query(query, snapshot, params=params)
            old_times.append(time.perf_counter() - began)
        warm_times = []
        for _ in range(3):
            began = time.perf_counter()
            with closing(sqlite3.connect(root / "old-snapshot.db")) as snapshot:
                full = pd.read_sql_query(query, snapshot, params=params)
            warm_times.append(time.perf_counter() - began)
        os.chdir(root)
        sys.path.insert(0, str(ROOT))
        try:
            from windrecorder.db_manager import _DBManager

            began = time.perf_counter()
            manager = _DBManager(str(folder), 50, "benchmark")
            index_seconds = time.perf_counter() - began
            optimized_times = []
            for _ in range(3):
                began = time.perf_counter()
                refs, count, _ = manager.db_search_data("", start, end, defer_payload=True)
                manager.db_max_page_result = 50
                page = manager.db_search_data_page_turner(refs, 1)
                optimized_times.append(time.perf_counter() - began)
            pd.testing.assert_frame_equal(full.iloc[:50].reset_index(drop=True), page)
            assert count == len(full)
            return {
                "rows": count,
                "shard_bytes": path.stat().st_size,
                "legacy_copy_and_eager_seconds_median": statistics.median(old_times),
                "legacy_reused_snapshot_seconds_median": statistics.median(warm_times),
                "one_time_index_setup_seconds": index_seconds,
                "indexed_deferred_first_page_seconds_median": statistics.median(optimized_times),
                "legacy_retained_dataframe_bytes": int(full.memory_usage(deep=True).sum()),
                "deferred_references_and_page_bytes": int(
                    refs.memory_usage(deep=True).sum() + page.memory_usage(deep=True).sum()
                ),
                "first_page_identical": True,
                "note": "Three local runs; warm filesystem cache. Index build is excluded; no production files changed.",
            }
        finally:
            logging.shutdown()
            os.chdir(original_cwd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--rows", type=int, default=10000)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.database, args.rows), indent=2))

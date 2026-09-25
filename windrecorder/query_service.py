"""Read-only record queries for agents, without app/config/database initialization.

Only standard-library dependencies are used. All time ranges are [start, end),
in the same naive local wall-clock seconds as historical Windrecorder records.
"""

import csv
import datetime as dt
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from windrecorder.query_sql import keyword_conditions, record_counts

EPOCH = dt.datetime(1970, 1, 1)


def parse_datetime(value):
    result = dt.datetime.fromisoformat(value)
    if result.tzinfo is not None or result.microsecond:
        raise ValueError("Use local wall-clock dates/times without a timezone or fractional seconds")
    return result


def seconds(value):
    if value.tzinfo is not None or value.microsecond:
        raise ValueError("Use local wall-clock dates/times without a timezone or fractional seconds")
    return int((value - EPOCH).total_seconds())


def time_text(value):
    return (EPOCH + dt.timedelta(seconds=int(value))).isoformat(sep=" ") if value is not None else None


class RecordQuery:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        default = self.root / "windrecorder/config_src/config_default.json"
        settings = json.loads(default.read_text(encoding="utf-8-sig"))
        # Read the legacy location too, without moving it or filling config fields.
        for path in (self.root / "userdata/config_user.json", self.root / "config/config_user.json"):
            if path.exists():
                settings.update(json.loads(path.read_text(encoding="utf-8-sig")))
                break
        self.user = settings["user_name"]
        self.data_dir = self._path(settings["userdata_dir"])
        self.db_dir = self.data_dir / settings["db_path"]
        self.notes_path = self.data_dir / settings["flag_mark_note_filename"]

    def _path(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    def _shards(self, start=None, end=None):
        pattern = re.compile(re.escape(self.user) + r"_(\d{4}-\d{2})_wind\.db")
        result = []
        if not self.db_dir.exists():
            return result
        for path in self.db_dir.iterdir():
            match = pattern.fullmatch(path.name)
            if not path.is_file() or not match:
                continue
            try:
                month = dt.datetime.strptime(match[1], "%Y-%m")
            except ValueError:
                continue
            if start is not None and month.strftime("%Y-%m") < start.strftime("%Y-%m"):
                continue
            if end is not None and month >= end:
                continue
            result.append(path)
        return sorted(result, key=lambda path: path.name)

    @staticmethod
    def _open(path):
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        return closing(conn)

    @staticmethod
    def _columns(conn):
        columns = {row[1] for row in conn.execute("PRAGMA table_info(video_text)")}
        required = {"videofile_time", "videofile_name", "picturefile_name", "ocr_text"}
        if not required <= columns:
            raise ValueError("Unsupported video_text schema; missing columns: " + ", ".join(sorted(required - columns)))
        return columns

    @staticmethod
    def _range(start, end):
        if seconds(start) >= seconds(end):
            raise ValueError("start must be before end (the end is exclusive)")

    @staticmethod
    def _limits(limit, offset, text_limit):
        if not 1 <= limit <= 200 or not 0 <= offset <= 100000 or not 1 <= text_limit <= 20000:
            raise ValueError("limit must be 1..200, offset 0..100000, text-limit 1..20000")

    @staticmethod
    def _projection(columns):
        optional = [name if name in columns else f"NULL AS {name}" for name in ("win_title", "deep_linking")]
        return (
            "rowid AS record_rowid, videofile_time, videofile_name, picturefile_name, "
            "substr(COALESCE(ocr_text, ''), ?, ?) AS ocr_text, length(COALESCE(ocr_text, '')) AS text_length, "
            + ", ".join(optional)
        )

    @staticmethod
    def _record(row, path, text_offset=0):
        item = dict(row)
        rowid = item.pop("record_rowid")
        timestamp = item["videofile_time"]
        item.update(
            record_id=f"{path.name}:{rowid}:{timestamp}",
            source_type="screen_ocr",
            database=path.name,
            rowid=rowid,
            recorded_at=time_text(timestamp),
            text_offset=text_offset,
            text_truncated=text_offset + len(item["ocr_text"]) < item["text_length"],
        )
        try:
            video_start = dt.datetime.strptime(Path(item["videofile_name"]).name[:19], "%Y-%m-%d_%H-%M-%S")
            item["video_offset_seconds"] = int(timestamp) - seconds(video_start)
        except (ValueError, TypeError):
            item["video_offset_seconds"] = None
        return item

    def status(self):
        shards = self._shards()
        earliest, latest, count = None, None, 0
        for path in shards:
            with self._open(path) as conn:
                self._columns(conn)
                low, high, total = conn.execute(
                    "SELECT MIN(videofile_time), MAX(videofile_time), COUNT(*) FROM video_text"
                ).fetchone()
            count += total
            if low is not None:
                earliest = low if earliest is None else min(earliest, low)
                latest = high if latest is None else max(latest, high)
        return dict(
            root=str(self.root),
            db_dir=str(self.db_dir),
            user=self.user,
            db_directory_exists=self.db_dir.is_dir(),
            shard_count=len(shards),
            record_count=count,
            earliest=time_text(earliest),
            latest=time_text(latest),
            notes_available=self.notes_path.is_file(),
            time_basis="local wall clock; ranges include start and exclude end",
            capabilities=["search", "context", "record", "counts", "notes"],
        )

    def search(self, start, end, query="", exclude="", *, limit=20, offset=0, text_limit=2000):
        self._range(start, end)
        self._limits(limit, offset, text_limit)
        result, total, skip = [], 0, offset
        shards = self._shards(start, end)
        for path in shards:
            with self._open(path) as conn:
                conn.execute("BEGIN")  # Count and page see one committed snapshot within this shard.
                columns = self._columns(conn)
                conditions, params = keyword_conditions(
                    query, exclude, title_column="win_title" if "win_title" in columns else "NULL"
                )
                conditions.append("videofile_time >= ? AND videofile_time < ?")
                params.extend([seconds(start), seconds(end)])
                where = " AND ".join(conditions)
                count = conn.execute("SELECT COUNT(*) FROM video_text WHERE " + where, params).fetchone()[0]
                total += count
                if skip >= count:
                    skip -= count
                    continue
                if len(result) < limit:
                    rows = conn.execute(
                        f"SELECT {self._projection(columns)} FROM video_text WHERE {where} "
                        "ORDER BY videofile_time, rowid LIMIT ? OFFSET ?",
                        [1, text_limit, *params, limit - len(result), skip],
                    ).fetchall()
                    result.extend(self._record(row, path) for row in rows)
                skip = 0
        has_more = offset + len(result) < total
        return dict(
            records=result,
            total_matches=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
            next_offset=offset + len(result) if has_more else None,
            searched_shards=len(shards),
            start=start.isoformat(sep=" "),
            end_exclusive=end.isoformat(sep=" "),
        )

    def context(self, at, radius_seconds=300, **kwargs):
        if not 1 <= radius_seconds <= 86400:
            raise ValueError("seconds must be 1..86400")
        # Include the second at the upper boundary as well.
        return self.search(at - dt.timedelta(seconds=radius_seconds), at + dt.timedelta(seconds=radius_seconds + 1), **kwargs)

    def record(self, record_id, *, text_limit=2000, text_offset=0):
        self._limits(1, 0, text_limit)
        if text_offset < 0:
            raise ValueError("text-offset cannot be negative")
        name, rowid, timestamp = record_id.rsplit(":", 2)
        # Resolve only an enumerated user shard, never a caller-supplied path.
        path = next((path for path in self._shards() if path.name == name), None)
        if path is None:
            return {"record": None, "reason": "record database is unavailable"}
        with self._open(path) as conn:
            columns = self._columns(conn)
            row = conn.execute(
                f"SELECT {self._projection(columns)} FROM video_text WHERE rowid=? AND videofile_time=?",
                [text_offset + 1, text_limit, int(rowid), int(timestamp)],
            ).fetchone()
        return {"record": self._record(row, path, text_offset) if row else None}

    def counts(self, start, end, frequency="day"):
        self._range(start, end)
        if frequency not in {"hour", "day", "month"}:
            raise ValueError("by must be hour, day or month")
        if frequency == "hour" and end - start > dt.timedelta(days=366):
            raise ValueError("Hourly statistics are limited to 366 days; use day/month or a narrower range")
        counts = {}
        for path in self._shards(start, end):
            with self._open(path) as conn:
                self._columns(conn)
                for bucket, count in record_counts(conn, seconds(start), seconds(end), frequency):
                    counts[bucket] = counts.get(bucket, 0) + count
        return dict(
            buckets=[dict(time=key, count=value) for key, value in sorted(counts.items())],
            total_records=sum(counts.values()),
            frequency=frequency,
        )

    def notes(self, start, end, query="", *, limit=20, offset=0, text_limit=2000):
        self._range(start, end)
        self._limits(limit, offset, text_limit)
        if not self.notes_path.exists():
            return dict(records=[], total_matches=0, has_more=False, next_offset=None, notes_available=False)
        csv.field_size_limit(16 * 1024 * 1024)  # Historical rows also contain base64 screenshots.
        result, total = [], 0
        with self.notes_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not {"datetime", "note"} <= set(reader.fieldnames or []):
                raise ValueError("Unsupported flag notes CSV: datetime/note columns are required")
            for row_number, row in enumerate(reader, 2):
                recorded_at = parse_datetime(row["datetime"])
                text = row["note"] or ""
                if not start <= recorded_at < end or not all(word.casefold() in text.casefold() for word in query.split()):
                    continue
                if offset <= total < offset + limit:
                    result.append(
                        dict(
                            source_type="flag_note",
                            source_file=str(self.notes_path),
                            row_number=row_number,
                            recorded_at=recorded_at.isoformat(sep=" "),
                            note=text[:text_limit],
                            text_length=len(text),
                            text_truncated=len(text) > text_limit,
                        )
                    )
                total += 1
        has_more = offset + len(result) < total
        return dict(
            records=result,
            total_matches=total,
            has_more=has_more,
            next_offset=offset + len(result) if has_more else None,
            notes_available=True,
        )

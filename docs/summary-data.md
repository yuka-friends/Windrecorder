# Summary data and compatibility

Memory summaries accept missing monthly databases and empty tables. Search still
returns `(dataframe, count, pages)` with the existing inclusive range semantics;
an empty result retains the nine `video_text` column names.

Calendar statistics use a separate read-only SQLite aggregation over `[start, end)`.
They count indexed rows without loading OCR text or base64 thumbnails. Every hour,
day, and month appears, including zero-count buckets. Hour labels remain 1–24:
1 represents 00:00–01:00. Midnight and the last hour/day of a period count once.
Stored epoch seconds continue to represent naive local wall-clock values; no
timezone or daylight-saving conversion is applied.

The data layer owns summary caching. `*_calendar_v2.json` files in the configured
date-state directory are disposable, atomic caches validated against the source
database and WAL file metadata. Backfills and deletions invalidate historical
periods too. Invalid caches regenerate; a concurrent write during aggregation
prevents that result from being cached. A page rerun revalidates the cache even
when the selected month has not changed.

Old `*_month_data_state.csv` and `*_year_data_state.csv` files are left intact and
ignored by the new charts, because they may contain counts from the old calendar
boundary calculation. No source database schema, rowid, thumbnail, timestamp,
video, FAISS index, user setting, or existing generated image is migrated.

On an empty month, the page shows an explicit message and disables image generation.
On an empty library it shows an empty state instead of constructing invalid date
controls. Record bounds skip empty shards, including a newly created current month.

# Query and capture performance

## Query changes

Interactive searches and record counts use short-lived SQLite `mode=ro`
connections. They see committed WAL data without copying the monthly database.
The legacy snapshot helper remains available for explicit callers, but is no
longer in the interactive path. SQLite's existing journal mode is preserved.

Two non-unique indexes are added on upgrade or shard creation: record time and
capture identity (video name, picture name, timestamp). Existing rows, rowids,
FAISS mappings, and schemas' columns are unchanged. The first upgrade spends time
building these indexes and needs additional disk space; later launches reuse them.

The OCR search UI retains compact row references, then loads text/thumbnails only
for the displayed page. The original full-dataframe search API remains the default
for other callers. Keyword, exclusion and fuzzy-character semantics are preserved.
Deleted/replaced matches are skipped on page load; run a new search to refresh its
total. Vector search keeps probability scores attached to their original rowids.

Daily chart buckets use one sorted timestamp array, rather than repeatedly scanning
the whole dataframe (including thumbnails) for every six-minute interval.

## Reproducible comparison

Run `python scripts/benchmark_pipeline.py` with the application environment for a
synthetic fixture, or add `--database path/to/user_YYYY-MM_wind.db`. The latter
opens the source read-only and makes a disposable copy. Only the copy is indexed.
No recording, model download, or production database migration is involved.

On this Windows machine, a historical 62,949-row shard produced these medians over
three local runs with warm filesystem caches:

| Operation | Seconds |
| --- | ---: |
| Legacy snapshot refresh plus eager results | 5.021 |
| Legacy eager results, reusing an unchanged snapshot | 1.906 |
| Indexed reference search plus first 50 results | 0.376 |
| One-time index setup (separate from search timing) | 0.793 |

Pandas' retained-dataframe estimate fell from 142,117,019 bytes for all payloads to
5,824,845 bytes for references plus the first page. This is not a process RSS or
peak-memory measurement. Result counts and first-page contents were identical.
These are local measurements, not guarantees for every disk, dataset, or query.
Substring searches still scan candidate text; a full-text index would change
matching semantics and is intentionally not part of this compatibility update.

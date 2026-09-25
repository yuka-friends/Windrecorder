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

## Capture changes

The screenshot loop reuses the accepted frame's ORB descriptors, bypasses feature
extraction for identical pixels, and handles blank frames or resolution changes.
The existing ORB score and thresholds remain unchanged for textured frames. OCR
failure leaves the previous baseline intact, so an unchanged screen can be retried.
Segment duration uses elapsed monotonic time, including OCR work. Repeated content
checking now actually skips the outer insertion rather than only the inner loop.

WeChat OCR requests are serialized. Completion is cleared before dispatch, so a
fast callback cannot lose its notification. Timeouts raise an error instead of
returning the previous screenshot's text; late callbacks for other paths are ignored.

Capture submission builds a dataframe once and inserts in a transaction per monthly
shard. Retrying the same video/image/timestamp skips an existing row while keeping
its rowid. Existing duplicates are not removed and there is no unique constraint.
Even a single valid OCR result is submitted. A failed cross-month submission keeps
its JSON and images, and can retry already-committed months safely.

Active capture folders have a process marker released on exit. Video conversion
and cleanup share a nonblocking Windows lock, automatically released on a crash;
busy maintenance is deferred. Unsubmitted, active, short, or malformed caches are
retained for recovery. Successful conversion requires a submitted index and an
existing compressed output of the same minimum size used by the compressor.
The video writer is checked and released on failure. Each screenshot is displayed
from its own timestamp until the next capture, fixing the old one-frame shift.

These markers are additive; existing JSON layouts, database columns, video names,
and wall-clock timestamps remain compatible. Incomplete and very short caches can
occupy disk longer than before: preservation is intentional, and persistent OCR or
encoding failures still need investigation via the logs. This change does not
implement historical re-OCR recovery or rewrite previously generated videos.

`python scripts/benchmark_capture.py` compares 20 synthetic 854×480 frame pairs.
Three-run local medians were approximately 0.61s → 0.002s for identical frames and
0.69s → 0.37s for changing textured frames, with matching similarity scores. This
measures frame comparison only, not end-to-end OCR, screen capture or encoding.

Regression tests cover deferred pages, committed WAL reads, deleted rowids,
vector score association, concurrent submission, retry after a partial monthly
commit, active-cache protection, lock contention, OCR timeout/callback ordering,
capture-loop retry and duration, blank frames, failed encoding and video timing.

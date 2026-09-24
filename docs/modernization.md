# Compatibility-first modernization

## Architecture and invariants

`main.py` owns the Windows tray and launches the recording service and Streamlit.
`record.py` and `ocr_manager.py` produce screenshot/video metadata and OCR rows;
`db_manager.py` stores these in monthly SQLite `video_text` tables. Search, activity
statistics and optional FAISS/uform image search consume the same rows.
Configuration is merged from `windrecorder/config_src` into `userdata/config_user.json`.
Originally, batch launchers discovered a Poetry environment and optional extensions
installed additional packages directly into it. Launchers now share a uv bootstrap
and use the project's ready environment without a network sync on normal startup.

Existing monthly filenames, column order/types, SQLite rowids, thumbnails, video
names, config keys and naive wall-clock seconds since 1970 must remain compatible.
In particular these timestamps must **not** be converted to local/UTC timestamps.
FAISS indexes refer to SQLite rowids, so no table rewrite or reindex is planned.

## Milestones

1. Establish Windows regression tests in temporary workspaces with real SQLite,
   documenting known failures with strict xfails before modifying production code.
2. Fix covered storage/search/configuration/locking defects through small changes.
3. Validate newer Python and dependency wheels; migrate packaging and every launcher
   to uv, including existing Poetry environments and optional extensions.
4. Validate upgrade failure/retry behavior, Windows runtime imports and CI; document
   deployment and remaining manual hardware checks.

Tests never import the application before changing into a temporary directory.
They do not record the desktop, call external OCR services, download models or open user DBs.

## Milestone 2 verification

22 Windows tests pass. The original seven strict expected failures now pass normally.
Monthly routing handles singleton, unsorted and cross-year batches; queries bind all
values and parenthesize keyword alternatives. Read snapshots use SQLite backup and
track WAL changes. Existing schema migrations preserve rowids and data. Configuration
reads retain unknown fields, only write missing defaults, and publish JSON atomically.
Single-setting saves do not overwrite unrelated settings from another application
instance. Lock release is idempotent; timeout threads are daemonized. Legacy migration
retains both copies when directories conflict and never deletes a DB based on its size.

The existing application-wide import-time config/DB objects are retained for compatibility;
new persistence primitives have no desktop dependencies, and DB instances now respect
their own paths/usernames. A wholesale service/container rewrite is intentionally deferred.

## Python and dependency decisions

The supported range is now Python 3.11–3.12; the installer selects managed 3.12.
This is a compatibility release, not an unrestricted upgrade of every library.
The resolver pins a reproducible graph in `uv.lock`, including all three optional
extensions together. Only Windows x64 is claimed as a supported runtime.

| Previous constraint / behavior | Change and reason |
| --- | --- |
| Python `<3.12` | Standard project metadata now allows 3.12; uv installs the interpreter. |
| ONNX Runtime `~1.15.1`, pywin32 `~306`, pyclipper `~1.3.0.post4` | Updated to releases with Windows CPython 3.12 wheels; native imports and bundled model inference are tested. |
| Old NumPy / OpenCV / Shapely binary stack | NumPy 1.26.4, OpenCV 4.10–4.11 and Shapely 2.0.6+ avoid introducing the NumPy 2 ABI change in the same migration. |
| FAISS 1.7.4 | FAISS 1.9 reads a fixture written by 1.7.4 with its original integer IDs; no index conversion. |
| Undeclared `requests` import | Declared directly, independent of Streamlit's transitive dependencies. |
| Unbounded extension pip installs | Locked extras: RapidOCR 1.4.4, WeChat OCR 0.0.3, uform 3.1.3 with ONNX support. |
| WeChat pins protobuf 3.20.3 | Streamlit 1.41 and ONNX <1.18 remain compatible with this required version. |
| `datetime.utcfromtimestamp` deprecated in 3.12 | Epoch arithmetic retains naive wall-clock semantics, including fractional and negative values. |
| Poetry activation in each batch | Shared activation and transactional uv setup; legacy onboarding hands off before application imports. |

RapidOCR's existing distribution explicitly requires Python `<3.13`. Supporting
3.13/3.14 requires migrating to the newer `rapidocr` package/API and validating its
recognition behavior. NumPy 1.26 only supports Python through 3.12, so that work also
requires a NumPy 2/native binary audit. These are remaining compatibility gates,
not a claim that newer Python is inherently incompatible with screen recording.

Primary references: [NumPy 1.26 support](https://numpy.org/doc/1.26/release/1.26.0-notes.html),
[ONNX Runtime wheels](https://pypi.org/project/onnxruntime/1.20.1/),
[RapidOCR Python constraint](https://pypi.org/project/rapidocr-onnxruntime/),
[WeChat dependencies](https://pypi.org/project/wechat-ocr/),
[uform backend](https://github.com/unum-cloud/uform/blob/v3.1.3/python/uform/__init__.py),
[uv sync and extras](https://docs.astral.sh/uv/concepts/projects/sync/).

## Validation boundaries

Automated coverage protects storage, monthly routing, query semantics, schema/rowid
compatibility, configuration persistence, locks and setup failure/retry/rollback.
Runtime checks include native imports, bundled ONNX OCR inference and old FAISS
index loading. Setup has also been run with real uv and all three extras on Windows.
Tests validate launch paths containing spaces and Chinese characters.

Before release, manually verify the system tray, startup shortcut, monitor capture,
FFmpeg encoders, Windows OCR language packs, WeChat's external binary and a complete
embedding-model download/search on representative machines. These depend on hardware,
OS installation or external assets and are not established by passing unit tests.

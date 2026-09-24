# Compatibility-first modernization

## Architecture and invariants

`main.py` owns the Windows tray and launches the recording service and Streamlit.
`record.py` and `ocr_manager.py` produce screenshot/video metadata and OCR rows;
`db_manager.py` stores these in monthly SQLite `video_text` tables. Search, activity
statistics and optional FAISS/uform image search consume the same rows.
Configuration is merged from `windrecorder/config_src` into `userdata/config_user.json`.
The batch launchers currently discover a Poetry environment; optional extensions
install additional packages directly into it.

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
They do not record the desktop, call OCR services, download models or open user DBs.

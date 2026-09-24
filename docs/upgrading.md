# Installation, upgrade and recovery

Windrecorder runs on Windows x64. The installer uses uv and a managed Python 3.12;
Python 3.11 remains covered for developers. Install Git and FFmpeg as described in
the README. New users can install [uv](https://docs.astral.sh/uv/getting-started/installation/)
without installing Python separately. Existing Python/Poetry users can simply run
`install_update.bat`: the bootstrap installs uv with their existing Python if needed.

## Existing installations

1. Exit Windrecorder and any recording, embedding or standalone web UI processes.
2. Run `install_update.bat`. If the current branch has an upstream, Git must
   fast-forward successfully before setup runs. Local branches without an upstream
   and detached checkouts skip the pull with a notice and install the current code.
   Setup does not switch branches or assign an upstream automatically.
3. Setup discovers the local `.venv` or Poetry's external environment, inventories
   installed packages, and restores the RapidOCR, WeChat OCR and uform extensions
   indicated by the old environment or configuration.
4. The old local environment is renamed to `.venv-backup-<timestamp>-<id>`;
   an external Poetry environment stays at its original location. A new `.venv`
   is created at its final path so Windows entry points contain the correct paths.
5. Dependencies come from `uv.lock`. Native and selected extension imports must
   pass before `.uv-state.json` is marked ready and onboarding opens.

`userdata`, video files, SQLite databases, FAISS indexes and model download caches
are not moved or rewritten by environment setup. Packaged FFmpeg executables and
DLLs in the old environment root are copied to the replacement environment.
The old data migration no longer deletes small databases or overwrites conflicting
legacy directories. Conflicting legacy data stays in place for manual reconciliation.

An already-running old installer can finish its Poetry commands after pulling this
update. The new `onboard_setting.py` hands off to uv before importing the application.
All new launchers also perform setup when no ready uv environment is present. If an
old batch file stops midway as Git replaces it, reopen `install_update.bat`.
Poetry is not uninstalled globally; the small `[tool.poetry]` table only permits
legacy environment discovery. `uv.lock` is the authoritative dependency lock.

## Failed or interrupted upgrades

Install/import failure automatically restores the previous local environment.
An interrupted install is recovered on the next attempt. Partial environments are
retained under `.venv-failed-*`; no recursive deletion is used. The installer holds
an OS lock, which is released automatically if it crashes.

To retry environment setup without pulling Git or opening onboarding, run from the
project directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
```

To restore the most recent local environment explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1 -Rollback
```

An explicitly restored legacy environment stays ready for offline launching. This
restores packages, not repository code. External Poetry environment paths and all
old package versions are recorded in `.uv-migration/*.json`. Unrecognized, manually
installed packages are inventoried and retained in the old environment; they are not
blindly copied between Python versions. Reinstall custom plugins after checking
their Python 3.12 compatibility. Keep the backup until recording and your preferred
OCR/embedding engine have been checked; backups can consume significant disk space.

## Extensions and offline launching

Existing extension batch files remain the supported installation entry points.
Their selections persist across future upgrades. Removing one extension does not
remove another's shared dependencies. For noninteractive package setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1 -AddExtra rapidocr
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1 -AddExtra wechat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1 -AddExtra embedding
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1 -RemoveExtra embedding
```

The extension batch files also perform the relevant engine configuration, binary
setup and model checks. The noninteractive commands above only manage packages.
Normal `start_app.bat` launches the ready environment directly without resolving
dependencies or requiring network access. Installation and initial model downloads
still require network access. Configure uv's index/proxy environment variables if
PyPI is unavailable; no third-party mirror is silently substituted.

## Development

```powershell
uv sync --locked --all-extras
.venv/Scripts/python.exe -m pytest
uv pip check --python .venv/Scripts/python.exe
```

Use a separate environment for the compatibility matrix, for example:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-py311'
uv sync --locked --python 3.11 --all-extras
.venv-py311/Scripts/python.exe -m pytest
```

Tests change into temporary workspaces before importing application modules. They
use real SQLite files, bundled reference images and a FAISS 1.7.4 fixture, and do
not record the desktop or download embedding models. Windows CI covers both Python
versions with the base install and with all extras. Use `--all-extras` when manually
syncing a development environment with extensions: plain `uv sync` is exact and may
remove extras. User-facing setup remembers selected extras automatically.

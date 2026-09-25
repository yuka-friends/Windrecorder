"""Transactional uv installation; stdlib only, never import application config.

Run through setup.ps1 so this process does not use the .venv being replaced.
Old local environments are temporary recovery backups, removed after successful setup.
"""

import argparse
import ctypes
import datetime
import email.parser
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from windrecorder.storage import atomic_write_json  # noqa: E402

EXTRAS = {"rapidocr-onnxruntime": "rapidocr", "wechat-ocr": "wechat", "uform": "embedding"}
STATE_NAME = ".uv-state.json"


def read_state(root):
    path = root / STATE_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def inventory(environment):
    packages = {}
    if environment:
        for metadata in (environment / "Lib" / "site-packages").glob("*.dist-info/METADATA"):
            message = email.parser.Parser().parsestr(metadata.read_text(encoding="utf-8"))
            if message["Name"]:
                packages[message["Name"].lower().replace("_", "-")] = message["Version"]
    return packages


def discover_legacy(root, run=subprocess.run):
    if (root / ".venv").exists():
        return root / ".venv"
    # This remains available through the small [tool.poetry] discovery bridge.
    poetry = shutil.which("poetry")
    command = [poetry] if poetry else ["python", "-m", "poetry"]
    try:
        result = run(command + ["env", "info", "--path"], cwd=root, capture_output=True, text=True, timeout=30)
        path = Path(result.stdout.strip())
        if result.returncode == 0 and result.stdout.strip() and (path / "pyvenv.cfg").is_file():
            return path
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def select_extras(root, state, packages):
    if state.get("status") == "ready":
        return set(state.get("extras", []))
    selected = {extra for package, extra in EXTRAS.items() if package in packages}
    config_path = root / "userdata" / "config_user.json"
    if not config_path.exists():
        config_path = root / "config" / "config_user.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("img_embed_module_install"):
            selected.add("embedding")
        engines = set(config.get("support_ocr_lst", [])) | {config.get("ocr_engine")}
        if "PaddleOCR" in engines:
            selected.add("rapidocr")
        if "WeChatOCR" in engines:
            selected.add("wechat")
    return selected


def process_alive(pid):
    if os.name != "nt":
        raise RuntimeError("Windrecorder's installer requires Windows x64.")
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return ctypes.get_last_error() == 5  # Access denied: do not replace its files.
    try:
        code = wintypes.DWORD()
        return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
    finally:
        kernel.CloseHandle(handle)


def check_not_running(root, alive=process_alive):
    config = json.loads((root / "windrecorder/config_src/config_default.json").read_text(encoding="utf-8"))
    user = root / "userdata/config_user.json"
    if not user.exists():
        user = root / "config/config_user.json"
    if user.exists():
        config.update(json.loads(user.read_text(encoding="utf-8")))
    lock_dir = root / config["lock_file_dir"]
    for key in ("tray_lock_name", "record_lock_name", "img_emb_lock_name"):
        path = lock_dir / config[key]
        if path.exists():
            try:
                pid = int(path.read_text(encoding="utf-8").strip())
            except ValueError:
                raise RuntimeError(f"Cannot verify process lock {path}; close Windrecorder and inspect this lock.")
            if pid > 0 and alive(pid):
                raise RuntimeError(f"Close Windrecorder and its recording/embedding processes first (PID {pid}).")


def unique_path(root, kind):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return root / f".venv-{kind}-{stamp}-{uuid.uuid4().hex[:8]}"


def checked_backup(root, name):
    path = (root / name).resolve()
    if path.parent != root.resolve() or not path.name.startswith(".venv-backup-"):
        raise ValueError("Backup path must be a .venv-backup-* directory inside this checkout.")
    return path


def cleanup_backups(root):
    """Only delete ordinary local backup environments after the new one is ready."""
    for candidate in root.glob(".venv-backup-*"):
        try:
            if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
                continue
            backup = checked_backup(root, candidate.name)
            if backup != root.resolve() / candidate.name:
                continue
            if not (backup / "pyvenv.cfg").is_file():
                continue
            shutil.rmtree(backup)
        except (OSError, ValueError) as error:
            print(f"[Environment] Could not remove backup {candidate}: {error}. Retry cleanup on the next setup.", flush=True)


def restore(root, journal):
    environment = root / ".venv"
    backup = checked_backup(root, journal["backup"]) if journal.get("backup") else None
    if backup and backup.exists():
        if environment.exists():
            environment.rename(unique_path(root, "failed"))
        backup.rename(environment)
    elif not journal.get("had_environment") and environment.exists():
        environment.rename(unique_path(root, "failed"))
    previous = journal.get("previous_state", {})
    atomic_write_json(root / STATE_NAME, previous)


def check_controller_outside_environment(root):
    environment = (root / ".venv").resolve()
    if any(Path(path).resolve().is_relative_to(environment) for path in (sys.prefix, sys.executable)):
        raise RuntimeError(
            "Setup is running inside the .venv it needs to replace. "
            "Run install_update.bat or scripts/setup.ps1 to use an external Python interpreter."
        )


def install(root, uv, *, add=None, remove=None, run=subprocess.run):
    check_controller_outside_environment(root)
    print("[Environment] Checking the previous installation and installed extensions...", flush=True)
    state = read_state(root)
    if state.get("status") == "installing":
        print("[Environment] Recovering the interrupted installation...", flush=True)
        restore(root, state)
        state = read_state(root)
    legacy = discover_legacy(root, run)
    packages = inventory(legacy)
    extras = select_extras(root, state, packages)
    if add:
        extras.add(add)
    if remove:
        extras.discard(remove)
    environment = root / ".venv"
    if (
        environment.is_symlink()
        or (hasattr(environment, "is_junction") and environment.is_junction())
        or (environment.exists() and not (environment / "pyvenv.cfg").is_file())
    ):
        raise RuntimeError(".venv must be an ordinary virtual environment; refusing to replace this path.")
    backup = unique_path(root, "backup") if environment.exists() else None
    journal = {
        "status": "installing",
        "backup": backup.name if backup else None,
        "had_environment": environment.exists(),
        "previous_state": state,
    }
    atomic_write_json(root / STATE_NAME, journal)
    try:
        if backup:
            print("[Environment] Saving the previous environment for recovery...", flush=True)
            environment.rename(backup)
        report = root / ".uv-migration" / f"{uuid.uuid4().hex}.json"
        atomic_write_json(report, {"legacy_environment": str(legacy) if legacy else None, "packages": packages})
        command = [uv, "sync", "--locked", "--python", "3.12", "--managed-python", "--no-dev", "--inexact"]
        for extra in sorted(extras):
            command += ["--extra", extra]
        env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(environment), UV_LINK_MODE="copy")
        env.pop("VIRTUAL_ENV", None)
        print("[Environment] Downloading and installing dependencies. This may take several minutes...", flush=True)
        run(command, cwd=root, env=env, check=True)
        # Packaged releases keep FFmpeg and its DLLs at the old environment root.
        asset_source = backup or legacy
        if asset_source:
            for path in asset_source.iterdir():
                if path.is_file() and path.suffix.lower() in {".exe", ".dll"}:
                    shutil.copy2(path, environment / path.name)
        imports = "import numpy,pandas,cv2,onnxruntime,faiss,win32api,streamlit,tkinter"
        if "rapidocr" in extras:
            imports += "; import rapidocr_onnxruntime"
        if "wechat" in extras:
            imports += "; import wechat_ocr"
        if "embedding" in extras:
            imports += "; from uform import Modality,get_model; import uform.onnx_encoders,uform.numpy_processors"
        print("[Environment] Verifying installed components. First-time loading may take a while...", flush=True)
        run([str(environment / "Scripts/python.exe"), "-c", imports], cwd=root, check=True)
        atomic_write_json(
            root / STATE_NAME,
            {
                "status": "ready",
                "python": "3.12",
                "extras": sorted(extras),
                "backup": None,
            },
        )
    except BaseException:
        print("[Environment] Setup failed. Restoring the previous environment state...", flush=True)
        restore(root, journal)
        raise
    # Commit the ready state before cleanup: a cleanup failure must never roll back
    # to a backup which may already have been partially deleted.
    cleanup_backups(root)
    print("uv environment ready. Temporary local backups cleaned up; package inventories retained.", flush=True)


def rollback(root):
    check_controller_outside_environment(root)
    print("[Environment] Restoring the previous environment...", flush=True)
    state = read_state(root)
    if not state.get("backup") or not checked_backup(root, state["backup"]).exists():
        raise RuntimeError("No local environment backup is available. Run setup again to reinstall dependencies.")
    restore(root, state)
    if read_state(root).get("status") != "ready":
        # An explicitly restored pre-uv environment must remain usable offline.
        atomic_write_json(
            root / STATE_NAME,
            {
                "status": "ready",
                "python": "legacy",
                "extras": sorted(extra for package, extra in EXTRAS.items() if package in inventory(root / ".venv")),
                "backup": None,
            },
        )
    print("Previous environment restored. Failed/replaced environment retained for inspection.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", default="uv")
    parser.add_argument("--add-extra", choices=EXTRAS.values())
    parser.add_argument("--remove-extra", choices=EXTRAS.values())
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    check_not_running(ROOT)
    # The OS releases this byte-range lock on crashes; no stale lock blocks retries.
    import msvcrt

    with open(ROOT / ".uv-setup.lock", "a+b") as lock:
        lock.seek(0)
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("Another Windrecorder setup is already running.")
        try:
            if args.rollback:
                rollback(ROOT)
            else:
                install(ROOT, args.uv, add=args.add_extra, remove=args.remove_extra)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        sys.exit(1)

"""Start the tray app with diagnostics available even if its imports fail."""

import argparse
import contextlib
import ctypes
import datetime
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wait_for_tray():
    """Keep startup feedback visible, without tying the app to Windows Terminal."""
    # A separate hidden console preserves CTRL_BREAK_EVENT for recording shutdown.
    # CREATE_NO_WINDOW/pythonw would lose that console and break graceful stopping.
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    try:
        with tempfile.TemporaryDirectory(prefix="windrecorder-startup-") as status_dir:
            ready_path = Path(status_dir) / "ready"
            child = subprocess.Popen(
                [sys.executable, "-u", str(Path(__file__).resolve()), "--background", str(ready_path)],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=startup,
                close_fds=True,
            )
            print("Loading application components; first startup may take a little longer...", flush=True)
            next_notice = time.monotonic() + 10
            while True:
                code = child.poll()
                if code is not None:
                    if code:
                        print(f"Startup failed. See {ROOT / 'cache/logs/startup.log'}", file=sys.stderr)
                    return code
                if ready_path.exists():
                    print("Windrecorder is ready in the system tray. Closing this window.", flush=True)
                    return 0
                if time.monotonic() >= next_notice:
                    print("Still loading Windrecorder. Please keep this window open...", flush=True)
                    next_notice = time.monotonic() + 10
                time.sleep(0.1)
    except Exception:
        traceback.print_exc()
        return 1


def launch(ready_path=None):
    log_path = ROOT / "cache/logs/startup.log"
    code = 1
    ready = False
    try:
        os.chdir(ROOT)
        sys.path.insert(0, str(ROOT))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if log_path.exists() and log_path.stat().st_size > 5 * 1024 * 1024:
            log_path.replace(log_path.with_suffix(".log.1"))
        with log_path.open("a", encoding="utf-8", buffering=1) as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                print(f"\n[{datetime.datetime.now().isoformat()}] Starting Windrecorder: {sys.executable}")
                try:
                    import main

                    def on_ready():
                        nonlocal ready
                        print("Tray ready; application running in the background.")
                        if ready_path is not None:
                            ready_path.touch()
                        ready = True

                    main.main(on_ready=on_ready)
                except SystemExit as error:
                    if error.code is None or error.code == 0:
                        print("Application exited normally.")
                        return 0
                    code = error.code if isinstance(error.code, int) else 1
                    traceback.print_exc()
                except Exception:
                    traceback.print_exc()
                else:
                    print("Application exited normally.")
                    return 0
    except Exception:
        traceback.print_exc()
    message = f"Startup failed. See the error details in:\n{log_path}"
    print(message, file=sys.stderr)
    if ready and ready_path is not None:
        # The startup window has already exited; a later crash must remain visible.
        ctypes.windll.user32.MessageBoxW(None, message, "Windrecorder", 0x10)
    return code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--background", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--foreground", action="store_true", help="Run directly for console diagnostics")
    args = parser.parse_args()
    sys.exit(launch(args.background) if args.foreground or args.background is not None else wait_for_tray())

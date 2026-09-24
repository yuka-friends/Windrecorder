"""Start the tray app with diagnostics available even if its imports fail."""

import contextlib
import ctypes
import datetime
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def show_console(visible):
    if os.name == "nt":
        # Target our console, never whichever window happens to be foreground.
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetConsoleWindow.restype = ctypes.c_void_p
        window = kernel.GetConsoleWindow()
        if window:
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user.ShowWindow(window, 5 if visible else 0)


def launch():
    log_path = ROOT / "cache/logs/startup.log"
    code = 1
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
                        print("Tray ready; hiding startup console.")
                        show_console(False)

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
    show_console(True)
    print(f"Startup failed. See the error details in:\n{log_path}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(launch())

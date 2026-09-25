"""Allow an already-running pre-uv installer to hand off before application imports."""

import json
import os
import sys
from pathlib import Path


def handoff_if_needed(script):
    root = Path(__file__).resolve().parents[1]
    state_path = root / ".uv-state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") == "ready" and Path(sys.executable).resolve() == (root / ".venv/Scripts/python.exe").resolve():
            return
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    # Replace this process so the old environment's Python executable is released.
    os.execv(
        str(powershell),
        [
            str(powershell),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / "scripts/setup.ps1"),
            "-LaunchScript",
            script,
        ],
    )

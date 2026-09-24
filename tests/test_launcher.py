"""Exercise startup diagnostics before application dependencies can be imported."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def launch(workspace, source, *, batch=False):
    root = workspace / "startup with spaces and 中文"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/launch_app.py", scripts / "launch_app.py")
    (root / "main.py").write_text(source, encoding="utf-8")
    command = [sys.executable, str(scripts / "launch_app.py")]
    if batch:
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")], check=True)
        shutil.copyfile(ROOT / "start_app.bat", root / "start_app.bat")
        (scripts / "activate_runtime.bat").write_text("@exit /b 0\n", encoding="ascii")
        command = ["cmd", "/d", "/c", str(root / "start_app.bat")]
    result = subprocess.run(
        command,
        input="\n",
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result, root / "cache/logs/startup.log"


@pytest.mark.parametrize(
    "source",
    [
        "raise ImportError('missing startup dependency')\n",
        "def main(on_ready):\n    on_ready()\n    raise RuntimeError('failed after tray creation')\n",
    ],
)
def test_startup_failure_logs_traceback_and_returns_failure(workspace, source):
    result, log = launch(workspace, source)
    assert result.returncode == 1
    assert "Startup failed" in result.stderr
    assert "startup.log" in result.stderr
    content = log.read_text(encoding="utf-8")
    assert "Traceback" in content
    assert "missing startup dependency" in content or "failed after tray creation" in content


def test_startup_logs_readiness_and_captures_output(workspace):
    result, log = launch(workspace, "def main(on_ready):\n    print('application output')\n    on_ready()\n")
    assert result.returncode == 0, result.stderr
    content = log.read_text(encoding="utf-8")
    assert "application output" in content
    assert "Tray ready" in content
    assert "Application exited" in content


def test_nonzero_system_exit_is_reported(workspace):
    result, log = launch(workspace, "def main(on_ready):\n    raise SystemExit(7)\n")
    assert result.returncode == 7
    assert "Startup failed" in result.stderr
    assert "SystemExit: 7" in log.read_text(encoding="utf-8")


@pytest.mark.parametrize("fails", [False, True])
def test_batch_reaches_python_and_reports_its_failure(workspace, fails):
    source = "raise RuntimeError('batch startup failure')\n" if fails else "def main(on_ready):\n    on_ready()\n"
    result, log = launch(workspace, source, batch=True)
    assert result.returncode == int(fails), result.stdout + result.stderr
    if fails:
        assert "Windrecorder could not start" in result.stdout
        assert "batch startup failure" in log.read_text(encoding="utf-8")
    else:
        assert "Tray ready" in log.read_text(encoding="utf-8")

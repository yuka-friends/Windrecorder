"""Exercise startup diagnostics before application dependencies can be imported."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def launch(workspace, source, *, batch=False):
    root = workspace / "startup with spaces and 中文"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/launch_app.py", scripts / "launch_app.py")
    (root / "main.py").write_text(source, encoding="utf-8")
    command = [sys.executable, str(scripts / "launch_app.py"), "--foreground"]
    if batch:
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")], check=True)
        shutil.copyfile(ROOT / "start_app.bat", root / "start_app.bat")
        (scripts / "activate_runtime.bat").write_text("@exit /b 0\n", encoding="ascii")
        command = ["cmd", "/d", "/c", str(root / "start_app.bat")]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    result = subprocess.run(
        command,
        input="\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        timeout=20,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        startupinfo=startup,
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
    assert "正在加载 Windrecorder" in result.stdout
    if fails:
        assert "Windrecorder could not start" in result.stdout
        assert "batch startup failure" in log.read_text(encoding="utf-8")
    else:
        assert "Tray ready" in log.read_text(encoding="utf-8")


def test_batch_exits_while_app_has_hidden_console_and_can_stop_recording(workspace):
    """Real Windows consoles: verify detachment and the recorder's break signal."""
    root = workspace / "startup with spaces and 中文"
    source = """import ctypes
import signal
import subprocess
import sys
import time
from pathlib import Path

def main(on_ready):
    ctypes.windll.user32.MessageBoxW = lambda *_: 0
    kernel = ctypes.windll.kernel32
    kernel.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel.GetConsoleWindow()
    assert window, 'Background app needs a console for recorder shutdown'
    user = ctypes.windll.user32
    user.IsWindowVisible.argtypes = [ctypes.c_void_p]
    assert not user.IsWindowVisible(window), 'Background console must be hidden'
    worker_code = "import signal,time; from pathlib import Path; signal.signal(signal.SIGBREAK, lambda *_: exit(0)); Path('worker-ready').touch()\\nwhile True: time.sleep(0.05)"
    worker = subprocess.Popen([sys.executable, '-c', worker_code], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        deadline = time.monotonic() + 10
        while not Path('worker-ready').exists():
            assert time.monotonic() < deadline
            time.sleep(0.05)
        on_ready()
        deadline = time.monotonic() + 30
        while not Path('release').exists():
            assert time.monotonic() < deadline
            time.sleep(0.05)
        worker.send_signal(signal.CTRL_BREAK_EVENT)
        assert worker.wait(timeout=5) == 0
        Path('worker-stopped').touch()
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait()
"""
    try:
        result, log = launch(workspace, source, batch=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Windrecorder is ready" in result.stdout
        assert "Tray ready" in log.read_text(encoding="utf-8")
        assert "Application exited" not in log.read_text(encoding="utf-8")
    finally:
        (root / "release").touch()
    deadline = time.monotonic() + 10
    while not (root / "worker-stopped").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert (root / "worker-stopped").exists(), log.read_text(encoding="utf-8")

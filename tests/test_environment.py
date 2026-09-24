import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import manage_environment as setup


def legacy_env(root, package=None):
    env = root / ".venv"
    env.mkdir(exist_ok=True)
    (env / "pyvenv.cfg").write_text("version = 3.11.7")
    (env / "old-marker").write_text("keep me")
    if package:
        metadata = env / "Lib/site-packages" / (package + "-1.dist-info")
        metadata.mkdir(parents=True)
        (metadata / "METADATA").write_text(f"Name: {package}\nVersion: 1\n")
    return env


def runner(root, commands, *, fail=False):
    def run(command, **kwargs):
        commands.append(command)
        if "sync" in command:
            env = root / ".venv"
            env.mkdir()
            (env / "pyvenv.cfg").write_text("version = 3.12")
            if fail:
                raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    return run


def test_upgrade_retains_old_environment_assets_and_optional_extension(workspace):
    old = legacy_env(workspace, "rapidocr_onnxruntime")
    (old / "ffmpeg.exe").write_bytes(b"release asset")
    commands = []
    setup.install(workspace, "uv", run=runner(workspace, commands))
    state = setup.read_state(workspace)
    assert state["status"] == "ready"
    assert state["extras"] == ["rapidocr"]
    assert (workspace / state["backup"] / "old-marker").read_text() == "keep me"
    assert (workspace / ".venv/ffmpeg.exe").read_bytes() == b"release asset"
    assert commands[0][-2:] == ["--extra", "rapidocr"]
    assert "--locked" in commands[0] and "--inexact" in commands[0]
    report = json.loads(next((workspace / ".uv-migration").glob("*.json")).read_text())
    assert report["packages"] == {"rapidocr-onnxruntime": "1"}


def test_failed_sync_restores_old_environment_and_user_data(workspace):
    old = legacy_env(workspace)
    config = workspace / "userdata/config_user.json"
    before = config.read_bytes()
    with pytest.raises(subprocess.CalledProcessError):
        setup.install(workspace, "uv", run=runner(workspace, [], fail=True))
    assert (old / "old-marker").read_text() == "keep me"
    assert config.read_bytes() == before
    assert setup.read_state(workspace) == {}
    assert len(list(workspace.glob(".venv-failed-*"))) == 1


def test_explicit_rollback_to_poetry_remains_ready_for_offline_launch(workspace):
    legacy_env(workspace)
    setup.install(workspace, "uv", run=runner(workspace, []))
    setup.rollback(workspace)
    assert (workspace / ".venv/old-marker").read_text() == "keep me"
    assert setup.read_state(workspace)["status"] == "ready"
    assert setup.read_state(workspace)["python"] == "legacy"


def test_interrupted_upgrade_recovers_before_retry(workspace):
    old = legacy_env(workspace)
    backup = workspace / ".venv-backup-interrupted"
    journal = {"status": "installing", "backup": backup.name, "had_environment": True, "previous_state": {}}
    setup.atomic_write_json(workspace / setup.STATE_NAME, journal)
    old.rename(backup)
    old.mkdir()
    (old / "partial-install").write_text("incomplete")
    setup.install(workspace, "uv", run=runner(workspace, []))
    state = setup.read_state(workspace)
    assert (workspace / state["backup"] / "old-marker").exists()
    assert any(p.joinpath("partial-install").exists() for p in workspace.glob(".venv-failed-*"))


def test_remove_extra_is_remembered_across_updates(workspace):
    legacy_env(workspace, "uform")
    setup.atomic_write_json(workspace / setup.STATE_NAME, {"status": "ready", "extras": ["embedding", "wechat"]})
    setup.install(workspace, "uv", remove="embedding", run=runner(workspace, []))
    assert setup.read_state(workspace)["extras"] == ["wechat"]
    setup.install(workspace, "uv", run=runner(workspace, []))
    assert setup.read_state(workspace)["extras"] == ["wechat"]


def test_running_recorder_stops_upgrade_before_mutation(workspace):
    config = json.loads((workspace / "windrecorder/config_src/config_default.json").read_text())
    lock = workspace / config["lock_file_dir"] / config["record_lock_name"]
    lock.parent.mkdir(parents=True)
    lock.write_text("1234")
    with pytest.raises(RuntimeError, match="1234"):
        setup.check_not_running(workspace, alive=lambda pid: True)
    assert not (workspace / setup.STATE_NAME).exists()


def test_discover_external_poetry_environment(workspace, tmp_path_factory):
    external = tmp_path_factory.mktemp("external-poetry")
    (external / "pyvenv.cfg").write_text("version = 3.11")

    def run(command, **kwargs):
        assert command[-3:] == ["env", "info", "--path"]
        return subprocess.CompletedProcess(command, 0, stdout=str(external) + "\n")

    assert setup.discover_legacy(workspace, run) == external


@pytest.mark.parametrize("path", ["../outside", "userdata", "C:/Windows"])
def test_rollback_rejects_paths_outside_environment_backups(workspace, path):
    with pytest.raises(ValueError):
        setup.checked_backup(workspace, path)


def test_existing_user_config_restores_extensions_even_without_old_python(workspace):
    (workspace / "userdata/config_user.json").write_text(
        json.dumps({"img_embed_module_install": True, "support_ocr_lst": ["PaddleOCR", "WeChatOCR"]}), encoding="utf-8"
    )
    assert setup.select_extras(workspace, {}, {}) == {"embedding", "rapidocr", "wechat"}


def test_unrelated_venv_directory_is_not_moved(workspace):
    (workspace / ".venv").mkdir()
    (workspace / ".venv/user-file").write_text("data")
    with pytest.raises(RuntimeError, match="ordinary virtual environment"):
        setup.install(workspace, "uv", run=runner(workspace, []))
    assert (workspace / ".venv/user-file").read_text() == "data"


def test_clean_install_and_failed_clean_install(workspace):
    setup.install(workspace, "uv", run=runner(workspace, []))
    assert setup.read_state(workspace)["backup"] is None
    assert setup.read_state(workspace)["status"] == "ready"


def test_smoke_import_failure_restores_previous_environment(workspace):
    old = legacy_env(workspace)
    sync = runner(workspace, [])

    def run(command, **kwargs):
        if "-c" in command:
            raise subprocess.CalledProcessError(1, command)
        return sync(command, **kwargs)

    with pytest.raises(subprocess.CalledProcessError):
        setup.install(workspace, "uv", run=run)
    assert (old / "old-marker").exists()


def test_batch_activation_in_directory_with_spaces_and_unicode(workspace):
    root = workspace / "space and 中文"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")], check=True)
    (root / "scripts").mkdir()
    shutil.copyfile(Path(setup.__file__).with_name("activate_runtime.bat"), root / "scripts/activate_runtime.bat")
    setup.atomic_write_json(root / setup.STATE_NAME, {"status": "ready"})
    launcher = root / "check.bat"
    launcher.write_text(
        '@echo off\ncall "%~dp0scripts\\activate_runtime.bat"\n'
        "if errorlevel 1 exit /b 1\n"
        'python -c "import sys; print(ascii(sys.prefix))"\n',
        encoding="utf-8",
    )
    result = subprocess.run(["cmd", "/d", "/c", str(launcher)], capture_output=True, text=True, check=True)
    assert ascii(str(root / ".venv")) in result.stdout

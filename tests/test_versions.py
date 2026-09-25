import runpy
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests


@pytest.mark.parametrize(
    "current,remote,expected",
    [
        ("0.1.0", "0.0.31", None),
        ("0.0.31", "0.1.0", "0.1.0"),
        ("0.1.0", "0.1.0", None),
        ("1.0.0", "0.99.99", None),
        ("0.1.9", "0.1.10", "0.1.10"),
        ("0.1.0b2", "0.1.0b10", "0.1.0b10"),
        ("0.1.0", "0.1.0b10", None),
        ("0.1.0b", "0.1.0", "0.1.0"),
    ],
)
def test_update_version_order(monkeypatch, current, remote, expected):
    from windrecorder import utils

    monkeypatch.setattr(utils, "get_current_version", lambda: current)
    monkeypatch.setattr(utils, "get_github_version", lambda: remote)
    assert utils.get_new_version_if_available() == expected


def test_remote_version_is_data_and_has_a_network_timeout(monkeypatch, workspace):
    from windrecorder import utils

    def get(url, *, timeout):
        assert 0 < timeout <= 10
        return SimpleNamespace(
            text='__version__ = "0.1.0"\nopen("executed.txt", "w").write("unsafe")',
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(requests, "get", get)
    assert utils.get_github_version() == "0.1.0"
    assert not (workspace / "executed.txt").exists()


@pytest.mark.parametrize("body", ["<html>unavailable</html>", "", '__version__ = "invalid"', "__version__ = 123"])
def test_bad_remote_version_is_reported(monkeypatch, body):
    from windrecorder import utils

    monkeypatch.setattr(requests, "get", lambda *a, **kw: SimpleNamespace(text=body, raise_for_status=lambda: None))
    with pytest.raises(ValueError):
        utils.get_github_version()


def test_remote_http_failure_is_reported(monkeypatch):
    from windrecorder import utils

    def failed_status():
        raise requests.HTTPError("503")

    monkeypatch.setattr(
        requests, "get", lambda *a, **kw: SimpleNamespace(text='__version__ = "99.0.0"', raise_for_status=failed_status)
    )
    with pytest.raises(requests.HTTPError):
        utils.get_github_version()


@pytest.mark.parametrize("error", [requests.Timeout("offline"), requests.HTTPError("503"), ValueError("invalid version")])
def test_tray_menu_remains_usable_when_update_check_fails(monkeypatch, workspace, error):
    from windrecorder import utils

    def fail_check():
        raise error

    monkeypatch.setattr(utils, "get_new_version_if_available", fail_check)
    # Import a copy so main.py's working-directory setup cannot touch real data.
    source = Path(__file__).resolve().parents[1] / "main.py"
    copied = workspace / "main.py"
    shutil.copyfile(source, copied)
    module = runpy.run_path(str(copied))
    menu = module["menu_callback"]()
    update_item = next(item for item in menu if item._action is module["update"])
    assert not update_item.enabled
    assert utils.get_current_version() in update_item.text

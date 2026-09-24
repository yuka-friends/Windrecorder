"""Run application imports only after switching to a disposable workspace."""
import importlib
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "windrecorder" / "config_src", tmp_path / "windrecorder" / "config_src")
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("windrecorder.config")
    module.initialize_config()
    monkeypatch.setattr(module.config, "use_similar_ch_char_to_search", False)
    return tmp_path


@pytest.fixture
def db(workspace):
    import sqlite3

    from windrecorder.config import config
    from windrecorder.db_manager import _DBManager

    manager = _DBManager(config.db_path_ud, 20, config.user_name)
    for path in Path(manager.db_path).glob("*.db"):
        with sqlite3.connect(path) as conn:
            conn.execute("DELETE FROM video_text")
    return manager


@pytest.fixture
def make_rows():
    import pandas as pd

    from windrecorder.utils import dtstr_to_seconds

    def make(*timestamps, text="hello", title="window"):
        return pd.DataFrame([
            dict(videofile_name=t + ".mp4", picturefile_name="0.jpg", videofile_time=dtstr_to_seconds(t),
                 ocr_text=text, is_videofile_exist=True, is_picturefile_exist=False,
                 thumbnail="base64", win_title=title, deep_linking="https://example.com")
            for t in timestamps
        ])

    return make

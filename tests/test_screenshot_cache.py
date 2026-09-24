from pathlib import Path

import pytest


def test_initial_maintenance_without_any_screenshot_cache(workspace):
    from windrecorder import record

    record.index_cache_screenshots_dir_process()
    record.clean_cache_screenshots_dir_process()
    assert not Path("cache_screenshot").exists()


def test_cache_listing_keeps_existing_folder_selection(workspace):
    from windrecorder.file_utils import get_screenshots_cache_dir_lst

    cache = workspace / "cache_screenshot"
    expected = {cache / "2026-09-24_20-00-00", cache / "2026-09-24_21-00-00-VIDEO"}
    for folder in expected | {cache / "unrelated"}:
        folder.mkdir(parents=True)
    (cache / "2026-09-24_22-00-00.txt").write_text("not a directory")
    assert set(map(Path, get_screenshots_cache_dir_lst(cache))) == expected


def test_cache_listing_does_not_hide_invalid_path(workspace):
    from windrecorder.file_utils import get_screenshots_cache_dir_lst

    path = workspace / "cache_screenshot"
    path.write_text("not a directory")
    with pytest.raises(NotADirectoryError):
        get_screenshots_cache_dir_lst(path)

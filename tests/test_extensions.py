import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_memory_skill_is_discovered_with_shipped_extensions():
    from windrecorder.file_utils import get_extension

    extensions = get_extension(ROOT / "extension")
    metadata = json.loads((ROOT / "extension/windrecorder-memory/meta.json").read_text(encoding="utf-8"))
    assert extensions[metadata["extension_name"]] == metadata
    assert metadata["description_markdown"]
    assert metadata["developer_name"]
    assert metadata["developer_url"]
    assert metadata["version"]


def test_discovery_ignores_retired_and_non_extension_directories(workspace, caplog):
    from windrecorder.file_utils import get_extension

    root = workspace / "extension"
    for name in ("LLM_search_and_summary", "incomplete", "active"):
        (root / name).mkdir(parents=True)
    retired_meta = root / "LLM_search_and_summary/meta.json"
    retired_meta.write_text('{"extension_name": "Retired plugin"}', encoding="utf-8")
    (root / "active/meta.json").write_text('{"extension_name": "Active plugin"}', encoding="utf-8")
    assert list(get_extension(root)) == ["Active plugin"]
    assert not [record for record in caplog.records if record.levelname == "WARNING"]
    assert retired_meta.exists()  # Discovery itself never deletes files.


@pytest.mark.parametrize("body", ['{"unfinished":', "{}", "[]"])
def test_invalid_metadata_still_reports_its_path(workspace, caplog, body):
    from windrecorder.file_utils import get_extension

    root = workspace / "extension"
    bad = root / "bad/meta.json"
    bad.parent.mkdir(parents=True)
    bad.write_text(body, encoding="utf-8")
    assert get_extension(root) == {}
    assert str(bad) in caplog.text


def test_upgrade_removes_only_retired_bytecode_cache(workspace):
    from windrecorder.upgrade_migration_routine import cleanup_retired_extension_cache

    root = workspace / "extension"
    retired = root / "LLM_search_and_summary"
    cache = retired / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "_natural_search.cpython-311.pyc").write_bytes(b"obsolete bytecode")
    active = root / "windrecorder-memory"
    shutil.copytree(ROOT / "extension/windrecorder-memory", active)
    cleanup_retired_extension_cache(root)
    cleanup_retired_extension_cache(root)
    assert not retired.exists()
    assert (active / "meta.json").exists()


@pytest.mark.parametrize("custom_file", ["notes.txt", "__pycache__/notes.txt"])
def test_upgrade_preserves_custom_files_in_retired_directory(workspace, custom_file):
    from windrecorder.upgrade_migration_routine import cleanup_retired_extension_cache

    root = workspace / "extension"
    custom = root / "LLM_search_and_summary" / custom_file
    custom.parent.mkdir(parents=True)
    custom.write_text("user content", encoding="utf-8")
    cleanup_retired_extension_cache(root)
    assert custom.read_text(encoding="utf-8") == "user content"


def test_upgrade_does_not_follow_retired_directory_junction(workspace, tmp_path_factory):
    from windrecorder.upgrade_migration_routine import cleanup_retired_extension_cache

    external = tmp_path_factory.mktemp("external-extension")
    cache = external / "__pycache__"
    cache.mkdir()
    (cache / "keep.pyc").write_bytes(b"external file")
    root = workspace / "extension"
    root.mkdir()
    junction = root / "LLM_search_and_summary"
    subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(junction), str(external)], check=True, capture_output=True)
    try:
        cleanup_retired_extension_cache(root)
        assert (cache / "keep.pyc").read_bytes() == b"external file"
    finally:
        junction.rmdir()

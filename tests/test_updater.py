"""Exercise the actual PowerShell updater against local Git repositories."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit_file(repo, name, content):
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "-c", "user.name=Updater Test", "-c", "user.email=updater@example.invalid", "commit", "-m", name)


@pytest.fixture
def source_repo(workspace):
    repo = workspace / "source"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copyfile(ROOT / "scripts/update.ps1", scripts / "update.ps1")
    (scripts / "setup.ps1").write_text(
        "param([string]$LaunchScript)\n"
        "Set-Content -LiteralPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'setup-called.txt') -Value $LaunchScript\n"
        "exit 0\n",
        encoding="utf-8",
    )
    git(repo, "add", "scripts")
    commit_file(repo, "initial.txt", "initial version")
    return repo


@pytest.fixture
def tracked_repo(source_repo, workspace):
    repo = workspace / "checkout with spaces"
    subprocess.run(["git", "clone", str(source_repo), str(repo)], check=True, capture_output=True)
    return repo


def update(repo):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(repo / "scripts/update.ps1")],
        capture_output=True,
        text=True,
        timeout=45,
    )


def test_local_branch_without_upstream_installs_current_code(tracked_repo):
    git(tracked_repo, "switch", "-c", "codex/local-work")
    before = git(tracked_repo, "rev-parse", "HEAD")
    result = update(tracked_repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "has no upstream" in result.stdout
    assert (tracked_repo / "setup-called.txt").read_text().strip() == "onboard_setting.py"
    assert git(tracked_repo, "rev-parse", "HEAD") == before
    assert git(tracked_repo, "for-each-ref", "--format=%(upstream)", "refs/heads/codex/local-work") == ""


def test_tracked_branch_pulls_before_setup(source_repo, tracked_repo):
    commit_file(source_repo, "updated.txt", "new version")
    result = update(tracked_repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert git(tracked_repo, "rev-parse", "HEAD") == git(source_repo, "rev-parse", "HEAD")
    assert (tracked_repo / "updated.txt").read_text() == "new version"
    assert (tracked_repo / "setup-called.txt").exists()


def test_detached_revision_installs_current_code(tracked_repo):
    git(tracked_repo, "checkout", "--detach")
    before = git(tracked_repo, "rev-parse", "HEAD")
    result = update(tracked_repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "detached revision" in result.stdout
    assert (tracked_repo / "setup-called.txt").exists()
    assert git(tracked_repo, "rev-parse", "HEAD") == before
    assert git(tracked_repo, "branch", "--show-current") == ""


def test_diverged_tracking_branch_stops_before_setup(source_repo, tracked_repo):
    commit_file(source_repo, "remote-change.txt", "remote")
    commit_file(tracked_repo, "local-change.txt", "local")
    before = git(tracked_repo, "rev-parse", "HEAD")
    result = update(tracked_repo)
    assert result.returncode != 0
    assert "Git update failed" in result.stdout
    assert not (tracked_repo / "setup-called.txt").exists()
    assert git(tracked_repo, "rev-parse", "HEAD") == before


def test_unavailable_upstream_stops_before_setup(tracked_repo, workspace):
    git(tracked_repo, "remote", "set-url", "origin", str(workspace / "missing-repository"))
    result = update(tracked_repo)
    assert result.returncode != 0
    assert "Git update failed" in result.stdout
    assert not (tracked_repo / "setup-called.txt").exists()

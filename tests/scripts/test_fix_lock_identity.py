"""scripts/fix_lock_identity.py: a lock that names the upstream project must be re-pointed.

A regenerate arrives with every uv lock still naming upstream, because the rebrand deliberately
does not rewrite lockfiles (a lock holds a resolved graph). uv then refuses every strict entry
point -- pm's runtime staging, ``pm build_env``, the desktop pack, the test bootstrap -- with a
message that names no lock, so one stale string reads as four unrelated breakages.

The invariant under test is the pair's agreement: the project's own ``[[package]]`` entry carries
its manifest's ``[project]`` name, disagreements are reported rather than skipped, and a repair
touches that one entry and nothing else. ``uv lock --check`` judges the real tree; these cover the
rules without needing uv, a network, or a resolved graph.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = '[project]\nname = "{name}"\nversion = "0.0.0"\nrequires-python = ">=3.11"\n'
# Shaped like uv's own output: the project's entry is the one with an editable/virtual source.
LOCK = (
    'version = 1\nrevision = 3\nrequires-python = ">=3.11"\n\n'
    "[[package]]\n"
    'name = "{name}"\n'
    'version = "0.0.0"\n'
    'source = {{ editable = "." }}\n'
    'dependencies = ["packaging"]\n\n'
    "[[package]]\n"
    'name = "packaging"\n'
    'version = "26.3"\n'
    'source = {{ registry = "https://pypi.org/simple" }}\n'
)


def _module():
    spec = importlib.util.spec_from_file_location(
        "fix_lock_identity", REPO / "scripts" / "fix_lock_identity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project(root: Path, *, name: str = "anakot-agent", lock_name: str = "hermes-agent",
             newline: str = "\n") -> Path:
    (root / "pyproject.toml").write_text(MANIFEST.format(name=name), encoding="utf-8", newline=newline)
    lock = root / "uv.lock"
    lock.write_text(LOCK.format(name=lock_name), encoding="utf-8", newline=newline)
    return lock


def test_a_lock_naming_another_project_is_reported(tmp_path: Path) -> None:
    _project(tmp_path)
    stale = _module().stale_locks(tmp_path)
    assert [(p.name, current, wanted) for p, current, wanted in stale] == [
        ("uv.lock", "hermes-agent", "anakot-agent")]


def test_a_lock_that_already_agrees_is_not_reported(tmp_path: Path) -> None:
    _project(tmp_path, lock_name="anakot-agent")
    module = _module()
    assert module.stale_locks(tmp_path) == []
    assert module.repair_locks(tmp_path) == []


def test_repair_repoints_only_the_projects_own_entry(tmp_path: Path) -> None:
    lock = _project(tmp_path)
    module = _module()
    assert module.repair_locks(tmp_path) == [lock]
    text = lock.read_text(encoding="utf-8")
    assert 'name = "anakot-agent"' in text
    assert "hermes-agent" not in text
    # A dependency in the same file is not the project and must survive untouched.
    assert 'name = "packaging"\nversion = "26.3"' in text
    assert module.stale_locks(tmp_path) == []


def test_repair_keeps_the_newline_style(tmp_path: Path) -> None:
    """A Windows checkout can hand over CRLF; rewriting it as LF would fail the line-endings guard."""
    lock = _project(tmp_path, newline="\r\n")
    _module().repair_locks(tmp_path)
    raw = lock.read_bytes()
    assert b"\r\n" in raw and b'name = "anakot-agent"' in raw


def test_an_unreadable_lock_is_reported_not_skipped(tmp_path: Path) -> None:
    """Silence here is how a stale name survives a whole cycle: a lock we cannot vouch for is a finding."""
    (tmp_path / "pyproject.toml").write_text(MANIFEST.format(name="anakot-agent"), encoding="utf-8")
    (tmp_path / "uv.lock").write_text('version = 1\nrevision = 3\n', encoding="utf-8")
    stale = _module().stale_locks(tmp_path)
    assert [(p.name, current) for p, current, _ in stale] == [("uv.lock", "<no project entry>")]

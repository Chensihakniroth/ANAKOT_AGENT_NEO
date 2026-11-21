"""Regression tests for the lockfile and vendored-directory legs of the rebrand.

Both bugs were found by regenerating onto a fresh upstream tree and only surfaced
much later than the rebrand itself:

* ``pm/uv.lock`` kept ``hermes-pm-runtime`` while ``pm/pyproject.toml`` declared
  ``anakot-pm-runtime``, so every PM bootstrap died with a stale-lock error that
  reads as "Preparing the isolated Anakot runtime... failed".
* ``ui-tui/packages/hermes-ink`` was in ``SKIP_NAMES`` to protect the *directory*
  name, which also exempted its *contents*, leaving ``"name": "@hermes/ink"``
  while the workspace depended on ``@anakot/ink``.

The rebrand is exercised against a throwaway tree, never this checkout.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_rebrand():
    spec = importlib.util.spec_from_file_location(
        "_rebrand_under_test", REPO_ROOT / "scripts" / "rebrand.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def rebrand(tmp_path, monkeypatch):
    """The rebrand pointed at an empty throwaway tree."""
    module = _load_rebrand()
    monkeypatch.setattr(module, "REPO", str(tmp_path))
    monkeypatch.setattr(module, "BRAND", str(tmp_path / "brand"))
    return module


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _uv_lock(project: str, version: str = "0.0.0") -> str:
    return (
        'version = 1\n\n'
        '[[package]]\n'
        f'name = "{project}"\n'
        f'version = "{version}"\n'
        'source = { editable = "." }\n'
        '\n[[package]]\n'
        f'name = "requirements"\n'
        'version = "0.0.0"\n'
        'source = { virtual = "." }\n'
        'dependencies = [\n'
        f'    {{ name = "{project}", extras = ["all"] }},\n'
        ']\n'
    )


def test_pnpm_workspace_scope_follows_the_rebrand(rebrand, tmp_path):
    """`@hermes/ink` is a workspace package, `hermes-estree` is not."""
    _write(tmp_path, "pnpm-lock.yaml", (
        "  ui-tui:\n"
        "    dependencies:\n"
        "      '@hermes/ink':\n"
        "        specifier: workspace:*\n"
        "        version: link:packages/hermes-ink\n"
        "  hermes-parser@0.25.1: {}\n"
    ))

    assert rebrand.rewrite_lockfiles(apply=True) == ["pnpm-lock.yaml"]

    text = (tmp_path / "pnpm-lock.yaml").read_text(encoding="utf-8")
    assert "'@anakot/ink':" in text
    assert "@hermes/" not in text
    # A third-party package and the vendored path are not the rebrand's business.
    assert "hermes-parser@0.25.1" in text
    assert "link:packages/hermes-ink" in text


@pytest.mark.parametrize(
    ("project", "lock", "before", "after"),
    [
        ("pyproject.toml", "uv.lock", "hermes-agent", "anakot-agent"),
        ("pm/pyproject.toml", "pm/uv.lock", "hermes-pm-runtime", "anakot-pm-runtime"),
    ],
)
def test_uv_lock_takes_the_name_its_pyproject_declares(
    rebrand, tmp_path, project, lock, before, after
):
    """uv records a local project by name, at `name =` and in every extras marker."""
    _write(tmp_path, project, f'[project]\nname = "{before}"\nversion = "0.0.0"\n')
    _write(tmp_path, lock, _uv_lock(before))

    assert rebrand.rewrite_lockfiles(apply=True) == [lock]

    text = (tmp_path / lock).read_text(encoding="utf-8")
    assert f'name = "{after}"' in text
    assert f'{{ name = "{after}", extras = ["all"] }}' in text
    assert before not in text


def test_verify_fails_when_a_lock_still_names_the_pre_rename_package(rebrand, tmp_path):
    """The pm/uv.lock break: a lock that never followed the rename must fail the gate."""
    _write(tmp_path, "pm/pyproject.toml", '[project]\nname = "anakot-pm-runtime"\n')
    _write(tmp_path, "pm/uv.lock", _uv_lock("hermes-pm-runtime"))

    failures = rebrand.verify_lock_identity()

    assert len(failures) == 2  # does not name the project, and still names the old one
    assert all("pm/uv.lock" in line for line in failures)


def test_verify_passes_once_the_lock_matches_the_tree(rebrand, tmp_path):
    _write(tmp_path, "pm/pyproject.toml", '[project]\nname = "anakot-pm-runtime"\n')
    _write(tmp_path, "pm/uv.lock", _uv_lock("anakot-pm-runtime"))
    _write(tmp_path, "pnpm-lock.yaml", "      '@anakot/ink':\n")

    assert rebrand.verify_lock_identity() == []


def test_vendored_ink_keeps_its_directory_name_and_loses_the_old_package(rebrand, tmp_path):
    """KEEP_PATH_NAMES: the folder is an on-disk marker, the text inside is ours."""
    _write(
        tmp_path,
        "ui-tui/packages/hermes-ink/package.json",
        '{\n  "name": "@hermes/ink",\n  "version": "0.0.0"\n}\n',
    )

    assert rebrand.walk_files() == ["ui-tui/packages/hermes-ink/package.json"]

    rebrand.rewrite_tree([], apply=True)

    assert (tmp_path / "ui-tui/packages/hermes-ink/package.json").is_file()
    text = (tmp_path / "ui-tui/packages/hermes-ink/package.json").read_text(encoding="utf-8")
    assert '"name": "@anakot/ink"' in text


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_completeness_maps_a_capitalised_filename_rename(rebrand, tmp_path):
    """`HermesConsoleModal.tsx` becomes `AnakotConsoleModal.tsx`; the index still says Hermes.

    The check used to lowercase only, so this rename read as a lost file and failed the gate on
    a tree where nothing was wrong.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    old = _write(tmp_path, "web/src/components/HermesConsoleModal.tsx", "export {}\n")
    _git(tmp_path, "add", "-A")
    old.rename(tmp_path / "web/src/components/AnakotConsoleModal.tsx")

    assert rebrand.verify_completeness([]) == []


def test_completeness_still_reports_a_genuinely_lost_file(rebrand, tmp_path):
    """The other half of the contract: silence here is how 570 modules went missing."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _write(tmp_path, "hermes_cli/gone.py", "x = 1\n")
    _git(tmp_path, "add", "-A")
    (tmp_path / "hermes_cli/gone.py").unlink()

    assert rebrand.verify_completeness([]) == ["hermes_cli/gone.py"]
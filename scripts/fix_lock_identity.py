#!/usr/bin/env python3
"""Re-point every uv lock at its own manifest's project name, then let uv confirm it.

Lockfiles are checked in, and the rebrand deliberately does not rewrite them (rewriting a
resolved graph textually is unsafe), so a regenerate leaves each lock naming the *upstream*
project while its `pyproject.toml` names the fork's. uv then refuses the tree everywhere it
is asked to be strict:

    error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.

That surfaces as four unrelated-looking breakages -- pm's runtime staging, `pm build_env`,
the desktop pack step, and `scripts/run_tests.sh`'s bootstrap -- none of which names a lock,
so the real cause is a single stale string. Fixing it by hand every cycle is how it gets
missed; this script owns it instead, and `scripts/rebrand.py` imports it, so a
regenerate can neither ship past nor verify past a stale lock.

Only the root/virtual package entry is touched, so resolved versions and hashes stay exactly
as they were. `uv lock --check` (offline first, like pm.environment.check_lock) is the
authority on whether that was enough: if any reference is still stale, uv says so and we
fail loudly rather than shipping a tree that cannot be staged.

Usage:
    python scripts/fix_lock_identity.py [root]     # fix stale locks, verify each one
    python scripts/fix_lock_identity.py --check    # report only; exit 1 when stale
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".mypy_cache"}
MANIFEST_NAME = re.compile(r'^name\s*=\s*"([^"]+)"', re.MULTILINE)
# The entry uv writes for the project the lock belongs to, as opposed to a dependency.
ROOT_SOURCE = re.compile(r'^source\s*=\s*\{\s*(?:editable|virtual)\s*=\s*"\."\s*\}\s*\r?$', re.MULTILINE)
PACKAGE_HEAD = re.compile(r'^\[\[package\]\]\r?$', re.MULTILINE)


def uv_projects(root: Path | str) -> list[tuple[Path, Path]]:
    """Every (manifest, lock) pair in the tree. Accepts a str so a caller working in os.path
    terms (``rebrand.py``) needs no pathlib of its own."""
    root = Path(root)
    found = []
    for lock in sorted(root.rglob("uv.lock")):
        if SKIP_DIRS & set(lock.parts):
            continue
        manifest = lock.parent / "pyproject.toml"
        if manifest.is_file():
            found.append((manifest, lock))
    return found


def manifest_name(manifest: Path) -> str | None:
    match = MANIFEST_NAME.search(manifest.read_text(encoding="utf-8-sig"))
    return match.group(1) if match else None


def root_entry(text: str) -> tuple[int, int, str] | None:
    """Span and name of the project's own [[package]] entry, or None."""
    for block in PACKAGE_HEAD.finditer(text):
        start = block.end()
        end = text.find("[[package]]", start)
        end = len(text) if end == -1 else end
        if ROOT_SOURCE.search(text, start, end):
            name = re.search(r'^name\s*=\s*"([^"]+)"', text[start:end], re.MULTILINE)
            if name:
                # Absolute span of the name literal inside the lock.
                return start + name.start(1), start + name.end(1), name.group(1)
    return None


def _verify(directory: Path) -> tuple[bool, str]:
    """Ask uv whether the lock is current. Offline first: online re-downloads direct-URL
    wheels, so one unreachable asset would report a correct lock as stale."""
    for args in (["lock", "--check", "--offline"], ["lock", "--check"]):
        try:
            result = subprocess.run(["uv", *args], cwd=directory, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=600,
                                    check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"could not run uv: {exc}"
        if result.returncode == 0:
            return True, "uv lock --check: current"
    return False, (result.stderr or result.stdout).strip().splitlines()[-1] if (result.stderr or result.stdout) else "stale"


def stale_locks(root: Path) -> list[tuple[Path, str, str]]:
    """``(lock, name_in_lock, manifest_name)`` for every lock that disagrees with its manifest.

    A lock whose project entry cannot be located is reported as ``<no project entry>`` rather
    than skipped: silence here is how a stale name survives a whole cycle unnoticed.
    """
    stale: list[tuple[Path, str, str]] = []
    for manifest, lock in uv_projects(root):
        name = manifest_name(manifest)
        if not name:
            continue
        raw = lock.read_text(encoding="utf-8-sig", newline="")
        entry = root_entry(raw)
        if entry is None:
            if name not in raw:
                stale.append((lock, "<no project entry>", name))
        elif entry[2] != name:
            stale.append((lock, entry[2], name))
    return stale


def repair_locks(root: Path) -> list[Path]:
    """Re-point every stale lock at its manifest's name, preserving newline style."""
    fixed: list[Path] = []
    for manifest, lock in uv_projects(root):
        name = manifest_name(manifest)
        if not name:
            continue
        raw = lock.read_text(encoding="utf-8-sig", newline="")
        entry = root_entry(raw)
        if entry is None or entry[2] == name:
            continue
        start, end, _ = entry
        lock.write_text(raw[:start] + name + raw[end:], encoding="utf-8", newline="")
        fixed.append(lock)
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=".", help="checkout root (default: cwd)")
    parser.add_argument("--check", action="store_true", help="report stale locks, change nothing")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    projects = uv_projects(root)
    if not projects:
        print("no uv project (pyproject.toml beside uv.lock) found", file=sys.stderr)
        return 1

    if args.check:
        for lock, current, wanted in stale_locks(root):
            print(f"  {lock.relative_to(root).as_posix()}: STALE -- lock says {current!r}, "
                  f"manifest says {wanted!r}")
    else:
        for lock in repair_locks(root):
            print(f"  {lock.relative_to(root).as_posix()}: re-pointed at its manifest's name")

    failed = 0
    for _manifest, lock in projects:
        ok, detail = _verify(lock.parent)
        print(f"  {lock.relative_to(root).as_posix()}: {'OK' if ok else 'STILL STALE'} -- {detail}")
        failed += 0 if ok else 1

    if failed:
        print(f"\n{failed} lock(s) need attention: uv refuses a tree whose lock disagrees with its "
              "manifest, which pm's staging and the test bootstrap report as a missing "
              "environment.", file=sys.stderr)
        return 1
    print("\nall locks agree with their manifests and uv confirms it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

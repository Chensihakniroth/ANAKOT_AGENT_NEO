#!/usr/bin/env python3
"""Re-apply the Anakot rebrand to a Hermes tree, without breaking Hermes services.

The rebrand is a case-preserving ``hermes`` -> ``anakot`` substitution across
file contents and paths. What makes that safe is *masking*: every string in
``brand/protected-strings.txt`` is swapped for an opaque token first, restored
last, so a live wire (docs/API URLs, the upstream repo, on-disk markers, plugin
protocol globals) is never rewritten.

Brand-owned images keep their upstream filenames, so an upstream sync would
silently replace them with upstream art. ``brand/assets/`` holds the sources and
``brand/assets.manifest.json`` the hashes; ``--verify`` fails when a brand file
no longer matches, and ``--apply`` restores it.

    python scripts/rebrand.py --check      # dry run: report, write nothing
    python scripts/rebrand.py --apply      # rewrite tree + restore brand assets
    python scripts/rebrand.py --verify     # gate: protected strings + asset hashes

ponytail: text rewrite is byte-level substitution, not AST. It cannot tell a
docstring from a format string -- that is why the protected list exists and why
--verify runs the whole tree twice. Ceiling: a protected string that upstream
invents *after* the list was written. Upgrade path: --verify fails, add a rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = os.path.join(REPO, "brand")

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", ".cache",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".next", ".turbo", "coverage", "test-results", "playwright-report",
    ".pnpm", ".pnpm-store", "site-packages", ".idea", ".vscode",
}
# Build OUTPUT trees only. ``scripts/build/`` is SOURCE and must be rewritten:
# web.mjs, tui.mjs and node-deps.mjs all carried rebrand bugs.
SKIP_PATHS = (
    "brand/",                      # the rebrand's own inputs (protect list, manifest, masters)
    "scripts/rebrand.py",          # this script rewrites text; never itself
    "plugins/anakot-achievements/dashboard/dist/",
    "plugins/kanban/dashboard/dist/",
    "apps/desktop/release/",
    "apps/desktop/build/",
    "ui-tui/dist/",
    "web/dist/",
    "website/build/",
    "website/.docusaurus/",
)
# Never rewritten even if they contain "hermes": binary-ish sources, locks.
SKIP_FILES = {"pnpm-lock.yaml", "uv.lock", "package-lock.json", "yarn.lock"}
# On-disk compatibility markers: existing installs and built dists use these
# exact names (frontend-common.mjs productOwners, freshness.mjs receipts).
SKIP_NAMES = {".hermes-product", "hermes-build.json", ".hermes-stale", ".hermes-node-deps", "hermes-ink"}

SUBSTITUTIONS = (("Hermes", "Anakot"), ("HERMES", "ANAKOT"), ("hermes", "anakot"))


def load_protected(path: str | None = None) -> list[tuple[str, re.Pattern]]:
    path = path or os.path.join(BRAND, "protected-strings.txt")
    rules = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pattern = line.split("#")[0].strip()
            if pattern:
                rules.append((pattern, re.compile(pattern, re.IGNORECASE)))
    return rules


def _skip(rel: str, name: str) -> bool:
    if name in SKIP_FILES or name in SKIP_NAMES:
        return True
    return rel.startswith(SKIP_PATHS)


def rewrite_text(text: str, rules: list[tuple[str, re.Pattern]]) -> tuple[str, list[str]]:
    """Mask protected spans, substitute, restore. Returns (new_text, protected_hits)."""
    hits: list[str] = []
    masked: list[str] = []

    def stash(match: re.Match) -> str:
        hits.append(match.group(0))
        masked.append(match.group(0))
        return f"\x00{len(masked) - 1}\x00"

    for _, rx in rules:
        text = rx.sub(stash, text)

    for src, dst in SUBSTITUTIONS:
        text = text.replace(src, dst)

    for idx, original in enumerate(masked):
        text = text.replace(f"\x00{idx}\x00", original)
    return text, hits


def count_protected(text: str, rules: list[tuple[str, re.Pattern]]) -> int:
    return sum(len(rx.findall(text)) for _, rx in rules)


def walk_files() -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        rel_dir = os.path.relpath(dirpath, REPO).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not _skip(f"{rel_dir}/{d}/".lstrip("/"), d)
        ]
        for name in filenames:
            rel = f"{rel_dir}/{name}".lstrip("/")
            if _skip(rel, name):
                continue
            out.append(rel)
    return out


def rename_paths(apply: bool) -> list[tuple[str, str]]:
    """Rename any path segment containing 'hermes', deepest first."""
    changes: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(REPO, topdown=False):
        rel_dir = os.path.relpath(dirpath, REPO).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        parts = rel_dir.split("/") if rel_dir else []
        if any(p in SKIP_DIRS for p in parts):
            continue
        if any(_skip(f"{rel_dir}/", p) for p in parts):
            continue
        for name in filenames + dirnames:
            lower = name.lower()
            if "hermes" not in lower or name in SKIP_FILES or name in SKIP_NAMES:
                continue
            new = name.replace("Hermes", "Anakot").replace("HERMES", "ANAKOT").replace("hermes", "anakot")
            if new == name:
                continue
            src = os.path.join(dirpath, name)
            dst = os.path.join(dirpath, new)
            changes.append((os.path.relpath(src, REPO), os.path.relpath(dst, REPO)))
            if apply:
                if os.path.exists(dst):
                    print(f"  ! skip rename, target exists: {dst}")
                    continue
                os.rename(src, dst)
    return changes


def restore_assets(apply: bool) -> list[str]:
    """Copy brand/assets/** over the tree; report files that differ beforehand."""
    src_root = os.path.join(BRAND, "assets")
    drifted = []
    if not os.path.isdir(src_root):
        return drifted
    for dirpath, _, filenames in os.walk(src_root):
        for name in filenames:
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, src_root)
            dst = os.path.join(REPO, rel)
            same = os.path.isfile(dst) and _sha(src) == _sha(dst)
            if not same:
                drifted.append(rel.replace("\\", "/"))
                if apply:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(src, "rb") as fh, open(dst, "wb") as out:
                        out.write(fh.read())
    return drifted


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_assets() -> list[str]:
    manifest_path = os.path.join(BRAND, "assets.manifest.json")
    if not os.path.isfile(manifest_path):
        return []
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)["files"]
    bad = []
    for rel, meta in manifest.items():
        full = os.path.join(REPO, rel.replace("/", os.sep))
        if not os.path.isfile(full):
            bad.append(f"missing  {rel}")
        elif _sha(full)[:16] != meta["sha256"]:
            bad.append(f"CHANGED  {rel}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-apply the Anakot rebrand to a Hermes tree.")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--check", action="store_true", help="report only (default)")
    ap.add_argument("--verify", action="store_true", help="gate on protected strings + asset hashes")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    rules = load_protected()
    files = walk_files()
    rewritten, protected_total, path_changes = [], 0, []

    for rel in files:
        full = os.path.join(REPO, rel.replace("/", os.sep))
        try:
            with open(full, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "hermes" not in text.lower():
            continue
        protected_total += count_protected(text, rules)
        new_text, _ = rewrite_text(text, rules)
        if new_text != text:
            rewritten.append(rel)
            if args.apply:
                with open(full, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new_text)

    path_changes = rename_paths(apply=args.apply)
    drifted = restore_assets(apply=args.apply)
    asset_bad = verify_assets()

    if not args.quiet:
        mode = "APPLY" if args.apply else "CHECK (dry run)"
        print(f"[{mode}] {len(files)} files scanned")
        print(f"  protected occurrences : {protected_total}")
        print(f"  content rewrites      : {len(rewritten)}")
        print(f"  path renames          : {len(path_changes)}")
        print(f"  brand files drifted   : {len(drifted)}  ({'restored' if args.apply else 'would restore'})")
        for d in drifted[:8]:
            print(f"      {d}")
        if asset_bad:
            print(f"  asset manifest MISMATCH: {len(asset_bad)}")
            for b in asset_bad[:8]:
                print(f"      {b}")

    if args.verify:
        ok = not asset_bad
        print("VERIFY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
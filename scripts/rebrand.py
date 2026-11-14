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
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = os.path.join(REPO, "brand")

# ─── install-path repoint ───────────────────────────────────────────────────
# These four files decide where a NEW machine installs from. Upstream's defaults
# point at Hermes, so without this a fresh install clones and runs upstream —
# the rebrand never gets a chance to apply. Applied before the protect mask,
# because the URLs being replaced are themselves protected upstream strings.
#
# File-scoped and surgical on purpose. The fork guards (install.sh's
# `nousresearch/hermes-agent` grep, install.ps1's `$Origin -notmatch ...` regex)
# MUST keep saying hermes-agent: they are how the scripts recognise "this is not
# the official repo, so publish no release and follow the branch". Repoint one
# and a fresh install goes looking for a release on a repo that has none, then
# stops. The docs/catalog/plugin URLs also stay upstream: those are live services
# this fork still uses.
FORK = "Chensihakniroth/ANAKOT_AGENT_NEO"
INSTALL_REPO_EDITS: dict[str, tuple[tuple[str, str], ...]] = {
    "scripts/install.sh": (
        ("https://github.com/NousResearch/hermes-agent.git", f"https://github.com/{FORK}.git"),
        ("https://api.github.com/repos/NousResearch/hermes-agent/releases/latest",
         f"https://api.github.com/repos/{FORK}/releases/latest"),
        ("https://github.com/NousResearch/hermes-agent/releases/latest",
         f"https://github.com/{FORK}/releases/latest"),
    ),
    "scripts/install.ps1": (
        ('else { "https://github.com/NousResearch/hermes-agent.git" }', f'else {{ "https://github.com/{FORK}.git" }}'),
        ("https://api.github.com/repos/NousResearch/hermes-agent/releases/latest",
         f"https://api.github.com/repos/{FORK}/releases/latest"),
        ("https://github.com/NousResearch/hermes-agent/releases/latest",
         f"https://github.com/{FORK}/releases/latest"),
    ),
    "scripts/install.cmd": (
        ("https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.cmd",
         f"https://raw.githubusercontent.com/{FORK}/main/scripts/install.cmd"),
    ),
    "apps/bootstrap-installer/src-tauri/src/install_script.rs": (
        ("https://raw.githubusercontent.com/NousResearch/hermes-agent/{}/scripts/{}",
         f"https://raw.githubusercontent.com/{FORK}/{{}}/scripts/{{}}"),
    ),
    # Project identity: package metadata (repository/issues/homepage). A sync restores
    # upstream's own URLs, which would advertise a project that is not this one.
    "package.json": (
        ("github.com/NousResearch/Hermes-Agent", f"github.com/{FORK}"),
        ("github.com/NousResearch/hermes-agent", f"github.com/{FORK}"),
        ("github.com/NousResearch/Anakot-Agent", f"github.com/{FORK}"),
    ),
    "apps/desktop/package.json": (
        ("github.com/NousResearch/hermes-agent", f"github.com/{FORK}"),
    ),
}

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
    # The porting ledger names upstream ("Hermes-specific", `hermes_*` renames) as DATA about the
    # relationship between the two trees. Rewriting it produces "Anakot-specific" and
    # "anakot_* -> anakot_*", i.e. it destroys the meaning it exists to record.
    "UPSTREAM_PORTING.md",
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
SKIP_NAMES = {".hermes-product", "hermes-build.json", ".hermes-stale", ".hermes-node-deps"}
# Path names a rename must keep, while their CONTENTS are still ours to rewrite.
# The vendored ink fork keeps its upstream folder name (``build:ink`` and the lockfile's
# ``link:packages/hermes-ink`` point at it) but its package is ``@anakot/ink``. Keeping this in
# SKIP_NAMES instead also exempted every file inside from the text rewrite, which left
# ``"name": "@hermes/ink"`` while the workspace depended on ``@anakot/ink``.
KEEP_PATH_NAMES = {"hermes-ink"}

SUBSTITUTIONS = (("Hermes", "Anakot"), ("HERMES", "ANAKOT"), ("hermes", "anakot"))


def load_protected(path: str | None = None) -> list[tuple[str, re.Pattern]]:
    path = path or os.path.join(BRAND, "protected-strings.txt")
    rules = []
    with open(path, encoding="utf-8-sig") as fh:
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


def rename_paths(apply: bool) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Rename any path segment containing 'hermes', deepest first.

    Returns ``(changes, conflicts)``. A conflict is a rename whose target already exists — the
    common cause is an ignored leftover (``node_modules``, ``data/``, ``.venv``) inside a directory
    the rebrand wants to rename, because ``git clean -fd`` does not remove ignored paths. Skipping
    those silently left BOTH trees in place (``hermes_cli/`` next to ``anakot_cli/``) and every
    later step happily operated on a half-rebranded checkout, so the caller now aborts instead.
    """
    changes: list[tuple[str, str]] = []
    conflicts: list[tuple[str, str]] = []
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
            if "hermes" not in lower or name in SKIP_FILES or name in SKIP_NAMES or name in KEEP_PATH_NAMES:
                continue
            new = name.replace("Hermes", "Anakot").replace("HERMES", "ANAKOT").replace("hermes", "anakot")
            if new == name:
                continue
            src = os.path.join(dirpath, name)
            dst = os.path.join(dirpath, new)
            rel_src = os.path.relpath(src, REPO)
            rel_dst = os.path.relpath(dst, REPO)
            if os.path.exists(dst):
                conflicts.append((rel_src, rel_dst))
                continue
            changes.append((rel_src, rel_dst))
            if apply:
                os.rename(src, dst)
    return changes, conflicts


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
            if rel.replace("\\", "/") in GENERATED:
                continue
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


def _generated_targets() -> set[str]:
    """Paths owned by the icon generator (``scripts/generate_icons.py`` TARGETS).

    Those files are rendered from the masters, so guarding their bytes would flag
    every regeneration as drift — and ``--apply`` would then revert the brand to a
    stale render, undoing the generator. The generator owns them, not this
    snapshot. Loaded from the module rather than parsed: half the list comes from
    ``appx_targets()``, which a static read would silently miss. If the module
    cannot load (no resvg-py/Pillow), fall back to guarding everything."""
    path = os.path.join(REPO, "scripts", "generate_icons.py")
    if not os.path.isfile(path):
        return set()
    spec = importlib.util.spec_from_file_location("_generate_icons", path)
    if spec is None or spec.loader is None:
        return set()
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return set()
    return {entry[0] for entry in module.TARGETS}


GENERATED = _generated_targets()


def _snapshot_rels() -> list[str]:
    """Brand-art paths the snapshot keeps (relative, posix), minus generator-owned
    targets. The snapshot tree is the brand set: dropping a copy drops it."""
    root = os.path.join(BRAND, "assets")
    rels = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace("\\", "/")
            if rel not in GENERATED:
                rels.append(rel)
    return sorted(rels)


def rebaseline() -> tuple[int, int]:
    """Re-snapshot the brand art from the tree and refresh the manifest hashes.

    Run after deliberately changing brand art. The snapshot is the rebrand's
    memory of what the brand looks like, so a stale one makes ``--apply`` revert
    the tree to the previous art. A file whose copy was removed from the snapshot
    is dropped from the manifest (that is how brand art is retired)."""
    manifest_path = os.path.join(BRAND, "assets.manifest.json")
    with open(manifest_path, encoding="utf-8-sig") as fh:
        manifest = json.load(fh)
    files = manifest["files"]
    root = os.path.join(BRAND, "assets")
    kept, dropped = 0, 0
    for rel in _snapshot_rels():
        src = os.path.join(REPO, rel.replace("/", os.sep))
        snap = os.path.join(root, rel.replace("/", os.sep))
        if os.path.isfile(src):
            shutil.copyfile(src, snap)
            files[rel] = {"bytes": os.path.getsize(src), "sha256": _sha(src)[:16]}
            kept += 1
        else:
            os.remove(snap)
            files.pop(rel, None)
            dropped += 1
    manifest["count"] = len(files)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return kept, dropped


def verify_assets() -> list[str]:
    manifest_path = os.path.join(BRAND, "assets.manifest.json")
    if not os.path.isfile(manifest_path):
        return []
    with open(manifest_path, encoding="utf-8-sig") as fh:
        manifest = json.load(fh)["files"]
    bad = []
    for rel, meta in manifest.items():
        if rel in GENERATED:
            continue
        full = os.path.join(REPO, rel.replace("/", os.sep))
        if not os.path.isfile(full):
            bad.append(f"missing  {rel}")
        elif _sha(full)[:16] != meta["sha256"]:
            bad.append(f"CHANGED  {rel}")
    return bad


def rewrite_tree(rules: list[tuple[str, re.Pattern]], apply: bool) -> tuple[list[str], int, int]:
    """Rewrite every file's content. Returns (rewritten paths, files scanned, protected hits)."""
    files = walk_files()
    rewritten, protected_total = [], 0
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
        original = text
        for old, new in INSTALL_REPO_EDITS.get(rel, ()):
            text = text.replace(old, new)
        if "hermes" not in text.lower() and text == original:
            continue
        protected_total += count_protected(text, rules)
        new_text, _ = rewrite_text(text, rules)
        if new_text != original:
            rewritten.append(rel)
            if apply:
                with open(full, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new_text)
    return rewritten, len(files), protected_total


def report(apply: bool, scanned: int, protected_total: int, rewritten: list[str],
           path_changes: list[tuple[str, str]], path_conflicts: list[tuple[str, str]],
           drifted: list[str], asset_bad: list[str]) -> None:
    mode = "APPLY" if apply else "CHECK (dry run)"
    print(f"[{mode}] {scanned} files scanned")
    print(f"  protected occurrences : {protected_total}")
    print(f"  content rewrites      : {len(rewritten)}")
    print(f"  path renames          : {len(path_changes)}")
    if path_conflicts:
        print(f"  path rename CONFLICTS : {len(path_conflicts)}  (target already exists)")
        for src, dst in path_conflicts[:8]:
            print(f"      {src}  ->  {dst}")
    print(f"  brand files drifted   : {len(drifted)}  ({'restored' if apply else 'would restore'})")
    for d in drifted[:8]:
        print(f"      {d}")
    if asset_bad:
        print(f"  asset manifest MISMATCH: {len(asset_bad)}")
        for b in asset_bad[:8]:
            print(f"      {b}")


def verify_completeness(path_changes: list[tuple[str, str]]) -> list[str]:
    """Index paths that are neither on disk nor on disk under their rebranded name.

    The other three legs all ask "is work still pending?", so a file that was *lost* passes every
    one of them: no rewrite is owed, no rename is owed, no asset drifted. That is not theoretical
    -- a tree missing 570 renamed modules once reported ``VERIFY: PASS``. Only asking the index
    catches it, so a lost file and a rename that quietly never happened both fail here.
    """
    pending_src = {src for src, _ in path_changes}
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []  # not a checkout (a plain tree copy): completeness is undefined, not failed
    missing = []
    for rel in filter(None, listed.split("\0")):
        if rel in pending_src or os.path.exists(os.path.join(REPO, rel.replace("/", os.sep))):
            continue
        rebranded = "/".join(re.sub(r"hermes", "anakot", part) for part in rel.split("/"))
        if rebranded != rel and os.path.exists(os.path.join(REPO, rebranded.replace("/", os.sep))):
            continue
        missing.append(rel)
    return missing


def verify_failures(rewritten: list[str], path_changes: list[tuple[str, str]],
                    drifted: list[str], asset_bad: list[str], missing: list[str]) -> list[str]:
    """Every kind of pending work, as report lines. Empty means the tree is fully rebranded.

    A gate that only looks at asset hashes passes a half-rebranded tree: a rename that collided
    (``target exists``) leaves ``hermes_cli/`` standing while every brand file is intact, and the
    next ``git add -A`` ships both trees. So any pending work fails the gate.
    """
    out: list[str] = []
    for label, items in (
        ("file(s) still need a content rewrite", rewritten),
        ("path(s) still need a rename", [f"{s}  ->  {d}" for s, d in path_changes]),
        ("brand file(s) still drifted", drifted),
        ("asset manifest mismatch(es)", asset_bad),
        ("file(s) in the index with neither the old nor the new path on disk", missing),
    ):
        if items:
            out.append(f"  {len(items)} {label}:")
            out.extend(f"      {item}" for item in items[:8])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-apply the Anakot rebrand to a Hermes tree.")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--check", action="store_true", help="report only (default)")
    ap.add_argument("--verify", action="store_true", help="gate on protected strings + asset hashes")
    ap.add_argument("--rebaseline", action="store_true", help="re-snapshot brand art + refresh manifest hashes")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.rebaseline:
        kept, dropped = rebaseline()
        print(f"[REBASELINE] {kept} brand files re-snapshotted, {dropped} dropped")
        return 0

    rewritten, scanned, protected_total = rewrite_tree(load_protected(), args.apply)
    path_changes, path_conflicts = rename_paths(apply=args.apply)
    drifted = restore_assets(apply=args.apply)
    asset_bad = verify_assets()

    if not args.quiet:
        report(args.apply, scanned, protected_total, rewritten, path_changes, path_conflicts,
               drifted, asset_bad)

    if path_conflicts:
        print("ABORT: a rename target already exists (an ignored leftover inside that directory).")
        print("       Remove it and re-run; a half-renamed tree must never be committed.")
        return 2

    if args.verify:
        failures = verify_failures(rewritten, path_changes, drifted, asset_bad,
                                  verify_completeness(path_changes))
        print("VERIFY:", "PASS" if not failures else "FAIL")
        print("\n".join(failures))
        return 0 if not failures else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
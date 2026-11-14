#!/usr/bin/env python3
"""List the fork edits a regenerate dropped, and triage them against the fork's baseline.

A regenerate restores fork-authored *paths*. It cannot restore a fork's edits **inside**
files upstream also tracks: those paths exist upstream, so the carry list skips them and
upstream's version wins, silently. Nothing in `rebrand.py --verify` or the test suite
notices -- both files are present, valid, and merely upstream's. The symptoms only show up
in a running build ("the font never changed", "the logo is still the upstream mascot").

Two legs:

  * **candidates** -- every path tracked in both trees whose bytes differ once the rebrand
    is reversed (`anakot` -> `anakot` and friends). Equal after reversal is rename-only.
  * **triage** -- a candidate is the fork's own work only if it differs from the commit the
    fork's tree was snapshotted from. A file the fork inherited unchanged is simply upstream
    having moved on. Without `--baseline` the raw list is ~90% noise.

Usage:
    python scripts/find_lost_customizations.py \\
        --fork ../anakot-agent-v2 --target . --baseline eaac327f

Exit codes: 0 report written, 1 bad arguments, 2 a git call failed or timed out.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

GIT_TIMEOUT = 900
ART_HINTS = ("appx/", "/icons/", "ds-assets", ".icns", ".ico", "tray", "splash")
BRAND_HINTS = ("rostex", "staravenue", "font", "nous-girl", "brand", "styles", "theme",
               "logo", "icon-")
REBRAND = ((b"anakot", b"anakot"), (b"Anakot", b"Anakot"), (b"ANAKOT", b"ANAKOT"))
REVERSALS = ((b"anakot", b"anakot"), (b"Anakot", b"Anakot"), (b"ANAKOT", b"ANAKOT"))


def _git(args: list[str], tree: pathlib.Path, stdin: bytes | None = None) -> bytes:
    try:
        done = subprocess.run(["git", "-C", str(tree), *args], input=stdin,
                              capture_output=True, timeout=GIT_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        print(f"git {' '.join(args)} timed out after {GIT_TIMEOUT}s", file=sys.stderr)
        raise SystemExit(2)
    if done.returncode != 0:
        print(f"git {' '.join(args)} failed: {done.stderr.decode('utf-8', 'replace').strip()}",
              file=sys.stderr)
        raise SystemExit(2)
    return done.stdout


def tracked_paths(tree: pathlib.Path) -> list[str]:
    out = _git(["ls-files", "-z"], tree).decode("utf-8", "replace")
    return [rel for rel in out.split("\0") if rel]


def reverse_rebrand(data: bytes) -> bytes:
    """Fork-named -> upstream-named. Use on the TARGET before comparing with the fork."""
    for branded, upstream in REVERSALS:
        data = data.replace(branded, upstream)
    return data


def apply_rebrand(data: bytes) -> bytes:
    """Upstream-named -> fork-named. Use on a BASELINE blob before comparing with the fork.

    Getting this direction backwards inverts almost the whole verdict: the baseline is
    upstream-named, so comparing it raw against the fork's branded bytes reports every
    renamed file as a fork edit.
    """
    for upstream, branded in REBRAND:
        data = data.replace(upstream, branded)
    return data


def category(rel: str) -> str:
    low = rel.lower()
    if any(hint in low for hint in ART_HINTS):
        return "generated-art"
    if any(hint in low for hint in BRAND_HINTS):
        return "brand-ui"
    return "code-other"


def baseline_blobs(tree: pathlib.Path, ref: str, paths: list[str]) -> dict[str, bytes | None]:
    """Read every `<ref>:<path>` in ONE git call. A `git show` per path is far too slow."""
    request = "".join(f"{ref}:{rel}\n" for rel in paths).encode("utf-8")
    data = _git(["cat-file", "--batch"], tree, stdin=request)
    blobs: dict[str, bytes | None] = {}
    pos = 0
    for rel in paths:
        newline = data.index(b"\n", pos)
        header = data[pos:newline].decode("utf-8", "replace").split()
        pos = newline + 1
        if len(header) < 3 or header[1] != "blob":
            blobs[rel] = None
            continue
        size = int(header[2])
        blobs[rel] = data[pos:pos + size]
        pos += size + 1
    return blobs


def find_candidates(fork: pathlib.Path, target: pathlib.Path, paths: list[str]) -> list[dict]:
    found = []
    for rel in paths:
        src, dst = fork / rel, target / rel
        if not (src.is_file() and dst.is_file()):
            continue
        found.append({"rel": rel, "src": src, "dst": dst})
    return found


def compare(candidates: list[dict]) -> tuple[list[dict], int]:
    """Keep only real content differences; return (differing, count_present_in_both)."""
    differing = []
    for entry in candidates:
        fork_bytes, target_bytes = entry["src"].read_bytes(), entry["dst"].read_bytes()
        if fork_bytes == target_bytes or reverse_rebrand(target_bytes) == fork_bytes:
            continue
        differing.append({"path": entry["rel"], "category": category(entry["rel"]),
                          "fork_bytes": len(fork_bytes), "target_bytes": len(target_bytes)})
    return differing, len(candidates)


def triage(fork: pathlib.Path, candidates: list[dict], blobs: dict[str, bytes | None]) -> None:
    for entry in candidates:
        base = blobs.get(entry["path"])
        if base is None:
            entry["verdict"] = "baseline-unavailable"
            continue
        fork_bytes = (fork / entry["path"]).read_bytes()
        entry["verdict"] = "fork-edited" if apply_rebrand(base) != fork_bytes else "upstream-moved"


def render(candidates: list[dict]) -> str:
    lines = []
    for verdict, label in (("fork-edited", "FORK EDITED (must survive)"),
                           ("upstream-moved", "upstream moved on (harmless)"),
                           ("baseline-unavailable", "baseline unavailable")):
        rows = sorted((c for c in candidates if c["verdict"] == verdict),
                      key=lambda c: (c["category"], c["path"]))
        lines.append(f"=== {label}: {len(rows)} ===")
        for entry in rows:
            lines.append(f"  [{entry['category']:13}] {entry['path']:70} "
                         f"fork={entry['fork_bytes']:>9}b target={entry['target_bytes']:>9}b")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fork", type=pathlib.Path, required=True,
                        help="the fork checkout that has the brand/edit state you want")
    parser.add_argument("--target", type=pathlib.Path, required=True,
                        help="the regenerated tree to compare against")
    parser.add_argument("--baseline", help="commit the fork's tree was snapshotted from "
                                           "(without it, the list is not triaged)")
    parser.add_argument("--json", type=pathlib.Path, help="write the triaged list as JSON")
    args = parser.parse_args(argv)

    for tree in (args.fork, args.target):
        if not (tree / ".git").exists():
            parser.error(f"not a git checkout: {tree}")

    paths = tracked_paths(args.target)
    present = find_candidates(args.fork.resolve(), args.target.resolve(), paths)
    candidates, compared = compare(present)
    if args.baseline:
        triage(args.fork.resolve(), candidates, baseline_blobs(args.fork.resolve(),
                                                               args.baseline, [c["path"] for c in candidates]))
    else:
        for entry in candidates:
            entry["verdict"] = "untriaged"

    counted = {verdict: sum(1 for c in candidates if c["verdict"] == verdict)
               for verdict in ("fork-edited", "upstream-moved", "baseline-unavailable", "untriaged")}
    print(f"tracked in target  : {len(paths)}")
    print(f"present in both    : {compared}")
    print(f"content differences: {len(candidates)}")
    for verdict, count in counted.items():
        if count:
            print(f"  {verdict:20} {count}")
    print()
    print(render(candidates))
    if args.json:
        args.json.write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
        print(f"json -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
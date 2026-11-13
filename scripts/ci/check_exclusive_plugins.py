#!/usr/bin/env python3
"""Fail when an Anakot-exclusive plugin ships incomplete or renders nothing.

An exclusive plugin exists only in this fork: there is no upstream counterpart and
no catalog entry, so nothing restores a file that a rebrand pass, an upstream
merge or a stray `git rm` dropped. Worse, neither half fails loudly when it goes
missing. The desktop half is registered by a vite glob over
``apps/desktop/src/plugins/*/plugin.{ts,tsx}``, so an absent ``plugin.tsx`` is not
an unresolved import and not a type error — it is a plugin that renders nowhere
while every check stays green. That is what happened: the Free Model Suite kept
its dashboard half (``plugins/free-model-suite/dashboard/``) and lost its desktop
half entirely, and its nav row asked for codicon ``leaf``, which the bundled
``@vscode/codicons`` has never contained — a blank row, a blank page header, no
warning, nothing in any log.

So each exclusive plugin is asserted twice:

  1. both halves are on disk — the dashboard half the gateway mounts and serves,
     and the desktop half the app registers — plus every file the manifest
     declares (a manifest naming a missing ``api`` module mounts nothing);
  2. every codicon name it draws is a glyph the bundled font actually has.

The glyph half needs ``node_modules``, so on a bare checkout it reports that and
skips rather than failing; the presence half always runs.

Add a plugin id to ``_EXCLUSIVE`` when it must ship with every Anakot install.

Run: python scripts/ci/check_exclusive_plugins.py [repo_root]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Plugins that ship with Anakot and have no upstream counterpart.
_EXCLUSIVE = ("free-model-suite",)

_DASHBOARD = "plugins/{pid}/dashboard"
_DESKTOP = "apps/desktop/src/plugins/{pid}"

# The three ways a contribution names a glyph: the descriptor field, the component
# attribute, and the SDK's Tabler-shaped wrapper.
_CODICONS = (
    re.compile(r"codicon:\s*'([a-z0-9-]+)'"),
    re.compile(r"<Codicon[^>]*?\bname=\"([a-z0-9-]+)\""),
    re.compile(r"codiconIcon\(\s*'([a-z0-9-]+)'"),
)
_GLYPH = re.compile(r"\.codicon-([a-z0-9-]+)")
_FONT = "node_modules/.pnpm/@vscode+codicons@*/node_modules/@vscode/codicons/dist/codicon.css"


def _codicon_names(files: list[Path]) -> dict[str, str]:
    """Map glyph name -> ``file:line`` of its first use."""
    found: dict[str, str] = {}
    for path in files:
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in _CODICONS:
                for match in pattern.finditer(line):
                    found.setdefault(match.group(1), f"{path}:{lineno}")
    return found


def check_plugin(repo: Path, pid: str, problems: list[str]) -> list[Path]:
    """Record *pid*'s defects in *problems*; return its desktop-half sources."""
    dashboard = repo / _DASHBOARD.format(pid=pid)
    desktop = repo / _DESKTOP.format(pid=pid)

    manifest_path = dashboard / "manifest.json"
    if not manifest_path.is_file():
        problems.append(f"{_DASHBOARD.format(pid=pid)}/manifest.json: missing — the gateway serves no API for {pid}")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            problems.append(f"{manifest_path.relative_to(repo).as_posix()}: unreadable manifest ({exc})")
            manifest = {}
        # A manifest that declares an api module owns mounting it: a missing file
        # mounts nothing and the page fails at request time, not at load time.
        api = manifest.get("api") if isinstance(manifest, dict) else None
        if isinstance(api, str) and api and not (dashboard / api).is_file():
            problems.append(
                f"{_DASHBOARD.format(pid=pid)}/{api}: declared by manifest.json but missing — the API never mounts"
            )

    sources = sorted(desktop.glob("*.ts")) + sorted(desktop.glob("*.tsx"))
    if not (desktop / "plugin.tsx").is_file() and not (desktop / "plugin.ts").is_file():
        problems.append(
            f"{_DESKTOP.format(pid=pid)}/plugin.tsx: missing — nothing registers {pid}, so it appears on no surface"
        )
    return sources


def main(argv: list[str]) -> int:
    repo = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parents[2]
    if not repo.is_dir():
        print(f"error: no such directory: {repo}", file=sys.stderr)
        return 2

    problems: list[str] = []
    used: dict[str, str] = {}
    for pid in _EXCLUSIVE:
        for name, where in _codicon_names(check_plugin(repo, pid, problems)).items():
            used.setdefault(name, where)

    fonts = sorted(repo.glob(_FONT))
    if not fonts:
        print(f"exclusive plugins: {len(_EXCLUSIVE)} present; codicon glyphs NOT checked (no bundled font installed)")
    else:
        glyphs = set(_GLYPH.findall(fonts[0].read_text(encoding="utf-8-sig", errors="replace")))
        for name, where in sorted(used.items()):
            if name not in glyphs:
                problems.append(
                    f"{where}: codicon '{name}' is not a glyph in the bundled {fonts[0].name} "
                    f"({len(glyphs)} available) — it renders blank with no warning; pick a real name"
                )

    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} problem(s) in the exclusive plugin(s) {', '.join(_EXCLUSIVE)}. These ship with "
            f"Anakot and have no upstream counterpart, so an incomplete one reaches every user silently: "
            f"restore the missing half, or fix the glyph name (see scripts/ci/check_exclusive_plugins.py).",
            file=sys.stderr,
        )
        return 1
    print(f"exclusive plugins: {len(_EXCLUSIVE)} intact ({len(used)} codicon name(s) resolved)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

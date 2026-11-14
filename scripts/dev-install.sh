#!/usr/bin/env bash
# Install and run a DEV build of Anakot from a fork branch, isolated from the live install.
#
#   scripts/dev-install.sh                        # set up the tree you are standing in
#   scripts/dev-install.sh --dir D:/anakot-dev --ref update/upstream-2026-11-14
#                                                 # fresh checkout of that ref, then set it up
#   scripts/dev-install.sh --js                   # also install JS deps (desktop app, dashboard)
#   scripts/dev-install.sh --seed-home            # copy the live profile's config.yaml + .env
#   scripts/dev-install.sh --run                  # launch the CLI against the dev home when done
#   scripts/dev-install.sh --run-desktop          # JS deps, then build and open the desktop app
#   scripts/dev-install.sh --shortcut             # a Desktop icon that launches this dev build
#   scripts/dev-install.sh --pack                 # JS deps, then package the desktop app (no launch)
#
# Why this exists. A regenerated fork tree cannot be set up the documented way:
#   * Lockfiles are exempt from the rebrand, so the tree arrives with each uv lock still naming the
#     upstream project and uv refuses every strict entry point -- pm's runtime staging,
#     `pm.build_env`, the desktop pack, the test bootstrap -- with a message that names no lock.
#     This script re-points them first (scripts/fix_lock_identity.py), then builds straight from the
#     repo lock (`uv sync --locked --all-packages --group dev --group test`).
#   * The JS tree declares `engines.node >= 26`. A system Node 22 aborts with
#     ERR_PNPM_UNSUPPORTED_ENGINE before pnpm reads anything, and on Windows the newer interpreter
#     has to be put on PATH in the MSYS spelling or bash silently keeps the old one.
#
# Everything here is scoped to the dev checkout and a dev home. The live install and the live
# profile are never written to: seeding copies files out of the live profile, never into it.
set -euo pipefail

REPO_URL="${ANAKOT_DEV_REPO_URL:-https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO.git}"
REF=""
DIR=""
DEV_HOME="${ANAKOT_DEV_HOME:-}"
WITH_JS=0
SEED_HOME=0
RUN_CLI=0
RUN_DESKTOP=0
SHORTCUT=0
PACK=0
FULL_CLONE=0

usage() {
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --ref)       REF="${2:?--ref needs a value}"; shift 2 ;;
        --dir)       DIR="${2:?--dir needs a value}"; shift 2 ;;
        --home)      DEV_HOME="${2:?--home needs a value}"; shift 2 ;;
        --js)        WITH_JS=1; shift ;;
        --seed-home) SEED_HOME=1; shift ;;
        --run)       RUN_CLI=1; shift ;;
        --run-desktop) RUN_DESKTOP=1; WITH_JS=1; shift ;;
        --shortcut)  SHORTCUT=1; WITH_JS=1; shift ;;
        --pack)      PACK=1; WITH_JS=1; shift ;;
        --full)      FULL_CLONE=1; shift ;;
        -h|--help)   usage 0 ;;
        *)           echo "unknown argument: $1" >&2; usage 2 ;;
    esac
done

say()  { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# git is not only how the tree arrives: pyproject pins a real git source (`misaki`), so `uv sync`
# needs the binary too and a source tarball would not get past it. Say that here, with the install
# line, rather than letting a missing git surface as a resolver error that reads like a bad pin.
command -v git >/dev/null 2>&1 || die "git is required — the tree pins a git dependency, not just the clone.
    Debian/Ubuntu:  sudo apt update && sudo apt install -y git
    Fedora/RHEL:    sudo dnf install -y git
    Arch:           sudo pacman -S git
    Alpine:         sudo apk add git
    Windows:        winget install --id Git.Git    (also provides the bash this script runs in)"

is_windows=0
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) is_windows=1 ;; esac

# A Windows path on PATH is accepted silently by bash and loses to the existing entry, so convert
# to the MSYS spelling before prepending. Idempotent: a path already in MSYS form is returned as-is,
# because prepending another slash yields `//c/...`, which matches nothing — and the drive-letter sed
# already writes the leading slash, so it must not be added twice.
to_msys_path() {
    local p="$1"
    if [ "$is_windows" = 1 ]; then
        case "$p" in
            [A-Za-z]:[\\/]*)
                printf '%s' "$(printf '%s' "$p" | sed 's|\\|/|g; s|^\([A-Za-z]\):|/\L\1|')"
                return ;;
        esac
    fi
    printf '%s' "$p"
}

# ─── 1. locate or create the checkout ────────────────────────────────────────
if [ -z "$DIR" ]; then
    DIR="$(cd "$(dirname "$0")/.." && pwd)"
    say "in-place mode: $DIR"
fi

if [ -e "$DIR/.git" ]; then
    say "using existing checkout at $DIR"
    if [ -n "$REF" ]; then
        git -C "$DIR" fetch --quiet origin "$REF" 2>/dev/null || true
        git -C "$DIR" checkout --quiet "$REF" || die "could not check out $REF in $DIR"
    fi
else
    [ -n "$REF" ] || die "no checkout at $DIR and no --ref to clone (try --ref main)"
    say "cloning $REF into $DIR"
    if [ "$FULL_CLONE" = 1 ]; then
        git clone --branch "$REF" "$REPO_URL" "$DIR"
    else
        # A dev install runs the tree; it does not need upstream's 16k commits.
        git clone --depth 1 --branch "$REF" "$REPO_URL" "$DIR"
    fi
fi

cd "$DIR"
say "at $(git rev-parse --short HEAD 2>/dev/null || echo '<no git>') ($(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached))"

# ─── 2. Python environment, from the repo lock ───────────────────────────────
UV_BIN="$(command -v uv 2>/dev/null || true)"
if [ -z "$UV_BIN" ]; then
    # A tree that has bootstrapped once leaves a pinned uv under the Anakot tools dir. On a fresh
    # box that is the difference between a one-command dev install and a toolchain detour.
    tools_msys="$(to_msys_path "${LOCALAPPDATA:-$HOME/AppData/Local}")/anakot/tools"
    for candidate in "$HOME"/.anakot/tools/uv-*/uv* "$tools_msys"/uv-*/uv*; do
        if [ -x "$candidate" ] && [ ! -d "$candidate" ]; then UV_BIN="$candidate"; break; fi
    done
fi
if [ -z "$UV_BIN" ]; then
    die "uv not found. Install it first:
      Windows:  powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"
      Linux/mac: curl -LsSf https://astral.sh/uv/install.sh | sh
    then re-run this script."
fi
say "uv: $("$UV_BIN" --version 2>/dev/null || echo "$UV_BIN")"
# The rebrand does not touch lockfiles, so a regenerated tree arrives with locks that still name
# the upstream project. uv then refuses every strict entry point (this sync, pm's staging, the
# desktop pack, the test bootstrap) with a message that never mentions a lock. Harmless -- and a
# no-op -- on a tree whose locks already agree.
if [ -f "$DIR/scripts/fix_lock_identity.py" ]; then
    ( cd "$DIR" && "$UV_BIN" run --no-project python scripts/fix_lock_identity.py ) \
        || die "scripts/fix_lock_identity.py could not make the locks agree with their manifests"
fi
say "building the Python environment (uv sync --locked --all-packages --group dev --group test)"
"$UV_BIN" sync --locked --all-packages --group dev --group test

if [ "$is_windows" = 1 ]; then
    PY="$DIR/.venv/Scripts/python.exe"
    ANAKOT_BIN="$DIR/.venv/Scripts/anakot.exe"
else
    PY="$DIR/.venv/bin/python"
    ANAKOT_BIN="$DIR/.venv/bin/anakot"
fi
[ -f "$PY" ] || die "expected an interpreter at $PY after uv sync"
"$PY" -c "import pytest, sys; print('  python', sys.version.split()[0], '| pytest', pytest.__version__)" \
    || die "the environment did not import pytest; the sync above did not complete cleanly"

# ─── 3. JS dependencies (optional) ───────────────────────────────────────────
if [ "$WITH_JS" = 1 ]; then
    tools_msys="$(to_msys_path "${LOCALAPPDATA:-$HOME/AppData/Local}")/anakot/tools"

    node_bin=""
    node_msys=""
    for candidate in "$tools_msys"/node-*-win32-x64; do
        if [ -x "$candidate/node.exe" ] || [ -x "$candidate/bin/node" ]; then
            node_bin="$candidate"
            break
        fi
    done
    if [ -n "$node_bin" ]; then
        node_msys="$(to_msys_path "$node_bin")"
        export PATH="$node_msys:$PATH"
    fi

    # Anakot bundles pnpm the same way it bundles node, and the bundled version is the one the
    # lockfile was written with. A machine that already has the app therefore needs no separate
    # pnpm install -- which is the difference between this working on a fresh VM and dying with
    # "pnpm: not recognized".
    pnpm_msys=""
    for candidate in "$tools_msys"/pnpm-* \
                     "$(to_msys_path "${LOCALAPPDATA:-$HOME/AppData/Local}")/anakot/node"; do
        if [ -x "$candidate/pnpm.exe" ] || [ -x "$candidate/pnpm" ] || [ -x "$candidate/pnpm.cmd" ]; then
            pnpm_msys="$(to_msys_path "$candidate")"
            export PATH="$pnpm_msys:$PATH"
            break
        fi
    done

    have_node="$(node --version 2>/dev/null || echo none)"
    say "JS deps with node $have_node"
    case "$have_node" in
        v26.*|v[3-9][0-9].*) : ;;
        *) warn "package.json requires node >= 26; pnpm install will abort before reading anything" ;;
    esac

    if command -v pnpm >/dev/null 2>&1; then
        PNPM="pnpm"
    elif command -v corepack >/dev/null 2>&1; then
        PNPM="corepack pnpm"   # corepack ships with Node, so even a bare install can get here
    else
        die "pnpm not found and no corepack to stand in. Install it with: npm install -g pnpm"
    fi
    say "package manager: $PNPM"
    $PNPM install

    # pnpm skips dependency install scripts without approval, and Electron's binary arrives exactly
    # that way -- silently, in a non-interactive run, with no warning printed. The later symptom is
    # "Electron failed to install correctly" at launch, which reads as a broken checkout. Electron's
    # own installer is the deterministic fix: no interactive `pnpm approve-builds`, and no edit to a
    # repo-owned manifest that the next regenerate would have to replay.
    for electron_dir in apps/desktop/node_modules/electron node_modules/electron; do
        if [ -f "$electron_dir/install.js" ] && [ ! -d "$electron_dir/dist" ]; then
            say "fetching the Electron binary (pnpm skipped its install script; ~320 MB)"
            node "$electron_dir/install.js" \
                || warn "Electron's installer failed — the desktop app cannot start until it succeeds"
            break
        fi
    done
fi

# ─── 4. an isolated dev home ─────────────────────────────────────────────────
if [ -z "$DEV_HOME" ]; then
    DEV_HOME="$HOME/anakot-dev-home"
fi
mkdir -p "$DEV_HOME"
say "dev home: $DEV_HOME"

if [ "$SEED_HOME" = 1 ] && [ ! -f "$DEV_HOME/config.yaml" ]; then
    live_home="${LOCALAPPDATA:-$HOME/AppData/Local}/anakot"
    [ -d "$live_home" ] || live_home="$HOME/.anakot"
    if [ -f "$live_home/config.yaml" ]; then
        cp "$live_home/config.yaml" "$DEV_HOME/"
        [ -f "$live_home/.env" ] && cp "$live_home/.env" "$DEV_HOME/"
        say "seeded from $live_home"
        warn "$DEV_HOME/.env holds live credentials — delete the dev home when you are done with it"
    else
        warn "no config.yaml found at $live_home; the dev build will start unconfigured"
    fi
fi

# Prove the brand home is read before anything else runs: a build that ignores ANAKOT_HOME answers
# "no API keys or providers found" no matter how correct its config is.
home_seen="$(ANAKOT_HOME="$DEV_HOME" "$PY" -c 'from anakot_constants import get_anakot_home; print(get_anakot_home())' 2>/dev/null || echo '')"
if [ -z "$home_seen" ]; then
    warn "could not read the brand home (ignored, or the module moved) — check before trusting this build"
else
    say "ANAKOT_HOME resolves to: $home_seen"
fi

# ─── 5. hand over ────────────────────────────────────────────────────────────
printf '\n'
say "ready. run the CLI with:"
printf '    ANAKOT_HOME="%s" "%s" chat\n' "$DEV_HOME" "$ANAKOT_BIN"
if [ "$WITH_JS" = 0 ]; then
    printf '    (desktop/web need --js first)\n'
else
    printf '\n'
    say "or open the desktop app with:"
    # The script's own PATH export does not survive into your shell, and the JS tree needs >= 26.
    js_prefix="$node_msys"
    [ -n "$pnpm_msys" ] && js_prefix="${js_prefix:+$js_prefix:}$pnpm_msys"
    printf '    cd "%s" && ANAKOT_HOME="%s" PATH="%s:$PATH" %s -C apps/desktop start\n' \
        "$DIR" "$DEV_HOME" "$js_prefix" "$PNPM"
    printf '    (or hot-reloading: %s -C apps/desktop dev)\n' "$PNPM"
    printf '    (window says "Gateway starting (deadline)"? ANAKOT_HOME="%s" "%s" gateway status)\n' \
        "$DEV_HOME" "$ANAKOT_BIN"
fi

if [ "$SHORTCUT" = 1 ]; then
    if [ "$is_windows" != 1 ]; then
        warn "--shortcut is Windows-only; on this host launch with: ANAKOT_HOME=\"$DEV_HOME\" \"$ANAKOT_BIN\" desktop"
    else
        # A .lnk cannot carry environment, and this app needs ANAKOT_HOME (a launch-only key read from
        # its own process env, never from a .env) plus the bundled Node/pnpm. So the shortcut points at
        # a .cmd that sets all three, then starts the app: an icon that needs no typing and no shell.
        win() { cygpath -w "$1" 2>/dev/null || printf '%s' "$1"; }
        path_pre="$(win "$node_bin")"
        [ -n "$pnpm_msys" ] && path_pre="$path_pre;$(win "$pnpm_msys")"
        launcher="$DIR/anakot-dev.cmd"
        {
            printf '@echo off\r\n'
            printf 'set "ANAKOT_HOME=%s"\r\n' "$(win "$DEV_HOME")"
            printf 'set "PATH=%s;%%PATH%%"\r\n' "$path_pre"
            printf 'cd /d "%s"\r\n' "$(win "$DIR")"
            printf '%s -C apps/desktop start\r\n' "$PNPM"
        } > "$launcher"
        say "launcher written: $launcher"
        ps_args=(-NoProfile -ExecutionPolicy Bypass -File "$(win "$DIR/scripts/dev-desktop-shortcut.ps1")"
                 -CmdPath "$(win "$launcher")")
        [ -n "${ANAKOT_SHORTCUT_DIR:-}" ] && ps_args+=(-OutDir "$(win "$ANAKOT_SHORTCUT_DIR")")
        powershell.exe "${ps_args[@]}" \
            || warn "could not create the Desktop shortcut (the .cmd launcher above still works)"
    fi
fi

if [ "$PACK" = 1 ]; then
    # The repo's own pack step. Its first stage prepares a pm runtime, which is exactly what the stale
    # lock used to refuse, so the fix above is why this can run at all. --build-only stops short of
    # launching, which keeps it safe on a machine that already has the app open.
    say "packaging the desktop app (the first build takes a few minutes)"
    ( cd "$DIR" && "$ANAKOT_BIN" desktop --build-only ) \
        || die "the desktop pack failed (re-run it: cd \"$DIR\" && \"$ANAKOT_BIN\" desktop --build-only)"
    # Name the artifact, not just the directory: --build-only prints it too, but a user reading a
    # scrollback should be handed the one path that matters.
    artifact=""
    for candidate in "$DIR/apps/desktop/release/win-unpacked/Anakot.exe" \
                     "$DIR/apps/desktop/release/linux-unpacked/anakot" \
                     "$DIR/apps/desktop/release/mac"*/*.app; do
        if [ -e "$candidate" ]; then artifact="$candidate"; break; fi
    done
    if [ -n "$artifact" ]; then
        say "packaged app: $artifact"
        say "start it with ANAKOT_HOME=\"$DEV_HOME\" \"$artifact\""
    else
        warn "the pack finished but no artifact was found under $DIR/apps/desktop/release"
    fi
fi

if [ "$RUN_DESKTOP" = 1 ]; then
    say "building and opening the desktop app (first build takes a few minutes)"
    # The app reads ANAKOT_HOME from its process env -- it is a launch-only key and the loader never
    # takes it from a .env -- so exporting it here is what keeps the dev app on the dev home. Without
    # it the app uses the machine's default home, spawns a backend against that, and the window
    # reports "Gateway starting (deadline). Use anakot gateway status for recovery."
    export ANAKOT_HOME="$DEV_HOME"
    exec $PNPM -C apps/desktop start
fi

if [ "$RUN_CLI" = 1 ]; then
    say "launching"
    ANAKOT_HOME="$DEV_HOME" exec "$ANAKOT_BIN" chat
fi

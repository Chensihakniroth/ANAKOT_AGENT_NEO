# Upstream Porting Tracker — Anakot Agent v2

This file tracks commits from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
and their status in **Anakot Agent v2** (`Chensihakniroth/ANAKOT_AGENT_NEO`).

It replaces the v1 tracker. That ledger lived in the v1 repository and described a *history-sharing*
fork (parity rows against `ca436069`, `scripts/hermes_sync.py`, 343 rows). **v2 starts from a snapshot
import with no shared history**, so the questions this file answers are different: not "which commit
did we already merge" but "which upstream commit do we re-express on top of a fresh regenerate, and
which fork-local work must survive it".

**How to use:**
1. Run the refresh command below to list new Hermes commits — local `git` is enough, the `upstream`
   remote is already configured and fetched.
2. Filter `plugin-catalog/`, `catalog/`, `chore/`, `docs/`, `test/`, re-pins and mailmap rows first;
   they are most of upstream's volume and almost never portable.
3. For each real candidate set status: `PENDING` → `PORTED` / `SKIPPED` / `CUSTOM`.
4. Add a note saying *what* you did, then commit this file.

---

## v2 status (2026-11-13)

> **Fork topology.** `git merge-base main upstream/main` returns **nothing** — v2 is a snapshot import
> (root commit `238ab19e`, *feat: initial release of Anakot Agent Neo*, 2026-11-12), so the two trees
> are parallel histories. An ahead/behind count is therefore meaningless:
> `git rev-list --left-right --count main...upstream/main` reports `14 70744`, where 70,744 is
> upstream's *entire* history, not a measure of debt. Compare trees and subsystems instead.

| Fact | Value |
|------|-------|
| Fork remote (`origin`) | `https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO.git` |
| Upstream remote | `https://github.com/NousResearch/hermes-agent.git` (already configured) |
| Snapshot baseline | `eaac327f` (2026-11-11) — closest upstream commit by byte-identical file count (9,087 of ~24.8k) |
| Upstream head at this scan | `9d94f822` (2026-11-13) |
| Window since baseline | 2,546 commits (2,491 excluding merges) |
| Upstream velocity | ~16.4k commits / 30 days |
| Fork-local commits | 15 (listed below) |
| Differing paths vs upstream head | 17,326 (798 added / 1,534 deleted / 11,805 modified / 3,189 renamed) |
| Rebrand mechanism | `scripts/rebrand.py` (`--check` / `--apply` / `--verify` / `--rebaseline`) |

Rename detection is skipped at this scale, so most added/deleted pairs are the rebrand's
`hermes_*` → `anakot_*` renames (e.g. `hermes_cli/` → `anakot_cli/`), not new functionality.

**Scan result for this window:** of 2,491 non-merge commits, **1,688 were filtered as noise**
(plugin-catalog 838, chore/docs/CI/build 620, re-pin/mailmap 108, test-only 90, catalog maintenance 31,
merge/revert 1), leaving **803 signal commits**, of which **311 land in tracked subsystems**
(`gateway`, `cli`, `desktop`, `plugins`, `cron`, `memory`, `agent`, `update`, `dashboard`, …).
Those collapse into **300 behavioural clusters**; the newest **70** are seeded into the table below as
`PENDING` — the initial work queue, not the whole backlog. Re-run the filtered refresh command to
surface the rest when the table drains.

The concentration matters more than the raw count: **193 of the 311 land in `gateway`** (186 once
collapsed to clusters) — a handful of long chains (voice-note echo, `/stop`/`/new` mid-stream,
wake-word gating, preview fragments). Port the **final-state** commit of a chain, not every step.

---

## Refresh command

The `upstream` remote is already configured, so prefer local git over the API:

```bash
git fetch upstream
git log upstream/main --oneline -100                                    # recent commits

# filtered candidate list (drops catalog / chore / docs / test noise)
git log upstream/main --format="%h %ad %s" --date=short --since="2026-11-11" \
  | grep -vE "catalog|^[0-9a-f]+ [0-9-]+ (chore|docs|test|ci)"

git rev-list --count <baseline>..upstream/main                          # window size
```

API fallback (when a commit body or patch is needed and the local object is absent):

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    msg = c['commit']['message'].splitlines()[0]
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {msg}\")
"
```

---

## Status legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Reviewed as a candidate, not yet implemented |
| `PORTED` | Behaviour re-expressed in Anakot v2 and verified |
| `SKIPPED` | Intentionally not ported (Hermes-specific, or conflicts with an Anakot customization) |
| `CUSTOM` | Anakot already has its own implementation of the behaviour |
| `N/A` | Not applicable (catalog/plugin-listing, docs-only, test-only, release machinery) |

Mark a cluster `PORTED (partial)` when only some surfaces were adapted, and record which ones.

---

## Tracking table

Seeded from the 2026-11-13 scan — the newest commit of each behavioural cluster. Empty `Notes` means
it has not been triaged yet.

| SHA | Date | Description | Status | Notes |
|-----|------|-------------|--------|-------|
| b895ec83 | 2026-11-13 | fix(plugins): retry a leftover default at the home's own pin, and never mistake our removal for the user's | `PENDING` | |
| 3d11e6ef | 2026-11-13 | fix(plugins): replace a leftover default by removing that dir, never by forcing the install | `PENDING` | |
| e79875fe | 2026-11-13 | fix(plugins): a queued install unsettles the revision; the child backs off on any error | `PENDING` | |
| 577811d7 | 2026-11-13 | fix(plugins): default plugins survive concurrent creates, legacy records, removals, Windows jobs | `PENDING` | |
| 459878a8 | 2026-11-13 | refactor(desktop): one alias-metadata lookup for the roster and the server overlay | `PENDING` | |
| 5c15df6e | 2026-11-13 | fix(desktop): a server bot record minted for an alias's row starts from the alias's look | `PENDING` | |
| e8fc0d17 | 2026-11-13 | fix(plugins): ctx.redact_text also strips URL credentials | `PENDING` | |
| 2e78cddd | 2026-11-13 | fix(tui): keep voice.tts in the requested profile | `PENDING` | |
| c5dc1971 | 2026-11-13 | fix(gateway): run a macOS app's own launcher for its gateway service | `PENDING` | |
| cd2500ab | 2026-11-13 | fix(desktop): give the gateway ticket helper the launchers' bytecode cache | `PENDING` | |
| 9f30f454 | 2026-11-12 | fix(plugins): record default plugins with a one-key config write | `PENDING` | |
| 1353fd7b | 2026-11-12 | fix(plugins): address review on default plugins (refused enable, owed retry, offline catalog) | `PENDING` | |
| 66cc4ac0 | 2026-11-12 | fix(plugins): default plugins install in a detached child, never on the boot path | `PENDING` | |
| 7adcd5e7 | 2026-11-12 | feat(plugins): catalog entries marked default: true are installed in every home | `PENDING` | |
| a3e4e721 | 2026-11-12 | fix(desktop): inspect catalog plugins at their pinned commit, not the default branch | `PENDING` | |
| 1f162f62 | 2026-11-12 | fix(gateway): restore an unrestored local parent before building its auto-resume stand-in | `PENDING` | |
| 4f8fdcd3 | 2026-11-12 | fix(gateway): the auto-resume stand-in parent runs on its own session's service tier | `PENDING` | |
| 71725967 | 2026-11-12 | fix(gateway): a reply repeated after a tool round is not uploaded as a second file | `PENDING` | |
| aeb40f7b | 2026-11-12 | fix(gateway): a reply past the 8-message cap is one file on every path the review found | `PENDING` | |
| e9a12b5d | 2026-11-12 | fix(gateway): a ceiling-cut reply numbers its parts out of the whole reply | `PENDING` | |
| 83941187 | 2026-11-12 | fix(gateway): one streamed reply never opens more messages than the adapter's split cap | `PENDING` | |
| 5e3f7bc8 | 2026-11-12 | fix(cli): delete the session branch without filter discovery at exit | `PENDING` | |
| 517cfa8b | 2026-11-12 | fix(desktop): read-aloud off works in every window, stops the reply being read (#154705) | `PENDING` | |
| 2f016d58 | 2026-11-12 | fix(tui): an explicit launch route or stored session skips Setup Required | `PENDING` | |
| 4544973d | 2026-11-12 | fix(tui): a blank install on the shared gateway opens Setup Required | `PENDING` | |
| 81ed3d89 | 2026-11-12 | fix(dashboard): allow a link chain of exactly the hop bound | `PENDING` | |
| 621b1df2 | 2026-11-12 | fix(dashboard): walk the link chain from the path the client sent | `PENDING` | |
| 47e8a497 | 2026-11-12 | fix(dashboard): check link-chain hops with a canonical parent, refuse past the hop bound | `PENDING` | |
| 5b406998 | 2026-11-12 | fix(dashboard): refuse a managed write through a credential name mid link chain | `PENDING` | |
| faef126c | 2026-11-12 | fix(plugins): require a hostname for catalog docs_url at admission | `PENDING` | |
| b545c8d9 | 2026-11-12 | fix(plugins): drop malformed catalog docs_url instead of failing the load | `PENDING` | |
| f62ffe08 | 2026-11-12 | fix(plugins): drop non-https catalog docs_url at load and gate every docs href | `PENDING` | |
| 2073ba4f | 2026-11-12 | fix(memory): fence clarify-context prose when interim messages are off | `PENDING` | |
| 05e760de | 2026-11-12 | fix(memory): keep whitespace commentary parts in history replay too | `PENDING` | |
| ee6ab395 | 2026-11-12 | fix(memory): retain Codex commentary whitespace at fence boundaries | `PENDING` | |
| 0fb5c961 | 2026-11-12 | fix(memory): hide held rows on stored text, not fenced interim text | `PENDING` | |
| 1a602a01 | 2026-11-12 | fix(memory): fence pre_transform_response and filtered-out commentary | `PENDING` | |
| 3998bf9c | 2026-11-12 | fix(desktop): an older pick's late reply never overrides a newer one | `PENDING` | |
| 4e923f5e | 2026-11-12 | fix(desktop): bind the queued launch pick to the owner that made it | `PENDING` | |
| 52a54bce | 2026-11-12 | fix(desktop): keep the queued launch pick's origin next to the pick it saved | `PENDING` | |
| e488bac7 | 2026-11-12 | fix(desktop): release only the exact saved route a failed pick left behind | `PENDING` | |
| 82bf5a0e | 2026-11-12 | fix(desktop): a refused next-turn pick hands new chats back to the default | `PENDING` | |
| 596083a8 | 2026-11-12 | fix(desktop): route the gateway-file download join through joinBackendApiUrl | `PENDING` | |
| de0135e5 | 2026-11-12 | fix(desktop): bump electron 44.10.0 -> 44.10.2 (latest 44.x patch) | `PENDING` | |
| 7128caa0 | 2026-11-12 | fix(gateway): let a session switch away from a stopped local model | `PENDING` | |
| ac248c81 | 2026-11-12 | fix(agent): a named reasoning alias collision drops only `reasoning` | `PENDING` | |
| 5437fbb1 | 2026-11-12 | fix(agent): one alias-collision rule for named and keyless reasoning rejections | `PENDING` | |
| 1a88f1e2 | 2026-11-12 | fix(cli): align shared foreground and delegation defaults | `PENDING` | |
| 7469dc64 | 2026-11-12 | fix(update): keep every owed migration reason; a stopped sibling is not reported as updated | `PENDING` | |
| a866251e | 2026-11-12 | fix(gateway): a stale-lock heal leaves a replying command's guard, and a drain owns the owner's guard | `PENDING` | |
| a3d70d83 | 2026-11-12 | fix(acp): match V4A headers without a space after the stars in edit approval | `PENDING` | |
| 175dd9a7 | 2026-11-12 | fix(gateway): a refused command hands the session to a command still in flight | `PENDING` | |
| d5547727 | 2026-11-12 | fix(gateway): overlapping refused commands restore the owner's guard, not each other's | `PENDING` | |
| cc28398b | 2026-11-12 | fix(gateway): an accepted busy /stop, /new drops held input before the route fence | `PENDING` | |
| 4a0143fd | 2026-11-12 | fix(gateway): a pre_gateway_dispatch rewrite keeps a /stop's acceptance visible to the adapter | `PENDING` | |
| beae0755 | 2026-11-12 | fix(gateway): an accepted /stop, /new, /reset drops adapter-held media; a refused one drains if the owner finished | `PENDING` | |
| ac03ff92 | 2026-11-12 | fix(cron): read monitor_url bodies raw so the size cap bounds encoded responses | `PENDING` | |
| a9a95304 | 2026-11-12 | refactor(gateway): move _local_completion_card into run_notifications_ownership | `PENDING` | |
| 2663c26b | 2026-11-12 | fix(dashboard): strip the requested path before the managed-file write guard | `PENDING` | |
| f8f8256f | 2026-11-12 | fix(dashboard): check the requested path in the managed-file write guard | `PENDING` | |
| f82df7e1 | 2026-11-12 | refactor(dashboard): move unverified /api/status projection into status_public | `PENDING` | |
| a77d2049 | 2026-11-12 | fix(dashboard): redact warm-up errors returned in audio lease bodies | `PENDING` | |
| 4366dc8d | 2026-11-11 | fix(gateway): a /stop or /new during the seal of a visible preview sends no overflow chunk | `PENDING` | |
| b04d8af9 | 2026-11-11 | fix(gateway): skip post-reset retry after awaited final send | `PENDING` | |
| a3e55a38 | 2026-11-11 | fix(gateway): /stop or /new mid-stream no longer leaves the cursor on the preview (#123530) | `PENDING` | |
| b594fd97 | 2026-11-11 | fix(gateway): a fragment whose Telegram delete is only queued is continued, never repeated | `PENDING` | |
| 536a4e4d | 2026-11-11 | fix(gateway): a first-word fragment that cannot be deleted is continued, never repeated | `PENDING` | |
| 10c64dee | 2026-11-11 | fix(gateway): a refused final edit leaves no stuck cursor or mid-word cut (#153317) | `PENDING` | |
| d47cbe14 | 2026-11-11 | fix(gateway): a busy voice note's transcript belongs to its message, never another chat's copy | `PENDING` | |
| fedb2772 | 2026-11-11 | fix(gateway): one refused busy voice echo no longer stops the later clips' echoes | `PENDING` | |

---

## Fork-local commits (must survive every sync)

These 15 commits are Anakot v2's own work. A scripted regenerate drops all of them unless they are
re-applied.

| SHA | Date | Subject | Why it exists |
|-----|------|---------|---------------|
| `238ab19e` | 2026-11-12 | feat: initial release of Anakot Agent Neo | Snapshot import root — **no shared history with upstream** |
| `f0cd730a` | 2026-11-13 | feat: add Anakot rebrand master assets | Brand masters (`anakot_rebrand_masters/`), the rebrand's source of truth |
| `3025dbf9` | 2026-11-13 | fix(build): accept anakot_cli/web_dist as a product output | Fork-only build output path |
| `04f330a6` | 2026-11-13 | fix(build): finish the anakot rename in TUI build + lock ordering | TUI build rename |
| `452294c8` | 2026-11-13 | feat(rebrand): scripted deep rename with a protected-strings gate | Adds `scripts/rebrand.py` + `brand/protected-strings.txt` |
| `32d2394d` | 2026-11-13 | feat(icons): raster brand masters + regenerate all icon targets | Icon targets regenerated from masters |
| `cf0f5c53` | 2026-11-13 | fix(rebrand): stop guarding generator-owned icons, add --rebaseline | Rebrand tooling fix |
| `4e9be1b9` | 2026-11-13 | fix(rebrand): repair 95 case-blinded over-renames; point installs at this fork | Case-insensitive protected strings; install URL repoint |
| `95d72085` | 2026-11-13 | chore(lint): clear 36 pre-existing ruff findings so the pre-push gate can run | Lint debt cleared to enable `scripts/check` |
| `bb8e200d` | 2026-11-13 | fix(rebrand): point project metadata at this fork | Fork identity in `package.json` + desktop package |
| `bc46f233` | 2026-11-13 | fix(auth): restore the Portal-registered OAuth client id (sign-in was 400) | Server-registered identifier — must never follow the rebrand |
| `ce266c24` | 2026-11-13 | fix(catalog): read the compatibility field the catalog actually publishes | Remote-producer field name (`requires_hermes`) is protected |
| `c5a437db` | 2026-11-13 | feat(desktop): port the Free Model Suite plugin (v1 -> v2) | Exclusive plugin desktop half recovered from v1 |
| `8d1ab28d` | 2026-11-13 | test(guards): fail when an exclusive plugin ships incomplete or unreadable | Guard for the exclusive-plugin class |
| `9b0cfdf2` | 2026-11-13 | docs(upstream): add the v2 porting ledger with a measured baseline | This file — restore it explicitly on every regenerate (upstream has no copy) |

---

## Anakot v2-only surfaces (upstream has no counterpart)

| Surface | Location | Notes |
|---------|----------|-------|
| Scripted rebrand | `scripts/rebrand.py` | `--check` (dry run) / `--apply` / `--verify` (gate) / `--rebaseline` |
| Protected strings | `brand/protected-strings.txt` | Live wires that must **never** be renamed: docs/API endpoints, upstream repo identity, on-disk build markers, plugin-SDK globals, `HERMES_*` build contracts, and server-registered identifiers (`hermes-cli` OAuth client id, `requires_hermes` catalog field) |
| Brand masters | `anakot_rebrand_masters/` | Source art + `MANIFEST.json`; `brand/assets.manifest.json` records applied hashes |
| Exclusive-plugin guard | `scripts/ci/check_exclusive_plugins.py` (run by `scripts/check`) | Fails when a fork-only plugin ships an incomplete or unreadable half |
| Free Model Suite (desktop half) | `apps/desktop/src/plugins/free-model-suite/` | Recovered from v1; no upstream counterpart |
| Hikari Pixel persona | `SOUL.md` / system prompt | Fork identity, not an upstream feature |

---

## Sync procedure (regenerate, then re-apply)

Because the histories are unrelated, updating is a **regenerate**, not a merge. Nine steps, in order;
the numbers are load-bearing (a lock resolved before the rebrand is wrong, a carry applied before
`--verify` hides a broken transform).

**Step 1 — pick the target.** A release tag (`v2026.9.24` is the newest) or a specific upstream
commit. Record it in the scan line of the porting log before touching anything.

**Step 2 — fresh tree.** A worktree at that ref, cleaned hard. `-x` matters: `git clean -fd` keeps
ignored paths (`data/`, `node_modules`), and an ignored leftover inside a directory the rebrand
renames makes the rename collide — the transform now aborts on that, but a clean tree avoids it.

```bash
git tag backup/pre-update
git fetch upstream --tags
git worktree add --detach ../anakot-trial <upstream-ref>
cd ../anakot-trial && git clean -fdxq
```

**Step 3 — restore the fork's own files.** Upstream has none of these, and `--verify` needs them:

| Restore | Why |
|---|---|
| `brand/` | protected strings, asset snapshot, manifest — the rebrand's inputs |
| `anakot_rebrand_masters/` | source art |
| `scripts/rebrand.py` | the transform itself |
| `UPSTREAM_PORTING.md` | this ledger |
| `scripts/ci/check_exclusive_plugins.py` | the exclusive-plugin guard script |
| `plugins/free-model-suite/`, `apps/desktop/src/plugins/free-model-suite/` | fork-only plugin (both halves) |

```bash
git checkout backup/pre-update -- brand/ anakot_rebrand_masters/ scripts/rebrand.py \
  UPSTREAM_PORTING.md scripts/ci/check_exclusive_plugins.py \
  plugins/free-model-suite/ apps/desktop/src/plugins/free-model-suite/
```

**Step 4 — transform.** `python scripts/rebrand.py --apply` (~90 s, ~25.5k files).

**Step 5 — gate.** `python scripts/rebrand.py --verify` must print `VERIFY: PASS`. It now fails on
any pending content rewrite, path rename, brand drift or asset mismatch — not just asset hashes.

**Step 6 — re-lock.** Both lockfiles are deliberately never text-rewritten (`SKIP_FILES`), so they
still name upstream while `pyproject.toml` / `package.json` name Anakot. `--verify` cannot see this;
only a re-resolve fixes it:

```bash
anakot pm lock          # uv.lock: name = "hermes-agent" -> "anakot-agent"
pnpm install            # pnpm-lock.yaml: @hermes/* -> @anakot/*  (NOT --frozen-lockfile)
```

**Step 7 — re-apply only what the transform did NOT already do.** Most fork commits are *subsumed*:
the text rewrite reproduces the build-path fixes, the metadata repoint, the protected identifiers,
and the rebrand tooling comes from step 3. Verified against `9d94f822`: what genuinely needs
re-applying is small — the exclusive-plugin guard's registration in `scripts/check` (the guard
script alone is not wired), plus any ruff/lint findings the fork had cleared that upstream still has.
Port the behaviour; do not replay the 15 commits blindly.

**Step 8 — prove it.** `scripts/rebrand.py --verify`, `scripts/check`, then
`scripts/run_tests.sh` compared against the host baseline recorded in the porting log (10 known
failures on Windows). A regenerate is green when it adds nothing to that set.

**Step 9 — land.** Commit on the branch, push, review the diff, fast-forward `main`, then update this
ledger: the new scan head, the rows you ported, and the new baseline.

**Never do this in the live checkout.** `D:\School\PROJECT\anakot-agent-v2` is the running Anakot
install, so `git switch` there is refused (it would mix module versions inside the live process).
Work in a linked worktree instead, which shares one object store and costs no extra clone:

```bash
git worktree add ../anakot-agent-v2-update update/upstream-2026-11-13
cd ../anakot-agent-v2-update          # regenerate, test, commit here
python -m pm.build_env --source . --out .venv --group dev --group test   # ~350 MB, once
git worktree remove ../anakot-agent-v2-update    # when done
```

`main` stays checked out and untouched in the live checkout; advance it only by fast-forward after
the branch is verified.

`git merge upstream/main` is **not** an option: with no merge base it treats every file present in
both trees as a conflict, and `--allow-unrelated-histories` scales the conflict count with the tree.

---

## Porting log

### 2026-11-13 — v2 ledger created; baseline established

- Confirmed v2 shares **no history** with upstream (`git merge-base` empty; independent roots).
  Measured divergence by tree, not by commit count.
- Located the snapshot baseline by byte-identical file count against candidate upstream commits:
  `eaac327f` (2026-11-11) matches best at 9,087 identical files, ahead of `2663c26b` (9,072) and the
  then-head `9d94f822` (9,015).
- Scanned `eaac327f..upstream/main` = 2,546 commits (2,491 non-merge). Filtered 1,688 as noise,
  leaving 803 signal commits / 311 in tracked subsystems / 300 behavioural clusters; seeded the
  newest of each as `PENDING`.
- Recorded the 15 fork-local commits and the fork-only surfaces so a regenerate cannot silently
  drop them.
- **Not yet triaged:** every row in the tracking table.

### 2026-11-13 — worktree env built; host baseline of failing tests recorded

- `update/upstream-2026-11-13` lives in a linked worktree (`../anakot-agent-v2-update`) because the
  live checkout is the running install and refuses `git switch`. Env:
  `python -m pm.build_env --source . --out .venv --group dev --group test` (354 MB, Python 3.14.9).
- **Pre-existing failures on this Windows host, identical on `main`.** Do not chase these as
  regressions; they are the comparison baseline for a regenerate:
  - `tests/ci/` — 6 failures + 1 collection error out of 49 files / 626 passing:
    `test_js_tests_vitest_history`, `test_messaging_gated_selection`, `test_tag_builds_summary[True]`,
    `test_prompt_surface`, `test_stable_release_graph`, `test_desktop_release_tag_admission`;
    `test_e2e_upgrade_start_version` cannot even import (`import pwd`, POSIX-only module).
  - `tests/anakot_cli/test_profiles.py` — 4 failures / 102 passing: POSIX file mode `0o600` vs
    Windows `0o438`, and `mybot` vs `mybot.bat` wrapper naming.
- Verified working in the worktree: `scripts/rebrand.py --check` (24,555 files, 1,486 protected
  occurrences, 0 drift) and `scripts/run_tests.sh` end to end.

### 2026-11-13 — flow dry-run on a real upstream tree (`9d94f822`); three transform bugs fixed

Ran steps 2–5 of the procedure above on a throwaway worktree at upstream head. The rebrand produced
25,528 files with 28,305 protected occurrences and left three defects, each of which made a broken
tree look green:

- **`hermes-ink` was in `SKIP_NAMES`**, which exempted the whole directory from the text rewrite.
  The package shipped as `"name": "@hermes/ink"` while the workspace depended on `@anakot/ink`, so
  the TUI workspace resolved nothing. It is a *path* to keep, not contents: split into
  `KEEP_PATH_NAMES`, honoured by `rename_paths` only.
- **Five brand fonts had no snapshot copy** (SaintCarell/SaintCarellClean/staravenue, in two dirs),
  so `--verify` reported them missing on every fresh tree and `--apply` could not restore them.
  Snapshotted + `--rebaseline` (40 files, 0 dropped).
- **A rename collision was skipped with a print.** An ignored leftover inside the directory being
  renamed (e.g. `anakot_cli/data/` surviving `git clean -fd`) left `hermes_cli/` *and* `anakot_cli/`
  standing — and `--verify` still said PASS because it only checked asset hashes. `rename_paths` now
  returns conflicts and the run aborts (exit 2); `--verify` fails on any pending rewrite, rename or
  drift. `git clean -fdx` in step 2 is what avoids the collision in the first place.

Verified after the fixes: clean upstream → 25,528 files → `--apply` → `--verify PASS`; a conflicted
tree exits 2 instead of 0. Also confirmed the two steps the transform cannot do by itself: the
lockfiles keep upstream identity until re-resolved (step 6), and `scripts/check` still needs the
exclusive-plugin guard registration re-applied (step 7).

**Operational note — the line-endings pre-push guard can time out, and it is not a real failure.**
`scripts/ci/check_line_endings.py` shells out to `git ls-files --eol -z` with a 120 s subprocess
timeout; on this 24,769-file tree that call takes ~15 s idle but exceeded 120 s twice while a
rebrand `--apply` was running in another worktree on the same disk. Both pushes were rejected with
`FAILED: line-endings` and `subprocess.TimeoutExpired`, and the identical commit then passed all 18
checks once the I/O settled. So: do not push while a rebrand or a test run is hammering the disk,
and treat a lone `line-endings` failure as contention until a quiet re-run says otherwise.

### 2026-11-14 — REGENERATED onto upstream `422ad18618` (latest main)

**Target.** Upstream main `422ad18618` (2026-11-14), chosen over the newest *stable release* tag
`v0.23.1` (2026-11-09): this fork's own content matches a 2026-11-11 commit most closely, so
targeting the release tag would have moved the tree backwards and dropped ~1,100 files. `v0.23.1`
is an ancestor of head, so head is a strict superset — verified, not assumed.

**Carry list, computed not hand-written.** 1,204 fork paths had no counterpart in the target. Of
those, 1,110 were files upstream *added* after the release and 7 were files upstream *deleted* —
`plugins/observability/langfuse` and `plugins/spotify`, both moved into the plugin catalog.
Restoring either set would have resurrected or duplicated upstream's own work, so the discriminator
was whether upstream *ever* tracked the path. That leaves **87 genuinely fork-authored paths**.

**Transform.** 25,775 files, 4,349 protected occurrences, 15,894 content rewrites, 576 path
renames, 4 brand files restored from the snapshot → `VERIFY: PASS`. `ANAKOT_HOME` ends up in 3,165
files and `HERMES_HOME` in 0; `anakot_cli`, `anakot_platform`, `anakot_yaml`, `anakot_state` all
present.

**Locks.** `uv.lock` passes the rename-only test: 18 `hermes` refs → 0, and `uv lock --check`
resolves 355 packages with zero diff, so no re-resolve was needed. `pnpm-lock.yaml` needs a real
re-resolve (names only, no version churn) because pnpm re-sorts keys, and it needs Node ≥ 26 — the
system Node 22 aborts with `ERR_PNPM_UNSUPPORTED_ENGINE` before reading anything.

#### Defects found this cycle — five, and the first is the important one

1. **The protected-strings rule swallowed the whole env-var surface.** §11 protected
   `(?-i:HERMES_[A-Z0-9_]+)` as "build-time env-var contracts". It was written to stop the script
   double-renaming an already-renamed tree — a property of one invocation, not of the brand — and
   it silently produced a tree with `HERMES_HOME` in 3,165 files and `ANAKOT_HOME` in none. A real
   `anakot chat` against an explicit `ANAKOT_HOME` answered "no API keys or providers found",
   because the home was ignored and the default was empty. v1's own tree has 0 files containing
   `HERMES_HOME` and 3,051 containing `ANAKOT_HOME`, so the rule contradicted the tree it was
   protecting. Fix (`50da217d28`): the family renames as a unit. The half-renamed contract it
   feared was in fact something it caused — `scripts/build/launchers.py` wrote
   `HERMES_RUNTIME_DIR` while the app read `ANAKOT_RUNTIME_DIR`, and both silently fell back to a
   default (that straggler is fixed too; both sides now say `ANAKOT_RUNTIME_DIR`). Five narrow
   entries stay protected because they are real external contracts: the dashboard/plugin browser
   globals (`__HERMES_PLUGIN_SDK__`, `__HERMES_PLUGINS__`, `__HERMES_SESSION_TOKEN__`, set by
   third-party plugin code we do not ship), the build wrapper vars (`HERMES_PYTHON`,
   `HERMES_INSTALL_ROOT`), and the Portal OAuth client id.
2. **`--verify` cannot see a missing file.** A tree that had lost ~570 renamed modules passed
   `VERIFY: PASS`, because the gate only looks for *pending* work (renames to do, rewrites to
   apply, asset drift) and never asks whether an expected path exists at all. A completeness leg —
   every index path either present or renamed-present — would have caught it.
3. **Rename collisions come from *ignored* files, not just untracked ones.** The abort fires when a
   rename target exists; `anakot_cli/data/` and a `__pycache__` were enough, and they are invisible
   to `git status`. Cleaning a worktree for a re-run must remove ignored files **and** the empty
   directories they leave behind — deleting the files alone leaves the collision intact.
4. **`pm.build_env` fails on a regenerated tree**, and so does anything that shells through it
   (lefthook, `scripts/anakot-python`): it rewrites the workspace manifest with
   `workspace.members`/`sources`, after which `uv sync --locked` judges the seeded core lock stale
   even though `uv lock` yields zero diff. Building straight from the same lock
   (`uv sync --locked --group dev --group test`) works, which is the workaround used here.
5. **Trimmed, but recorded:** `rebrand-asset-update/` at repo root is a stray skill-reference file
   the fork committed by mistake. Carried faithfully for now; a candidate for deletion.

**The lesson worth carrying forward:** unit tests and CI cannot catch defect 1 — they passed on the
broken tree, because a test that sets its own `ANAKOT_HOME` fixture and a test that reads the wrong
variable look identical. Only smoke-testing the real entrypoint against an explicit
`ANAKOT_HOME` did. Make that the last step of every regenerate:

```bash
ANAKOT_HOME=<copy-of-a-real-profile> anakot -z "say hi" --cli
```

A "no API keys or providers found" answer means the *brand surface*, not the model, is broken.

**Tests.** `tests/ci/` shows 6 failures + 1 import error, byte-identical to the recorded host baseline
(the same six files, one test each; `test_e2e_upgrade_start_version` cannot even import, since `pwd`
is POSIX-only), and `tests/anakot_cli/test_profiles.py` 4 failed / 102 passed — also identical. The
open question was `tests/ci/test_update_ci_routing.py`, which exceeds the default 300 s per-file cap
on this host. Raised, it **passes: 105 passed, 0 failed, 1 skipped in 631 s.** It parametrizes over
lane sets and spawns a classifier subprocess per case — cheap on Linux CI, seconds each on Windows —
so this is host slowness, not a regression. The cap variable is `ANAKOT_TEST_FILE_TIMEOUT` on this
tree; exporting the pre-rename `HERMES_` spelling silently leaves the default in place, which is how
one run reported it as a timeout.

**Gates.** 18 of 20 `scripts/check` guards pass. The two ratchet guards are **not measurable for a
regenerate**, and that is a property of the base rather than of the tree:

- `blob-size --base 422ad18618` reports four blobs over the 500 KiB limit —
  `assets/banner.png`, `brand/assets/assets/banner.png`,
  `apps/desktop/public/ds-assets/filler-bg0.jpg` and its snapshot copy. Every one is byte-identical
  to the same path on `main` (`git rev-parse <ref>:<path>` agrees), so merging this branch adds no
  new blob object: there is nothing to compress and nothing to allowlist. Measuring against upstream
  simply makes the fork's own brand art look new.
- `health --base 422ad18618` exceeds its own internal 900 s budget over a 16k-path delta and cannot
  finish on this host.

Both need a per-change base (an ordinary PR) to mean anything. For a whole-tree regenerate, record
them as unmeasurable — never as passed, and not as failed either.

**Environment findings.** A full system drive disguises itself as `curl: (23) client returned ERROR
on write` while pm bootstraps uv; `uv cache clean` reclaimed 5.6 GB. `run_tests.sh` on this version
honours **`HERMES_PYTHON`** (protected), not `ANAKOT_PYTHON`, and the per-file cap variable it reads
is `ANAKOT_TEST_FILE_TIMEOUT`.

**New this cycle — `scripts/dev-install.sh`.** A regenerated tree cannot be set up the documented way
(`pm.build_env` refuses it, and the JS tree wants Node ≥ 26 that PATH rarely has), and the resulting
build must not be pointed at the live profile. This script encodes both: build with
`uv sync --locked --all-packages --group dev --group test` from the repo lock, reuse a staged uv when
none is on PATH, optionally install JS deps with the bundled Node through the MSYS PATH spelling,
create an isolated dev home (optionally seeded by copying — never moving — the live config), and
verify the brand home actually resolves before handing over. Two modes: in-place (the tree you are
standing in) and bootstrap (`--dir` + `--ref`, shallow clone by default; a dev install runs the tree,
it does not need upstream's 16k commits). Measured on this host: a fresh shallow clone plus a full
Python env in 49 s. It is fork-authored, so the computed carry list picks it up on its own next cycle.

**The brand layer a regenerate cannot carry (found by running the dev build).** The carry list
restores paths upstream never tracked. It cannot restore a fork's edits **inside** upstream-tracked
files: those paths exist upstream, so the carry list skips them and upstream's version wins. Measured
across both trees (24,755 paths compared, rebrand reversed before comparing): 21,550 identical, 4
rename-only, 3,201 with a real content difference — and of those, 2,307 are simply upstream moving on
since the fork's baseline while **246 are files the fork edited deliberately**. The discriminator is
the fork's baseline commit, not the target: a file the fork inherits unchanged is upstream's problem,
a file whose bytes differ from `eaac327f:<path>` is the fork's own work.

Two of the 246 showed up immediately in the dev desktop — this is what "the font never changed" and
"the logo is still the Hermes girl" actually were:

- `apps/desktop/src/styles.css` — the `@font-face` for Rostex plus the `.wordmark` family (13 lines
  total). The brand font files were present and byte-perfect the whole time; nothing referenced them.
- `scripts/generate_icons.py` — the fork's copy reads the fork's own single-path girl art. Upstream's
  asserts `no <path> found in nous-girl-black.svg`, so the icons cannot be rendered at all with it,
  and every icon/logo target stays upstream art. Note `brand/assets.manifest.json` cannot catch this:
  generator-owned paths are excluded from **both** `restore_assets` and `verify_assets` by design, so
  a missing render is invisible to the gate.

95 of the 246 are brand art (15 `brand-ui` + 80 `generated-art`) and are restored verbatim in this
branch, along with the fork's generator. Re-running the restored generator in a clone that has the JS deps renders every target cleanly, exit
0, and its output is **pixel-identical** to the fork's committed art (mean channel difference 0.00/255
on every file probed) — the bytes differ only in PNG encoder metadata. So a future regenerate may
either restore these files verbatim or re-render them; the generator is the durable route, the verbatim
copy is the byte-exact one.

The other 151 are code and config the fork edited — build
scripts, installers, CI workflows, agent files — where upstream has *also* moved on, so a blind
restore would revert upstream work and a blind keep would drop the fork's. Those need a three-way
merge (`base` = the file at `eaac327f` rebranded, `ours` = the fork, `theirs` = this tree) and are
outstanding.

---

## Quick commands

```bash
# Full commit detail (message + per-file patch)
git show <sha> --stat && git show <sha>

# Files a commit touched, as paths only
git show --name-only --format="" <sha>

# Compare a fork path against upstream
git diff upstream/main main -- path/to/file

# How the fork's tree differs from a given upstream commit
git diff --shortstat <upstream-sha> main

# Recheck which upstream commit matches the fork tree best (baseline drift)
scratch="$(mktemp -d)"
git ls-tree -r main           | awk '{print $3, $4}' | sort -k2 > "$scratch/fork.tsv"
git ls-tree -r <upstream-sha> | awk '{print $3, $4}' | sort -k2 > "$scratch/up.tsv"
join -1 2 -2 2 -o 1.1,2.1 "$scratch/fork.tsv" "$scratch/up.tsv" | awk '$1==$2' | wc -l
rm -rf "$scratch"

# Verify the rebrand is intact
python scripts/rebrand.py --check
```

## See also

- `brand/protected-strings.txt` — the authoritative list of strings the rebrand must not touch
- `scripts/rebrand.py --help` — the rebrand's own contract
- Root `AGENTS.md`, `anakot_cli/AGENTS.md`, `apps/desktop/AGENTS.md` — invariants a port must respect

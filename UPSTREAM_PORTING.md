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
| Fork-local commits | 14 (listed below) |
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

These 14 commits are Anakot v2's own work. A scripted regenerate drops all of them unless they are
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

Because the histories are unrelated, updating is a **regenerate**, not a merge:

```bash
git tag backup/pre-update                        # safety point
git fetch upstream
git checkout -b update/vNEXT upstream/main       # start from fresh upstream
git checkout backup/pre-update -- scripts/rebrand.py brand/ anakot_rebrand_masters/
python scripts/rebrand.py --apply
python scripts/rebrand.py --verify               # gate: protected strings + asset hashes
git cherry-pick <the fork-local commits above>   # re-apply Anakot's own work
scripts/run_tests.sh                             # prove it
```

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
- Recorded the 14 fork-local commits and the fork-only surfaces so a regenerate cannot silently
  drop them.
- **Not yet triaged:** every row in the tracking table.

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

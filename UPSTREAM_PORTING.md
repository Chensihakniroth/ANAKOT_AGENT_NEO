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

## v2 status (2026-11-16)

> **Fork topology.** `git merge-base main upstream/main` returns **nothing** — v2 is a snapshot import
> (root commit `238ab19e`, *feat: initial release of Anakot Agent Neo*, 2026-11-12), so the two trees
> are parallel histories. An ahead/behind count is therefore meaningless:
> `git rev-list --left-right --count main...upstream/main` reports `17 73214`, where 73,214 is
> upstream's *entire* history, not a measure of debt. Compare trees and subsystems instead.

| Fact | Value |
|------|-------|
| Fork remote (`origin`) | `https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO.git` |
| Upstream remote | `https://github.com/NousResearch/hermes-agent.git` (already configured) |
| Snapshot baseline | `eaac327f` (2026-11-11) — closest upstream commit by byte-identical file count (9,087 of ~24.8k) |
| Upstream head at this scan | `be73ce8e76` (2026-11-15) |
| Previous scan head | `9d94f822` (2026-11-13) — ancestor of the current tip, so this is a clean linear addition |
| New since the previous scan | 2,470 commits (2,297 excluding merges) |
| Window since baseline | 5,016 commits (4,788 excluding merges) |
| Upstream velocity | ~16.4k commits / 30 days |
| Fork-local commits | 17 (listed below) |
| Differing paths vs upstream head | re-measure with `git diff --name-status` before quoting |
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

**Scan result for the 2026-11-16 window** (`9d94f822..be73ce8e76`, 2,470 commits / 2,297 non-merge):
**772 filtered as noise** (catalog/maintenance 242, test-only 233, chore 205, docs 77, style 6,
ci 6, build 2, revert 1), leaving **1,525 signal commits**, of which **1,293 land in tracked
subsystems** and collapse into **1,262 behavioural clusters**. The newest **70** are seeded in the
second tracking table below. Concentration by area (files touched across tracked commits): cli 605,
tools 533, agent 370, gateway 365, desktop 215, plugins 207, cron 62.

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

## Tracking table — 2026-11-16 window (9d94f822..be73ce8e76)

Seeded from the 2026-11-16 scan — the newest commit of each behavioural cluster in the
`9d94f822..be73ce8e76` window. These are **disjoint** from the 2026-11-13 table above (that window was
`eaac327f..9d94f822`), so both queues stay live. Empty `Notes` means untriaged.

| SHA | Date | Description | Status | Notes |
|-----|------|-------------|--------|-------|
| fbc65ec989 | 2026-11-15 | fix(approval): fail closed on over-nested eval inside carried payloads | `PENDING` | |
| fb48931764 | 2026-11-15 | fix(cron): exempt Stop-Process -WhatIf only for a single plain statement | `PENDING` | |
| f66b6cddb3 | 2026-11-15 | fix(gateway): a reply's attachments follow its text onto the reconnected adapter | `PENDING` | |
| f3661de135 | 2026-11-15 | Update cron/jobs.py | `PENDING` | |
| e4783c505b | 2026-11-15 | fix(redact): mask a key that an overlapping prefix match hid | `PENDING` | |
| ce4de3cdc2 | 2026-11-15 | fix(tts): a command provider never receives the caller's output path | `PENDING` | |
| cbdc6af748 | 2026-11-15 | fix(approval): an fd redirection between osascript -e arguments does not end the command | `PENDING` | |
| c066ed4dcd | 2026-11-15 | fix(approval): split >&/>\| redirects and fd-input operators between osascript -e args | `PENDING` | |
| b2c6bc4e1e | 2026-11-15 | fix(usage): provider limits first, Nous balance apart | `PENDING` | |
| b0f072515b | 2026-11-15 | fix(approval): keep a quoted glob char literal when dequoting rm operands | `PENDING` | |
| aa561bbc02 | 2026-11-15 | fix(approval): a CR before -Include ends main's rm drive-root delete too | `PENDING` | |
| a11598f389 | 2026-11-15 | fix(redact): recover a key swallowed by a skipped glued candidate | `PENDING` | |
| 9fb34895ba | 2026-11-15 | fix(approval): a .md file name is not the md verb in the registry-write rule | `PENDING` | |
| 8c784998a6 | 2026-11-15 | fix(redact): step over contained matches when looking for a swallowed key | `PENDING` | |
| 8ad7e62d4f | 2026-11-15 | fix(redact): keep a template DB URL query password from hiding a ; sibling | `PENDING` | |
| 893c3948aa | 2026-11-15 | fix(cron): check spps, the Stop-Process alias, against the gateway PID | `PENDING` | |
| 7defffc296 | 2026-11-15 | fix(lint): clear the findings ruff preview reports | `PENDING` | |
| 7c644207d1 | 2026-11-15 | fix(approval): flag AppleScript text-element assignment as risky | `PENDING` | |
| 76e07759df | 2026-11-15 | refactor(approval): move the git global-option grammar to tools/approval_git_options.py | `PENDING` | |
| 71b871d40e | 2026-11-15 | fix(threat-patterns): keep forget_rules unbounded for the raw-line scanners | `PENDING` | |
| 70ae41f8dc | 2026-11-15 | fix(dashboard): run the locked-root /api/fs read guard off the event loop | `PENDING` | |
| 6cea8f027b | 2026-11-15 | fix(skills): print the third-party notice after the file list on unprompted installs | `PENDING` | |
| 617bba2512 | 2026-11-15 | fix(cron): a trailing-colon parameter takes -WhatIf as its value | `PENDING` | |
| 5dc14e15ba | 2026-11-15 | fix(approval): peel leading redirections and abbreviated sudo long options; hardline rm.exe | `PENDING` | |
| 51dfa80e89 | 2026-11-15 | fix(cron): scrub pre-upgrade stamps on idle sibling jobs when a run saves | `PENDING` | |
| 50632609bf | 2026-11-15 | refactor(approval): move the quoted-newline mask into approval_quoted_newlines | `PENDING` | |
| 5047796127 | 2026-11-15 | fix(approval): let the collapse tail own quote pairs after a quoted system dir | `PENDING` | |
| 5009935d40 | 2026-11-15 | refactor(approval): move the variation-selector matcher into approval_variation_selectors | `PENDING` | |
| 5008e6a83c | 2026-11-15 | fix(threat-patterns): anchor the long-word forget branch at whitespace; let CRLF wrap a negator | `PENDING` | |
| 445d699ab2 | 2026-11-15 | fix(redact): accept configparser's `:` delimiter in credential-store INI lines | `PENDING` | |
| 3e6cfbaf98 | 2026-11-15 | fix(redact): run the INI pass before the netrc scan so `password =a b` masks whole | `PENDING` | |
| 3d5c4eaa4b | 2026-11-15 | fix(redact): end a DB URL query password only at &, # or whitespace | `PENDING` | |
| 34c4c497d4 | 2026-11-15 | refactor(approval): fold the dequoted-verb yields into one filter | `PENDING` | |
| 2fd57b4403 | 2026-11-15 | fix(redact): treat PowerShell gc and -Path:<file> reads as credential-file reads | `PENDING` | |
| 2a51b76696 | 2026-11-15 | fix(plugins): demote plugin-guard findings inside Python docstrings | `PENDING` | |
| 260e4331a4 | 2026-11-15 | fix(approval): flag a bare ~/.ssh create/link target anywhere in the command | `PENDING` | |
| 25654c4f1f | 2026-11-15 | fix(approval): quoted or escaped > never makes a real & a redirection; ordinal text selectors | `PENDING` | |
| 234bd742d2 | 2026-11-15 | fix(approval): read git option substitutions nested up to four levels as one word | `PENDING` | |
| 1f72a86a40 | 2026-11-15 | refactor(approval): import _split_env_string from approval_env_split directly | `PENDING` | |
| 10905ca004 | 2026-11-15 | refactor(approval): move the span-keeping shell lexer to tools/approval_shell_tokens.py | `PENDING` | |
| feac245d8e | 2026-11-14 | fix(post_update): migration backups are owner-only | `PENDING` | |
| fdbfd1b86e | 2026-11-14 | fix(threat-patterns): make the negated-forget mask linear on emphasis runs | `PENDING` | |
| fd773ff54a | 2026-11-14 | fix(gateway): the restart watcher judges the old gateway by pid and start time | `PENDING` | |
| fd0655ab84 | 2026-11-14 | fix(redact): mask quoted/spaced credential-store values, cover ~/.aws/config and _netrc | `PENDING` | |
| fcabfe38bc | 2026-11-14 | fix(gateway): keep primary re-login hint on the resolved backup account | `PENDING` | |
| fc73b06fb9 | 2026-11-14 | fix(redact): stop DB URL query scan at quotes/angle brackets; keep templates | `PENDING` | |
| fc562d87b7 | 2026-11-14 | fix(plugins): a docstring sharing its line with code, or read back as data, stays critical | `PENDING` | |
| fb98fd527c | 2026-11-14 | fix(skills): keep hardlinked siblings in the background-scan scope; tolerate symlink loops | `PENDING` | |
| faa5ad003d | 2026-11-14 | fix(redact): URL query mask drops the _value suffix like the JSON rule; pin closed-list names | `PENDING` | |
| fa8a9e79ac | 2026-11-14 | refactor(desktop): move the global-remote session route out of main.ts | `PENDING` | |
| f81385553e | 2026-11-14 | fix(redact): keep == comparisons out of spaced config-assignment passes | `PENDING` | |
| f7cd1f45b2 | 2026-11-14 | fix(gateway): a non-forced restart or update never stops a gateway still doing work | `PENDING` | |
| f6f389fee3 | 2026-11-14 | refactor(cron): scan a path's written bodies in a helper | `PENDING` | |
| f670c8b4a8 | 2026-11-14 | fix(telegram): a comment and the video, voice or file sent right after it are one turn | `PENDING` | |
| f61bc58e5b | 2026-11-14 | fix(approval): stop the DELETE WHERE lookahead at shell redirections | `PENDING` | |
| f3e3bade84 | 2026-11-14 | fix(approval): a glued redirect still ends the socat/nc command word | `PENDING` | |
| f25aed52f6 | 2026-11-14 | fix(gateway): load the restart watcher builder with the gateway module | `PENDING` | |
| f24c795aa2 | 2026-11-14 | fix(desktop): resolve a relocated Hermes .env in the credential-store sweep | `PENDING` | |
| f218799808 | 2026-11-14 | fix(gateway): catch a profile refusal raised on scope entry, per event | `PENDING` | |
| f1ecb5e08f | 2026-11-14 | fix(signal): clear the 👀 actually sent even if the auth verdict flips mid-turn | `PENDING` | |
| f17cecbdf3 | 2026-11-14 | refactor(telegram): move legacy-edit bookkeeping out of edit_message | `PENDING` | |
| f144ad5433 | 2026-11-14 | fix(redact): mask bare Grafana glsa_/glc_ tokens | `PENDING` | |
| ee63c99341 | 2026-11-14 | fix(cron): scan heredoc bodies a command writes and then executes | `PENDING` | |
| ee40506d07 | 2026-11-14 | fix(update): a restart left pending survives into the completion process, by (pid, start time), and reconciles as pending | `PENDING` | |
| ed828d4c5e | 2026-11-14 | fix(code-exec): mask env-dump lines in execute_code output | `PENDING` | |
| ed6c244abe | 2026-11-14 | fix(approval): keep the Windows hardline scan linear on runs of bare CRs | `PENDING` | |
| ed3ffe8095 | 2026-11-14 | fix(telegram): split replies can drop the first-part anchor with opt-in extra.anchor_multipart_replies | `PENDING` | |
| ed1f43c1f3 | 2026-11-14 | fix(context): surface SSRF and secret-URL refusals in @url references | `PENDING` | |
| ec460b1e5a | 2026-11-14 | feat(security): opt-in security.redact_phone_numbers keeps E.164 numbers in chat replies | `PENDING` | |
| ebfa8435b5 | 2026-11-14 | refactor(desktop): Bot Mode sidebar scope lives in its own module | `PENDING` | |

---

## Fork-local commits (must survive every sync)

These 17 commits are Anakot v2's own work. A scripted regenerate drops all of them unless they
are re-applied.

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
| `9b0cfdf2` | 2026-11-13 | docs(upstream): add the v2 porting ledger with a measured baseline | This file — regenerate restores it only if the carry list includes it |
| `0be8c3ed` | 2026-11-15 | feat(desktop): add GUI-only desktop variant | A `desktop` build variant: bundled payload with no TUI/web frontends planted |
| `c36521d9` | 2026-11-16 | fix(desktop): teach the build stamp about the desktop variant | The variant must stamp as `bundled` (the stamp's own mechanism table) |

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

## Cycle tree for this scan

| Item | Value |
|------|-------|
| Branch | `update/upstream-2026-11-16` |
| Worktree | `D:/School/PROJECT/anakot-next3` |
| Tip | `be73ce8e76` — fresh `upstream/main`, pre-rebrand |
| Safety tag | `backup/pre-update-2026-11-16` -> `c36521d908` (`main`) |

The tree is a **pristine upstream checkout**: no rebrand applied, no fork files carried yet. The
regenerate (carry list -> `rebrand.py --apply` -> `--verify` -> re-lock -> residue) has not run.

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

### 2026-11-16 — cycle opened; window re-scanned

- Fetched `upstream/main` to `be73ce8e76` (2026-11-15). The ledger's recorded head `9d94f822` is an
  ancestor, so the 2,470 new commits are a linear addition — not a rewrite.
- Created the fresh cycle tree `update/upstream-2026-11-16` in worktree `anakot-next3`, checked out at
  the pristine upstream tip, plus safety tag `backup/pre-update-2026-11-16` at `main` (`c36521d908`).
- Re-scanned `9d94f822..be73ce8e76`: 2,470 commits (2,297 non-merge) -> 772 noise ->
  1,525 signal -> 1,293 in tracked subsystems -> 1,262 clusters; seeded the newest 70.
- Corrected the fork-local commit count 14 -> 17 (the ledger itself, plus the two
  `desktop`-variant commits, had never been listed).
- **Known tooling gap:** the workflow's `scripts/carry_list.py` and `scripts/lock_decide.py` do not
  exist in this repo (only `rebrand.py`, `fix_lock_identity.py`, `find_lost_customizations.py` and
  `dev-install.sh`, and those live on the update branches, not `main`). The carry list must be
  computed another way until they are added.
- **Not done:** the regenerate itself (carry, `--apply`, `--verify`, re-lock, residue, gates,
  suite, smoke). The tree is upstream-only.

---

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

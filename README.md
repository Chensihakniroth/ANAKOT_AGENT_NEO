<p align="center">
  <img src="assets/banner.png" alt="Anakot Agent" width="100%">
</p>

# Anakot Agent ☤
<p align="center">
  <a href="https://anakot-agent-doc.up.railway.app/">Anakot Agent</a> | <a href="https://anakot-agent-doc.up.railway.app/user-guide/desktop">Anakot Desktop</a>
</p>
<p align="center">
  <a href="https://anakot-agent-doc.up.railway.app/"><img src="https://img.shields.io/badge/Docs-anakot--agent--doc.up.railway.app-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO/releases/latest/download/Anakot-Setup.exe"><img src="https://img.shields.io/badge/Download-Windows_Installer-2ea043?style=for-the-badge" alt="Download the Windows installer"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-OASIS-blueviolet?style=for-the-badge" alt="Built by OASIS"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**The self-improving AI agent built by [OASIS](https://anakot-agent-doc.up.railway.app/).** It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions. Run it on a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. It's not tied to your laptop — talk to it from Telegram while it works on a cloud VM.

Use any model you want — [Nous Portal](https://portal.nousresearch.com), OpenRouter, OpenAI, your own endpoint, and [many others](https://anakot-agent-doc.up.railway.app/integrations/providers). Switch with `anakot model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. In Desktop, choose their provider, model, and limits under Settings → Model → Subagents, then Apply the complete route. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Six built-in terminal backends — local, Docker, SSH, Modal, Daytona, and Vercel Sandbox — plus plugin backends such as Singularity/Apptainer. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, trajectory compression for training the next generation of tool-calling models.</td></tr>
</table>

---

## Quick Install

### Download the installer (Windows)

**[Anakot-Setup.exe](https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO/releases/latest/download/Anakot-Setup.exe)** — the bootstrap installer. It provisions Python, Node.js and Git, clones this repository, and builds the CLI, TUI and Desktop app. It also removes a source install again: `Anakot-Setup.exe --uninstall` keeps your configuration and data, `--uninstall --full` takes those too.

### From source

#### Linux, macOS, WSL2

```bash
git clone https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO.git && cd ANAKOT_AGENT_NEO && ./setup-anakot.sh
```

#### Windows (native, PowerShell)

> **Heads up:** Native Windows runs Anakot without WSL — CLI, gateway, TUI, and tools all work natively. If you'd rather use WSL2, the Linux/macOS one-liner above works there too. Found a bug? Please [file issues](https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO/issues).

Run this in PowerShell:

```powershell
git clone https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO.git; cd ANAKOT_AGENT_NEO; ./setup-anakot.ps1
```

The source installer delegates Python 3.14, Node.js, npm, pnpm, ripgrep, FFmpeg,
and Python dependencies to PM. If Git is absent, it stages the verified Git
for Windows archive in Anakot' tool store. It does not replace your system Git.
See [installation methods](https://anakot-agent-doc.up.railway.app/getting-started/installation)
for the separate MSIX/App Installer package and its update ownership.

> **Android / Termux:** A signed APT repository is available for aarch64 devices, with a `stable` channel (tagged releases) and a prerelease `canary` channel. The package includes Python, Node.js, and the TUI. Use the [Termux guide](https://anakot-agent-doc.up.railway.app/getting-started/termux), not the desktop/server installer script.
>
> **Windows:** Native Windows is fully supported — the PowerShell one-liner above installs everything. If you'd rather use WSL2, the Linux command works there too. Native Windows install lives under `%LOCALAPPDATA%\anakot`; WSL2 installs under `~/.anakot` as on Linux.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
anakot              # start chatting!
```

### Troubleshooting

#### Windows Defender or antivirus flags `uv.exe` as malware

If your antivirus (Bitdefender, Windows Defender, etc.) quarantines `uv.exe` from the Anakot `bin` folder (`%LOCALAPPDATA%\anakot\bin\uv.exe`), this is a **false positive**. The file is Astral's `uv` — the Rust Python package manager Anakot bundles to manage its Python environment. ML-based antivirus engines commonly flag unsigned Rust binaries that download and install packages.

**To verify your copy is authentic:**

```powershell
# Install GitHub CLI if needed
winget install --id GitHub.cli

# Login to GitHub
gh auth login

# Run verification
$uv = "$env:LOCALAPPDATA\anakot\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

If attestation says "Verification succeeded" and the last line prints `True`, you're good.

**To whitelist Anakot:**
- **Windows Defender:** Run PowerShell as Admin → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\anakot\bin"`
- **Bitdefender:** Add an exception in the Bitdefender console (Protection > Antivirus > Settings > Manage Exceptions)
- Whitelist the **folder**, not the file hash — Anakot updates `uv` and the hash changes every version

For more context, see the upstream Astral reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553), [astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011), [astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079).

---

## Getting Started

```bash
anakot              # Interactive CLI — start a conversation
anakot model        # Choose your LLM provider and model
anakot tools        # Configure which tools are enabled
anakot config set   # Set individual config values
anakot config get   # Print individual config values
anakot gateway      # Start the messaging gateway (Telegram, Discord, etc.)
anakot setup        # Run the full setup wizard (configures everything at once)
anakot update       # Update to the latest version
anakot doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://anakot-agent-doc.up.railway.app/)**

---

## Skip the API-key collection — Nous Portal

Anakot works with whatever provider you want — that's not changing. But if you'd rather not collect five separate API keys for the model, web search, image generation, TTS, and a cloud browser, **[Nous Portal](https://portal.nousresearch.com)** covers all of them under one subscription:

- **300+ models** — pick any of them with `/model <name>`
- **Tool Gateway** — web search, image generation (FAL), text-to-speech (OpenAI), cloud browser (Browser Use), all routed through your sub. No extra accounts.

One command from a fresh install:

```bash
anakot setup --portal
```

That logs you in via OAuth, sets Nous as your provider, and turns on the Tool Gateway. Check what's wired up any time with `anakot portal info`. Full details on the [Tool Gateway docs page](https://anakot-agent-doc.up.railway.app/user-guide/features/tool-gateway).

You can still bring your own keys per-tool whenever you want — the gateway is per-backend, not all-or-nothing.

---

## CLI vs Messaging Quick Reference

Anakot has two entry points: start the terminal UI with `anakot`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Start chatting                 | `anakot`                                      | Run `anakot gateway setup` + `anakot gateway start`, then send the bot a message |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

For the full command lists, see the [CLI guide](https://anakot-agent-doc.up.railway.app/user-guide/cli) and the [Messaging Gateway guide](https://anakot-agent-doc.up.railway.app/user-guide/messaging).

---

## Documentation

All documentation lives at **[anakot-agent-doc.up.railway.app](https://anakot-agent-doc.up.railway.app/)**:

| Section                                                                                             | What's Covered                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Quickstart](https://anakot-agent-doc.up.railway.app/getting-started/quickstart)                 | Install → setup → first conversation in 2 minutes          |
| [CLI Usage](https://anakot-agent-doc.up.railway.app/user-guide/cli)                              | Commands, keybindings, personalities, sessions             |
| [Configuration](https://anakot-agent-doc.up.railway.app/user-guide/configuration)                | Config file, providers, models, all options                |
| [Messaging Gateway](https://anakot-agent-doc.up.railway.app/user-guide/messaging)                | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://anakot-agent-doc.up.railway.app/user-guide/security)                          | Command approval, DM pairing, container isolation          |
| [Tools & Toolsets](https://anakot-agent-doc.up.railway.app/user-guide/features/tools)            | 40+ tools, toolset system, terminal backends               |
| [Skills System](https://anakot-agent-doc.up.railway.app/user-guide/features/skills)              | Procedural memory, Skills Hub, creating skills             |
| [Memory](https://anakot-agent-doc.up.railway.app/user-guide/features/memory)                     | Persistent memory, user profiles, best practices           |
| [MCP Integration](https://anakot-agent-doc.up.railway.app/user-guide/features/mcp)               | Connect any MCP server for extended capabilities           |
| [Cron Scheduling](https://anakot-agent-doc.up.railway.app/user-guide/features/cron)              | Scheduled tasks with platform delivery                     |
| [Context Files](https://anakot-agent-doc.up.railway.app/user-guide/features/context-files)       | Project context that shapes every conversation             |
| [Architecture](https://anakot-agent-doc.up.railway.app/developer-guide/architecture)             | Project structure, agent loop, key classes                 |
| [Contributing](https://anakot-agent-doc.up.railway.app/developer-guide/contributing)             | Development setup, PR process, code style                  |
| [CLI Reference](https://anakot-agent-doc.up.railway.app/reference/cli-commands)                  | All commands and flags                                     |
| [Environment Variables](https://anakot-agent-doc.up.railway.app/reference/environment-variables) | Complete env var reference                                 |

---

## Migrating from OpenClaw or another agent

If you're coming from OpenClaw, Claude Code, Codex CLI or Cursor, Anakot can import your settings, memories and skills (and, for OpenClaw, API keys when you ask for them).

**During setup:** `anakot setup` asks whether to import from another agent, pre-selects the ones it finds (`~/.openclaw`, `~/.claude`, `~/.codex`, `~/.cursor`), installs the official `agent-importers` plugin and runs the import with a preview first.

**Anytime after install:**

```bash
anakot plugins install agent-importers          # once per profile
anakot import-agent openclaw                    # interactive migration (full preset)
anakot import-agent openclaw --dry-run          # preview what would be migrated
anakot import-agent openclaw --migrate-secrets  # also bring allowlisted API keys
anakot import-agent claude-code                 # or codex / cursor
```

What gets imported from OpenClaw:

- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.anakot/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs), only with `--migrate-secrets`
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

`anakot claw migrate` still works as the older spelling. See the [OpenClaw migration guide](https://anakot-agent-doc.up.railway.app/guides/migrate-from-openclaw) and [Import from Other Agents](https://anakot-agent-doc.up.railway.app/user-guide/import-from-other-agents).

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://anakot-agent-doc.up.railway.app/developer-guide/contributing) for development setup, code style, and PR process.

Start with the [PM developer workflow](website/docs/reference/package-management.md#developer-workflow)
for activation, daily use, dependency changes, and leaving the environment.
[Development Setup](CONTRIBUTING.md#development-setup) covers the separate test environment and verification commands.

---

## Community

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/Chensihakniroth/ANAKOT_AGENT_NEO/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server for Anakot and other MCP hosts, with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.
- 🔌 [AnakotClaw](https://github.com/AaronWong1999/anakotclaw) — Community WeChat bridge: Run Anakot Agent and OpenClaw on the same WeChat account.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [OASIS](https://anakot-agent-doc.up.railway.app/).

//! Uninstall mode — Anakot Setup's hand-off to the canonical uninstaller.
//!
//! Removal semantics are NOT reimplemented here. `anakot_cli/uninstall.py` owns
//! them: it is steward-gated (only a git checkout may have its code removed;
//! nix / desktop-app / docker trees get data-only), it stops the gateway, and
//! it strips the launcher from PATH. This module is the same kind of shell for
//! `anakot uninstall` that `bootstrap.rs` is for `scripts/install.ps1`, so the
//! GUI and the CLI can never disagree about what "uninstall" means.
//!
//! Invocation: `Anakot-Setup.exe --uninstall [--full]`. The flag IS the intent —
//! there is no bare-launch uninstall — mirroring the CLI's own `--yes` contract
//! for non-interactive callers (anakot_cli/main.py::cmd_uninstall). Anchoring on
//! the CLI also means the GUI inherits `--gui-summary`, `--dry-run` and the
//! `--gui` / `--data` scopes for free when a chooser screen wants them.

use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter};

use crate::events::{BootstrapEvent, LogStream, StageInfo, StageState};
use crate::paths;
use crate::update::{resolve_anakot, run_streamed};

/// Which data policy the run uses. Mirrors the CLI: the default removes the
/// installation but preserves configuration and user data; `Full` is
/// `anakot uninstall --full`. Never travels over the Tauri boundary — the
/// frontend passes no policy, so nothing can ask for a different removal than
/// the command line did.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum UninstallMode {
    #[default]
    Keep,
    Full,
}

impl UninstallMode {
    /// `--full` selects Full; anything else keeps data. Arg-iterator generic so
    /// it stays unit-testable, like `AppMode::from_args`.
    pub fn from_args<I, S>(args: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        for a in args {
            if a.as_ref() == "--full" {
                return Self::Full;
            }
        }
        Self::Keep
    }
}

/// One uninstall at a time, same guard shape as UPDATE_RUNNING.
static UNINSTALL_RUNNING: AtomicBool = AtomicBool::new(false);

/// Frontend → Rust: run the uninstall.
///
/// The data policy is deliberately NOT a parameter: `--full` is a launch-time
/// fact, so the UI cannot ask for a different removal than the command line
/// specified, and a retry after a failure re-uses the original policy instead of
/// defaulting a wipe back to a keep. Fire-and-forget; progress arrives on the
/// `bootstrap` channel. Mirrors `start_update`'s shape.
#[tauri::command]
pub async fn start_uninstall(
    app: AppHandle,
    state: tauri::State<'_, std::sync::Arc<crate::AppState>>,
) -> Result<(), String> {
    let mode = state.uninstall_mode;
    if UNINSTALL_RUNNING
        .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
        .is_err()
    {
        // Already running: re-emit the manifest so a duplicate start call (which
        // resets the frontend store) recovers its stage list.
        emit(
            &app,
            BootstrapEvent::Manifest {
                stages: uninstall_stages(),
                protocol_version: None,
            },
        );
        return Ok(());
    }
    tokio::spawn(async move {
        if let Err(err) = run_uninstall(app.clone(), mode).await {
            emit(
                &app,
                BootstrapEvent::Failed {
                    stage: None,
                    error: format!("{err:#}"),
                },
            );
        }
        UNINSTALL_RUNNING.store(false, Ordering::SeqCst);
    });
    Ok(())
}

/// The synthetic uninstall manifest. Three stages, each a real operation below
/// — never a cosmetic split of one `anakot uninstall` call.
fn uninstall_stages() -> Vec<StageInfo> {
    let stage = |name: &str, title: &str| StageInfo {
        name: name.to_string(),
        title: title.to_string(),
        category: "uninstall".to_string(),
        needs_user_input: false,
    };
    vec![
        stage("detect", "Checking the installation"),
        stage("remove", "Removing Anakot"),
        stage("verify", "Verifying removal"),
    ]
}

async fn run_uninstall(app: AppHandle, mode: UninstallMode) -> anyhow::Result<()> {
    let home = paths::anakot_home();
    let install_root = home.join("anakot-agent");

    emit(
        &app,
        BootstrapEvent::Manifest {
            stages: uninstall_stages(),
            protocol_version: None,
        },
    );

    // ---- detect -----------------------------------------------------------
    emit_stage(&app, "detect", StageState::Running, None, None);
    let started = Instant::now();
    // A launcher owned by THIS installation is the same proof the update mode
    // relies on, and it doubles as the child we will run.
    let status = resolve_anakot(&install_root).await;
    let Some(launcher) = status else {
        let msg = format!(
            "No Anakot installation found under {}. Nothing to uninstall.",
            install_root.display()
        );
        emit_log(&app, Some("detect"), LogStream::Stderr, &format!("✗ {msg}"));
        emit_stage(
            &app,
            "detect",
            StageState::Failed,
            Some(elapsed_ms(started)),
            Some(msg.clone()),
        );
        emit(
            &app,
            BootstrapEvent::Failed {
                stage: Some("detect".to_string()),
                error: msg,
            },
        );
        return Ok(());
    };
    emit_log(
        &app,
        Some("detect"),
        LogStream::Stdout,
        &format!("→ Uninstalling from {}", install_root.display()),
    );
    emit_log(
        &app,
        Some("detect"),
        LogStream::Stdout,
        &format!(
            "→ Data policy: {}",
            match mode {
                UninstallMode::Keep => "keep configuration and user data",
                UninstallMode::Full => "--full: remove user data too",
            }
        ),
    );
    emit_stage(
        &app,
        "detect",
        StageState::Succeeded,
        Some(elapsed_ms(started)),
        None,
    );

    // ---- remove -----------------------------------------------------------
    // `--yes` is the CLI's non-interactive contract, written for exactly this
    // caller ("the desktop app's detached cleanup script"). All prompting,
    // gateway stopping and PATH stripping happen inside the CLI.
    emit_stage(&app, "remove", StageState::Running, None, None);
    let started = Instant::now();
    let mut args = vec!["uninstall".to_string(), "--yes".to_string()];
    if mode == UninstallMode::Full {
        args.push("--full".to_string());
    }
    let result = run_streamed(
        &app,
        &launcher,
        &args,
        &install_root,
        &uninstall_child_env(),
        Some("remove"),
    )
    .await?;

    if result.exit_code != Some(0) {
        let tail = result.stdout_tail.join("\n");
        let msg = format!(
            "anakot uninstall exited with {:?}.{}",
            result.exit_code,
            if tail.trim().is_empty() {
                String::new()
            } else {
                format!("\n{tail}")
            }
        );
        emit_stage(
            &app,
            "remove",
            StageState::Failed,
            Some(elapsed_ms(started)),
            Some(msg.clone()),
        );
        emit(
            &app,
            BootstrapEvent::Failed {
                stage: Some("remove".to_string()),
                error: msg,
            },
        );
        return Ok(());
    }
    emit_stage(
        &app,
        "remove",
        StageState::Succeeded,
        Some(elapsed_ms(started)),
        None,
    );

    // ---- verify -----------------------------------------------------------
    // The CLI reports its own failures; this proves the checkout the launcher
    // ran from is actually gone, so a silent partial removal (a locked file, a
    // scanner holding the tree) is reported instead of claimed as success.
    emit_stage(&app, "verify", StageState::Running, None, None);
    let started = Instant::now();
    if crate::bootstrap::anakot_is_installed(&install_root) {
        let msg = format!(
            "Some files under {} could not be removed — close any running Anakot window and retry.",
            install_root.display()
        );
        emit_log(&app, Some("verify"), LogStream::Stderr, &format!("✗ {msg}"));
        emit_stage(
            &app,
            "verify",
            StageState::Failed,
            Some(elapsed_ms(started)),
            Some(msg.clone()),
        );
        emit(
            &app,
            BootstrapEvent::Failed {
                stage: Some("verify".to_string()),
                error: msg,
            },
        );
        return Ok(());
    }
    emit_log(
        &app,
        Some("verify"),
        LogStream::Stdout,
        "✓ Anakot removed",
    );
    emit_stage(
        &app,
        "verify",
        StageState::Succeeded,
        Some(elapsed_ms(started)),
        None,
    );

    emit(
        &app,
        BootstrapEvent::Complete {
            install_root: install_root.to_string_lossy().into_owned(),
            marker: None,
        },
    );
    exit_after_success(&app);
    Ok(())
}

/// The CLI is a Python process writing into a pipe, so CPython block-buffers
/// its stdout: nothing would reach the log pane until 8 KB accumulate or the
/// process exits, and a long removal renders as a frozen stage. Force
/// line-by-line output, and hand the child the home it is removing from.
///
/// Deliberately NOT `update::update_child_env`: that one also exports the
/// update hand-off pid, which is a claim on the update lock and meaningless
/// (and misleading) for an uninstall.
fn uninstall_child_env() -> Vec<(String, std::ffi::OsString)> {
    vec![
        (
            "ANAKOT_HOME".to_string(),
            paths::anakot_home().as_os_str().to_os_string(),
        ),
        ("PYTHONUNBUFFERED".to_string(), "1".into()),
    ]
}

fn elapsed_ms(started: Instant) -> u64 {
    started.elapsed().as_millis() as u64
}

/// Give the webview a moment to paint the finished stage before the process
/// goes away, with a hard watchdog so a wedged exit cannot leave an uninstaller
/// holding an invisible window. Same shape as update.rs::exit_after_success.
fn exit_after_success(app: &AppHandle) {
    std::thread::spawn(|| {
        std::thread::sleep(Duration::from_secs(3));
        std::process::exit(0);
    });
    std::thread::spawn({
        let app = app.clone();
        move || {
            std::thread::sleep(Duration::from_millis(1200));
            app.exit(0);
        }
    });
}

fn emit(app: &AppHandle, event: BootstrapEvent) {
    let event = event.sanitized_for_ui();
    if let Err(e) = app.emit(BootstrapEvent::CHANNEL, &event) {
        tracing::warn!(?e, "failed to emit uninstall event");
    }
}

fn emit_stage(
    app: &AppHandle,
    name: &str,
    state: StageState,
    duration_ms: Option<u64>,
    error: Option<String>,
) {
    tracing::info!(stage = %name, ?state, ?duration_ms, ?error, "uninstall stage");
    emit(
        app,
        BootstrapEvent::Stage {
            name: name.to_string(),
            state,
            duration_ms,
            result: None,
            error,
        },
    );
}

fn emit_log(app: &AppHandle, stage: Option<&str>, stream: LogStream, line: &str) {
    match stage {
        Some(s) => tracing::info!(target: "bootstrap.log", stage = %s, "{line}"),
        None => tracing::info!(target: "bootstrap.log", "{line}"),
    }
    emit(
        app,
        BootstrapEvent::Log {
            stage: stage.map(|s| s.to_string()),
            line: line.to_string(),
            stream,
        },
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bare_args_keep_data() {
        assert_eq!(UninstallMode::from_args(Vec::<String>::new()), UninstallMode::Keep);
        assert_eq!(UninstallMode::from_args(["--uninstall"]), UninstallMode::Keep);
    }

    #[test]
    fn full_flag_selects_the_wipe() {
        assert_eq!(UninstallMode::from_args(["--uninstall", "--full"]), UninstallMode::Full);
        assert_eq!(UninstallMode::from_args(["--full"]), UninstallMode::Full);
    }

    #[test]
    fn an_unrelated_flag_never_wipes_data() {
        // The destructive choice must be spelled out: nothing else may select it.
        assert_eq!(UninstallMode::from_args(["--update", "--repair"]), UninstallMode::Keep);
    }

    #[test]
    fn manifest_is_three_real_stages() {
        let stages = uninstall_stages();
        let names: Vec<&str> = stages.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(names, ["detect", "remove", "verify"]);
        assert!(stages.iter().all(|s| s.category == "uninstall"));
        assert!(stages.iter().all(|s| !s.needs_user_input));
    }
}

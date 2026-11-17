//! Anakot Setup — Tauri entrypoint.
//!
//! Spawns a single window pointed at the React frontend (apps/bootstrap-installer/src/).
//! All install-time work lives in `bootstrap.rs` and is invoked through the Tauri
//! commands registered at the bottom of `run()`.
//!
//! Three CLI-driven modes share that one window: Install (bare launch), Update
//! (`--update`, the desktop's hand-off) and Uninstall (`--uninstall`, see
//! `uninstall.rs`). Each mode is a shell over the owner of its semantics —
//! `scripts/install.ps1`, the update pipeline, and `anakot uninstall`
//! respectively — so none of them grows its own copy of the rules.
//!
//! The Windows-subsystem strip lives on the binary crate (src/main.rs), not
//! here — a crate-level attribute on a lib doesn't propagate to the linker
//! flags of the executable that consumes it.

mod bootstrap;
mod events;
mod install_script;
mod marker;
mod powershell;
mod paths;
mod uninstall;
mod update;

use std::sync::Arc;
use tokio::sync::Mutex;

use uninstall::UninstallMode;

/// How the installer was invoked. Resolved once from the process args in
/// `run()` and exposed to the frontend via `get_mode` so it can route to the
/// install flow (first-run onboarding), the update flow (driven by the desktop
/// app handing off via `Anakot-Setup.exe --update`), or the uninstall flow.
///
/// Bare launch (double-click, first-run) => Install.
/// `--update` (spawned by the desktop's "Update" button) => Update.
/// `--uninstall` => Uninstall. Never a bare launch: removal is destructive, so
/// it always requires the flag, the same way the CLI requires `--yes`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum AppMode {
    Install,
    Update,
    Uninstall,
}

impl AppMode {
    /// Resolve the mode from an argument iterator. Kept arg-iterator generic
    /// (not reading `std::env` directly) so it's unit-testable.
    ///
    /// `--uninstall` is checked before `--update`: if a caller passes both, the
    /// more consequential request must not be silently downgraded to an update
    /// that leaves the installation in place.
    pub fn from_args<I, S>(args: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let mut update = false;
        for a in args {
            match a.as_ref() {
                "--uninstall" => return AppMode::Uninstall,
                "--update" => update = true,
                _ => {}
            }
        }
        if update {
            return AppMode::Update;
        }
        AppMode::Install
    }
}

/// Returns true when the args request a forced installer UI (repair/reinstall)
/// via `--reinstall` or `--repair`, which overrides the macOS launcher
/// fast-path so a broken install can be repaired. Arg-iterator generic so it's
/// unit-testable, mirroring `AppMode::from_args`. Independent of mode selection:
/// these flags never flip between modes.
pub fn force_setup_from_args<I, S>(args: I) -> bool
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    args.into_iter()
        .any(|a| a.as_ref() == "--reinstall" || a.as_ref() == "--repair")
}

/// Whether an already-installed launch must hand off before Tauri/AppKit.
///
/// The runtime's default activation policy is Regular. Entering it registers
/// this bootstrap process as a Dock app even when Info.plist sets
/// `LSUIElement`, and the real desktop is a different bundle id, so that
/// registration is a second Anakot icon. Update, repair, and non-macOS
/// launches still build the installer UI. The installed-on-disk check is I/O
/// and stays with the caller.
///
/// Only `AppMode::Install` hands off, so Uninstall always reaches its own UI —
/// an uninstall that relaunched the desktop it is about to remove would lock
/// the very files the CLI has to delete.
pub fn handoff_before_appkit(is_macos: bool, mode: AppMode, force_setup: bool) -> bool {
    is_macos && mode == AppMode::Install && !force_setup
}

/// Process-wide install state, shared across Tauri commands.
///
/// The bootstrap is a one-shot, single-tenant process — we only need one
/// of these per window. `Arc<Mutex<...>>` lets command handlers grab it
/// without lifetime gymnastics.
pub struct AppState {
    pub bootstrap: Mutex<Option<bootstrap::BootstrapHandle>>,
    /// How this process was launched. Immutable for the lifetime of the
    /// process; read by the `get_mode` command.
    pub mode: AppMode,
    /// The data policy of an uninstall launch. Immutable for the process; read
    /// by `get_uninstall_mode` so the frontend can hand it back to
    /// `start_uninstall`.
    pub uninstall_mode: UninstallMode,
}

impl AppState {
    fn new(mode: AppMode, uninstall_mode: UninstallMode) -> Self {
        Self {
            bootstrap: Mutex::new(None),
            mode,
            uninstall_mode,
        }
    }
}

/// Frontend → Rust: which flow should the UI render?
#[tauri::command]
fn get_mode(state: tauri::State<'_, Arc<AppState>>) -> AppMode {
    state.mode
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Tracing → bootstrap-installer.log under ANAKOT_HOME/logs/ so install
    // failures leave a trail for support. Console output also goes here in
    // debug builds.
    let _guard = paths::init_logging();

    // Collected once: `Skip<Args>` is not Clone, and each resolver consumes what
    // it is given. The uninstall data policy stays a launch fact held in
    // AppState, so the UI never round-trips it (uninstall::start_uninstall).
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mode = AppMode::from_args(&args);
    let uninstall_mode = UninstallMode::from_args(&args);
    // Escape hatch: `--reinstall`/`--repair` forces the installer UI even when
    // Anakot is already installed, so users can re-run setup to repair a broken
    // install instead of the launcher fast path silently relaunching the app.
    let force_setup = force_setup_from_args(&args);
    tracing::info!(
        ?mode,
        ?uninstall_mode,
        force_setup,
        "Anakot installer starting"
    );

    // Hand off before constructing Tauri/AppKit. The setup callback is too
    // late: by then the process has already been registered as a regular
    // Dock application.
    if handoff_before_appkit(cfg!(target_os = "macos"), mode, force_setup) {
        let install_root = paths::anakot_home().join("anakot-agent");
        if bootstrap::anakot_is_installed(&install_root) {
            match bootstrap::spawn_installed_desktop(&install_root) {
                Ok(()) => {
                    // Brief grace so the spawned app is registered before we
                    // exit (mirrors launch_anakot_desktop).
                    std::thread::sleep(std::time::Duration::from_millis(200));
                    tracing::info!(
                        "anakot already installed — relaunched desktop; exiting installer"
                    );
                    return;
                }
                Err(err) => {
                    tracing::warn!(
                        ?err,
                        "relaunch of installed desktop failed; showing installer UI"
                    );
                }
            }
        }
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .manage(Arc::new(AppState::new(mode, uninstall_mode)))
        .setup(|app| {
            use tauri::Manager;
            // LSUIElement keeps the launcher hand-off out of the Dock. A
            // visible installer (first run, repair, update, uninstall) must
            // still be a regular foreground app. The successful fast path
            // returned before Tauri was constructed and cannot reach this
            // callback.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Regular);

            // First run / repair install, update, or uninstall: reveal the UI.
            match app.get_webview_window("main") {
                Some(win) => {
                    if let Err(err) = win.show() {
                        tracing::error!(?err, "failed to show main installer window");
                    }
                }
                None => {
                    tracing::error!(
                        "main installer window not found; installer UI will not appear"
                    );
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Mode (install vs update vs uninstall)
            get_mode,
            // Bootstrap lifecycle
            bootstrap::start_bootstrap,
            bootstrap::cancel_bootstrap,
            bootstrap::get_bootstrap_status,
            // Update lifecycle
            update::start_update,
            // Uninstall lifecycle
            uninstall::start_uninstall,
            // Hand-off
            bootstrap::launch_anakot_desktop,
            // Diagnostics
            paths::get_log_path,
            paths::get_anakot_home,
            paths::open_log_dir,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Anakot Setup");
}

#[cfg(test)]
mod tests {
    use super::{force_setup_from_args, handoff_before_appkit, AppMode};

    #[test]
    fn bare_args_are_install() {
        assert_eq!(AppMode::from_args(Vec::<String>::new()), AppMode::Install);
        assert_eq!(AppMode::from_args(["--foo", "bar"]), AppMode::Install);
    }

    #[test]
    fn update_flag_selects_update() {
        assert_eq!(AppMode::from_args(["--update"]), AppMode::Update);
        assert_eq!(
            AppMode::from_args(["--something", "--update", "--else"]),
            AppMode::Update
        );
    }

    #[test]
    fn uninstall_flag_selects_uninstall() {
        assert_eq!(AppMode::from_args(["--uninstall"]), AppMode::Uninstall);
        assert_eq!(
            AppMode::from_args(["--uninstall", "--full"]),
            AppMode::Uninstall
        );
    }

    #[test]
    fn uninstall_is_never_downgraded_to_an_update() {
        // Passing both is caller error; the destructive request must win rather
        // than the process quietly updating and leaving the install in place.
        assert_eq!(
            AppMode::from_args(["--update", "--uninstall"]),
            AppMode::Uninstall
        );
    }

    #[test]
    fn reinstall_and_repair_flags_force_setup() {
        assert!(force_setup_from_args(["--reinstall"]));
        assert!(force_setup_from_args(["--repair"]));
        assert!(force_setup_from_args(["--foo", "--repair", "--bar"]));
    }

    #[test]
    fn bare_or_unrelated_args_do_not_force_setup() {
        assert!(!force_setup_from_args(Vec::<String>::new()));
        assert!(!force_setup_from_args(["--foo", "bar"]));
        // --update must not be mistaken for a force-setup flag.
        assert!(!force_setup_from_args(["--update"]));
        // ...nor may an uninstall launch turn into a repair.
        assert!(!force_setup_from_args(["--uninstall"]));
    }

    #[test]
    fn bare_macos_install_hands_off_before_appkit() {
        assert!(handoff_before_appkit(true, AppMode::Install, false));
    }

    #[test]
    fn repair_update_uninstall_and_other_platforms_build_installer_ui() {
        assert!(!handoff_before_appkit(true, AppMode::Install, true));
        assert!(!handoff_before_appkit(true, AppMode::Update, false));
        assert!(!handoff_before_appkit(true, AppMode::Update, true));
        assert!(!handoff_before_appkit(true, AppMode::Uninstall, false));
        assert!(!handoff_before_appkit(true, AppMode::Uninstall, true));
        assert!(!handoff_before_appkit(false, AppMode::Install, false));
        assert!(!handoff_before_appkit(false, AppMode::Install, true));
        assert!(!handoff_before_appkit(false, AppMode::Update, false));
        assert!(!handoff_before_appkit(false, AppMode::Uninstall, false));
    }

    #[test]
    fn force_setup_flags_do_not_affect_mode_selection() {
        // The repair flags must never flip between modes.
        assert_eq!(AppMode::from_args(["--reinstall"]), AppMode::Install);
        assert_eq!(AppMode::from_args(["--repair"]), AppMode::Install);
        assert_eq!(
            AppMode::from_args(["--update", "--reinstall"]),
            AppMode::Update
        );
        assert_eq!(
            AppMode::from_args(["--uninstall", "--repair"]),
            AppMode::Uninstall
        );
    }
}

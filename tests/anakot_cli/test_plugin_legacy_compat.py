"""Hermes-era plugin imports must resolve against the Anakot runtime.

Installed plugins from a Hermes source import ``hermes_constants`` /
``hermes_state``; without the aliases their dashboard API (the connector half)
dies with ModuleNotFoundError even though the plugin itself is fine.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from anakot_constants import get_anakot_home, reset_anakot_home_override, set_anakot_home_override


@pytest.fixture(autouse=True)
def _restore_compat_state():
    had_constants = "hermes_constants" in sys.modules
    had_state = "hermes_state" in sys.modules
    old_constants = sys.modules.get("hermes_constants")
    old_state = sys.modules.get("hermes_state")
    ctx: dict = {"token": None}
    yield ctx
    for name, existed, old in (
        ("hermes_constants", had_constants, old_constants),
        ("hermes_state", had_state, old_state),
    ):
        if existed:
            sys.modules[name] = old
        else:
            sys.modules.pop(name, None)
    if ctx["token"] is not None:
        reset_anakot_home_override(ctx["token"])


def test_install_aliases_legacy_module_names():
    from anakot_cli.plugin_legacy_compat import install

    install()

    from hermes_constants import get_hermes_home
    from hermes_state import SessionDB

    import anakot_state

    assert sys.modules["hermes_state"] is anakot_state
    assert get_hermes_home() == get_anakot_home()
    assert SessionDB is anakot_state.SessionDB


def test_install_is_idempotent():
    from anakot_cli.plugin_legacy_compat import install

    install()
    first = sys.modules["hermes_constants"]
    install()

    assert sys.modules["hermes_constants"] is first


def test_legacy_plugin_api_loads_and_resolves_active_home(_restore_compat_state, tmp_path: Path):
    """A real Hermes-era plugin_api.py imports cleanly through the compat shim."""
    from anakot_cli.plugin_legacy_compat import install

    install()
    _restore_compat_state["token"] = set_anakot_home_override(str(tmp_path))

    plugin_api = Path(__file__).resolve().parent / "fixtures" / "legacy_plugin_api.py"

    spec = importlib.util.spec_from_file_location("_compat_test_plugin_api", plugin_api)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.home() == tmp_path
    assert module.open_db() is None  # real legacy resolver + state import both work

"""Backward-compatible import names for Hermes-era plugins.

The official plugin catalogue and many third-party plugins were authored
against Hermes, whose Python modules were named ``hermes_*`` and whose home
resolver was ``get_hermes_home()``. Anakot renamed those modules, but plugins
installed from a Hermes source still import the old names at call time. Without
this shim their dashboard API (the ``plugin_api.py`` behind a plugin's connector
tab) fails with ``ModuleNotFoundError`` even though the plugin itself is fine.

Registering aliases in ``sys.modules`` fixes every such plugin at once — no
per-install editing — and keeps the names pointing at the live Anakot runtime,
so a plugin always resolves the active profile's home and state DB.

The Hermes names below are deliberate compatibility surface. They are listed
in ``brand/protected-strings.txt`` so ``scripts/rebrand.py`` never rewrites them.
"""

from __future__ import annotations

import sys
import types


def install() -> None:
    """Expose the legacy ``hermes_constants`` / ``hermes_state`` module names.

    Idempotent: the plugin host and the in-process loader may both call it, and
    discovery runs several times per process.
    """
    import anakot_constants
    import anakot_state

    if "hermes_constants" not in sys.modules:
        legacy = types.ModuleType("hermes_constants")
        # The old resolver name maps onto Anakot's profile-aware home lookup.
        legacy.get_hermes_home = anakot_constants.get_anakot_home  # type: ignore[attr-defined]

        def _forward(name: str):
            return getattr(anakot_constants, name)

        legacy.__getattr__ = _forward  # type: ignore[attr-defined]
        sys.modules["hermes_constants"] = legacy

    if "hermes_state" not in sys.modules:
        sys.modules["hermes_state"] = anakot_state

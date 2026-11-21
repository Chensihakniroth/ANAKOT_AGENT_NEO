"""Stand-in for a Hermes-era ``plugin_api.py`` (the connector half of a plugin).

Uses only the legacy import names a real installed plugin uses, so loading this
module through the compat shim proves the real path works.
"""

from __future__ import annotations

from hermes_constants import get_hermes_home
from hermes_state import SessionDB


def home():
    return get_hermes_home()


def open_db():
    path = home() / "state.db"
    return SessionDB(db_path=path, read_only=True) if path.exists() else None

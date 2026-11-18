"""The desktop build environment hands the prepared Python to packaging hooks."""
from __future__ import annotations

from types import SimpleNamespace


def test_build_environment_bridges_prepared_python_for_packagers(monkeypatch, tmp_path):
    from scripts.bundles import desktop_inputs

    python = tmp_path / "prepared-python"
    node = tmp_path / "prepared-node"
    prepared = SimpleNamespace(
        request=SimpleNamespace(
            source=tmp_path, work=tmp_path / "work", cache=tmp_path / "cache", target="test-target",
        ),
        python=python,
        node=node,
    )
    selection = SimpleNamespace(
        entries={"python": SimpleNamespace(binary=python), "node": SimpleNamespace(binary=node)},
        environment=lambda env: dict(env),
    )
    monkeypatch.setattr("pm.build_operations.verified_tools", lambda *args, **kwargs: selection)
    monkeypatch.setattr("pm.lock.Lockfile", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        "scripts.bundles.desktop_toolchain.bootstrap_environment",
        lambda source, work, cache, inherited: dict(inherited),
    )
    monkeypatch.setattr(
        desktop_inputs, "identity_environment", lambda request, variant, env: dict(env),
    )

    env = desktop_inputs.build_environment(prepared, "bundled", {})

    assert env["ANAKOT_PYTHON"] == str(python)
    assert env["HERMES_PYTHON"] == str(python)

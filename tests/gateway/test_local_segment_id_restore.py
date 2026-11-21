"""A canonical LOCAL physical segment id resolves to its receipt owner before a restore (#139306 class).

Regression: a served profile logged

    Local session <physical tip> receipt refused: storage_unavailable at local_receipt

on every switch. A reset (or compression) advances a local conversation to a new physical transcript,
and the history picker / Desktop addresses it by that tip (``list_sessions`` projects the lineage onto
it), but only the creation receipt's logical owner is an id a restore can name -- the receipt is stored
under the owner, so the tip itself is refused ``storage_unavailable``.
"""
from types import SimpleNamespace

import pytest


def _runner(tmp_path):
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    store = SessionStore(tmp_path / 'sessions', GatewayConfig())
    return SimpleNamespace(session_store=store, _session_db=store._db, adapters={}, _draining=False)


@pytest.mark.asyncio
async def test_local_segment_id_resolves_to_its_receipt_owner(tmp_path, monkeypatch):
    from gateway import run
    from gateway.session_authority import initialize_session_authority
    from gateway.session_contract import SessionActor, SessionRef
    from gateway.session_local import create_local_session
    from gateway.session_local_recovery import local_owner_ref
    from anakot_state_local import local_receipt
    from anakot_state_runtime import RuntimeStoreError

    monkeypatch.setattr(run, '_load_gateway_config', dict)
    authority = await initialize_session_authority(_runner(tmp_path), profile_id='fixture', instance_id='first')
    actor = SessionActor('owner', 'fixture', frozenset({'session:create', 'session:read'}), 'socket')
    ref = create_local_session(authority, actor, dict(
        request_id='segment', source='gui', cwd=str(tmp_path), model='frozen', toolsets=[]))
    # A reset advances the conversation to a NEW physical transcript; the receipt stays on the owner.
    segment = authority.runner.session_store.reset_session(authority.sessions[ref.session_id].route).session_id
    assert segment != ref.session_id, 'the fixture must mint a distinct physical segment id'
    assert local_receipt(authority.db, ref.session_id)['entry']['session_id'] == segment

    # The raw segment id carries no receipt of its own -- exactly the refusal the switch logged.
    with pytest.raises(RuntimeStoreError) as exc:
        local_receipt(authority.db, segment)
    assert exc.value.reason == 'storage_unavailable'

    # The resolver maps the tip to the owner and leaves anything else untouched.
    assert local_owner_ref(authority, SessionRef('fixture', segment)) == SessionRef('fixture', ref.session_id)
    assert local_owner_ref(authority, SessionRef('fixture', ref.session_id)) == SessionRef('fixture', ref.session_id)
    assert local_owner_ref(authority, SessionRef('fixture', 'unknown-id')) == SessionRef('fixture', 'unknown-id')

    # A restore the client reaches with the raw tip is refused; resolved first, it succeeds.
    del authority.sessions[ref.session_id]
    with pytest.raises(RuntimeStoreError) as exc:
        await authority.attach(actor, SessionRef('fixture', segment))
    assert exc.value.reason == 'storage_unavailable'
    await authority.attach(actor, local_owner_ref(authority, SessionRef('fixture', segment)))
    assert ref.session_id in authority.sessions


@pytest.mark.asyncio
async def test_control_seam_resolves_a_segment_id_before_authorize(tmp_path, monkeypatch):
    """The control RPC normalizes a physical tip to its owner, so no handler or ``authorize`` sees it."""
    from gateway import run
    from gateway.session_authority import initialize_session_authority
    from gateway.session_controls import AuthorityConnection
    from gateway.session_local import create_local_session

    monkeypatch.setattr(run, '_load_gateway_config', dict)
    authority = await initialize_session_authority(_runner(tmp_path), profile_id='fixture', instance_id='owner')
    connection = AuthorityConnection(authority, object(), {'user_id': 'human', 'profile_id': 'fixture'})
    ref = create_local_session(authority, connection.actor, dict(
        request_id='seam', source='gui', cwd=str(tmp_path), model='frozen', toolsets=[]))
    segment = authority.runner.session_store.reset_session(authority.sessions[ref.session_id].route).session_id
    assert segment != ref.session_id
    del authority.sessions[ref.session_id]  # cold: the request must restore the conversation from its receipt
    reply = await connection.dispatch({'id': 1, 'method': 'session.events.since', 'params': {'session_id': segment}})
    assert 'error' not in reply, reply
    assert ref.session_id in authority.sessions
    assert segment not in authority.sessions

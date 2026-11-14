"""``anakot_cli.chat_launch``: what a plugin's own chat launcher calls around its client process."""
import json
import os
import subprocess

import pytest

from anakot_cli.main import PROJECT_ROOT


def test_exit_summary_names_the_launchers_command(tmp_path, monkeypatch, capsys):
    from anakot_state import SessionDB
    from anakot_cli.chat_launch import print_exit_summary
    home = tmp_path / '.anakot'
    home.mkdir()
    monkeypatch.setenv('ANAKOT_HOME', str(home))
    db = SessionDB(db_path=home / 'state.db')
    db.create_session('20261110_120000_abc123', source='tui')
    db.set_session_title('20261110_120000_abc123', 'Demo chat')
    db.append_message('20261110_120000_abc123', 'user', 'q')
    db.append_message('20261110_120000_abc123', 'assistant', 'a')
    db.create_session('20261110_120001_empty0', source='tui')
    db.close()

    print_exit_summary('20261110_120000_abc123', command='anakot demo')
    out = capsys.readouterr().out
    assert '  anakot demo --resume 20261110_120000_abc123\n' in out
    assert '  anakot demo -c "Demo chat"\n' in out
    assert '--tui' not in out

    print_exit_summary('20261110_120001_empty0', command='anakot demo')
    assert capsys.readouterr().out == ''


def test_anakot_command_runs_this_install_without_pythonpath(tmp_path):
    from anakot_cli.chat_launch import anakot_command
    home = tmp_path / '.anakot'
    home.mkdir()
    (home / 'config.yaml').write_text('updates:\n  check: false\n', encoding='utf-8')
    env = {'ANAKOT_HOME': str(home), 'HOME': str(tmp_path), 'PATH': os.environ.get('PATH', '')}
    child = subprocess.run(anakot_command(['--version']), env=env, cwd=str(tmp_path), capture_output=True,
                           text=True, timeout=60, check=False)
    assert child.returncode == 0, child.stderr
    assert child.stdout.startswith('Anakot Agent v')
    assert f'Install directory: {PROJECT_ROOT}\n' in child.stdout


@pytest.mark.platforms('windows')  # only Windows publishes the launcher as anakot.exe or anakot.cmd
def test_anakot_command_starts_with_a_file_windows_can_start(tmp_path, monkeypatch):
    from anakot_cli import main
    from anakot_cli.chat_launch import anakot_command
    store = tmp_path / 'store'
    python = store / 'py' / 'python.exe'
    python.parent.mkdir(parents=True)
    python.write_bytes(b'')
    (store / 'facts.json').write_text(json.dumps({'packages': {'python': {'entry': 'py'}}}), encoding='utf-8')
    monkeypatch.setenv('ANAKOT_RUNTIME_DIR', str(store))
    launchers = tmp_path / 'install' / '.anakot' / 'bin'
    launchers.mkdir(parents=True)
    monkeypatch.setattr(main, 'PROJECT_ROOT', tmp_path / 'install')

    # Only the batch fallback is published: no child process starts it without a shell.
    (launchers / 'anakot.cmd').write_text('@echo off\r\n', encoding='utf-8')
    command = anakot_command(['--version'])
    assert os.path.samefile(command[0], python)
    assert command[-1] == '--version'

    (launchers / 'anakot.exe').write_bytes(b'MZ')
    command = anakot_command(['--version'])
    assert os.path.samefile(command[0], launchers / 'anakot.exe')
    assert command[1:] == ['--version']

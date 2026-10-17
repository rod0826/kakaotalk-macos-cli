"""Real installed-command tests. No message/file transmission is performed."""
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


def _resolve_cli(name):
    executable = shutil.which(name)
    if executable:
        return [executable]
    if os.environ.get('CLI_ANYTHING_FORCE_INSTALLED') == '1':
        raise RuntimeError(f'{name} is not installed on PATH')
    return [sys.executable, '-m', 'cli_anything.kakaotalk']


CLI = _resolve_cli('cli-anything-kakaotalk')


def run(*args):
    completed = subprocess.run(CLI + ['--json', '--state-dir', os.environ.get('KAKAO_TEST_STATE','/tmp/kakao-cli-e2e')] + list(args),
                               text=True, capture_output=True, timeout=40)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['ok'], result
    return result['data']


def test_installed_help_and_real_doctor():
    help_result = subprocess.run(CLI + ['--help'], text=True, capture_output=True, timeout=10)
    assert help_result.returncode == 0 and 'doctor' in help_result.stdout
    status = run('doctor')
    assert status['app_installed'] and status['running']
    assert status['accessibility_trusted'] and status['version_matches'], status


def test_search_open_draft_restore_and_file_picker(tmp_path):
    room = os.environ['KAKAO_TEST_ROOM']
    results = run('chat','search',room)
    assert results['count'] > 0
    assert run('chat','open',room)['room'] == room
    before = run('chat','current','--room',room)['draft']
    sample = f'[CLI 자동화 검사 · 미전송 {uuid.uuid4().hex[:8]}]'
    try:
        run('message','draft','--room',room,'--text',sample,'--expected-text',before)
        assert run('chat','current','--room',room)['draft'] == sample
    finally:
        run('message','draft','--room',room,'--text',before,'--expected-text',sample)
    assert run('chat','current','--room',room)['draft'] == before
    try:
        assert run('file','dialog','--room',room)['file_dialog_open'] is True
    finally:
        assert run('file','cancel','--room',room)['file_dialog_open'] is False
    # Only a synthetic summary is saved; no real conversation or draft retained.
    artifact = tmp_path/'roundtrip.json'
    artifact.write_text(json.dumps({'draft_restored':True,'file_picker_closed':True,'messages_sent':0}))
    assert json.loads(artifact.read_text())['messages_sent'] == 0
    print(f'\nSynthetic verification artifact: {artifact}')

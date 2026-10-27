import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from click.testing import CliRunner

from cli_anything.kakaotalk.core.service import Service, ToolError, validate_room
from cli_anything.kakaotalk.core.journal import Journal
from cli_anything.kakaotalk.kakaotalk_cli import cli


class FakeBackend:
    def __init__(self):
        self.calls = []

    def call(self, operation, **payload):
        self.calls.append((operation, payload))
        return {'operation': operation, 'room': payload.get('room')}


@pytest.mark.parametrize('room', ['', '   ', 'a\nb', 'a\x00b'])
def test_invalid_room_rejected(room):
    with pytest.raises(ToolError):
        validate_room(room)


def test_dry_run_does_not_touch_backend_or_claim_request(tmp_path):
    backend = FakeBackend()
    journal = Journal(tmp_path / 'journal.db')
    service = Service(backend, journal, dry_run=True)
    result = service.send('Self', 'hello', 'Self', 'request-one')
    assert result['dry_run'] is True
    assert backend.calls == []
    assert journal.status() == []


def test_wrong_room_confirmation_cannot_dispatch(tmp_path):
    backend = FakeBackend()
    service = Service(backend, Journal(tmp_path / 'j.db'))
    with pytest.raises(ToolError, match='confirm'):
        service.send('Alice', 'hello', 'Bob', 'r1')
    assert backend.calls == []


def test_duplicate_request_is_never_dispatched_twice(tmp_path):
    backend = FakeBackend()
    service = Service(backend, Journal(tmp_path / 'j.db'))
    service.send('Self', 'hello', 'Self', 'r1')
    with pytest.raises(ToolError, match='already'):
        service.send('Self', 'hello', 'Self', 'r1')
    assert len(backend.calls) == 1


def test_changed_payload_with_same_request_fails(tmp_path):
    journal = Journal(tmp_path / 'j.db')
    journal.claim('r1', 'hash-a')
    with pytest.raises(ToolError, match='different'):
        journal.claim('r1', 'hash-b')


def test_pending_request_is_not_replayed(tmp_path):
    journal = Journal(tmp_path / 'j.db')
    journal.claim('r1', 'same')
    with pytest.raises(ToolError, match='already'):
        journal.claim('r1', 'same')


def test_concurrent_claim_has_one_winner(tmp_path):
    journal = Journal(tmp_path / 'j.db')
    barrier = threading.Barrier(4)
    def claim(_):
        barrier.wait()
        try:
            journal.claim('same-id', 'same-hash')
            return True
        except ToolError:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(claim, range(4))) == 1


def test_backend_failure_keeps_unknown_request(tmp_path):
    class Broken:
        def call(self, operation, **payload):
            raise ToolError('BACKEND_TIMEOUT', 'unknown outcome')
    journal = Journal(tmp_path / 'j.db')
    with pytest.raises(ToolError):
        Service(Broken(), journal).send('Self', 'hello', 'Self', 'r1')
    assert journal.status()[0]['state'] == 'unknown'


@pytest.mark.parametrize('text', ['', '   ', 'x\x00y'])
def test_invalid_message_cannot_dispatch(tmp_path, text):
    backend = FakeBackend()
    with pytest.raises(ToolError):
        Service(backend, Journal(tmp_path / 'j.db')).send('Self', text, 'Self', 'r1')
    assert backend.calls == []


def test_missing_file_cannot_dispatch(tmp_path):
    backend = FakeBackend()
    with pytest.raises(ToolError):
        Service(backend, Journal(tmp_path / 'j.db')).send_file('Self', tmp_path/'missing', 'Self', 'r1')
    assert backend.calls == []


def test_journal_contains_hashes_not_message_text(tmp_path):
    journal = Journal(tmp_path / 'j.db')
    Service(FakeBackend(), journal).send('Self', 'SECRET_CONTENT', 'Self', 'r1')
    assert 'SECRET_CONTENT' not in json.dumps(journal.status())
    assert 'Self' not in json.dumps(journal.status())


def test_json_invalid_command_returns_machine_readable_error():
    result = CliRunner().invoke(cli, ['--json', 'does-not-exist'])
    assert result.exit_code != 0
    assert json.loads(result.output)['ok'] is False


def test_cli_dry_run_sending_requires_confirmation(tmp_path):
    result = CliRunner().invoke(cli, ['--json', '--dry-run', '--state-dir', str(tmp_path),
        'message', 'send', '--room', 'Self', '--text', 'hi', '--request-id', 'r1'])
    assert result.exit_code != 0
    assert json.loads(result.output)['ok'] is False


def test_cli_dry_run_with_stdin_text(tmp_path):
    result = CliRunner().invoke(cli, ['--json', '--dry-run', '--state-dir', str(tmp_path),
        'message', 'send', '--room', 'Self', '--text-file', '-', '--confirm-room', 'Self', '--request-id', 'r1'], input='hello\nworld')
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['data']['dry_run'] is True


def test_draft_dry_run_preserves_state(tmp_path):
    backend = FakeBackend()
    result = Service(backend, Journal(tmp_path/'j.db'), dry_run=True).draft('Self', 'draft')
    assert result['dry_run'] is True
    assert backend.calls == []


def test_symlink_file_cannot_dispatch(tmp_path):
    target = tmp_path/'target.txt'
    target.write_text('synthetic')
    link = tmp_path/'alias.txt'
    link.symlink_to(target)
    backend = FakeBackend()
    with pytest.raises(ToolError):
        Service(backend, Journal(tmp_path/'j.db')).send_file('Self', link, 'Self', 'r1')
    assert backend.calls == []


def test_file_request_reuse_detects_changed_bytes(tmp_path):
    target = tmp_path/'target.txt'
    target.write_text('first')
    service = Service(FakeBackend(), Journal(tmp_path/'j.db'))
    service.send_file('Self', target, 'Self', 'r1')
    target.write_text('second')
    with pytest.raises(ToolError, match='different'):
        service.send_file('Self', target, 'Self', 'r1')


def test_unicode_message_byte_limit_is_enforced(tmp_path):
    backend = FakeBackend()
    with pytest.raises(ToolError):
        Service(backend, Journal(tmp_path/'j.db')).send('Self', '가'*20001, 'Self', 'r1')
    assert backend.calls == []


def test_unknown_dispatch_result_remains_unknown(tmp_path):
    class Uncertain:
        def call(self, operation, **payload):
            return {'dispatch_attempted':True,'delivery_verified':False,'status':'unknown'}
    journal = Journal(tmp_path/'j.db')
    Service(Uncertain(), journal).send('Self', 'hello', 'Self', 'r1')
    assert journal.status()[0]['state'] == 'unknown'


def test_backend_rejects_an_old_broker_without_build_handshake(tmp_path, monkeypatch):
    from cli_anything.kakaotalk.utils.kakaotalk_backend import Backend
    bundle = tmp_path/'App.app'
    native = bundle/'Contents/MacOS/KakaoTalkCLI'
    native.parent.mkdir(parents=True)
    native.write_bytes(b'synthetic-native')
    class Channel:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def sendall(self,data): pass
        def recv(self,size): return b'{"ok":true,"data":{}}\n'
    backend = Backend(tmp_path)
    monkeypatch.setattr(backend,'app_bundle',lambda: bundle)
    monkeypatch.setattr(backend,'connect',lambda: Channel())
    with pytest.raises(ToolError, match='build'):
        backend.call('doctor')


def test_backend_accepts_equivalent_unicode_bundle_paths(tmp_path, monkeypatch):
    import hashlib
    import unicodedata
    from cli_anything.kakaotalk.utils.kakaotalk_backend import Backend
    bundle = tmp_path/'한글.app'
    native = bundle/'Contents/MacOS/KakaoTalkCLI'
    native.parent.mkdir(parents=True)
    native.write_bytes(b'synthetic-native')
    response = {'ok':True,'data':{'probe':True},'broker_build':hashlib.sha256(native.read_bytes()).hexdigest(),
                'broker_bundle':unicodedata.normalize('NFD',str(bundle))}
    class Channel:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def sendall(self,data): self.request=json.loads(data)
        def recv(self,size): return (json.dumps(response)+'\n').encode()
    backend = Backend(tmp_path)
    monkeypatch.setattr(backend,'app_bundle',lambda: bundle)
    monkeypatch.setattr(backend,'connect',lambda: Channel())
    assert backend.call('doctor')['probe'] is True


def test_file_selection_never_dispatches_or_claims_request(tmp_path):
    sample = tmp_path / '선택 검사.zip'
    sample.write_bytes(b'file-selection-only')
    backend = FakeBackend()
    journal = Journal(tmp_path / 'selection.db')
    service = Service(backend, journal)
    result = service.select_file('Self', sample)
    assert result['operation'] == 'file-select'
    assert backend.calls[0][1]['path'] == str(sample.resolve())
    assert journal.status() == []


def test_file_selection_dry_run_does_not_touch_ui(tmp_path):
    sample = tmp_path / 'sample.zip'
    sample.write_bytes(b'test')
    backend = FakeBackend()
    service = Service(backend, Journal(tmp_path / 'dry.db'), dry_run=True)
    result = service.select_file('Self', sample)
    assert result['dry_run'] and result['operation'] == 'file-select'
    assert backend.calls == []


def test_file_selection_rejects_missing_file_before_ui(tmp_path):
    backend = FakeBackend()
    service = Service(backend, Journal(tmp_path / 'invalid.db'))
    with pytest.raises(ToolError):
        service.select_file('Self', tmp_path / 'missing.zip')
    assert backend.calls == []


def test_broker_mismatch_explains_translocation_without_accepting_it(tmp_path, monkeypatch):
    from cli_anything.kakaotalk.utils.kakaotalk_backend import Backend
    bundle = tmp_path / 'KakaoTalk CLI.app'
    native = bundle / 'Contents/MacOS/KakaoTalkCLI'
    native.parent.mkdir(parents=True)
    native.write_bytes(b'native')
    class Channel:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def sendall(self, payload): pass
        def recv(self, size):
            return json.dumps({'ok': True, 'broker_build': 'old',
                'broker_bundle': '/private/AppTranslocation/uuid/d/KakaoTalk CLI.app',
                'data': {'accessibility_trusted': True}}).encode() + b'\n'
    backend = Backend(tmp_path)
    monkeypatch.setattr(backend, 'app_bundle', lambda: bundle)
    monkeypatch.setattr(backend, 'connect', lambda: Channel())
    with pytest.raises(ToolError) as error:
        backend.call('doctor')
    assert error.value.code == 'BROKER_BUILD_MISMATCH'
    assert 'AppTranslocation' in str(error.value)
    assert str(bundle) in str(error.value)

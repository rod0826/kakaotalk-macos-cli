"""Signing identity configuration must fail closed and cover nested code."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('build_app', ROOT/'scripts/build.py')
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)
FINGERPRINT = 'A'*40


def test_signing_argument_overrides_environment():
    assert build.signing_argument(['--signing-identity', 'Explicit'], {'KAKAOTALK_SIGNING_IDENTITY': 'Env'}) == 'Explicit'
    assert build.signing_argument([], {'KAKAOTALK_SIGNING_IDENTITY': 'Env'}) == 'Env'
    assert build.signing_argument([], {}) == '-'


def test_requested_missing_identity_never_falls_back(monkeypatch):
    monkeypatch.setattr(build.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='0 valid identities found', stderr=''))
    with pytest.raises(ValueError, match='unavailable'):
        build.resolve_signing_identity('Company certificate')
    assert build.resolve_signing_identity('-') == '-'


def test_exact_identity_resolves_to_certificate_fingerprint(monkeypatch):
    output = f'  1) {FINGERPRINT} "Company Signing"\n     1 valid identities found\n'
    monkeypatch.setattr(build.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout=output, stderr=''))
    assert build.resolve_signing_identity('Company Signing') == FINGERPRINT
    assert build.resolve_signing_identity(FINGERPRINT.lower()) == FINGERPRINT
    with pytest.raises(ValueError, match='unavailable'):
        build.resolve_signing_identity('Company')


def test_pyinstaller_receives_explicit_certificate():
    assert build.pyinstaller_signing_args(FINGERPRINT) == ['--codesign-identity', FINGERPRINT]
    assert build.pyinstaller_signing_args('-') == []


def test_nested_code_is_signed_before_containing_bundle(tmp_path, monkeypatch):
    app = tmp_path/'KakaoTalk CLI.app'
    binary = app/'Contents/Resources/cli/helper'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'\xcf\xfa\xed\xfe' + b'native payload')
    alias = binary.parent/'alias'
    alias.symlink_to('helper')
    commands = []
    monkeypatch.setattr(build, 'run', lambda *args: commands.append(args))
    build.sign_bundle(app, FINGERPRINT)
    assert commands[0][-1] == binary
    assert commands[-1][-1] == app
    assert all('--deep' not in c for c in commands)
    assert all(c[c.index('--sign')+1] == FINGERPRINT for c in commands)
    assert not any(c[-1] == alias for c in commands)


def test_missing_requested_identity_preserves_existing_build(tmp_path, monkeypatch):
    app = tmp_path/'KakaoTalk CLI.app'
    app.mkdir()
    marker = app/'existing-build'
    marker.write_text('keep')
    monkeypatch.setattr(build, 'APP', app)
    monkeypatch.setattr(build.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='0 valid identities found', stderr=''))
    with pytest.raises(ValueError, match='unavailable'):
        build.main(['--signing-identity', 'Missing certificate'])
    assert marker.read_text() == 'keep'


def test_same_named_certificates_require_fingerprint(monkeypatch):
    output = f'1) {FINGERPRINT} "Company"\n2) {"B"*40} "Company"\n'
    monkeypatch.setattr(build.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout=output, stderr=''))
    with pytest.raises(ValueError, match='ambiguous'):
        build.resolve_signing_identity('Company')
    assert build.resolve_signing_identity(FINGERPRINT) == FINGERPRINT


def test_frozen_framework_copy_preserves_versioned_symlinks(tmp_path):
    source = tmp_path/'frozen'
    framework = source/'_internal/Python.framework'
    binary = framework/'Versions/3.12/Python'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'\xcf\xfa\xed\xfe' + b'framework')
    (framework/'Versions/Current').symlink_to('3.12', target_is_directory=True)
    (framework/'Python').symlink_to('Versions/Current/Python')
    destination = tmp_path/'app/Contents/Resources/cli'
    build.copy_frozen_cli(source, destination)
    copied = destination/'_internal/Python.framework'
    assert (copied/'Python').is_symlink()
    assert (copied/'Versions/Current').is_symlink()
    assert (copied/'Python').read_bytes() == binary.read_bytes()
    # Signing skips aliases and signs the real framework binary once.
    assert not build.is_macho(copied/'Python')
    assert build.is_macho(copied/'Versions/3.12/Python')

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


def metadata_tree(tmp_path, release='0.1.3', python='0.1.3', setup='0.1.3'):
    root = tmp_path/'source'
    package = root/'agent-harness/cli_anything/kakaotalk'
    package.mkdir(parents=True)
    (root/'VERSION').write_text(release+'\n')
    (root/'BUILD_VERSION').write_text('4\n')
    (package/'__init__.py').write_text(f'__version__ = "{python}"\n')
    (root/'agent-harness/setup.py').write_text(f'setup(name="cli-anything-kakaotalk", version="{setup}")\n')
    return root


def test_release_metadata_mismatch_preserves_existing_build(tmp_path, monkeypatch):
    root = metadata_tree(tmp_path, python='0.1.2')
    app = root/'dist/KakaoTalk CLI.app'
    app.mkdir(parents=True)
    (app/'previous').write_text('keep')
    monkeypatch.setattr(build, 'ROOT', root)
    monkeypatch.setattr(build, 'APP', app)
    with pytest.raises(ValueError, match='version mismatch'):
        build.main(['--signing-identity', '-'])
    assert (app/'previous').read_text() == 'keep'


def test_release_metadata_agrees_without_executing_setup(tmp_path):
    root = metadata_tree(tmp_path)
    with (root/'agent-harness/setup.py').open('a') as stream:
        stream.write('raise RuntimeError("must never execute setup.py")\n')
    assert build.release_version(root) == '0.1.3'
    assert build.bundle_versions(root) == {'CFBundleShortVersionString': '0.1.3', 'CFBundleVersion': '4'}


def test_setup_version_mismatch_is_detected(tmp_path):
    root = metadata_tree(tmp_path, setup='0.1.2')
    with pytest.raises(ValueError, match='version mismatch'):
        build.release_version(root)


@pytest.mark.parametrize('number', [None, '0', '-1', '04', '10000', '4.1', 'text'])
def test_invalid_build_counter_preserves_prior_app(tmp_path, monkeypatch, number):
    root = metadata_tree(tmp_path)
    if number is None:
        (root/'BUILD_VERSION').unlink()
    else:
        (root/'BUILD_VERSION').write_text(number)
    app = root/'dist/KakaoTalk CLI.app'
    app.mkdir(parents=True)
    (app/'previous').write_text('keep')
    monkeypatch.setattr(build, 'ROOT', root)
    monkeypatch.setattr(build, 'APP', app)
    monkeypatch.setattr(build, 'run', lambda *a: pytest.fail('Build must not start'))
    with pytest.raises(ValueError, match='BUILD_VERSION'):
        build.main(['--signing-identity', '-'])
    assert (app/'previous').read_text() == 'keep'

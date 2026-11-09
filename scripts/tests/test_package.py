"""Regression tests for release resource names and final archive checksums."""
import hashlib
import importlib.util
import json
import plistlib
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('release_package', ROOT/'scripts/package.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def fixture_tree(tmp_path):
    root = tmp_path/'source'
    app = root/'dist/KakaoTalk CLI.app'
    native = app/'Contents/MacOS/KakaoTalkCLI'
    native.parent.mkdir(parents=True)
    native.write_bytes(b'native')
    with (app/'Contents/Info.plist').open('wb') as stream:
        plistlib.dump({'CFBundleShortVersionString': release.VERSION, 'CFBundleVersion': '4'}, stream)
    cli = app/'Contents/Resources/cli/cli-anything-kakaotalk'
    cli.parent.mkdir(parents=True)
    cli.write_bytes(b'cli')
    (app/'Contents/Resources/usage-guide.html').write_text('guide')
    for name in ['LICENSE', 'NOTICE']:
        (root/name).write_text(name)
    (root/'THIRD_PARTY_LICENSES').mkdir()
    (root/'THIRD_PARTY_LICENSES/LICENSE.txt').write_text('third party')
    (root/'BUILD_VERSION').write_text('4\n')
    (root/'docs').mkdir()
    (root/'docs/company-mac-test.md').write_text('test instructions')
    (root/'docs/version-support.md').write_text('version scope')
    (root/'docs/signing.md').write_text('signing instructions')
    # Historical evidence must never leak an obsolete archive checksum into a new ZIP.
    (root/'VERIFICATION.md').write_text('old zip SHA256: stale-hash')
    return root, app


def test_final_checksum_and_clean_manifest(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    checked = []
    monkeypatch.setattr(release, 'signing_metadata', lambda path: {'type': 'certificate', 'designated_requirement': 'identifier test and certificate leaf = H"ABC"'})
    monkeypatch.setattr(release, 'verify_signature', lambda path: checked.append(path))
    monkeypatch.setattr(release, 'verify_extracted_archive', lambda path: checked.append(path))
    archive = release.package(root=root, app=app, output=root/'dist')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert Path(str(archive)+'.sha256').read_text() == f'{digest}  {archive.name}\n'
    with zipfile.ZipFile(archive) as bundle:
        prefix = f'KakaoTalk-CLI-{release.VERSION}-company-test-arm64/'
        manifest = json.loads(bundle.read(prefix+'BUILD.json'))
        assert manifest['version'] == release.VERSION
        assert manifest['bundle_version'] == '4'
        assert manifest['signature']['type'] == 'certificate'
        assert manifest['signature']['designated_requirement'] == 'identifier test and certificate leaf = H"ABC"'
        assert manifest['native_sha256'] == hashlib.sha256(b'native').hexdigest()
        verification = bundle.read(prefix+'VERIFICATION.md').decode()
        assert 'stale-hash' not in verification
        assert digest not in verification
        assert '.zip.sha256' in verification
    assert len(checked) == 2


def test_archive_is_repeatable_and_preserves_symlinks(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    (app/'Contents/Resources/alias').symlink_to('usage-guide.html')
    monkeypatch.setattr(release, 'signing_metadata', lambda path: {'type': 'certificate', 'designated_requirement': 'identifier test and certificate leaf = H"ABC"'})
    monkeypatch.setattr(release, 'verify_signature', lambda path: None)
    monkeypatch.setattr(release, 'verify_extracted_archive', lambda path: None)
    archive = release.package(root=root, app=app, output=root/'dist')
    original = archive.read_bytes()
    (app/'Contents/Resources/usage-guide.html').touch()
    assert release.package(root=root, app=app, output=root/'dist').read_bytes() == original
    with zipfile.ZipFile(archive) as bundle:
        info = next(i for i in bundle.infolist() if i.filename.endswith('/alias'))
        assert (info.external_attr >> 16) & 0o170000 == 0o120000
        assert bundle.read(info) == b'usage-guide.html'


def test_non_ascii_signed_resource_is_rejected(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    (app/'Contents/Resources/사용안내.html').write_text('guide')
    monkeypatch.setattr(release, 'signing_metadata', lambda path: {'type': 'certificate', 'designated_requirement': 'identifier test and certificate leaf = H"ABC"'})
    monkeypatch.setattr(release, 'verify_signature', lambda path: None)
    with pytest.raises(ValueError, match='ASCII'):
        release.package(root=root, app=app, output=root/'dist')


def test_build_uses_ascii_resource_and_clean_bundle():
    script = (ROOT/'scripts/build.py').read_text()
    installer = (ROOT/'native/Installer.swift').read_text()
    assert '사용안내.html' not in script
    assert 'usage-guide.html' in script
    assert 'usage-guide.html' in installer
    assert 'shutil.rmtree(APP)' in script


def test_failed_extraction_keeps_previous_release(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    monkeypatch.setattr(release, 'signing_metadata', lambda path: {'type': 'certificate', 'designated_requirement': 'identifier test and certificate leaf = H"ABC"'})
    monkeypatch.setattr(release, 'verify_signature', lambda path: None)
    monkeypatch.setattr(release, 'verify_extracted_archive', lambda path: None)
    archive = release.package(root=root, app=app, output=root/'dist')
    previous = archive.read_bytes()
    checksum = Path(str(archive)+'.sha256').read_text()
    (app/'Contents/MacOS/KakaoTalkCLI').write_bytes(b'new-build')

    def reject_archive(path):
        raise ValueError('extracted signature mismatch')

    monkeypatch.setattr(release, 'verify_extracted_archive', reject_archive)
    with pytest.raises(ValueError, match='signature mismatch'):
        release.package(root=root, app=app, output=root/'dist')
    assert archive.read_bytes() == previous
    assert Path(str(archive)+'.sha256').read_text() == checksum


def test_system_extractor_preserves_framework_style_symlink(tmp_path, monkeypatch):
    if not Path('/usr/bin/ditto').exists():
        pytest.skip('macOS system extractor required')
    root, app = fixture_tree(tmp_path)
    (app/'Contents/Resources/alias').symlink_to('usage-guide.html')
    checked = []

    def signature_check(path):
        checked.append(path)
        if len(checked) == 2:
            alias = path/'Contents/Resources/alias'
            assert alias.is_symlink()
            assert alias.read_text() == 'guide'

    monkeypatch.setattr(release, 'signing_metadata', lambda path: {'type': 'certificate', 'designated_requirement': 'identifier test and certificate leaf = H"ABC"'})
    monkeypatch.setattr(release, 'verify_signature', signature_check)
    release.package(root=root, app=app, output=root/'dist')
    assert len(checked) == 2


def test_signing_metadata_uses_actual_certificate_and_requirement(monkeypatch):
    from types import SimpleNamespace
    details = ('Identifier=local.kakaotalk-cli\nAuthority=Company Signing\n'
               'Authority=Company Root\nTeamIdentifier=TEAM123\n'
               'designated => identifier "local.kakaotalk-cli" and certificate leaf = H"ABC"\n')
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='', stderr=details))
    metadata = release.signing_metadata(Path('/app'))
    assert metadata['type'] == 'certificate'
    assert metadata['authorities'] == ['Company Signing', 'Company Root']
    assert metadata['team_identifier'] == 'TEAM123'
    assert metadata['designated_requirement'].endswith('H"ABC"')
    assert metadata['notarization'] == 'not assessed'


def test_adhoc_metadata_does_not_promise_stable_identity(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='', stderr='Signature=adhoc\n# designated => cdhash H"abc"\n'))
    assert release.signing_metadata(Path('/app'))['type'] == 'ad-hoc'


def test_missing_actual_identity_metadata_fails_closed(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='', stderr='Identifier=app\n'))
    with pytest.raises(ValueError, match='Cannot determine'):
        release.signing_metadata(Path('/app'))


def test_app_version_cannot_be_mislabeled_by_packaging(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    with (app/'Contents/Info.plist').open('wb') as stream:
        plistlib.dump({'CFBundleShortVersionString': '0.1.1'}, stream)
    monkeypatch.setattr(release, 'verify_signature', lambda path: None)
    with pytest.raises(ValueError, match='does not match'):
        release.package(root=root, app=app, output=root/'dist')


def test_release_verify_checks_sidecar_before_extraction(tmp_path, monkeypatch):
    archive = tmp_path/'test.zip'
    archive.write_bytes(b'zip payload')
    Path(str(archive)+'.sha256').write_text('0'*64+'  test.zip\n')
    monkeypatch.setattr(release, 'verify_extracted_archive', lambda path: pytest.fail('Must check digest first'))
    with pytest.raises(ValueError, match='checksum'):
        release.verify_release(archive)


def test_release_verify_accepts_matching_sidecar_and_checks_contents(tmp_path, monkeypatch):
    archive = tmp_path/f'KakaoTalk-CLI-{release.VERSION}-company-test-macOS-arm64.zip'
    archive.write_bytes(b'zip payload')
    Path(str(archive)+'.sha256').write_text(release.sha256(archive)+'  '+archive.name+'\n')
    checked = []
    monkeypatch.setattr(release, 'verify_extracted_archive', lambda path: checked.append(path) or {'version': release.VERSION})
    assert release.verify_release(archive)['version'] == release.VERSION
    assert checked == [archive]


def test_manifest_validation_detects_hash_and_identity_changes(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    signature = {'type': 'ad-hoc', 'designated_requirement': 'cdhash old'}
    manifest = {'version': release.VERSION, 'bundle_version': '4',
                'native_sha256': release.sha256(app/'Contents/MacOS/KakaoTalkCLI'),
                'cli_sha256': release.sha256(app/'Contents/Resources/cli/cli-anything-kakaotalk'),
                'signature': signature}
    (app.parent/'BUILD.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(release, 'signing_metadata', lambda path: signature)
    assert release.verify_bundle_manifest(app) == manifest
    monkeypatch.setattr(release, 'signing_metadata', lambda path: {'type': 'certificate'})
    with pytest.raises(ValueError, match='signing metadata'):
        release.verify_bundle_manifest(app)
    monkeypatch.setattr(release, 'signing_metadata', lambda path: signature)
    (app/'Contents/MacOS/KakaoTalkCLI').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='native_sha256'):
        release.verify_bundle_manifest(app)


def unsafe_archive(tmp_path, entries):
    archive = tmp_path/'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        for name, data, symlink in entries:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (0o120777 if symlink else 0o100644) << 16
            zipped.writestr(info, data)
    return archive


@pytest.mark.parametrize('entries', [
    [('root/link', '.', True), ('root/link/escape', '../../outside', True)],
    [('root/link/file', 'payload', False), ('root/link', '.', True)],
    [('root/LINK', '.', True), ('root/link/file', 'payload', False)],
])
def test_extractor_rejects_entries_beneath_symlink_parents(tmp_path, monkeypatch, entries):
    archive = unsafe_archive(tmp_path, entries)
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: pytest.fail('Extractor must not run'))
    with pytest.raises(ValueError, match='symlink parent'):
        release.verify_extracted_archive(archive)


@pytest.mark.parametrize('names', [
    ('root/duplicate', 'root/duplicate'),
    ('root/Readme', 'root/readme'),
    ('root/é.txt', 'root/e\u0301.txt'),
])
def test_extractor_rejects_duplicate_filesystem_paths(tmp_path, monkeypatch, names):
    archive = unsafe_archive(tmp_path, [(name, 'payload', False) for name in names])
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: pytest.fail('Extractor must not run'))
    with pytest.raises(ValueError, match='duplicate'):
        release.verify_extracted_archive(archive)


def test_package_rejects_stale_bundle_build_number(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    (root/'BUILD_VERSION').write_text('5\n')
    monkeypatch.setattr(release, 'verify_signature', lambda path: None)
    with pytest.raises(ValueError, match='BUILD_VERSION'):
        release.package(root=root, app=app, output=root/'dist')


@pytest.mark.parametrize('entries', [
    [('root/p/link', '../..', True), ('root/p/escape', 'link/../outside', True)],
    [('root/safe', 'payload', False), ('root/p/link', '../safe', True)],
])
def test_release_format_rejects_all_parent_traversal_symlink_targets(tmp_path, monkeypatch, entries):
    archive = unsafe_archive(tmp_path, entries)
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: pytest.fail('Extractor must not run'))
    with pytest.raises(ValueError, match='parent-traversal'):
        release.verify_extracted_archive(archive)

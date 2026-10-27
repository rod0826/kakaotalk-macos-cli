"""Regression tests for release resource names and final archive checksums."""
import hashlib
import importlib.util
import json
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
    cli = app/'Contents/Resources/cli/cli-anything-kakaotalk'
    cli.parent.mkdir(parents=True)
    cli.write_bytes(b'cli')
    (app/'Contents/Resources/usage-guide.html').write_text('guide')
    for name in ['LICENSE', 'NOTICE']:
        (root/name).write_text(name)
    (root/'THIRD_PARTY_LICENSES').mkdir()
    (root/'THIRD_PARTY_LICENSES/LICENSE.txt').write_text('third party')
    (root/'docs').mkdir()
    (root/'docs/company-mac-test.md').write_text('test instructions')
    (root/'docs/version-support.md').write_text('version scope')
    # Historical evidence must never leak an obsolete archive checksum into a new ZIP.
    (root/'VERIFICATION.md').write_text('old zip SHA256: stale-hash')
    return root, app


def test_final_checksum_and_clean_manifest(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    checked = []
    monkeypatch.setattr(release, 'verify_signature', lambda path: checked.append(path))
    monkeypatch.setattr(release, 'verify_extracted_archive', lambda path: checked.append(path))
    archive = release.package(root=root, app=app, output=root/'dist')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert Path(str(archive)+'.sha256').read_text() == f'{digest}  {archive.name}\n'
    with zipfile.ZipFile(archive) as bundle:
        prefix = 'KakaoTalk-CLI-0.1.1-company-test-arm64/'
        manifest = json.loads(bundle.read(prefix+'BUILD.json'))
        assert manifest['version'] == '0.1.1'
        assert manifest['native_sha256'] == hashlib.sha256(b'native').hexdigest()
        verification = bundle.read(prefix+'VERIFICATION.md').decode()
        assert 'stale-hash' not in verification
        assert digest not in verification
        assert '.zip.sha256' in verification
    assert len(checked) == 2


def test_archive_is_repeatable_and_preserves_symlinks(tmp_path, monkeypatch):
    root, app = fixture_tree(tmp_path)
    (app/'Contents/Resources/alias').symlink_to('usage-guide.html')
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

    monkeypatch.setattr(release, 'verify_signature', signature_check)
    release.package(root=root, app=app, output=root/'dist')
    assert len(checked) == 2

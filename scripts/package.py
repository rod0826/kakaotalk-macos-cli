"""Create the company-test ZIP and its final, external SHA-256 sidecar.

Run after scripts/build.py. No archive hash is embedded inside its own archive.
ZIP timestamps and entry ordering are fixed; identical inputs produce identical ZIPs.
"""
import argparse
import hashlib
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION').read_text().strip()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_signature(app):
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)


def signing_metadata(app):
    result = subprocess.run(['codesign', '-d', '--verbose=4', '-r-', str(app)],
                            capture_output=True, text=True, check=True)
    lines = [line.removeprefix('# ').strip() for line in
             (result.stdout + '\n' + result.stderr).splitlines()]
    authorities = [line.split('=', 1)[1] for line in lines if line.startswith('Authority=')]
    requirements = [line.partition('designated => ')[2] for line in lines
                    if line.startswith('designated => ')]
    if not requirements or not (authorities or 'Signature=adhoc' in lines):
        raise ValueError('Cannot determine actual signing identity and designated requirement')
    return {
        'type': 'ad-hoc' if 'Signature=adhoc' in lines else 'certificate',
        'authorities': authorities,
        'team_identifier': next((line.split('=', 1)[1] for line in lines
                                 if line.startswith('TeamIdentifier=')), None),
        'designated_requirement': requirements[0],
        'notarization': 'not assessed',
    }


def verify_ascii_paths(app):
    for path in app.rglob('*'):
        if not str(path.relative_to(app)).isascii():
            raise ValueError(f'Signed bundle paths must be ASCII: {path.relative_to(app)}')


def verify_extracted_archive(archive):
    # Use the system extractor, independently of our archive writer. It preserves
    # framework symlinks; Finder/Archive Utility use the same ZIP conventions.
    with tempfile.TemporaryDirectory(prefix='kakaotalk-zip-check-') as directory:
        subprocess.run(['/usr/bin/ditto', '-x', '-k', str(archive), directory], check=True)
        apps = list(Path(directory).glob('*/KakaoTalk CLI.app'))
        if len(apps) != 1:
            raise ValueError('Expected exactly one app in the extracted archive')
        verify_ascii_paths(apps[0])
        verify_signature(apps[0])


def write_archive(stage, archive):
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(stage.rglob('*')):
            if path.is_dir() and not path.is_symlink():
                continue
            relative = path.relative_to(stage.parent).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = path.lstat().st_mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            data = os.readlink(path).encode('utf-8') if path.is_symlink() else path.read_bytes()
            output.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def package(root=ROOT, app=None, output=None):
    root = Path(root)
    app = Path(app) if app else root/'dist/KakaoTalk CLI.app'
    output = Path(output) if output else root/'dist'
    verify_ascii_paths(app)
    verify_signature(app)
    with (app/'Contents/Info.plist').open('rb') as stream:
        app_version = plistlib.load(stream)['CFBundleShortVersionString']
    if app_version != VERSION:
        raise ValueError(f'App version {app_version} does not match release version {VERSION}')
    signature = signing_metadata(app)
    output.mkdir(parents=True, exist_ok=True)
    name = f'KakaoTalk-CLI-{VERSION}-company-test-arm64'
    archive = output/f'KakaoTalk-CLI-{VERSION}-company-test-macOS-arm64.zip'
    with tempfile.TemporaryDirectory(prefix='kakaotalk-package-') as temporary:
        stage = Path(temporary)/name
        stage.mkdir()
        shutil.copytree(app, stage/app.name, symlinks=True)
        for notice in ['LICENSE', 'NOTICE']:
            shutil.copy2(root/notice, stage/notice)
        shutil.copytree(root/'THIRD_PARTY_LICENSES', stage/'THIRD_PARTY_LICENSES', symlinks=True)
        shutil.copy2(root/'docs/company-mac-test.md', stage/'company-mac-test.md')
        shutil.copy2(root/'docs/version-support.md', stage/'version-support.md')
        shutil.copy2(root/'docs/signing.md', stage/'signing.md')
        manifest = {
            'version': VERSION,
            'architecture': 'arm64',
            'native_sha256': sha256(app/'Contents/MacOS/KakaoTalkCLI'),
            'cli_sha256': sha256(app/'Contents/Resources/cli/cli-anything-kakaotalk'),
            'signature': signature,
        }
        (stage/'BUILD.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        (stage/'VERIFICATION.md').write_text(
            '# Company test build verification\n\n'
            'The app signature was checked with `codesign --verify --deep --strict` before packaging.\n'
            'The final ZIP is extracted with macOS ditto and its app signature is checked again.\n'
            'All signed bundle paths use ASCII to avoid filename normalization differences.\n\n'
            'BUILD.json records the native executable and CLI SHA-256 values, actual signing type, certificate chain and designated requirement.\n'
            'The final archive SHA-256 is in the adjacent `.zip.sha256` sidecar, created only after extraction verification.\n'
            'Keep that sidecar beside the ZIP; an archive cannot contain its own final checksum.\n\n'
            'This verifies packaging integrity; company-Mac UI behavior still requires the supplied test instructions.\n',
            encoding='utf-8',
        )
        # Publish only verified output, keeping a previous archive/sidecar pair
        # intact if codesign or extraction fails.
        pending = Path(temporary)/archive.name
        write_archive(stage, pending)
        verify_extracted_archive(pending)
        digest = sha256(pending)
        shutil.copyfile(pending, archive)
        Path(str(archive)+'.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=ROOT/'dist/KakaoTalk CLI.app')
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    print(package(app=args.app, output=args.output))


if __name__ == '__main__':
    main()

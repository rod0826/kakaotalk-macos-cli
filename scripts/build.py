"""Build a local arm64 .app with a frozen, agent-neutral CLI."""
import argparse
import os
import re
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'agent-harness/cli_anything/kakaotalk'
APP = ROOT / 'dist/KakaoTalk CLI.app'


def run(*args):
    environment = {**os.environ, 'PYINSTALLER_CONFIG_DIR': str(ROOT/'build/pyinstaller-cache')}
    subprocess.run([str(a) for a in args], cwd=ROOT, env=environment, check=True)


def signing_argument(argv=None, environment=None):
    environment = os.environ if environment is None else environment
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--signing-identity', default=environment.get('KAKAOTALK_SIGNING_IDENTITY', '-'),
                        help='Existing code-signing certificate name or SHA-1; default: ad-hoc (-)')
    return parser.parse_args(argv).signing_identity


def resolve_signing_identity(requested):
    if requested == '-':
        return '-'
    result = subprocess.run(['security', 'find-identity', '-v', '-p', 'codesigning'],
                            capture_output=True, text=True, check=True)
    identities = re.findall(r'\d+\) ([A-Fa-f0-9]{40}) "([^"]+)"', result.stdout)
    matches = [fingerprint.upper() for fingerprint, name in identities
               if requested == name or requested.upper() == fingerprint.upper()]
    if len(matches) != 1:
        raise ValueError('Requested signing identity is unavailable or ambiguous; '
                         'use security find-identity -v -p codesigning and provide an exact certificate name or SHA-1. '
                         'No ad-hoc fallback was performed.')
    return matches[0]


def pyinstaller_signing_args(identity):
    return [] if identity == '-' else ['--codesign-identity', identity]


def is_macho(path):
    if path.is_symlink() or not path.is_file():
        return False
    with path.open('rb') as stream:
        magic = stream.read(4)
    return magic in {bytes.fromhex(value) for value in
                    ['feedface', 'cefaedfe', 'feedfacf', 'cffaedfe',
                     'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca']}


def sign_bundle(app, identity):
    # Sign from the inside out. --deep is for verification, never signing:
    # nested frozen libraries and framework bundles need their own signatures.
    paths = sorted(app.rglob('*'), key=lambda path: (-len(path.parts), str(path)))
    for path in paths:
        if is_macho(path):
            run('codesign', '--force', '--sign', identity, '--timestamp=none', path)
    for path in paths:
        if (not path.is_symlink() and path.is_dir()
                and path.suffix in {'.framework', '.app', '.xpc', '.bundle'}):
            run('codesign', '--force', '--sign', identity, '--timestamp=none', path)
    run('codesign', '--force', '--sign', identity, '--timestamp=none', app)


def copy_frozen_cli(source, destination):
    if destination.exists():
        shutil.rmtree(destination)
    # Versioned framework aliases must remain links. Dereferencing Python and
    # Versions/Current creates an ambiguous framework that codesign rejects.
    shutil.copytree(source, destination, symlinks=True)


def main(argv=None):
    # Resolve before deleting a prior build. A requested unavailable certificate
    # must fail without silently emitting an ad-hoc release.
    identity = resolve_signing_identity(signing_argument(argv))
    (ROOT/'build').mkdir(exist_ok=True)
    # Remove stale signed resources from earlier builds before signing.
    if APP.exists():
        shutil.rmtree(APP)
    (APP/'Contents/MacOS').mkdir(parents=True, exist_ok=True)
    resources = APP/'Contents/Resources'
    resources.mkdir(parents=True, exist_ok=True)
    native = APP/'Contents/MacOS/KakaoTalkCLI'
    run('xcrun','swiftc','-O','-module-cache-path','/tmp/kakao-swift-modules',
        '-target','arm64-apple-macosx14.0',
        *sorted((ROOT/'native').glob('*.swift')), '-o', native)
    (PACKAGE/'bin').mkdir(exist_ok=True)
    shutil.copy2(native, PACKAGE/'bin/KakaoTalkCLI')
    run(sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir',
        '--name','cli-anything-kakaotalk','--distpath',ROOT/'build/frozen',
        '--workpath',ROOT/'build/pyinstaller','--specpath',ROOT/'build',
        '--paths',ROOT/'agent-harness','--hidden-import','cli_anything.kakaotalk.utils.repl_skin',
        '--collect-data','cli_anything.kakaotalk',*pyinstaller_signing_args(identity),ROOT/'scripts/entry.py')
    cli_dir = resources/'cli'
    copy_frozen_cli(ROOT/'build/frozen/cli-anything-kakaotalk', cli_dir)
    if (resources/'skills').exists(): shutil.rmtree(resources/'skills')
    shutil.copytree(ROOT/'skills',resources/'skills')
    shutil.copy2(ROOT/'usage-guide.html',resources/'usage-guide.html')
    for notice in ['LICENSE', 'NOTICE']:
        shutil.copy2(ROOT/notice, resources/notice)
    licenses = resources/'THIRD_PARTY_LICENSES'
    if licenses.exists(): shutil.rmtree(licenses)
    shutil.copytree(ROOT/'THIRD_PARTY_LICENSES', licenses)
    with (APP/'Contents/Info.plist').open('wb') as stream:
        plistlib.dump({'CFBundleIdentifier':'local.kakaotalk-cli',
            'CFBundleName':'KakaoTalk CLI','CFBundleDisplayName':'KakaoTalk CLI',
            'CFBundleExecutable':'KakaoTalkCLI','CFBundlePackageType':'APPL',
            'CFBundleShortVersionString':(ROOT/'VERSION').read_text().strip(),'CFBundleVersion':'3',
            'LSMinimumSystemVersion':'14.0','NSHighResolutionCapable':True,
            'NSAccessibilityUsageDescription':'카카오톡에서 요청한 채팅방 검색, 초안 입력과 명시적으로 지정한 전송을 수행합니다.'},stream)
    for path in APP.rglob('*'):
        if not str(path.relative_to(APP)).isascii():
            raise ValueError(f'Signed bundle paths must be ASCII: {path.relative_to(APP)}')
    sign_bundle(APP, identity)
    run('codesign','--verify','--deep','--strict',APP)
    print(APP)


if __name__ == '__main__': main()

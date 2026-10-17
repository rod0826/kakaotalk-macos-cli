"""Build a local arm64 .app with a frozen, agent-neutral CLI."""
import os
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


def main():
    (ROOT/'build').mkdir(exist_ok=True)
    (APP/'Contents/MacOS').mkdir(parents=True, exist_ok=True)
    resources = APP/'Contents/Resources'
    resources.mkdir(parents=True, exist_ok=True)
    native = APP/'Contents/MacOS/KakaoTalkCLI'
    run('xcrun','swiftc','-O','-module-cache-path','/tmp/kakao-swift-modules',
        '-target','arm64-apple-macosx14.0',
        ROOT/'native/Accessibility.swift', ROOT/'native/Broker.swift', ROOT/'native/Installer.swift', ROOT/'native/main.swift','-o',native)
    (PACKAGE/'bin').mkdir(exist_ok=True)
    shutil.copy2(native, PACKAGE/'bin/KakaoTalkCLI')
    run(sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir',
        '--name','cli-anything-kakaotalk','--distpath',ROOT/'build/frozen',
        '--workpath',ROOT/'build/pyinstaller','--specpath',ROOT/'build',
        '--paths',ROOT/'agent-harness','--hidden-import','cli_anything.kakaotalk.utils.repl_skin',
        '--collect-data','cli_anything.kakaotalk',ROOT/'scripts/entry.py')
    cli_dir = resources/'cli'
    if cli_dir.exists(): shutil.rmtree(cli_dir)
    shutil.copytree(ROOT/'build/frozen/cli-anything-kakaotalk',cli_dir)
    if (resources/'skills').exists(): shutil.rmtree(resources/'skills')
    shutil.copytree(ROOT/'skills',resources/'skills')
    shutil.copy2(ROOT/'사용안내.html',resources/'사용안내.html')
    for notice in ['LICENSE', 'NOTICE']:
        shutil.copy2(ROOT/notice, resources/notice)
    licenses = resources/'THIRD_PARTY_LICENSES'
    if licenses.exists(): shutil.rmtree(licenses)
    shutil.copytree(ROOT/'THIRD_PARTY_LICENSES', licenses)
    with (APP/'Contents/Info.plist').open('wb') as stream:
        plistlib.dump({'CFBundleIdentifier':'local.kakaotalk-cli',
            'CFBundleName':'KakaoTalk CLI','CFBundleDisplayName':'KakaoTalk CLI',
            'CFBundleExecutable':'KakaoTalkCLI','CFBundlePackageType':'APPL',
            'CFBundleShortVersionString':'0.1.0','CFBundleVersion':'1',
            'LSMinimumSystemVersion':'14.0','NSHighResolutionCapable':True,
            'NSAccessibilityUsageDescription':'카카오톡에서 요청한 채팅방 검색, 초안 입력과 명시적으로 지정한 전송을 수행합니다.'},stream)
    run('codesign','--force','--deep','--sign','-',APP)
    run('codesign','--verify','--deep','--strict',APP)
    print(APP)


if __name__ == '__main__': main()

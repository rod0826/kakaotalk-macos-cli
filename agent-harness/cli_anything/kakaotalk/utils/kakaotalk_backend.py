import json
import hashlib
import os
import socket
import stat
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from ..core.errors import ToolError


def default_state_dir():
    return Path.home() / 'Library/Application Support/KakaoTalkCLI'


class Backend:
    def __init__(self, state_dir, allow_untested=False):
        self.state_dir = Path(state_dir)
        self.allow_untested = allow_untested

    def app_bundle(self):
        if getattr(sys, 'frozen', False):
            candidate = Path(sys.executable).resolve().parents[3]
        else:
            candidate = Path(__file__).resolve().parents[4] / 'dist/KakaoTalk CLI.app'
        if not (candidate/'Contents/Info.plist').is_file():
            raise ToolError('APP_BUNDLE_MISSING', 'Build or install KakaoTalk CLI.app first.')
        return candidate

    def connect(self):
        path = default_state_dir()/'control.sock'
        if len(os.fsencode(path)) > 103:
            raise ToolError('SOCKET_PATH_TOO_LONG', 'Home directory path is too long for a macOS Unix socket.')
        def attempt():
            try:
                metadata = path.lstat()
                if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
                    raise ToolError('UNSAFE_SOCKET', 'Expected a same-user, mode-0600 local control socket.')
                channel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                channel.settimeout(30)
                try:
                    channel.connect(str(path))
                    return channel
                except OSError:
                    channel.close()
                    return None
            except FileNotFoundError:
                return None
        channel = attempt()
        if channel:
            return channel
        # LaunchServices makes the dedicated app responsible for AX authorization.
        launched = subprocess.run(['/usr/bin/open','-g','-a',str(self.app_bundle()),'--args','--serve'],
                                  text=True, capture_output=True, timeout=10)
        if launched.returncode:
            raise ToolError('APP_LAUNCH_FAILED', f'Could not launch {self.app_bundle()}. Open that app in Finder and follow macOS approval prompts; also check whether the agent sandbox blocks LaunchServices.')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            channel = attempt()
            if channel:
                return channel
            time.sleep(0.1)
        raise ToolError('BROKER_UNAVAILABLE', 'Local control app is unavailable. Quit/reopen the current KakaoTalk CLI.app; the agent execution sandbox may also block local IPC.')

    def call(self, operation, **payload):
        # AX runs inside the granted GUI app; no Terminal/agent-wide permission needed.
        bundle = self.app_bundle()
        native = bundle/'Contents/MacOS/KakaoTalkCLI'
        request = {'operation': operation, 'allow_untested': self.allow_untested,
                   'expires_at': time.time() + 20, 'expected_bundle': str(bundle),
                   'expected_build': hashlib.sha256(native.read_bytes()).hexdigest(), **payload}
        try:
            with self.connect() as channel:
                channel.sendall(json.dumps(request, ensure_ascii=False).encode('utf-8') + b'\n')
                output = bytearray()
                while len(output) <= 4_194_304:
                    chunk = channel.recv(65536)
                    if not chunk:
                        break
                    output.extend(chunk)
                    if b'\n' in chunk:
                        break
                if len(output) > 4_194_304:
                    raise ToolError('BACKEND_PROTOCOL_ERROR', 'Native response exceeded 4 MiB.')
        except (socket.timeout, TimeoutError):
            raise ToolError('BACKEND_TIMEOUT', 'Native backend timed out; do not retry a send automatically.')
        try:
            response = json.loads(output)
        except (ValueError, TypeError):
            raise ToolError('BACKEND_PROTOCOL_ERROR', 'Native backend did not return JSON.')
        if not isinstance(response, dict) or not isinstance(response.get('ok'), bool):
            raise ToolError('BACKEND_PROTOCOL_ERROR', 'Invalid native response envelope.')
        actual_bundle = response.get('broker_bundle')
        if response.get('broker_build') != request['expected_build'] or not isinstance(actual_bundle, str) or unicodedata.normalize('NFC', actual_bundle) != unicodedata.normalize('NFC', request['expected_bundle']):
            translocated = isinstance(actual_bundle, str) and 'AppTranslocation' in Path(actual_bundle).parts
            note = (' AppTranslocation detected. Quit the temporary app, then open '
                    'the extracted app folder in Finder, then drag the app into ~/Applications. '
                    'If the installed app still translocates, quit it and drag it to another user folder '
                    'and back to ~/Applications using Finder. Preserve the installation path; '
                    'follow company macOS approval policy. Do not remove quarantine automatically.'
                    if translocated else ' Quit the old app and open the expected app.')
            raise ToolError('BROKER_BUILD_MISMATCH',
                            f'Running broker build/path differs. Expected: {bundle}; '
                            f'actual: {actual_bundle}; expected build: {request["expected_build"]}; '
                            f'actual build: {response.get("broker_build")}.{note}')
        if not response['ok']:
            error = response.get('error', {})
            if not isinstance(error, dict):
                raise ToolError('BACKEND_PROTOCOL_ERROR', 'Invalid native error payload.')
            raise ToolError(error.get('code', 'BACKEND_ERROR'), error.get('message', 'Native backend error.'))
        if not isinstance(response.get('data'), dict):
            raise ToolError('BACKEND_PROTOCOL_ERROR', 'Invalid native data payload.')
        return response['data']

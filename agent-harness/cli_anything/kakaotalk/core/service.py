import hashlib
import json
import re
from pathlib import Path
from .errors import ToolError


def validate_room(room):
    if not room or not room.strip() or any(ord(c) < 32 for c in room) or len(room) > 200:
        raise ToolError('INVALID_ROOM', 'Room name must be nonempty, at most 200 characters, without control characters.')
    return room


def validate_text(text, allow_empty=False):
    if '\x00' in text or len(text.encode('utf-8')) > 60000 or (not allow_empty and not text.strip()):
        raise ToolError('INVALID_TEXT', 'Text must be nonempty, contain no NUL, and fit within 60,000 UTF-8 bytes.')
    return text


class Service:
    def __init__(self, backend, journal, dry_run=False):
        self.backend, self.journal, self.dry_run = backend, journal, dry_run

    def action(self, operation, **payload):
        if self.dry_run:
            return {'dry_run': True, 'operation': operation, 'room': payload.get('room')}
        return self.backend.call(operation, **payload)

    def draft(self, room, text, expected_text=None):
        validate_room(room); validate_text(text, allow_empty=True)
        return self.action('draft', room=room, text=text, expected_text=expected_text)

    def send(self, room, text, confirm_room, request_id):
        validate_text(text)
        return self._dispatch('send', room, confirm_room, request_id, text=text)

    def select_file(self, room, path):
        validate_room(room)
        payload = self._file_payload(path)
        return self.action('file-select', room=room, **payload)

    def send_file(self, room, path, confirm_room, request_id):
        return self._dispatch('file-send', room, confirm_room, request_id, **self._file_payload(path))

    @staticmethod
    def _file_payload(path):
        path = Path(path).expanduser()
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 100 * 1024 * 1024:
            raise ToolError('INVALID_FILE', 'Choose a regular file at most 100 MiB.')
        path = path.resolve()
        # Fingerprint bytes to prevent request ID reuse for changed files.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {'path': str(path), 'file_digest': digest}

    def _dispatch(self, operation, room, confirm_room, request_id, **payload):
        validate_room(room)
        if confirm_room != room:
            raise ToolError('ROOM_CONFIRMATION_REQUIRED', '--confirm-room must exactly match --room.')
        if not request_id or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,100}', request_id):
            raise ToolError('INVALID_REQUEST_ID', 'Supply a request ID (1–100 letters/digits/_.:-).')
        if self.dry_run:
            return {'dry_run': True, 'operation': operation, 'room': room, 'dispatch_attempted': False}
        digest = hashlib.sha256(json.dumps([operation, room, payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.journal.claim(request_id, digest)
        try:
            result = self.backend.call(operation, room=room, confirm_room=confirm_room, request_id=request_id, **payload)
        except Exception:
            self.journal.finish(request_id, 'unknown')
            raise
        self.journal.finish(request_id, 'unknown' if result.get('status') == 'unknown' else 'completed')
        return result

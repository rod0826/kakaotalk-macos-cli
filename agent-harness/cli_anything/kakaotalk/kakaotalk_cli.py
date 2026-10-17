"""Agent-neutral Click interface. Message bodies travel to the backend on stdin."""
import json
import shlex
import sqlite3
import sys
from pathlib import Path
import click
from . import __version__
from .core.errors import ToolError
from .core.journal import Journal
from .core.service import Service, validate_room
from .utils.kakaotalk_backend import Backend, default_state_dir


class StructuredGroup(click.Group):
    def main(self, args=None, **kwargs):
        arguments = list(sys.argv[1:] if args is None else args)
        json_mode = '--json' in arguments
        kwargs.pop('standalone_mode', None)
        try:
            return super().main(args=arguments, standalone_mode=False, **kwargs)
        except (ToolError, click.ClickException, OSError, ValueError, sqlite3.Error) as error:
            code = getattr(error, 'code', 'INVALID_ARGUMENT' if isinstance(error, click.ClickException) else 'LOCAL_ERROR')
            if json_mode:
                click.echo(json.dumps({'ok': False, 'error': {'code': code, 'message': str(error)}}, ensure_ascii=False))
            else:
                click.echo(f'{code}: {error}', err=True)
            raise SystemExit(2)


def emit(data):
    ctx = click.get_current_context().find_root()
    envelope = {'ok': True, 'data': data}
    click.echo(json.dumps(envelope if ctx.obj['json'] else data, ensure_ascii=False, indent=None if ctx.obj['json'] else 2))


def service():
    return click.get_current_context().find_root().obj['service']


@click.group(cls=StructuredGroup, invoke_without_command=True)
@click.option('--json', 'json_mode', is_flag=True, help='Emit a JSON envelope (put before command).')
@click.option('--dry-run', is_flag=True, help='Plan without touching KakaoTalk or recording a send.')
@click.option('--state-dir', type=click.Path(path_type=Path), default=default_state_dir)
@click.option('--allow-untested-version', is_flag=True, help='Explicitly allow a version other than 26.5.0.')
@click.version_option(__version__)
@click.pass_context
def cli(ctx, json_mode, dry_run, state_dir, allow_untested_version):
    """KakaoTalk for macOS — native accessibility CLI for Codex and Claude Code."""
    ctx.obj = {'json': json_mode, 'service': Service(Backend(state_dir, allow_untested_version), Journal(state_dir/'journal.sqlite3'), dry_run)}
    if ctx.invoked_subcommand is None:
        if json_mode:
            raise ToolError('COMMAND_REQUIRED', '--json requires a command.')
        ctx.invoke(repl)


@cli.command()
def doctor():
    """Check app version, running state and Accessibility permission."""
    emit(service().backend.call('doctor'))


@cli.group()
def chat():
    """Search/open a room; inspect already-loaded messages."""


@chat.command()
@click.argument('query')
def search(query):
    validate_room(query)
    emit(service().action('search', query=query))


@chat.command('open')
@click.argument('room')
def open_chat(room):
    validate_room(room)
    emit(service().action('open', room=room))


@chat.command()
@click.option('--room')
def current(room):
    """Return room title and unsent draft. Output may contain private text."""
    if room: validate_room(room)
    emit(service().action('current', room=room))


@chat.command()
@click.option('--room', required=True)
@click.option('--limit', type=click.IntRange(1,100), default=20)
def read(room, limit):
    """Read loaded rows only. Does not promise complete history."""
    validate_room(room)
    emit(service().action('read', room=room, limit=limit))


def text_options(fn):
    fn = click.option('--text-file', type=click.File('r', encoding='utf-8'), help='UTF-8 file or - for stdin.')(fn)
    return click.option('--text', help='Prefer --text-file - to avoid shell history.')(fn)


def text_input(text, text_file):
    if (text is None) == (text_file is None):
        raise ToolError('TEXT_REQUIRED', 'Specify exactly one of --text or --text-file.')
    if text_file is not None:
        text = text_file.read(60001)
    return text


@cli.group()
def message():
    """Draft safely; dispatch only an explicitly matching draft."""


@message.command()
@click.option('--room', required=True)
@text_options
@click.option('--expected-text', default=None, help='Existing draft must match before replacement.')
def draft(room, text, text_file, expected_text):
    emit(service().draft(room, text_input(text, text_file), expected_text))


@message.command()
@click.option('--room', required=True)
@click.option('--expected-text', required=True, help='Only clear this exact unsent draft.')
def clear(room, expected_text):
    emit(service().draft(room, '', expected_text))


def confirmation_options(fn):
    fn = click.option('--request-id', required=True, help='Unique intent ID; never change to retry an uncertain send.')(fn)
    return click.option('--confirm-room', required=True, help='Repeat the exact room name to authorize dispatch.')(fn)


@message.command()
@click.option('--room', required=True)
@text_options
@confirmation_options
def send(room, text, text_file, confirm_room, request_id):
    """Press Return once on an exact matching draft. Delivery is unverified."""
    emit(service().send(room, text_input(text, text_file), confirm_room, request_id))


@cli.group('file')
def file_group():
    """File picker operations and guarded, experimental file dispatch."""


@file_group.command()
@click.option('--room', required=True)
def dialog(room):
    validate_room(room)
    emit(service().action('file-dialog', room=room))


@file_group.command()
@click.option('--room', required=True)
def cancel(room):
    validate_room(room)
    emit(service().action('file-cancel', room=room))


@file_group.command('send')
@click.option('--room', required=True)
@click.argument('path', type=click.Path(path_type=Path))
@confirmation_options
def send_file(room, path, confirm_room, request_id):
    """Experimental: choose file and dispatch once. Not live-send validated."""
    emit(service().send_file(room, path, confirm_room, request_id))


@cli.group()
def session():
    """Inspect local request outcomes; no chat content is persisted."""


@session.command()
def status():
    emit({'requests': service().journal.status()})


@cli.command()
@click.pass_context
def repl(ctx):
    """Interactive shell, in-memory history only. exit/quit to leave."""
    from .utils.repl_skin import ReplSkin
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    skin = ReplSkin('kakaotalk', __version__, history_file='/dev/null')
    skin.print_banner()
    prompt = PromptSession(history=InMemoryHistory())
    while True:
        try:
            line = prompt.prompt('kakaotalk> ')
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip() in ('exit','quit'): break
        if not line.strip(): continue
        try:
            options = ['--state-dir', str(service().journal.path.parent)]
            if service().dry_run: options.append('--dry-run')
            if service().backend.allow_untested: options.append('--allow-untested-version')
            cli.main(options + shlex.split(line), prog_name='cli-anything-kakaotalk')
        except (SystemExit, ValueError):
            pass
    skin.print_goodbye()


def main():
    cli(prog_name='cli-anything-kakaotalk')


if __name__ == '__main__':
    main()

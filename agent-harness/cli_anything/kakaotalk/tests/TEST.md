# Test plan and sanitized results

This is an unofficial experimental project, not reviewed, approved or certified by Kakao.

## Unit tests
Run `python -m pytest agent-harness/cli_anything/kakaotalk/tests/test_core.py -v` after installing the editable package. The initial implementation passed 26 tests covering validation, exact-room checks, dry runs, journal claims/concurrency, duplicate requests, uncertain outcomes, file validation, request size, broker build identity and Unicode path normalization.

## Real application tests (explicit opt-in)
Build and install the app, grant its Accessibility permission, and log in to KakaoTalk. Set `KAKAO_TEST_ROOM` to your own uniquely named self-chat. Use `CLI_ANYTHING_FORCE_INSTALLED=1` and put the frozen CLI on PATH. Run only `test_full_e2e.py` in an unlocked GUI session. Do not use another person's chat for testing.

The live suite checks doctor, search/open, synthetic draft write/read/restore, and file chooser open/cancel. It never invokes message or file send. A failure may leave a chooser or synthetic draft: inspect the UI before continuing. Temporary artifacts contain synthetic test values only.

Initial local result: 2 live tests passed in 14.90 seconds on Apple Silicon, macOS 26.6.2, KakaoTalk 26.5.0. No real message or file was transmitted. Other macOS/app versions and fresh Macs have not been verified. Raw logs and personal paths are intentionally excluded from public source.

# Test plan and sanitized results

This is an unofficial experimental project, not reviewed, approved or certified by Kakao.

## Unit tests
Run `python -m pytest agent-harness/cli_anything/kakaotalk/tests/test_core.py -v` after installing the editable package. The initial implementation passed 26 tests covering validation, exact-room checks, dry runs, journal claims/concurrency, duplicate requests, uncertain outcomes, file validation, request size, broker build identity and Unicode path normalization.

## Real application tests (explicit opt-in)
Build and install the app, grant its Accessibility permission, and log in to KakaoTalk. Set `KAKAO_TEST_ROOM` to your own uniquely named self-chat. Use `CLI_ANYTHING_FORCE_INSTALLED=1` and put the frozen CLI on PATH. Run only `test_full_e2e.py` in an unlocked GUI session. Do not use another person's chat for testing.

The live suite checks doctor, search/open, synthetic draft write/read/restore, and file chooser open/cancel. It never invokes message or file send. A failure may leave a chooser or synthetic draft: inspect the UI before continuing. Temporary artifacts contain synthetic test values only.

Initial local result: 2 live tests passed in 14.90 seconds on Apple Silicon, macOS 26.6.2, KakaoTalk 26.5.0. No real message or file was transmitted. Other macOS/app versions and fresh Macs have not been verified. Raw logs and personal paths are intentionally excluded from public source.

## Company regression plan — 0.1.1

Before fixes: installation regression compile failed because the extracted installation policy did not exist; broker mismatch test failed because it omitted actual/expected paths and AppTranslocation diagnosis. Packaging/version policy tests were first run without their implementations and failed.

- Issue #1: reject non-ASCII signed resource paths, clean stale bundle output, verify codesign before packaging and after system ZIP extraction.
- Issue #2: test real symlink repair under a temporary home, preserve unrelated symlinks/files, fixed destination selection from a simulated translocated source, reject a different installed build, maintain fail-closed broker identity checks with actionable diagnostics.
- Issue #3: check final external archive digest, exclude historical/self-referential hashes, repeat identical archive inputs, preserve framework symlinks under actual ditto extraction.
- Issue #4: retain exact primary-title matching and recent-first duplicate policy; document label[0] and emoji verbatim. No fuzzy recipient selection.
- Issue #5: test version/operation matrix, unknown versions and unknown commands; 26.8.0 file selection and send remain blocked unless explicitly overridden for compatibility testing.

Company report establishes only the seven non-dispatch operations on 26.8.0; it does not establish file selection or dispatch compatibility. No new real messages/files will be sent during this regression pass. Company-Mac Finder extraction, Gatekeeper and permissions must be retested there with the new artifact.

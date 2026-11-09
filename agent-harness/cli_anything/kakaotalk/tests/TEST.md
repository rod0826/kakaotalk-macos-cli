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


## 0.1.2 company follow-up plan — 2026-10-31

- #7: replace programmatic app copy with Finder installation/update guidance, reveal the exact user Applications folder, preserve fixed-path links and fail-closed broker identity. Extend identity regressions to same-build translocation, not just old-build mismatch.
- #8: add exactly tested 26.9.0 non-dispatch operations; keep unknown future versions and untested sends blocked.
- #9: reproduce transient empty window lists with an injected reader, verify bounded retry, refresh AX root, and stop with WINDOWS_UNAVAILABLE when all probes are empty. Test visible wrong-title rooms separately. Never issue search/navigation keys until some AX windows are available.
- #10: explicit signing identity selection with no silent fallback, actual signing metadata in the build manifest, version consistency checks. No certificate/keychain/trust modifications. TCC permission retention and first-launch company policy require company-side validation with an approved certificate.

This pass does not send real messages or files. Offline tests model window availability; they cannot prove another-Space behavior on the company desktop. A successful retry must still pass exact room/composer/focus checks before edits or dispatch.


## 0.1.3 plan — 2026-11-09

- Reproduce stale metadata with a primed Foundation Bundle and rewritten Info.plist; fresh reader must see the new version. Cover malformed/missing metadata and restart timestamp limits.
- Verify release/Python metadata disagreement fails before prior app deletion.
- Verify final archive sidecar, extracted app signature, manifest digests/version/actual signature metadata; reject tampering.
- Live suite checks restart readiness, ten repeated reads and either verified file selection or the expected UNTESTED_VERSION rejection according to capabilities. It never sends, overrides version guards, or skips unsupported-capability checks.
- Company issue evidence remains the October26.9.0 report. No new0.1.2 company test results were found in the public API on November9. Certificate TCC retention and actual26.9.0 dispatch remain pending.

0.1.3 executed results: 71 Python regressions and five Swift suites pass. The native source backend passed the seven26.9.0 non-dispatch operations including ten reads in the user-authorized self-chat; no messages/files sent. That live run did not use frozen CLI broker IPC. Fresh app build, strictsignature, finalZIP --verify andCLIversion0.1.3 smoke passed. ZIP symlink traversal/duplicates and release buildcounter4 are covered.

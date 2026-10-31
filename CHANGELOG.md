# Changelog

## 0.1.2 — 2026-10-31
- Replaced programmatic app copy with Finder drag/Replace installation guidance and a user Applications folder button (#7).
- Added exact KakaoTalk 26.9.0 support for the seven company-tested non-dispatch operations (#8).
- Added bounded AX window-list recovery and a distinct WINDOWS_UNAVAILABLE diagnosis without navigation/dispatch retries (#9).
- Added explicit fixed signing-identity configuration and actual signature metadata; stable-certificate TCC retention remains pending company validation (#10).

## 0.1.1 — 2026-10-27
- Fixed signed resource filename normalization by using ASCII bundle paths (#1).
- Fixed installer links to use a matching build in ~/Applications; repair only stale app translocation links and show broker identity diagnostics (#2).
- Added repeatable ZIP packaging, extraction/signature verification and an external final SHA-256 sidecar (#3).
- Documented exact primary search titles including emoji; duplicate titles select the most recent exact match (#4).
- Added operation-scoped KakaoTalk 26.8.0 support based on company test results; file selection and dispatch remain unverified for that version (#5).
- Included prior local search, focus, composer and file selection fixes with regression tests.

## 0.1.0 — 2026-10-17
- Added agent-neutral Click CLI and native macOS accessibility backend.
- Added Finder-launchable setup/diagnostics app and shared Codex/Claude Code skill.
- Added explicit room/draft guards, request journal and process serialization.
- Added real-app E2E tests that never transmit; native permission-dependent results are recorded separately from unit checks.

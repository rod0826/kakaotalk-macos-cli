# KakaoTalk CLI 0.1.0

## Objective and contract
A macOS arm64 CLI shared by Codex and Claude Code, plus a Finder-launchable installation/diagnostics app. Initial target: `/Applications/KakaoTalk.app`, bundle `com.kakao.KakaoTalkMac`, version 26.5.0. KakaoTalk is proprietary; this is a CLI-Anything style native accessibility harness, not a source-derived official integration.

## Scope
`doctor`, `chat search/open/current/read`, `message draft/clear/send`, `file dialog/cancel/send`, `session status`, default REPL; global `--json`, `--dry-run`. Explicit room names for mutations; ambiguous rooms fail closed. Sending requires matching `--confirm-room` and a unique `--request-id`. No automatic resend after an uncertain result. App installs CLI and common skill for both agents on user action. No daemon, private API, database access, login extraction, or network service.

## Architecture and order
Swift ApplicationServices/AppKit backend → Click harness → AppKit installer → frozen Python distribution → agent skills. JSON over a same-user mode-0600 Unix socket to the dedicated AppKit app, no shell interpolation. CLI launches the app through LaunchServices to keep TCC attribution independent of Codex/Claude/Terminal. Each request carries a 20-second absolute expiry and expected backend hash/bundle path; disconnected and expired requests are rejected before key dispatch. AX handles are resolved afresh each process. Global process lock serializes UI operations; SQLite journal records hashes and send state, not content. Native backend rechecks room immediately before dispatch.

## Commands
Build: `.venv/bin/python scripts/build.py`
Tests: `.venv/bin/python -m pytest agent-harness/cli_anything/kakaotalk/tests/test_core.py -v`
Live tests: `CLI_ANYTHING_FORCE_INSTALLED=1 .venv/bin/python -m pytest agent-harness/cli_anything/kakaotalk/tests/test_full_e2e.py -v`

## Style
Python snake_case, Swift lowerCamelCase. Success `{ "ok": true, "data": {...} }`; failure `{ "ok": false, "error": { "code": "...", "message": "..." } }`. Unknown send outcome is not success. No chat contents in persistent journal.

## Verification and boundaries
Unit tests for validation, dry-run, wrong room, duplicate request, concurrent claims, interrupted dispatch and JSON errors. Real native backend and installed CLI for doctor, search/open, draft round-trip and file chooser round-trip. No actual message or file transmission without a named recipient and explicit authorization. Permission granting remains the user's macOS action. Preserve unrelated workspace files.

## Distribution limits
Local ad-hoc signature, no Apple notarization. Apple Silicon build for this laptop. Requires logged-in/unlocked GUI session; may activate KakaoTalk. UI changes can break compatibility. No delivery/read-receipt guarantee, whole-history extraction or headless guarantee. Preview/render export is not applicable to this messaging harness.

# Verification — 2026-10-17 (Asia/Seoul)

## Executed and passed
- Swift AppKit/AXUIElement app and frozen Python 3.12 CLI built for Apple Silicon/macOS 14+.
- Local signature: `codesign --verify --deep --strict` passed. Apple Developer ID signing/notarization were not performed.
- Real installer/diagnostics app opened and visually inspected with Codex Computer Use.
- Real frozen installed CLI, with `CLI_ANYTHING_FORCE_INSTALLED=1`: **2 E2E tests passed in 14.90 seconds**. Verified real KakaoTalk 26.5.0, running state, Accessibility permission, search, exact room opening, synthetic draft write/read/restore, actual file chooser open/cancel. No message or file transmission.
- Explicit CLI open → read also passed: 5 loaded rows and 15 text parts detected; no chat body printed or saved.
- **26 unit tests passed**: validation, wrong room, no-action dry-run, duplicate/conflicting/pending requests, concurrent claims, uncertain outcome, file validation, byte limits, old broker rejection and equivalent Korean Unicode paths.
- Real local broker rejected expired, old-build and missing-confirmation send packets before AX dispatch.
- Frozen CLI runs from `/tmp` without the project/Python environment; help, JSON dry-run, wrong-recipient refusal and native malformed requests were checked.
- Common SKILL.md format validation passed. Build dependency audit found no known vulnerabilities in the pinned build dependency set after updating the development-only pytest dependency. This is not a guarantee against all vulnerabilities; bundled Python and macOS frameworks were not covered by that package audit.

The actual test host was macOS 26.6.2 on arm64; macOS 14 is the compilation/deployment minimum, not an independently tested OS version.

## Fixed during verification
TCC logs proved that direct terminal children were attributed to the parent agent. Production requests now go to a same-user mode-0600 Unix socket in the dedicated app. ChatGPT/Terminal-wide Accessibility permission is not required. TCC also retained old ad-hoc code requirements after rebuilds; app-specific reset and the user's manual reapproval restored permission.

Independent review corrections: fixed per-user native UI lock independent of state-dir; full canonical file URL + SHA256 before file dispatch; exact header and focused-room identity; actual focus verification before Return; bounded request expiry and disconnected-client checks; broker build/path handshake. Korean path normalization is handled in the Python response verifier.

An early E2E run passed search but expired during room opening after 41.41 seconds. Repeated full-tree scans were replaced by early-exit lookups and table/message-subtree pruning. The same two-test workflow subsequently completed in 14.90 seconds, with the draft/file steps also passing.

## Not verified / limits
- No real message or file was sent. Dispatch remains experimental; delivery/read receipts are not guaranteed and unknown outcomes are never retried automatically.
- File-send additionally requires the chooser to expose the full selected file URL; unavailable path verification fails closed. Additional Kakao confirmation windows are not guessed/clicked.
- Native app-folder copy and global skill symlink installation are provided for the user to invoke; no persistent user installation was performed by the agent.
- No Intel build, Apple notarization, cold-Mac test, whole-history export, monitoring or headless guarantee.
- Other manual/third-party GUI manipulation is outside this CLI's process lock; do not drive the same chat simultaneously.

## Public evidence policy
Raw local logs, user paths, room names and runtime journals are excluded from this repository. This document is a sanitized summary of local test results, not a cold-Mac certification. The public export is additionally checked with the unit suite and a fresh output-directory build. Actual message/file transmission remains unverified.

## Source publication check
The sanitized export passed all 26 unit tests and built a new arm64 app from an empty output directory. The new output passed strict signature verification. It was not launched or used to change existing Accessibility permissions. The separately supplied company-test app remains the original verified build.

# Verification — 0.1.2 (2026-10-31, Asia/Seoul)

- Python core/signing/packaging: **49 passed** (31 core + 18 script tests).
- All four Swift suites passed: composer/path identity, installation, version/operation policy, and window availability. Full native build passed.
- Version 26.9.0 was added only for the seven company-reported non-dispatch operations. Unknown future versions and untested dispatch remain blocked by default.
- Window tests cover transient empty snapshots, bounded failure, mismatched/duplicate room windows and expired requests. Shared AX window availability now gates room access, current state and search navigation. These are offline regression tests; real other-Space recovery remains to be tested on the company desktop.
- Fresh app and frozen CLI built. Computer Use confirmed the setup window shows 0.1.2, the Finder installation/update controls and complete guidance without clipping. The permission button from the non-installed development path produced the intended refusal alert without requesting Accessibility permission. Existing user app/links/permissions were not replaced.
- An initial inside-out signing build failed because copying PyInstaller output expanded framework symlinks. A regression fixture reproduced the missing preservation behavior, the copy now preserves symlinks, and a fresh build passed strict signing verification.
- No actual messages or files were sent, and no TCC permissions, keychain entries, certificates, or security attributes were changed.

## Signing limitation

Read-only `security find-identity -v -p codesigning`, including outside the agent sandbox, found **0 valid identities**. This company ZIP remains **ad-hoc and not notarized**. Explicit identity selection, missing/ambiguous identity rejection without fallback, and actual signing metadata are implemented and tested. A build using a real approved certificate and TCC permission retention between two such builds are **not verified**. Issue #10 is partially addressed and needs an approved identity plus company-Mac validation.

## Packaging and remaining company checks

The final ZIP is verified by extracting with macOS ditto and running `codesign --verify --deep --strict` on the extracted app. The adjacent `.zip.sha256` contains the final archive digest. BUILD.json includes actual signature metadata and executable hashes; the archive never embeds its own final hash. Finder first-install/Replace, Gatekeeper, existing-link repair and other-Space behavior still require company-side retesting. The 0.1.2 guide describes these checks.

## Earlier records

The records below are historical and retain their own dates, test counts and limitations.

# Verification — 0.1.1 (2026-10-27, Asia/Seoul)

## Current patch validation

- Python core and packaging regressions: **36 passed** (30 core + 6 packaging).
- Swift composer/path-field identity, installation filesystem regressions, and version/operation policy suites: all passed.
- Fresh Apple Silicon/macOS 14 minimum app build and frozen CLI help smoke check: passed. The new app was not installed over the already authorized development app.
- `codesign --verify --deep --strict` passed before ZIP creation and after actual `/usr/bin/ditto -x -k` extraction of the final ZIP. Every signed bundle path is ASCII.
- Final archive hash is emitted in its external `.zip.sha256` sidecar after extraction verification. No current archive hash is embedded inside the archive. `BUILD.json` contains the native/CLI executable hashes.
- Independent review checked stable installation links, preservation of existing files, version restrictions, broker identity checks and packaging. No required findings remained.

## Remaining company checks

Finder/Archive Utility extraction, first launch under company Gatekeeper policy, Accessibility approval and actual company-Mac UI flows must be retested with 0.1.1. The local packaging check used ditto; it is not a claim that Finder was tested. No new real message or attachment was sent for this patch. The standalone native doctor smoke test ran inside the agent sandbox and is not evidence of actual GUI permission/running state.

[Issue #5](https://github.com/rod0826/kakaotalk-macos-cli/issues/5) reports seven non-dispatch operations on KakaoTalk 26.8.0. Only those operations are enabled by default for that version; file selection and message/file dispatch remain unverified. See [version support](docs/version-support.md).

Prior local 26.5.0 work verified file selection/cancel and one explicitly authorized file transmission using CLI selection plus Computer Use final confirmation, followed by sender-side attachment inspection. That observation does not imply delivery/read receipts or native handling of the final confirmation. Prior search/focus/composer/file-picker corrections and regression tests are included in this patch. The native dispatch result remains unknown until separately inspected.

## Historical 0.1.0 evidence

The dated record below describes the initial export only, not the current patch or current company ZIP. Its test counts and non-dispatch scope must not be interpreted as current aggregate results.

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

# Backend analysis and adaptation

Target artifact: `/Applications/KakaoTalk.app` / `com.kakao.KakaoTalkMac`, observed 26.5.0. No app source code is available. No `.sdef`, `OSAScriptingDefinition` or `NSAppleScriptEnabled` was found. URL schemes are launch/deep-link interfaces, not a validated full control surface.

Native data model: AXApplication → windows/Main Window → search field/table/rows; chat window → message table and composer. Real backend is the installed GUI through AXUIElement; no fake rendering, replacement messenger, private API, or database extraction. Project/export rendering and undo of sent messages are inapplicable. Local SQLite records send intents instead of storing conversation session content.

Preliminary Computer Use observations confirmed search input, own-room opening, draft set/clear, loaded message text, file picker open/cancel. These observations are not native CLI E2E proof. `VERIFICATION.md` distinguishes CLI results.

Explicit deviation from upstream's open-source-only Build input requirement: user authorized a native proprietary app adapter after a feasibility inspection. The package preserves namespace layout, Click commands, JSON, one-shot/REPL, packaged/canonical SKILL.md and real-backend tests, without claiming source-derived coverage or full upstream certification.

Native terminal children were observed by TCC as attributed to their parent agent. The production CLI therefore uses a same-user Unix socket to the LaunchServices-launched app. Logs also proved stale ad-hoc cdhash requirements after rebuilds; app-specific tccutil reset + manual user reapproval restored trust. Rebuilding after permission grant may require reapproval; do not ask users to grant the whole agent or disable macOS security.

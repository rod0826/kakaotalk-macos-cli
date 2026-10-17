import AppKit
import ApplicationServices
import Darwin
import CryptoKit

struct Failure: Error {
    let code: String
    let message: String
    init(_ code: String, _ message: String) { self.code = code; self.message = message }
}

let kakaoID = "com.kakao.KakaoTalkMac"
let testedVersion = "26.5.0"

func attribute(_ element: AXUIElement, _ key: String) -> CFTypeRef? {
    var result: CFTypeRef?
    guard AXUIElementCopyAttributeValue(element, key as CFString, &result) == .success else { return nil }
    return result
}
func string(_ element: AXUIElement, _ key: String) -> String {
    return attribute(element, key) as? String ?? ""
}
func children(_ element: AXUIElement) -> [AXUIElement] {
    return attribute(element, kAXChildrenAttribute) as? [AXUIElement] ?? []
}
func nodes(_ root: AXUIElement, depth: Int = 0) -> [AXUIElement] {
    if depth > 16 { return [] }
    return [root] + children(root).flatMap { nodes($0, depth: depth + 1) }
}
func firstNode(_ root: AXUIElement, skipping: Set<String> = [], depth: Int = 0,
               where matches: (AXUIElement) -> Bool) -> AXUIElement? {
    if depth > 16 { return nil }
    if matches(root) { return root }
    if skipping.contains(string(root, kAXRoleAttribute)) { return nil }
    for child in children(root) {
        if let found = firstNode(child, skipping: skipping, depth: depth + 1, where: matches) { return found }
    }
    return nil
}
func label(_ element: AXUIElement) -> String {
    for key in [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute, kAXValueAttribute] {
        let text = string(element, key)
        if !text.isEmpty { return text }
    }
    return ""
}
func set(_ element: AXUIElement, _ value: String) throws {
    guard AXUIElementSetAttributeValue(element, kAXValueAttribute as CFString, value as CFString) == .success else {
        throw Failure("AX_SET_FAILED", "입력창 값을 변경할 수 없습니다.")
    }
}
func press(_ element: AXUIElement) throws {
    guard AXUIElementPerformAction(element, kAXPressAction as CFString) == .success else {
        throw Failure("AX_ACTION_FAILED", "요소를 누를 수 없습니다.")
    }
}
func waitFor<T>(_ predicate: () -> T?) throws -> T {
    let deadline = Date().addingTimeInterval(5)
    repeat {
        if let result = predicate() { return result }
        RunLoop.current.run(until: Date().addingTimeInterval(0.12))
    } while Date() < deadline
    throw Failure("UI_TIMEOUT", "화면 확인 시간이 초과되었습니다. 전송 명령은 자동 재실행하지 마세요.")
}

final class KakaoAX {
    let app: NSRunningApplication
    let root: AXUIElement
    let expiresAt: Double
    let stillConnected: () -> Bool
    init(allowUntested: Bool = false, expiresAt: Double = Date().timeIntervalSince1970 + 20,
         stillConnected: @escaping () -> Bool = { true }) throws {
        guard AXIsProcessTrusted() else {
            throw Failure("ACCESSIBILITY_REQUIRED", "KakaoTalk CLI.app에 손쉬운 사용 권한을 허용한 뒤 다시 검사하세요.")
        }
        guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: kakaoID).first else {
            throw Failure("APP_NOT_RUNNING", "카카오톡을 실행하고 로그인하세요.")
        }
        let version = app.bundleURL.flatMap { Bundle(url: $0)?.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String } ?? "unknown"
        guard version == testedVersion || allowUntested else {
            throw Failure("UNTESTED_VERSION", "검증 대상은 \(testedVersion)이며 현재 버전은 \(version)입니다. 호환성 확인 후 --allow-untested-version을 사용하세요.")
        }
        self.app = app
        self.expiresAt = expiresAt
        self.stillConnected = stillConnected
        root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 2)
    }
    func windows() -> [AXUIElement] { attribute(root, kAXWindowsAttribute) as? [AXUIElement] ?? [] }
    func focusedWindow() -> AXUIElement? {
        guard let value = attribute(root, kAXFocusedWindowAttribute), CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        return unsafeBitCast(value, to: AXUIElement.self)
    }
    func focusedElement() -> AXUIElement? {
        guard let value = attribute(root, kAXFocusedUIElementAttribute), CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        return unsafeBitCast(value, to: AXUIElement.self)
    }
    func requireFocus(_ element: AXUIElement) throws {
        guard app.isActive, let actual = focusedElement(), CFEqual(actual, element) else {
            throw Failure("FOCUS_MISMATCH", "예상 입력 요소가 실제 포커스와 다릅니다. 키를 누르지 않았습니다.")
        }
    }
    func composer(_ window: AXUIElement) -> AXUIElement? {
        firstNode(window, skipping: [kAXTableRole]) { element in string(element, kAXRoleAttribute) == kAXTextAreaRole &&
            [kAXDescriptionAttribute, kAXTitleAttribute, kAXPlaceholderValueAttribute].contains { key in string(element, key).contains("메시지 입력") } }
    }
    func roomWindow(_ name: String) throws -> AXUIElement {
        let matches = windows().filter { string($0, kAXTitleAttribute) == name && composer($0) != nil }
        guard matches.count == 1 else { throw Failure("ROOM_NOT_OPEN", "이름이 정확히 일치하는 채팅창 하나를 열어야 합니다: \(name)") }
        return matches[0]
    }
    func key(_ code: CGKeyCode, flags: CGEventFlags = []) throws {
        try requireFreshRequest()
        guard let down = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: true),
              let up = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: false) else {
            throw Failure("KEY_EVENT_FAILED", "키 입력을 생성할 수 없습니다.")
        }
        down.flags = flags; up.flags = flags
        down.postToPid(app.processIdentifier); up.postToPid(app.processIdentifier)
    }
    func requireFreshRequest() throws {
        guard Date().timeIntervalSince1970 < expiresAt else { throw Failure("REQUEST_EXPIRED", "요청이 만료돼 실행하지 않았습니다.") }
        guard stillConnected() else { throw Failure("CLIENT_DISCONNECTED", "요청 연결이 종료돼 실행하지 않았습니다.") }
    }
    func activate(_ window: AXUIElement? = nil) throws {
        try requireFreshRequest()
        if !app.isActive {
            guard let url = app.bundleURL else { throw Failure("APP_PATH_MISSING", "카카오톡 앱 경로 없음") }
            let configuration = NSWorkspace.OpenConfiguration()
            configuration.activates = true
            NSWorkspace.shared.openApplication(at: url, configuration: configuration)
            let _: Bool = try waitFor { self.app.isActive ? true : nil }
        }
        if let window {
            guard AXUIElementPerformAction(window, kAXRaiseAction as CFString) == .success else {
                throw Failure("RAISE_FAILED", "대상 창 활성화 실패")
            }
            let _: Bool = try waitFor {
                guard self.app.isActive, let actual = self.focusedWindow(), CFEqual(actual, window) else { return nil }
                return true
            }
        }
    }
    func mainWindow() throws -> AXUIElement {
        try activate()
        try key(19, flags: .maskCommand) // Cmd+2: chats, observed in KakaoTalk
        return try waitFor { self.windows().first { string($0, kAXIdentifierAttribute) == "Main Window" } }
    }
    func searchTable(_ query: String) throws -> (AXUIElement, AXUIElement) {
        let main = try mainWindow()
        guard let field = firstNode(main, skipping: [kAXTableRole], where: {
            string($0, kAXRoleAttribute) == kAXTextFieldRole &&
            (string($0, kAXPlaceholderValueAttribute).contains("채팅방") || label($0).contains("검색"))
        }) else { throw Failure("SEARCH_NOT_FOUND", "채팅방 검색창을 찾을 수 없습니다.") }
        try set(field, query)
        RunLoop.current.run(until: Date().addingTimeInterval(0.45))
        guard let table = firstNode(main, where: { string($0, kAXRoleAttribute) == kAXTableRole }) else {
            throw Failure("SEARCH_TABLE_MISSING", "채팅방 검색 결과 표 없음")
        }
        return (main, table)
    }
    func headerNodes(_ row: AXUIElement) -> [AXUIElement] {
        let role = string(row, kAXRoleAttribute)
        if [kAXScrollAreaRole, kAXButtonRole, kAXImageRole].contains(role) { return [] }
        return [row] + children(row).flatMap { headerNodes($0) }
    }
    func search(_ query: String) throws -> [String: Any] {
        let (_, table) = try searchTable(query)
        let rows = children(table).filter { string($0, kAXRoleAttribute) == kAXRowRole }
        let items = rows.map { row -> [String: Any] in
            let texts = headerNodes(row).map { label($0) }.filter { !$0.isEmpty }
            return ["label": Array(NSOrderedSet(array: texts))]
        }
        return ["query": query, "results": items, "scope": "loaded_search_rows", "count": items.count]
    }
    func openRoom(_ name: String) throws -> [String: Any] {
        // Resolve by exact title from search row's primary text, not substring.
        let (main, table) = try searchTable(name)
        let rows = children(table).filter { string($0, kAXRoleAttribute) == kAXRowRole }
        let candidates = rows.filter { row in
            headerNodes(row).contains { element in
                let role = string(element, kAXRoleAttribute)
                guard role != kAXTextAreaRole && role != kAXButtonRole else { return false }
                let value = label(element)
                return value == name
            }
        }
        guard candidates.count == 1 else {
            throw Failure("AMBIGUOUS_ROOM", "검색 결과에서 고유한 채팅방을 판별할 수 없습니다(후보 \(candidates.count)개). 채팅방 이름을 고유하게 설정하세요.")
        }
        let row = candidates[0]
        // Native AXOpen if supported; otherwise selected row + Return.
        var actions: CFArray?
        AXUIElementCopyActionNames(row, &actions)
        if (actions as? [String] ?? []).contains("AXOpen") {
            guard AXUIElementPerformAction(row, "AXOpen" as CFString) == .success else { throw Failure("OPEN_FAILED", "채팅방 열기 실패") }
        } else {
            guard AXUIElementSetAttributeValue(row, kAXSelectedAttribute as CFString, kCFBooleanTrue) == .success else {
                throw Failure("SELECT_FAILED", "검색 결과 행을 선택할 수 없습니다.")
            }
            try activate(main)
            guard AXUIElementSetAttributeValue(table, kAXFocusedAttribute as CFString, kCFBooleanTrue) == .success,
                  (attribute(row, kAXSelectedAttribute) as? Bool) == true else {
                throw Failure("SELECT_FOCUS_FAILED", "선택한 결과 목록의 포커스를 확인할 수 없습니다.")
            }
            try requireFocus(table)
            try key(36)
        }
        let window: AXUIElement = try waitFor {
            guard let focused = self.focusedWindow(), string(focused, kAXTitleAttribute) == name,
                  self.composer(focused) != nil else { return nil }
            return focused
        }
        try activate(window)
        return ["room": name, "opened": true]
    }
    func current(_ name: String?) throws -> [String: Any] {
        let window: AXUIElement
        if let name { window = try roomWindow(name) }
        else if let focused = focusedWindow(), composer(focused) != nil { window = focused }
        else { throw Failure("NO_CHAT_WINDOW", "활성 채팅창이 없습니다.") }
        guard let input = composer(window) else { throw Failure("COMPOSER_NOT_FOUND", "메시지 입력창 없음") }
        return ["room": string(window, kAXTitleAttribute), "draft": string(input, kAXValueAttribute)]
    }
    func draft(_ name: String, _ text: String, expected: String?) throws -> [String: Any] {
        let window = try roomWindow(name)
        guard let input = composer(window) else { throw Failure("COMPOSER_NOT_FOUND", "메시지 입력창 없음") }
        let previous = string(input, kAXValueAttribute)
        if let expected {
            guard previous == expected else { throw Failure("DRAFT_CHANGED", "현재 초안이 예상 값과 다릅니다. 덮어쓰지 않았습니다.") }
        } else if !previous.isEmpty && previous != text {
            throw Failure("DRAFT_EXISTS", "기존 초안이 있습니다. --expected-text로 확인해야 변경할 수 있습니다.")
        }
        try set(input, text)
        guard string(input, kAXValueAttribute) == text else { throw Failure("DRAFT_VERIFY_FAILED", "초안 입력 결과 확인 실패") }
        return ["room": name, "draft": text, "sent": false]
    }
    func read(_ name: String, limit: Int) throws -> [String: Any] {
        let window = try roomWindow(name)
        guard let table = firstNode(window, where: { string($0, kAXRoleAttribute) == kAXTableRole }) else {
            throw Failure("MESSAGES_NOT_FOUND", "대화 목록을 찾을 수 없습니다.")
        }
        let rows = children(table).filter { string($0, kAXRoleAttribute) == kAXRowRole }
        let messages = rows.suffix(limit).map { row -> [String: Any] in
            let content = nodes(row).filter { [kAXTextAreaRole, kAXStaticTextRole].contains(string($0, kAXRoleAttribute)) }
                .map { ["text": label($0), "help": string($0, kAXHelpAttribute)] }
            return ["parts": content]
        }
        return ["room": name, "messages": messages, "scope": "currently_loaded_rows", "complete_history": false]
    }
    func fileDialog(_ name: String) throws -> [String: Any] {
        let window = try roomWindow(name)
        guard let button = firstNode(window, skipping: [kAXTableRole], where: { string($0, kAXRoleAttribute) == kAXButtonRole && label($0).contains("파일전송") }) else {
            throw Failure("FILE_BUTTON_NOT_FOUND", "파일전송 버튼 없음")
        }
        try activate(window); try press(button)
        let _: AXUIElement = try waitFor { firstNode(window, skipping: [kAXTableRole]) { string($0, kAXIdentifierAttribute) == "open-panel" } }
        return ["room": name, "file_dialog_open": true, "sent": false]
    }
    func cancelFile(_ name: String) throws -> [String: Any] {
        let window = try roomWindow(name)
        guard let cancel = firstNode(window, skipping: [kAXTableRole, kAXBrowserRole, kAXOutlineRole], where: { string($0, kAXIdentifierAttribute) == "CancelButton" }) else {
            throw Failure("FILE_DIALOG_NOT_OPEN", "파일 선택창이 없습니다.")
        }
        try press(cancel)
        return ["room": name, "file_dialog_open": false, "sent": false]
    }
    func send(_ name: String, text: String) throws -> [String: Any] {
        let window = try roomWindow(name)
        guard let input = composer(window), string(input, kAXValueAttribute) == text else {
            throw Failure("DRAFT_MISMATCH", "전송할 내용과 현재 입력창 내용이 일치하지 않습니다. 먼저 draft를 실행하세요.")
        }
        try activate(window)
        guard let focused = focusedWindow(), CFEqual(focused, window), app.isActive else {
            throw Failure("FOCUS_MISMATCH", "대상 채팅창 활성화 확인 실패")
        }
        guard AXUIElementSetAttributeValue(input, kAXFocusedAttribute as CFString, kCFBooleanTrue) == .success else {
            throw Failure("FOCUS_FAILED", "입력창 포커스 실패")
        }
        try requireFocus(input)
        try requireFreshRequest()
        try key(36)
        // Empty composer alone cannot prove server delivery.
        RunLoop.current.run(until: Date().addingTimeInterval(0.3))
        return ["room": name, "dispatch_attempted": true, "delivery_verified": false,
                "composer_cleared": string(input, kAXValueAttribute).isEmpty, "status": "unknown"]
    }
    func sendFile(_ name: String, path: String, digest: String) throws -> [String: Any] {
        guard FileManager.default.fileExists(atPath: path), !path.contains("\n"), !path.contains("\0") else {
            throw Failure("INVALID_FILE", "유효한 파일 경로가 필요합니다.")
        }
        _ = try fileDialog(name)
        let window = try roomWindow(name)
        try key(5, flags: [.maskCommand, .maskShift]) // standard Open panel: Go to Folder
        let field: AXUIElement = try waitFor {
            firstNode(window, skipping: [kAXTableRole]) { string($0, kAXRoleAttribute) == kAXComboBoxRole }
        }
        try set(field, path)
        guard AXUIElementSetAttributeValue(field, kAXFocusedAttribute as CFString, kCFBooleanTrue) == .success,
              string(field, kAXValueAttribute) == path else {
            throw Failure("FILE_PATH_FOCUS_FAILED", "파일 경로 입력창 검증 실패")
        }
        try requireFocus(field)
        try key(36)
        let canonical = URL(fileURLWithPath: path).resolvingSymlinksInPath().standardizedFileURL
        let panel: AXUIElement = try waitFor {
            guard let panel = firstNode(window, skipping: [kAXTableRole], where: { string($0, kAXIdentifierAttribute) == "open-panel" }) else { return nil }
            let selected = nodes(panel).filter { (attribute($0, kAXSelectedAttribute) as? Bool) == true }
            let matches = selected.contains { item in
                guard let url = attribute(item, kAXURLAttribute) as? URL, url.isFileURL else { return false }
                return url.resolvingSymlinksInPath().standardizedFileURL == canonical
            }
            return matches ? panel : nil
        }
        let currentDigest = SHA256.hash(data: try Data(contentsOf: canonical)).map { String(format: "%02x", $0) }.joined()
        guard currentDigest == digest else { throw Failure("FILE_CHANGED", "선택 중 파일 내용이 바뀌었습니다. 전송하지 않았습니다.") }
        guard string(window, kAXTitleAttribute) == name,
              let open = nodes(panel).first(where: { string($0, kAXIdentifierAttribute) == "OKButton" }) else {
            throw Failure("FILE_TARGET_CHANGED", "파일 전송 대상 확인 실패")
        }
        try requireFreshRequest()
        try press(open)
        // Kakao may send directly or present another confirmation. Never guess-click it.
        return ["room": name, "dispatch_attempted": true, "delivery_verified": false,
                "status": "unknown", "note": "추가 확인창이 있으면 사용자가 확인해야 합니다."]
    }
}

func diagnostic() -> [String: Any] {
    let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: kakaoID)
    let version = url.flatMap { Bundle(url: $0)?.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String }
    return ["platform": "macOS", "architecture": "arm64", "accessibility_trusted": AXIsProcessTrusted(),
            "app_installed": url != nil, "app_path": url?.path ?? "", "app_version": version ?? "",
            "tested_app_version": testedVersion, "version_matches": version == testedVersion,
            "running": !NSRunningApplication.runningApplications(withBundleIdentifier: kakaoID).isEmpty,
            "backend": "native-AXUIElement", "background_supported": false]
}

func handle(_ request: [String: Any], stillConnected: @escaping () -> Bool = { true }) throws -> [String: Any] {
    guard let operation = request["operation"] as? String else { throw Failure("INVALID_REQUEST", "operation 필요") }
    if operation == "doctor" { return diagnostic() }
    // All invocations, including direct native calls, share one per-user UI lock.
    let directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/KakaoTalkCLI")
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
    let descriptor = Darwin.open(directory.appendingPathComponent("ui.lock").path, O_CREAT | O_RDWR | O_NOFOLLOW, 0o600)
    guard descriptor >= 0 else { throw Failure("LOCK_FAILED", "UI 잠금 파일을 열 수 없습니다.") }
    defer { Darwin.close(descriptor) }
    guard flock(descriptor, LOCK_EX | LOCK_NB) == 0 else { throw Failure("UI_BUSY", "다른 카카오톡 CLI 작업이 실행 중입니다.") }
    let backend = try KakaoAX(allowUntested: request["allow_untested"] as? Bool ?? false,
                             expiresAt: request["expires_at"] as? Double ?? Date().timeIntervalSince1970 + 20,
                             stillConnected: stillConnected)
    func room() throws -> String {
        guard let name = request["room"] as? String, !name.isEmpty else { throw Failure("INVALID_REQUEST", "room 필요") }
        return name
    }
    switch operation {
    case "search": return try backend.search(request["query"] as? String ?? "")
    case "open": return try backend.openRoom(room())
    case "current": return try backend.current(request["room"] as? String)
    case "draft": return try backend.draft(room(), request["text"] as? String ?? "", expected: request["expected_text"] as? String)
    case "read": return try backend.read(room(), limit: min(100, max(1, request["limit"] as? Int ?? 20)))
    case "file-dialog": return try backend.fileDialog(room())
    case "file-cancel": return try backend.cancelFile(room())
    case "send": return try backend.send(room(), text: request["text"] as? String ?? "")
    case "file-send": return try backend.sendFile(room(), path: request["path"] as? String ?? "", digest: request["file_digest"] as? String ?? "")
    default: throw Failure("UNKNOWN_OPERATION", "지원하지 않는 operation")
    }
}

import AppKit
import ApplicationServices

final class Installer: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    let status = NSTextField(wrappingLabelWithString: "")
    let details = NSTextField(wrappingLabelWithString: "")
    var broker: Broker?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        let menu = NSMenu()
        let item = NSMenuItem()
        menu.addItem(item)
        let submenu = NSMenu()
        submenu.addItem(withTitle: "KakaoTalk CLI 종료", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = submenu
        NSApp.mainMenu = menu

        window = NSWindow(contentRect: NSRect(x: 0,y: 0,width: 600,height: 530),
                          styleMask: [.titled,.closable,.miniaturizable], backing: .buffered, defer: false)
        window.title = "KakaoTalk CLI · 설치 및 진단"
        let stack = NSStackView()
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 18
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 30),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -30),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 30)])
        let title = NSTextField(labelWithString: "KakaoTalk CLI")
        title.font = .systemFont(ofSize: 29, weight: .bold)
        stack.addArrangedSubview(title)
        let subtitle = NSTextField(wrappingLabelWithString: "Codex와 Claude Code가 함께 사용하는 macOS 카카오톡 제어 도구")
        subtitle.font = .systemFont(ofSize: 14); stack.addArrangedSubview(subtitle)
        status.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        status.setAccessibilityIdentifier("diagnostic-status")
        stack.addArrangedSubview(status)
        for (title, action) in [
            ("1. 사용자 앱 폴더에 설치", #selector(installApp)),
            ("2. 손쉬운 사용 권한 설정 열기", #selector(permission)),
            ("3. CLI + Codex·Claude Code 스킬 설치", #selector(installTools)),
            ("상태 다시 검사", #selector(refresh)),
            ("사용 안내 열기", #selector(help))] {
            let button = NSButton(title: title, target: self, action: action)
            button.bezelStyle = .rounded; stack.addArrangedSubview(button)
        }
        details.font = .systemFont(ofSize: 12)
        details.textColor = .secondaryLabelColor
        details.stringValue = "처음 한 번 권한 설정이 필요합니다. 카카오톡 로그인과 잠금 해제된 데스크톱이 필요하며, 실행 중 카카오톡이 앞으로 나올 수 있습니다. 이 앱은 카카오의 공식 제품이 아닙니다."
        stack.addArrangedSubview(details)
        for view in [subtitle,status,details] {
            view.widthAnchor.constraint(equalToConstant: 535).isActive = true
        }
        do { broker = try Broker(); broker?.start() }
        catch { details.stringValue = (error as? Failure)?.message ?? error.localizedDescription }
        refresh()
        if !CommandLine.arguments.contains("--serve") {
            window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate()
        }
    }
    @objc func refresh() {
        let d = diagnostic()
        status.stringValue = "카카오톡: \(d["app_version"] as? String ?? "미설치")  ·  검증 대상: \(testedVersion)\n실행 상태: \((d["running"] as? Bool ?? false) ? "실행 중" : "종료됨")\n손쉬운 사용 권한: \(AXIsProcessTrusted() ? "허용됨" : "설정 필요")\nCLI 버전: 0.1.0 · Apple Silicon"
    }
    func alert(_ message: String, error: Bool = false) {
        let alert = NSAlert(); alert.messageText = error ? "작업을 완료하지 못했습니다" : "완료"
        alert.informativeText = message; alert.runModal()
    }
    @objc func permission() {
        // Permission is granted manually by the human in System Settings.
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
        details.stringValue = "시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용에서 이 앱을 추가하고 켜세요. 돌아온 뒤 ‘상태 다시 검사’를 누르세요."
    }
    @objc func installApp() {
        let source = Bundle.main.bundleURL
        let destination = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Applications/KakaoTalk CLI.app")
        if source.standardizedFileURL == destination.standardizedFileURL { alert("이미 사용자 앱 폴더에 설치되어 있습니다."); return }
        do {
            try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
            if FileManager.default.fileExists(atPath: destination.path) {
                throw Failure("INSTALL_EXISTS", "기존 KakaoTalk CLI.app이 있습니다. 기존 앱을 보관하거나 이동한 뒤 다시 설치하세요.")
            }
            try FileManager.default.copyItem(at: source, to: destination)
            broker?.stop()
            let launch = Process()
            launch.executableURL = URL(fileURLWithPath: "/usr/bin/open")
            launch.arguments = ["-n", destination.path]
            try launch.run()
            NSApp.terminate(nil)
        } catch { alert((error as? Failure)?.message ?? error.localizedDescription, error: true) }
    }
    func link(_ source: URL, _ destination: URL) throws {
        let fm = FileManager.default
        try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
        if let target = try? fm.destinationOfSymbolicLink(atPath: destination.path), target == source.path { return }
        if fm.fileExists(atPath: destination.path) || (try? fm.destinationOfSymbolicLink(atPath: destination.path)) != nil {
            throw Failure("INSTALL_EXISTS", "덮어쓰지 않았습니다. 기존 경로를 확인하세요: \(destination.path)")
        }
        try fm.createSymbolicLink(at: destination, withDestinationURL: source)
    }
    @objc func installTools() {
        guard let resources = Bundle.main.resourceURL else { return }
        let home = FileManager.default.homeDirectoryForCurrentUser
        do {
            let cli = resources.appendingPathComponent("cli/cli-anything-kakaotalk")
            guard FileManager.default.isExecutableFile(atPath: cli.path) else { throw Failure("CLI_MISSING", "CLI 실행 파일 없음") }
            let skill = resources.appendingPathComponent("skills/cli-anything-kakaotalk")
            // Preserve all existing user tools and skills; no shell profile edits.
            try link(cli, home.appendingPathComponent(".local/bin/cli-anything-kakaotalk"))
            try link(skill, home.appendingPathComponent(".codex/skills/cli-anything-kakaotalk"))
            try link(skill, home.appendingPathComponent(".claude/skills/cli-anything-kakaotalk"))
            alert("CLI와 양쪽 스킬을 설치했습니다.\n\n명령: ~/.local/bin/cli-anything-kakaotalk --json doctor\n\nCodex·Claude Code에서 새 대화를 시작하세요. PATH에 ~/.local/bin이 없어도 위 전체 경로를 사용할 수 있습니다.")
        } catch { alert((error as? Failure)?.message ?? error.localizedDescription, error: true) }
    }
    @objc func help() {
        if let url = Bundle.main.resourceURL?.appendingPathComponent("사용안내.html") { NSWorkspace.shared.open(url) }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { window.makeKeyAndOrderFront(nil) }
        return true
    }
}

func runInstaller() {
    let delegate = Installer()
    NSApplication.shared.delegate = delegate
    NSApplication.shared.run()
    withExtendedLifetime(delegate) {}
}

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

        window = NSWindow(contentRect: NSRect(x: 0,y: 0,width: 600,height: 700),
                          styleMask: [.titled,.closable,.miniaturizable], backing: .buffered, defer: false)
        window.title = "KakaoTalk CLI · 설치 및 진단"
        let stack = NSStackView()
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 12
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
            ("1. Finder로 설치·업데이트 안내", #selector(installApp)),
            ("사용자 앱 폴더를 Finder에서 보기", #selector(showInstallFolder)),
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
        if isAppTranslocated(Bundle.main.bundleURL) {
            details.stringValue = "AppTranslocation 임시 경로에서 실행 중입니다. 이 앱을 종료하고 압축 푼 앱을 Finder로 ~/Applications에 직접 드래그하세요. 이미 설치된 앱도 임시 실행되면 Finder로 다른 사용자 폴더로 옮겼다가 같은 위치로 되돌리세요. 보안 승인 안내가 나오면 회사 정책에 따라 승인하세요. 임시 경로 앱에는 권한을 부여하지 마세요."
        }
        if !CommandLine.arguments.contains("--serve") {
            window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate()
        }
    }
    @objc func refresh() {
        let d = diagnostic()
        status.stringValue = "카카오톡: \(d["app_version"] as? String ?? "미설치")  ·  검증 대상: \(supportedVersions.joined(separator: ", "))\n실행 상태: \((d["running"] as? Bool ?? false) ? "실행 중" : "종료됨")\n손쉬운 사용 권한: \(AXIsProcessTrusted() ? "허용됨" : "설정 필요")\nCLI 버전: \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "unknown") · Apple Silicon"
    }
    func alert(_ message: String, error: Bool = false) {
        let alert = NSAlert(); alert.messageText = error ? "작업을 완료하지 못했습니다" : "완료"
        alert.informativeText = message; alert.runModal()
    }
    @objc func permission() {
        let installed = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Applications/KakaoTalk CLI.app")
        guard !isAppTranslocated(Bundle.main.bundleURL),
              Bundle.main.bundleURL.standardizedFileURL == installed.standardizedFileURL else {
            alert("임시·다른 경로의 앱에는 권한을 요청하지 않았습니다. Finder로 앱을 ~/Applications에 직접 설치·교체한 뒤 그 위치의 앱을 열어 권한을 설정하세요.", error: true)
            return
        }
        // Permission is granted manually by the human in System Settings.
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
        details.stringValue = "시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용에서 이 앱을 추가하고 켜세요. 돌아온 뒤 ‘상태 다시 검사’를 누르세요."
    }
    @objc func showInstallFolder() {
        let directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Applications")
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            NSWorkspace.shared.open(directory)
        } catch { alert(error.localizedDescription, error: true) }
    }
    @objc func installApp() {
        showInstallFolder()
        alert("열린 사용자 앱 폴더(~/Applications)에 압축 푼 KakaoTalk CLI.app을 Finder로 직접 드래그하세요. 시스템 /Applications와 다릅니다.\n\n업데이트: 이전 제어 앱을 종료한 뒤 같은 위치의 앱을 Finder ‘대치’로 교체하세요. CLI·스킬 링크는 그대로 유지됩니다. 새 앱을 열고 서명 방식에 따라 손쉬운 사용 권한을 다시 확인하세요.\n\n이미 설치된 앱도 AppTranslocation으로 실행되면 종료 후 Finder로 다른 사용자 폴더로 옮겼다가 ~/Applications로 되돌리세요. 이 도구는 앱을 프로그램으로 복사하거나 보안 속성을 제거하지 않습니다.")
    }
    @objc func installTools() {
        let home = FileManager.default.homeDirectoryForCurrentUser
        do {
            let resources = try installedResources(currentBundle: Bundle.main.bundleURL, home: home)
            let cli = resources.appendingPathComponent("cli/cli-anything-kakaotalk")
            guard FileManager.default.isExecutableFile(atPath: cli.path) else { throw Failure("CLI_MISSING", "CLI 실행 파일 없음") }
            let skill = resources.appendingPathComponent("skills/cli-anything-kakaotalk")
            let links = [
                (cli, home.appendingPathComponent(".local/bin/cli-anything-kakaotalk")),
                (skill, home.appendingPathComponent(".codex/skills/cli-anything-kakaotalk")),
                (skill, home.appendingPathComponent(".claude/skills/cli-anything-kakaotalk"))]
            guard FileManager.default.fileExists(atPath: skill.appendingPathComponent("SKILL.md").path) else {
                throw Failure("SKILL_MISSING", "설치된 앱에 스킬 파일이 없습니다.")
            }
            // Preflight every destination before repairing any old links.
            for (source, destination) in links { try validateToolLink(source, destination) }
            for (source, destination) in links { try installToolLink(source, destination) }
            alert("CLI와 양쪽 스킬을 설치했습니다.\n\n명령: ~/.local/bin/cli-anything-kakaotalk --json doctor\n\nCodex·Claude Code에서 새 대화를 시작하세요. PATH에 ~/.local/bin이 없어도 위 전체 경로를 사용할 수 있습니다.")
        } catch { alert((error as? Failure)?.message ?? error.localizedDescription, error: true) }
    }
    @objc func help() {
        if let url = Bundle.main.resourceURL?.appendingPathComponent("usage-guide.html") { NSWorkspace.shared.open(url) }
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

import Foundation
import Darwin

struct InstallationError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}

func isAppTranslocated(_ url: URL) -> Bool {
    url.standardizedFileURL.pathComponents.contains("AppTranslocation")
}

func installedResources(currentBundle: URL, home: URL) throws -> URL {
    let installed = home.appendingPathComponent("Applications/KakaoTalk CLI.app").standardizedFileURL
    let resolved = installed.resolvingSymlinksInPath()
    guard resolved == installed, !isAppTranslocated(resolved),
          Bundle(url: installed)?.bundleIdentifier == "local.kakaotalk-cli",
          let current = try? Data(contentsOf: currentBundle.appendingPathComponent("Contents/MacOS/KakaoTalkCLI")),
          let target = try? Data(contentsOf: installed.appendingPathComponent("Contents/MacOS/KakaoTalkCLI")),
          current == target else {
        throw InstallationError("현재 빌드와 동일한 앱을 Finder로 ~/Applications/KakaoTalk CLI.app에 직접 드래그하세요. 업데이트는 이전 앱 종료 후 같은 위치의 앱을 Finder 대치로 교체하세요.")
    }
    return installed.appendingPathComponent("Contents/Resources")
}

private func replaceableTranslocationLink(_ target: String, source: URL) -> Bool {
    let url = URL(fileURLWithPath: target)
    guard target.hasPrefix("/"), isAppTranslocated(url) else { return false }
    // Repair only the three exact paths produced by this app's old installer.
    let suffixes = ["cli/cli-anything-kakaotalk", "skills/cli-anything-kakaotalk"]
    return suffixes.contains { suffix in
        let tail = "/KakaoTalk CLI.app/Contents/Resources/" + suffix
        return url.path.hasSuffix(tail) && source.path.hasSuffix(tail)
    }
}

func validateToolLink(_ source: URL, _ destination: URL) throws {
    let fm = FileManager.default
    if let target = try? fm.destinationOfSymbolicLink(atPath: destination.path) {
        if target == source.path || replaceableTranslocationLink(target, source: source) { return }
    } else if !fm.fileExists(atPath: destination.path) { return }
    throw InstallationError("덮어쓰지 않았습니다. 기존 경로를 확인하세요: \(destination.path)")
}

func installToolLink(_ source: URL, _ destination: URL) throws {
    let fm = FileManager.default
    try validateToolLink(source, destination)
    if (try? fm.destinationOfSymbolicLink(atPath: destination.path)) == source.path { return }
    try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
    let staged = destination.deletingLastPathComponent().appendingPathComponent(".kakao-link-" + UUID().uuidString)
    try fm.createSymbolicLink(at: staged, withDestinationURL: source)
    defer { try? fm.removeItem(at: staged) }
    try validateToolLink(source, destination)
    guard Darwin.rename(staged.path, destination.path) == 0 else {
        throw InstallationError("링크 교체 실패: \(destination.path)")
    }
}

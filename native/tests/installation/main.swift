import Foundation

func check(_ condition: Bool, _ message: String) {
    guard condition else { fatalError(message) }
}
let fm = FileManager.default
let root = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString)
try fm.createDirectory(at: root, withIntermediateDirectories: true)
defer { try? fm.removeItem(at: root) }
let source = root.appendingPathComponent("Applications/KakaoTalk CLI.app/Contents/Resources/cli/cli-anything-kakaotalk")
let link = root.appendingPathComponent("bin/cli-anything-kakaotalk")
try fm.createDirectory(at: source.deletingLastPathComponent(), withIntermediateDirectories: true)
try Data("cli".utf8).write(to: source)
try fm.createDirectory(at: link.deletingLastPathComponent(), withIntermediateDirectories: true)
let stale = "/private/var/folders/test/AppTranslocation/uuid/d/KakaoTalk CLI.app/Contents/Resources/cli/cli-anything-kakaotalk"
try fm.createSymbolicLink(atPath: link.path, withDestinationPath: stale)
try installToolLink(source, link)
check(try fm.destinationOfSymbolicLink(atPath: link.path) == source.path, "stale translocation link repaired")
try installToolLink(source, link)
try fm.removeItem(at: link)
try Data("user file".utf8).write(to: link)
do { try installToolLink(source, link); fatalError("must preserve real file") } catch {}
check(try String(contentsOf: link, encoding: .utf8) == "user file", "existing file preserved")
try fm.removeItem(at: link)
try fm.createSymbolicLink(atPath: link.path, withDestinationPath: "/some/AppTranslocation/Other.app/cli-anything-kakaotalk")
do { try installToolLink(source, link); fatalError("must preserve unrelated symlink") } catch {}
check(try fm.destinationOfSymbolicLink(atPath: link.path) == "/some/AppTranslocation/Other.app/cli-anything-kakaotalk", "unrelated symlink preserved")
check(isAppTranslocated(URL(fileURLWithPath: stale)), "recognize translocation component")
check(!isAppTranslocated(URL(fileURLWithPath: "/Applications/AppTranslocation-backup/KakaoTalk CLI.app")), "component match only")
let installed = root.appendingPathComponent("Applications/KakaoTalk CLI.app")
let temporary = root.appendingPathComponent("AppTranslocation/uuid/d/KakaoTalk CLI.app")
for bundle in [installed, temporary] {
    try fm.createDirectory(at: bundle.appendingPathComponent("Contents/MacOS"), withIntermediateDirectories: true)
    try Data("native".utf8).write(to: bundle.appendingPathComponent("Contents/MacOS/KakaoTalkCLI"))
    let info: [String: String] = ["CFBundleIdentifier": "local.kakaotalk-cli"]
    try PropertyListSerialization.data(fromPropertyList: info, format: .xml, options: 0).write(to: bundle.appendingPathComponent("Contents/Info.plist"))
}
check(try installedResources(currentBundle: temporary, home: root) == installed.appendingPathComponent("Contents/Resources"), "always links stable installed bundle")
try Data("other build".utf8).write(to: installed.appendingPathComponent("Contents/MacOS/KakaoTalkCLI"))
do { _ = try installedResources(currentBundle: temporary, home: root); fatalError("must reject different installed build") } catch {}
print("Installation regressions passed")

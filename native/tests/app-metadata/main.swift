import Foundation

func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
    guard condition() else { fatalError(message) }
}

let fm = FileManager.default
let directory = fm.temporaryDirectory.appendingPathComponent("kakao-app-metadata-" + UUID().uuidString)
defer { try? fm.removeItem(at: directory) }
let app = directory.appendingPathComponent("KakaoTalk.app")
let info = app.appendingPathComponent("Contents/Info.plist")
try fm.createDirectory(at: info.deletingLastPathComponent(), withIntermediateDirectories: true)
func writeInfo(_ values: [String: Any]) throws {
    let data = try PropertyListSerialization.data(fromPropertyList: values, format: .xml, options: 0)
    try data.write(to: info)
}
try writeInfo(["CFBundleIdentifier": "com.example.test", "CFBundleShortVersionString": "26.5.0"])
expect(readAppVersion(at: app) == "26.5.0", "Read original disk version")
// Read once through Bundle too: subsequent helper reads must never use its cache.
_ = Bundle(url: app)?.object(forInfoDictionaryKey: "CFBundleShortVersionString")
try writeInfo(["CFBundleIdentifier": "com.example.test", "CFBundleShortVersionString": "26.9.0"])
expect(readAppVersion(at: app) == "26.9.0", "Read replaced plist version without stale Bundle cache")
try writeInfo(["CFBundleShortVersionString": 269])
expect(readAppVersion(at: app) == nil, "Reject non-string version")
try writeInfo(["CFBundleShortVersionString": ""])
expect(readAppVersion(at: app) == nil, "Reject empty version")
try writeInfo(["CFBundleIdentifier": "com.example.test"])
expect(readAppVersion(at: app) == nil, "Missing version is unknown")
try Data("not a property list".utf8).write(to: info)
expect(readAppVersion(at: app) == nil, "Malformed plist is unknown")
try writeInfo(["CFBundleShortVersionString": "26.9.0"])
let launch = Date(timeIntervalSince1970: 1_700_000_000)
try fm.setAttributes([.modificationDate: launch.addingTimeInterval(-60)], ofItemAtPath: info.path)
expect(!appNeedsRestart(bundleURL: app, launchDate: launch), "Older disk metadata is not update evidence")
try fm.setAttributes([.modificationDate: launch], ofItemAtPath: info.path)
expect(!appNeedsRestart(bundleURL: app, launchDate: launch), "Equal timestamps are not newer")
try fm.setAttributes([.modificationDate: launch.addingTimeInterval(60)], ofItemAtPath: info.path)
expect(appNeedsRestart(bundleURL: app, launchDate: launch), "Metadata changed after process launch needs restart")
expect(!appNeedsRestart(bundleURL: app, launchDate: nil), "Absent launch date gives no update evidence")
let future = Date().addingTimeInterval(86_400)
try fm.setAttributes([.modificationDate: future], ofItemAtPath: info.path)
expect(appNeedsRestart(bundleURL: app, launchDate: Date()), "Future metadata date errs toward restart rather than allowing a possible old process")
try fm.removeItem(at: info)
expect(readAppVersion(at: app) == nil, "Missing plist is unknown")
expect(!appNeedsRestart(bundleURL: app, launchDate: launch), "Missing metadata gives no update evidence")
print("App metadata tests passed")

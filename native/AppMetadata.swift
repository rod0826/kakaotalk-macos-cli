import Foundation

/// Read the on-disk plist on every call. Bundle's cached Info.plist can retain
/// an older version when an updater replaces an app while the broker stays open.
func readAppVersion(at bundleURL: URL) -> String? {
    let info = bundleURL.appendingPathComponent("Contents/Info.plist")
    guard let data = try? Data(contentsOf: info, options: .uncached),
          let values = (try? PropertyListSerialization.propertyList(from: data, options: [], format: nil)) as? [String: Any],
          let version = values["CFBundleShortVersionString"] as? String,
          !version.isEmpty else { return nil }
    return version
}

/// A newer plist is evidence that the running process may predate an update.
/// False means no timestamp evidence, not proof that process and disk match:
/// updaters may preserve modification dates, and launch dates can be unavailable.
func appNeedsRestart(bundleURL: URL, launchDate: Date?) -> Bool {
    guard let launchDate,
          let attributes = try? FileManager.default.attributesOfItem(
            atPath: bundleURL.appendingPathComponent("Contents/Info.plist").path),
          let modified = attributes[.modificationDate] as? Date else { return false }
    // Future file dates also request a restart: clock skew must not silently
    // permit a potentially older running process.
    return modified > launchDate
}

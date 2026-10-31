import Foundation

func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
    guard condition() else { fatalError(message) }
}

let fullOperations = Set(["search", "open", "current", "draft", "read", "file-dialog", "file-cancel", "file-select", "send", "file-send"])
let companyOperations = Set(["search", "open", "current", "draft", "read", "file-dialog", "file-cancel"])
expect(Set(supportedOperations(version: "26.5.0")) == fullOperations, "26.5.0 must retain all supported operations")
expect(Set(supportedOperations(version: "26.8.0")) == companyOperations, "26.8.0 must allow only reported non-dispatch operations")
expect(Set(supportedOperations(version: "26.9.0")) == companyOperations, "26.9.0 must allow only reported non-dispatch operations")
for operation in companyOperations {
    expect(isOperationSupported(version: "26.9.0", operation: operation), "26.9.0 reported operation must be supported: \(operation)")
    expect(isOperationSupported(version: "26.8.0", operation: operation), "Company-tested operation must be supported: \(operation)")
}
for operation in ["file-select", "send", "file-send"] {
    expect(!isOperationSupported(version: "26.9.0", operation: operation), "26.9.0 untested operation must stay blocked: \(operation)")
    expect(!isOperationSupported(version: "26.8.0", operation: operation), "Untested operation must stay blocked: \(operation)")
}
for version in ["", "26.8", "26.8.1", "26.9.1", "27.0.0", "26.8.0-beta"] {
    expect(supportedOperations(version: version).isEmpty, "Unknown version must not inherit support: \(version)")
    expect(!isOperationSupported(version: version, operation: "search"), "Unknown versions must remain blocked")
    expect(isOperationSupported(version: version, operation: "doctor"), "Diagnostics must always be available")
}
expect(!isOperationSupported(version: "26.5.0", operation: "unknown"), "Unknown operations must never inherit version support")
expect(isOperationSupported(version: "26.8.0", operation: "doctor"), "Diagnostics must work on known versions")
print("Version policy tests passed")

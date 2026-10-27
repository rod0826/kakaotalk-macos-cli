let supportedVersions = ["26.5.0", "26.8.0"]

/// Operations validated against each exact KakaoTalk version. Diagnostics are
/// version independent and intentionally separate from this capability list.
func supportedOperations(version: String) -> [String] {
    let nonDispatchOperations = [
        "search", "open", "current", "draft", "read", "file-dialog", "file-cancel"
    ]
    switch version {
    case "26.5.0":
        return nonDispatchOperations + ["file-select", "send", "file-send"]
    case "26.8.0":
        return nonDispatchOperations
    default:
        return []
    }
}

func isOperationSupported(version: String, operation: String) -> Bool {
    operation == "doctor" || supportedOperations(version: version).contains(operation)
}

import AppKit
import ApplicationServices

if CommandLine.arguments.contains("--request") {
    do {
        let data = FileHandle.standardInput.readDataToEndOfFile()
        guard data.count <= 1_048_576,
              let request = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw Failure("INVALID_REQUEST", "JSON object required (max 1 MiB)")
        }
        let result = try handle(request)
        let encoded = try JSONSerialization.data(withJSONObject: ["ok": true, "data": result], options: [.sortedKeys])
        FileHandle.standardOutput.write(encoded)
    } catch {
        let failure = error as? Failure ?? Failure("BACKEND_ERROR", error.localizedDescription)
        let encoded = try! JSONSerialization.data(withJSONObject: ["ok": false, "error": ["code": failure.code, "message": failure.message]], options: [.sortedKeys])
        FileHandle.standardOutput.write(encoded)
        exit(1)
    }
} else {
    runInstaller()
}

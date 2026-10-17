import AppKit
import Darwin
import CryptoKit

let brokerBuild = (try? Data(contentsOf: Bundle.main.executableURL!)).map {
    SHA256.hash(data: $0).map { String(format: "%02x", $0) }.joined()
} ?? "unknown"

// Local same-user IPC keeps Accessibility attribution on the granted .app,
// rather than whichever terminal/agent happens to execute the Python CLI.
final class Broker {
    private var listener: Int32 = -1
    private let queue = DispatchQueue(label: "local.kakaotalk-cli.broker")
    private let path: String

    init() throws {
        _ = brokerBuild // capture running build before any later file replacement
        let directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/KakaoTalkCLI")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        path = directory.appendingPathComponent("control.sock").path
        guard path.utf8.count < MemoryLayout.size(ofValue: sockaddr_un().sun_path) else {
            throw Failure("SOCKET_PATH_TOO_LONG", "사용자 홈 경로가 너무 길어 로컬 소켓을 만들 수 없습니다.")
        }
        listener = Darwin.socket(AF_UNIX, SOCK_STREAM, 0)
        guard listener >= 0 else { throw Failure("SOCKET_FAILED", "로컬 제어 소켓 생성 실패") }
        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        address.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
        _ = withUnsafeMutableBytes(of: &address.sun_path) { buffer in
            path.withCString { source in memcpy(buffer.baseAddress!, source, strlen(source) + 1) }
        }
        // Refuse a live listener; remove only our own stale Unix socket.
        var existing = stat()
        if lstat(path, &existing) == 0 {
            guard existing.st_uid == getuid(), (existing.st_mode & S_IFMT) == S_IFSOCK else {
                Darwin.close(listener); throw Failure("SOCKET_PATH_CONFLICT", "소켓 경로에 다른 파일이 있습니다.")
            }
            let probe = Darwin.socket(AF_UNIX, SOCK_STREAM, 0)
            let active = withUnsafePointer(to: &address) { pointer in
                pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    Darwin.connect(probe, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) == 0
                }
            }
            Darwin.close(probe)
            guard !active else { Darwin.close(listener); throw Failure("BROKER_RUNNING", "제어 앱이 이미 실행 중입니다.") }
            unlink(path)
        }
        let result = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(listener, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard result == 0, chmod(path, 0o600) == 0, Darwin.listen(listener, 4) == 0 else {
            Darwin.close(listener); throw Failure("SOCKET_BIND_FAILED", "로컬 제어 소켓 준비 실패")
        }
    }

    func start() {
        queue.async { [self] in
            while listener >= 0 {
                let client = Darwin.accept(listener, nil, nil)
                if client < 0 { continue }
                DispatchQueue.global(qos: .userInitiated).async { [self] in
                    process(client)
                    Darwin.close(client)
                }
            }
        }
    }

    private func process(_ client: Int32) {
        var uid: uid_t = 0; var gid: gid_t = 0
        guard getpeereid(client, &uid, &gid) == 0, uid == getuid() else { return }
        var timeout = timeval(tv_sec: 10, tv_usec: 0)
        setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        var noSignal: Int32 = 1
        setsockopt(client, SOL_SOCKET, SO_NOSIGPIPE, &noSignal, socklen_t(MemoryLayout<Int32>.size))
        var data = Data(); var buffer = [UInt8](repeating: 0, count: 8192)
        while data.count <= 1_048_576 {
            let count = Darwin.read(client, &buffer, buffer.count)
            if count <= 0 { return }
            data.append(contentsOf: buffer.prefix(count))
            if data.contains(10) { break }
        }
        var response: [String: Any]
        do {
            guard data.count <= 1_048_576,
                  let request = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw Failure("INVALID_REQUEST", "JSON object required (max 1 MiB)")
            }
            response = DispatchQueue.main.sync {
                do {
                    guard request["expected_build"] as? String == brokerBuild,
                          request["expected_bundle"] as? String == Bundle.main.bundleURL.path else {
                        throw Failure("BROKER_BUILD_MISMATCH", "실행 중인 앱과 CLI 빌드/경로가 다릅니다. 이전 앱을 종료하고 현재 앱을 다시 여세요.")
                    }
                    guard let expiry = request["expires_at"] as? Double,
                          expiry > Date().timeIntervalSince1970,
                          expiry <= Date().timeIntervalSince1970 + 25 else {
                        throw Failure("REQUEST_EXPIRED", "만료됐거나 유효하지 않은 요청입니다.")
                    }
                    var peek: UInt8 = 0
                    let alive = Darwin.recv(client, &peek, 1, MSG_PEEK | MSG_DONTWAIT)
                    guard alive != 0 else { throw Failure("CLIENT_DISCONNECTED", "연결이 종료돼 요청을 실행하지 않았습니다.") }
                    if ["send", "file-send"].contains(request["operation"] as? String ?? "") {
                        guard let room = request["room"] as? String,
                              request["confirm_room"] as? String == room,
                              let intent = request["request_id"] as? String, !intent.isEmpty else {
                            throw Failure("DISPATCH_CONFIRMATION_REQUIRED", "전송에는 대상 확인과 요청 ID가 필요합니다.")
                        }
                    }
                    return ["ok": true, "data": try handle(request, stillConnected: {
                        var byte: UInt8 = 0
                        return Darwin.recv(client, &byte, 1, MSG_PEEK | MSG_DONTWAIT) != 0
                    })]
                }
                catch {
                    let error = error as? Failure ?? Failure("BACKEND_ERROR", error.localizedDescription)
                    return ["ok": false, "error": ["code": error.code, "message": error.message]]
                }
            }
        } catch {
            response = ["ok": false, "error": ["code": "INVALID_REQUEST", "message": "Invalid request JSON"]]
        }
        response["broker_build"] = brokerBuild
        response["broker_bundle"] = Bundle.main.bundleURL.path
        guard var output = try? JSONSerialization.data(withJSONObject: response, options: [.sortedKeys]) else { return }
        output.append(10)
        output.withUnsafeBytes { bytes in
            var offset = 0
            while offset < bytes.count {
                let count = Darwin.write(client, bytes.baseAddress!.advanced(by: offset), bytes.count - offset)
                if count <= 0 { break }
                offset += count
            }
        }
    }

    deinit {
        if listener >= 0 { Darwin.close(listener); unlink(path) }
    }
    func stop() {
        let descriptor = listener
        listener = -1
        if descriptor >= 0 {
            Darwin.shutdown(descriptor, SHUT_RDWR)
            Darwin.close(descriptor)
            unlink(path)
        }
    }
}

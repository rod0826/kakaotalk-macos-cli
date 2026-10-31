import Foundation

func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
    guard condition() else { fatalError(message) }
}

var probes = 0
var pauses = 0
let recovered: [String] = try availableWindows(attempts: 4, probe: {
    probes += 1
    return probes < 3 ? [] : ["창길"]
}, pause: { pauses += 1 })
expect(recovered == ["창길"], "Temporarily empty AXWindows must recover")
expect(probes == 3 && pauses == 2, "Stop retrying immediately after windows appear")
let recoveredWindow = try uniqueRoomWindow(in: recovered, matching: { $0 == "창길" })
expect(recoveredWindow == "창길", "Resolve recovered target")

probes = 0
pauses = 0
do {
    let _: [String] = try availableWindows(attempts: 4, probe: { probes += 1; return [] }, pause: { pauses += 1 })
    fatalError("All-empty probe must fail")
} catch WindowAvailabilityFailure.windowsUnavailable {}
expect(probes == 4 && pauses == 3, "Empty-window retries must be bounded without a trailing wait")

do {
    _ = try uniqueRoomWindow(in: ["다른 방"], matching: { $0 == "창길" })
    fatalError("Wrong title must fail")
} catch WindowAvailabilityFailure.roomNotOpen {}
do {
    let empty: [String] = []
    _ = try uniqueRoomWindow(in: empty, matching: { $0 == "창길" })
    fatalError("Empty snapshots must not be confused with a missing room")
} catch WindowAvailabilityFailure.windowsUnavailable {}
do {
    _ = try uniqueRoomWindow(in: ["창길", "창길"], matching: { $0 == "창길" })
    fatalError("Ambiguous already-open windows must not choose a recipient")
} catch WindowAvailabilityFailure.roomNotOpen {}

enum ProbeError: Error { case expired }
probes = 0
do {
    let _: [String] = try availableWindows(attempts: 4, probe: {
        probes += 1
        throw ProbeError.expired
    }, pause: {})
    fatalError("Expiration must propagate")
} catch ProbeError.expired {}
expect(probes == 1, "Do not retry expired or disconnected requests")
print("Window availability tests passed")

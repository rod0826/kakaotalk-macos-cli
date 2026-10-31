/// An unavailable AX window list does not prove that the requested room is closed
/// or establish which Space contains it. Keep that failure distinct from a title
/// mismatch in a window list that the application did expose.
enum WindowAvailabilityFailure: Error {
    case windowsUnavailable
    case roomNotOpen
}

func availableWindows<Window>(attempts: Int = 5,
                              probe: () throws -> [Window],
                              pause: () throws -> Void) throws -> [Window] {
    for attempt in 0..<max(1, attempts) {
        let windows = try probe()
        if !windows.isEmpty { return windows }
        if attempt + 1 < max(1, attempts) { try pause() }
    }
    throw WindowAvailabilityFailure.windowsUnavailable
}

func uniqueRoomWindow<Window>(in windows: [Window], matching: (Window) -> Bool) throws -> Window {
    guard !windows.isEmpty else { throw WindowAvailabilityFailure.windowsUnavailable }
    let matches = windows.filter(matching)
    guard matches.count == 1 else { throw WindowAvailabilityFailure.roomNotOpen }
    return matches[0]
}

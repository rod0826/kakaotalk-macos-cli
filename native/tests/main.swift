import Foundation

func check(_ condition: Bool, _ message: String) {
    guard condition else { fputs("FAIL: \(message)\n", stderr); exit(1) }
}
check(isMessageComposer(description: "메시지 입력", title: "", placeholder: "", value: "draft"), "description identifies composer with an existing draft")
check(isMessageComposer(description: "", title: "", placeholder: "메시지 입력", value: ""), "placeholder identifies empty composer")
check(isMessageComposer(description: "", title: "", placeholder: "", value: "메시지 입력"), "Kakao empty composer can expose its hint as AXValue")
check(!isMessageComposer(description: "", title: "", placeholder: "", value: "다른 메시지 입력 내용"), "message body substring must not identify a composer")
print("Composer identity regression tests passed")

check(isFilePathField(role: "AXTextField", identifier: "PathTextField"), "current macOS Go To path text field is recognized")
check(isFilePathField(role: "AXComboBox", identifier: "PathTextField"), "identified legacy combo path field is recognized")
check(!isFilePathField(role: "AXTextField", identifier: "Search"), "file-picker search is not a path field")
check(!isFilePathField(role: "AXComboBox", identifier: "unrelated"), "unrelated combo cannot receive a path")
print("File path identity regression tests passed")

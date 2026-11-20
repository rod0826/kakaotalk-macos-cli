import Foundation

func check(_ condition: Bool, _ message: String) {
    guard condition else { fputs("FAIL: \(message)\n", stderr); exit(1) }
}
check(isMessageComposer(description: "메시지 입력", title: "", placeholder: "", value: "draft"), "description identifies composer with an existing draft")
check(isMessageComposer(description: "", title: "", placeholder: "메시지 입력", value: ""), "placeholder identifies empty composer")
check(isMessageComposer(description: "", title: "", placeholder: "", value: "메시지 입력"), "Kakao empty composer can expose its hint as AXValue")
check(!isMessageComposer(description: "", title: "", placeholder: "", value: "다른 메시지 입력 내용"), "message body substring must not identify a composer")
print("Composer identity regression tests passed")

check(searchRoomTitle("나와의 채팅, 📝 메모방") == "📝 메모방", "26.10.0 self-chat prefix is removed")
check(searchRoomTitle("오픈채팅, 스터디") == "스터디", "26.10.0 open-chat prefix is removed")
check(searchRoomTitle("팀채팅, 광고팀") == "광고팀", "26.10.0 team-chat prefix is removed")
check(searchRoomTitle("홍길동") == "홍길동", "plain titles are unchanged")
check(searchRoomTitle("나와의 채팅") == "나와의 채팅", "a title equal to a kind name is unchanged")
check(searchRoomTitle("나와의 채팅, ") == "나와의 채팅, ", "a bare prefix is not reduced to an empty title")
check(searchRoomTitle("친구, 나와의 채팅, 방") == "친구, 나와의 채팅, 방", "only a leading prefix is removed")
print("Search room title regression tests passed")

check(isFilePathField(role: "AXTextField", identifier: "PathTextField"), "current macOS Go To path text field is recognized")
check(isFilePathField(role: "AXComboBox", identifier: "PathTextField"), "identified legacy combo path field is recognized")
check(!isFilePathField(role: "AXTextField", identifier: "Search"), "file-picker search is not a path field")
check(!isFilePathField(role: "AXComboBox", identifier: "unrelated"), "unrelated combo cannot receive a path")
print("File path identity regression tests passed")

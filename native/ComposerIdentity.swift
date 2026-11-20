import Foundation

func isMessageComposer(description: String, title: String, placeholder: String, value: String) -> Bool {
    [description, title, placeholder].contains { $0.contains("메시지 입력") } || value == "메시지 입력"
}

/// KakaoTalk 26.10.0 prefixes some search-result titles with the room kind
/// ("나와의 채팅, ", "오픈채팅, ", "팀채팅, ") while the opened window title has none.
let searchRoomKindPrefixes = ["나와의 채팅, ", "오픈채팅, ", "팀채팅, "]
func searchRoomTitle(_ label: String) -> String {
    for prefix in searchRoomKindPrefixes where label.hasPrefix(prefix) && label.count > prefix.count {
        return String(label.dropFirst(prefix.count))
    }
    return label
}

func isFilePathField(role: String, identifier: String) -> Bool {
    identifier == "PathTextField" && ["AXTextField", "AXComboBox"].contains(role)
}

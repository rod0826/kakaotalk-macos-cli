import Foundation

func isMessageComposer(description: String, title: String, placeholder: String, value: String) -> Bool {
    [description, title, placeholder].contains { $0.contains("메시지 입력") } || value == "메시지 입력"
}

func isFilePathField(role: String, identifier: String) -> Bool {
    identifier == "PathTextField" && ["AXTextField", "AXComboBox"].contains(role)
}

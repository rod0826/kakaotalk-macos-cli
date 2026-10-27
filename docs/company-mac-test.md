# 회사 맥북 테스트 — 0.1.1

카카오의 검토·승인·인증을 받지 않은 비공식 실험 프로젝트입니다. Apple Silicon, macOS 14 이상용 별도 전달 ZIP이며 GitHub Releases에는 게시하지 않습니다. macOS 14는 빌드 최소값이며 회사 보고 환경은 macOS 26.6.2, 카카오톡 26.8.0입니다.

## 압축 및 설치

1. 새 `KakaoTalk-CLI-0.1.1-company-test-macOS-arm64.zip`과 같은 이름의 `.zip.sha256` 파일을 같은 폴더에 둡니다. 해당 폴더에서 `shasum -a 256 -c KakaoTalk-CLI-0.1.1-company-test-macOS-arm64.zip.sha256`이 `OK`인지 확인합니다. ZIP 내부 `BUILD.json`은 실행 파일 해시만 기록합니다.
2. Finder로 압축을 풉니다. 추출된 `KakaoTalk CLI.app`에 `codesign --verify --deep --strict "/전체/경로/KakaoTalk CLI.app"`를 실행해 서명을 확인합니다. 안내 파일은 앱 내부 `Contents/Resources/usage-guide.html`입니다.
3. 이전 KakaoTalk CLI 앱을 종료합니다. 기존 `~/Applications/KakaoTalk CLI.app`이 있다면 보관하거나 다른 폴더로 이동합니다. 새 앱을 열어 **사용자 앱 폴더에 설치**를 누릅니다. 기존 앱은 덮어쓰지 않습니다.
4. 원래 압축 폴더의 앱을 종료하고 **Finder에서 `~/Applications/KakaoTalk CLI.app`을 직접 엽니다**. 임시 서명·미공증 앱이므로 Gatekeeper가 막으면 macOS의 개별 앱 허용 절차와 회사 정책을 따릅니다. 허용되지 않으면 중단합니다. 보안 설정 일괄 해제나 quarantine 자동 제거는 하지 않습니다.
5. 설치된 앱에만 손쉬운 사용 권한을 허용합니다. 이전 빌드 권한이 켜져 있어도 새 빌드는 다시 허용해야 할 수 있습니다. AppTranslocation 임시 경로 앱에 권한을 부여하지 않습니다.
6. **CLI + Codex·Claude Code 스킬 설치**를 누릅니다. 이전 버전의 AppTranslocation 링크는 복구하며, 다른 기존 파일·링크가 있으면 보존하고 안내합니다. 두 에이전트에서 새 대화를 시작합니다.

## 기본 검사

카카오톡 로그인 및 잠금 해제 상태에서 실행합니다.

```sh
~/.local/bin/cli-anything-kakaotalk --json doctor
readlink ~/.local/bin/cli-anything-kakaotalk
readlink ~/.codex/skills/cli-anything-kakaotalk
readlink ~/.claude/skills/cli-anything-kakaotalk
```

링크는 모두 `~/Applications/KakaoTalk CLI.app/Contents/Resources/…`를 가리켜야 합니다. `doctor`에서 `accessibility_trusted:true`, `running:true`, `broker_translocated:false`를 확인합니다. `broker_bundle`은 설치 경로여야 합니다. `version_matches:true`는 알려진 버전이라는 뜻이며, 실제 사용할 수 있는 명령은 `supported_operations`를 확인합니다.

`BROKER_BUILD_MISMATCH`면 오류의 기대/실행 경로와 빌드 해시를 비교합니다. 실행 경로에 AppTranslocation이 있으면 임시 앱을 종료하고 위 4번부터 진행합니다. 계속 임시 경로라면 회사 관리자에게 개별 앱 승인 또는 정식 서명 배포를 요청합니다. 경로·서명 일치 검사는 해제하지 않습니다.

## 카카오톡 기능 재시험

본인 채팅방으로 검색 → 정확한 제목으로 열기 → 현재 방 확인 → 초안 작성/조회/복원 → 읽기 → 파일 선택창 열기/취소 순서로 시험합니다. 열면 읽음 표시가 바뀔 수 있습니다. 기존 초안은 `--expected-text`를 지정해 보존하고 복원하세요.

검색 결과의 `label[0]`이 실제 제목입니다. 예를 들어 `📝 이름`이면 이모지와 공백까지 그대로 사용합니다. 배열의 시간·인원수는 방 이름이 아닙니다. 동일 제목이 여러 개면 가장 최근의 정확한 일치 방을 선택합니다.

**26.8.0:** 위 비전송 기능 7개는 회사 보고에 따라 기본 허용됩니다. `file select`, `message send`, `file send`는 아직 검증되지 않아 기본 차단합니다. `--allow-untested-version`은 이를 해제하는 명시적 호환성 테스트 옵션이며, 자동으로 붙이지 마세요. 별도 테스트를 할 때만 본인 방·시험 파일로 실행하고 결과를 기록하세요.

**26.5.0:** `file select --room "정확한 제목" "/전체/파일/경로.zip"`으로 실제 파일 선택을 확인할 수 있습니다. `selection_verified:true`, `open_enabled:true`, `sent:false`를 확인한 다음 `file cancel`로 닫습니다. 이 테스트는 열기 버튼을 누르지 않습니다.

실제 전송 시험을 별도로 요청할 경우 정확한 수신 방·내용·파일을 지정하세요. 추가 **파일 전송** 확인창은 지원되는 Computer Use로 확인하고 한 번 누른 뒤 새 첨부를 검증합니다. 파일 선택이나 `status:unknown`을 전송 완료로 해석하거나 자동 재전송하지 않습니다. 전체 버전별 범위는 `version-support.md`를 참고하세요.

## 결과 공유

[GitHub Issues](https://github.com/rod0826/kakaotalk-macos-cli/issues)에 다음을 남겨주세요.

- ZIP 이름과 외부 SHA-256 검사 결과, Finder 추출 후 서명 검사 결과
- macOS/카카오톡/CLI 버전, doctor의 지원 명령과 broker_translocated
- 성공한 단계와 실패 명령의 종류·오류 코드
- 파일 선택/실제 전송 여부를 구분한 결과

채팅 내용·방 이름·개인 경로는 지우세요. 원래 Mac의 손쉬운 사용 권한은 다른 Mac으로 이전되지 않습니다.

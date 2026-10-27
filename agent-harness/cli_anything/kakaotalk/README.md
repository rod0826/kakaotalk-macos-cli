# KakaoTalk CLI for macOS — 비공식 실험 프로젝트

> **비공식 실험용 프로젝트입니다. 카카오의 검토·승인·인증을 받지 않았으며, 카카오가 제공하거나 지원하는 공식 CLI가 아닙니다.**
> Kakao has not reviewed, approved, or certified this project. It is an unofficial experiment and is not an official Kakao CLI.

카카오톡을 제어하는 공통 CLI와 설치·진단용 Mac 앱입니다. **카카오의 공식 제품이 아닙니다.** Codex와 Claude Code가 같은 실행 파일과 같은 스킬을 사용합니다.

이 저장소는 **소스만 공개**합니다. 설치 앱·ZIP은 GitHub Releases에 게시하지 않습니다. 개발자가 직접 빌드해야 하며, 별도 전달된 테스트 ZIP은 아래 회사 맥북 안내를 참고하세요. 새로 빌드하면 임시 서명이 달라져 손쉬운 사용 권한을 다시 허용해야 할 수 있습니다.

## 설치

1. `dist/KakaoTalk CLI.app`을 엽니다.
2. **사용자 앱 폴더에 설치**를 눌러 `~/Applications/KakaoTalk CLI.app`으로 복사합니다. 관리자 권한은 필요하지 않습니다. 기존 앱은 덮어쓰지 않습니다.
3. 원래 앱을 종료하고 **Finder에서 `~/Applications/KakaoTalk CLI.app`을 직접 연 뒤**, 앱의 **손쉬운 사용 권한 설정 열기**로 시스템 설정을 열고, KakaoTalk CLI 앱을 추가·허용합니다.
4. **CLI + Codex·Claude Code 스킬 설치**를 누릅니다. 새 대화부터 사용하세요.

CLI는 Python 런타임을 내장합니다. 배포 앱 사용자에게 Python·Homebrew·Node 설치가 필요하지 않습니다. Apple Silicon/macOS 14 이상용이며, 카카오톡 **26.5.0**의 기존 기능과 **26.8.0**의 검색·열기·초안·읽기·파일 선택창 열기/취소를 지원합니다. 26.8.0의 파일 선택·전송은 아직 검증되지 않아 기본 차단됩니다. `doctor`의 `supported_operations`를 확인하세요. 로컬 임시 서명만 적용됐고 Apple 공증은 받지 않았습니다. 다른 Mac에 배포하려면 정식 서명·공증이 필요합니다. macOS 보안 기능을 자동 해제하지 않습니다.

## 사용

`~/.local/bin`이 PATH에 있으면 아래 짧은 명령을 사용할 수 있습니다. 아니면 `~/.local/bin/cli-anything-kakaotalk` 전체 경로를 사용하세요. 터미널 설정 파일은 수정하지 않습니다.

```sh
cli-anything-kakaotalk --json doctor
cli-anything-kakaotalk --json chat search "채팅방 이름"
cli-anything-kakaotalk --json chat open "정확한 채팅방 이름"
cli-anything-kakaotalk --json chat current --room "정확한 채팅방 이름"
cli-anything-kakaotalk --json chat read --room "정확한 채팅방 이름" --limit 20
cli-anything-kakaotalk --json message draft --room "정확한 채팅방 이름" --text-file -
cli-anything-kakaotalk --json file dialog --room "정확한 채팅방 이름"
cli-anything-kakaotalk --json file select --room "정확한 채팅방 이름" "/전체/파일/경로.zip"
cli-anything-kakaotalk --json file cancel --room "정확한 채팅방 이름"
cli-anything-kakaotalk --json session status
```

검색 결과의 `label[0]`이 실제 제목입니다. `label` 배열 전체나 시간·인원수 항목을 이름으로 사용하지 마세요. 제목이 `📝 이름`이면 이모지와 공백까지 그대로 `chat open "📝 이름"`에 전달해야 합니다. 같은 제목이 여러 개면 최근 순 검색 결과의 첫 번째 정확한 일치 방을 선택합니다. 부분 일치로 수신 방을 자동 선택하지 않습니다.

`file select`는 파일 전체 경로와 SHA-256을 검증하고 **열기 버튼을 누르지 않은 채** 멈춥니다. `file cancel`로 닫으세요.

`--text-file -`는 표준입력에서 UTF-8 문구를 읽습니다. `--text`는 터미널 기록·프로세스 목록에 문구가 보일 수 있습니다. 기존 초안을 바꾸려면 `--expected-text`로 기존 내용을 정확히 지정하세요. 전송은 별도 명령입니다.

```sh
cli-anything-kakaotalk --json --dry-run message send \
  --room "정확한 채팅방 이름" --text-file - \
  --confirm-room "정확한 채팅방 이름" --request-id "intent-unique-id"
```

실제 전송은 `--dry-run` 없이 실행합니다. **현재 초안이 전달한 문구와 정확히 일치해야** Enter를 한 번 누릅니다. Enter 설정에 따라 전송 대신 줄바꿈이 될 수도 있습니다. 서버 전달을 검증하지 못하므로 `status: unknown`, `delivery_verified: false`로 반환하며, 이를 전송 성공으로 해석하면 안 됩니다. 요청 ID는 로컬에 영구 기록돼 같은 ID의 재실행을 거부합니다. 결과를 확인하지 않고 ID를 바꿔 재시도하지 마세요.

`file send --room NAME PATH --confirm-room NAME --request-id ID`는 **실험 기능**입니다. 파일 선택창의 선택된 전체 파일 URL과 파일 해시를 확인한 뒤 Open을 한 번 실행합니다. 선택 URL을 확인할 수 없으면 중단합니다. 추가 확인창을 추측해 클릭하지 않습니다. 메시지·파일 실제 발송은 별도 사용자 승인을 받은 실전 검증 전까지 검증 완료로 표시하지 않습니다.

명령 없이 실행하면 메모리 내 이력만 사용하는 REPL이 열립니다. `exit` 또는 `quit`로 종료합니다. JSON 전역 옵션은 명령 앞에 둡니다. `--json` 사용 시 작업 결과는 `{ok:true,data:{...}}`, 오류는 `{ok:false,error:{code,message}}`와 종료 코드 2입니다. `doctor`의 `ok:true`는 검사 성공을 뜻하며, 준비 상태는 `accessibility_trusted`, `running`, `version_matches`, `supported_operations`, `dispatch_supported`를 확인해야 합니다. `version_matches:true`도 모든 명령이 검증됐다는 뜻은 아닙니다.

CLI는 같은 사용자만 연결할 수 있는 로컬 Unix 소켓으로 전용 앱에 요청합니다. 접근성 권한은 이 앱에만 필요하며, ChatGPT나 터미널 전체에 부여할 필요가 없습니다. 명령 실행 시 전용 앱이 자동 실행될 수 있고 종료 전까지 요청을 받을 준비 상태로 남습니다. 로그인 항목·상주 데몬·수신 감시 서비스는 설치하지 않습니다. 임시 요청도 파일로 저장하지 않습니다.

## 한계와 데이터

- 로그인·잠금 해제된 macOS GUI 세션이 필요합니다. 작업 중 카카오톡이 앞으로 나올 수 있습니다. 채팅방을 열면 읽음 상태가 바뀔 수 있습니다.
- 정확한 제목이 필요합니다. 동일 제목은 가장 최근 방을 선택하며, 부분 일치는 중단합니다.
- 읽기는 앱이 로드한 대화 행에 한정됩니다. 전체 이력·보낸 사람 식별·새 메시지 감시·헤드리스 실행·전달 보장은 제공하지 않습니다.
- 버전별로 확인되지 않은 명령은 기본적으로 UI 제어를 막습니다. `--allow-untested-version`은 호환성을 따로 확인한 경우에만 사용합니다.
- 대화 내용·첨부파일은 카카오톡 자체 기능으로만 다룹니다. 내부 데이터베이스·로그인 토큰·비공개 서버 API에는 접근하지 않습니다.
- CLI 자체는 대화 내용을 저장하지 않습니다. 전송 의도의 ID·해시·시각·상태만 `~/Library/Application Support/KakaoTalkCLI/journal.sqlite3`에 저장합니다. 화면 출력이나 AI 도구의 실행 기록에는 내용이 남을 수 있습니다.
- 독립 프로세스의 UI 작업은 고정된 사용자별 잠금으로 직렬화합니다. 다른 CLI·수동 사용자 조작까지 막지는 못하므로 실행 중 같은 창을 동시에 조작하지 마세요.

## 개발 및 검증

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e agent-harness
.venv/bin/python scripts/build.py
.venv/bin/python scripts/package.py
(cd dist && shasum -a 256 -c KakaoTalk-CLI-0.1.1-company-test-macOS-arm64.zip.sha256)
.venv/bin/python -m pytest agent-harness/cli_anything/kakaotalk/tests/test_core.py -v
PATH="$PWD/.venv/bin:$PATH" CLI_ANYTHING_FORCE_INSTALLED=1 KAKAO_TEST_ROOM="나와의 채팅방 실제 이름" \
  .venv/bin/python -m pytest agent-harness/cli_anything/kakaotalk/tests/test_full_e2e.py -v
```

Xcode Command Line Tools가 빌드에 필요합니다. 실전 테스트는 실제 앱과 권한을 요구하고, 없으면 실패합니다. 실전 테스트는 본인 방에서만 사용하세요. 테스트는 기존 초안을 보존하고 복원하며 메시지·파일을 발송하지 않습니다. 실패 직후에는 파일 선택창이나 테스트 초안이 남았는지 확인하세요. 개발용 패키지 내 실행 파일 대신 배포 앱으로 테스트하려면 PATH 앞에 앱의 `Contents/Resources/cli`를 지정합니다.

자세한 결과는 `VERIFICATION.md`, 개인 경로와 대화 내용을 제외한 테스트 계획·요약은 `agent-harness/cli_anything/kakaotalk/tests/TEST.md`에 기록합니다.

## 회사 Mac 설치 문제 진단

0.1.1부터 서명된 앱 안의 안내 파일은 ASCII 이름 `usage-guide.html`을 사용합니다. ZIP은 앱 서명 검사 후 생성하며, macOS `ditto`로 다시 추출해 서명을 검사한 다음 최종 ZIP의 `.zip.sha256`을 외부에 생성합니다. ZIP 내부 문서에 현재 ZIP 자체의 해시는 넣지 않습니다.

CLI와 스킬 링크는 동일 빌드가 설치된 `~/Applications/KakaoTalk CLI.app`만 가리킵니다. 이전 설치가 만든 AppTranslocation 링크는 자동 복구하지만, 다른 파일·링크는 보존합니다. `BROKER_BUILD_MISMATCH` 오류에는 기대 경로·실행 경로와 빌드 해시가 표시됩니다. AppTranslocation이면 임시 앱을 종료하고 Finder에서 설치된 앱을 직접 연 뒤 macOS의 개별 앱 승인 절차를 따르세요. 계속 임시 경로에서 실행되면 회사 관리자에게 승인·정식 서명 배포를 요청하세요. 서명·경로 일치 검사를 끄거나 보안 설정을 일괄 해제하지 않습니다.

## 제거

앱을 종료한 뒤 설치 앱, `~/.local/bin/cli-anything-kakaotalk` 링크, `~/.codex/skills/cli-anything-kakaotalk` 및 `~/.claude/skills/cli-anything-kakaotalk` 링크를 제거하세요. 필요하면 상태 폴더도 제거하고 시스템 설정의 손쉬운 사용 목록에서 앱을 해제하세요. 이미 수행한 전송은 되돌려지지 않습니다.

## 구현 근거

CLI-Anything의 Click/JSON/REPL·실제 앱 백엔드 구조를 따르되, 비공개 카카오톡 소스 대신 공개 macOS 접근성 API와 실제 앱의 관찰 결과를 사용한 맞춤 어댑터입니다. 전체 CLI-Anything 공개 소스 분석 절차를 수행한 공식 지원 앱은 아닙니다.

- Apple AXUIElement: https://developer.apple.com/documentation/applicationservices/axuielement
- CLI-Anything: https://github.com/HKUDS/CLI-Anything
- Click: https://click.palletsprojects.com/
- Claude Code skills: https://code.claude.com/docs/en/skills

## 라이선스 및 고지

프로젝트 자체 소스는 [Apache-2.0](LICENSE)로 공개합니다. 외부 구성요소에는 각 원래 라이선스가 적용됩니다. CLI-Anything에서 가져온 `repl_skin.py`의 출처는 [NOTICE](NOTICE)에 명시했습니다. 카카오톡 상표·앱·서비스의 권리는 해당 권리자에게 있으며, 카카오톡 앱이나 서비스에 대한 이용 권한을 이 저장소의 라이선스가 부여하지 않습니다.

- [회사 맥북 테스트 안내](docs/company-mac-test.md)
- [검증 범위](VERIFICATION.md)
- [보안 제보 및 개인정보 주의](SECURITY.md)

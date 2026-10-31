# 빌드 서명과 손쉬운 사용 권한

0.1.2부터 기존 코드 서명 인증서를 선택해 네이티브 앱과 동봉 CLI·라이브러리를 함께 서명할 수 있습니다. 인증서를 지정하지 않은 개발 빌드는 기존처럼 ad-hoc 서명합니다. ad-hoc 서명은 업데이트할 때 앱의 식별 조건이 달라질 수 있어, 이전 손쉬운 사용 승인이 유지된다고 기대할 수 없습니다.

## 기존 인증서로 빌드하기

먼저 읽기 전용 명령으로 현재 키체인에서 사용할 수 있는 인증서를 확인합니다.

```sh
security find-identity -v -p codesigning
```

인증서의 **정확한 이름** 또는 출력에 표시된 **40자리 SHA-1 식별값**을 지정합니다. 같은 이름의 인증서가 여러 개라면 SHA-1을 사용합니다.

```sh
.venv/bin/python scripts/build.py --signing-identity '기존 인증서의 정확한 이름'
.venv/bin/python scripts/package.py
```

환경변수로도 지정할 수 있으며 명령행 옵션을 함께 주면 옵션이 우선합니다.

```sh
KAKAOTALK_SIGNING_IDENTITY='기존 인증서의 정확한 이름' .venv/bin/python scripts/build.py
```

요청한 인증서가 없거나 이름이 모호하면 빌드를 시작하기 전에 중단합니다. 서명 실패 시 ad-hoc으로 바꾸어 재시도하지 않습니다. 스크립트는 인증서·개인키를 생성하지 않으며 키체인이나 인증서 신뢰 설정을 바꾸지 않습니다. 인증서가 없다면 회사 IT 또는 기존 배포 담당자에게 적절한 코드 서명 인증서 준비를 요청해야 합니다.

PyInstaller에도 같은 인증서를 전달하며, 최종 앱은 중첩된 실행 파일·라이브러리부터 바깥 번들 순서로 서명합니다. 패키징은 서명을 확인하고 실제 인증서 체인, TeamIdentifier, designated requirement를 `BUILD.json`에 기록합니다. 공증 상태는 검사하지 않으므로 `not assessed`로 기록합니다. 인증서 서명만으로 Gatekeeper 승인이나 공증이 완료되지는 않습니다.

## 업데이트 후 확인

macOS는 designated requirement를 사용해 앱의 코드 정체성을 판별합니다. 같은 인증서·번들 식별자와 호환되는 requirement로 빌드하는 것은 권한 유지의 조건을 안정화하지만, 손쉬운 사용 승인이 반드시 유지된다는 보장은 아닙니다. 최초 ad-hoc 빌드에서 인증서 빌드로 바꿀 때도 다시 허용해야 할 수 있습니다. 회사 정책과 macOS 동작에 따라 결과가 달라질 수 있습니다.

설치 위치를 `~/Applications/KakaoTalk CLI.app`로 유지하고, 업데이트 전후 다음 결과와 `BUILD.json`을 비교합니다.

```sh
codesign --verify --deep --strict "$HOME/Applications/KakaoTalk CLI.app"
codesign -d --verbose=4 -r- "$HOME/Applications/KakaoTalk CLI.app"
```

회사 맥에서 같은 인증서로 만든 두 버전을 차례로 설치해 손쉬운 사용 권한이 유지되는지 실제로 확인해야 합니다. 유지되지 않으면 시스템 설정에서 새 앱을 다시 허용하고, 두 버전의 designated requirement와 설치 경로를 이슈에 남겨 주세요. TCC 데이터베이스를 수정하거나 보안 설정을 끄는 우회는 제공하지 않습니다.

근거: Apple [TN3127: Inside Code Signing: Requirements](https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements), [TN2206: macOS Code Signing In Depth](https://developer.apple.com/library/archive/technotes/tn2206/), PyInstaller [macOS code signing](https://pyinstaller.org/en/stable/feature-notes.html#macos-binary-code-signing).

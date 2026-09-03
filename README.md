# 영상 음악 분리·제거기 / Video Music Separator

[한국어](#한국어) | [English](#english)

## 한국어

영상에 섞인 배경음악을 줄이거나 제거하기 위한 Windows GUI다. AV-CASS가 원본 오디오를 `음악`과 `음악 아님(목소리·효과음)` 두 트랙으로 나누며, 결과를 번갈아 듣고 음악을 뮤트한 사본을 원본 옆에 저장할 수 있다. 원본 영상은 바꾸지 않으며 처리 속도보다 분리 품질을 우선한다.

- 현재 앱 버전: `0.2.0`
- 제작: [@ms-0606](https://www.youtube.com/@ms-0606) × OpenAI Codex

### 설치 안내

처음 설치할 때는 아래의 두 실행 파일을 같은 폴더에 두고 **설치 파일을 먼저 실행**한다.

#### 1. 설치 전 확인

| 항목 | 요구사항 |
| --- | --- |
| 운영체제 | Windows 64비트. 현재 빌드와 동작 확인 환경은 Windows 11이다. |
| GPU | CUDA를 사용할 수 있는 NVIDIA GPU가 필요하다. CPU 전용 실행은 지원하지 않는다. 최소 VRAM은 아직 검증된 지원 기준을 정하지 않았다. |
| 저장 공간 | 첫 설치 때 약 5.9GB를 내려받으며, 압축 해제와 설치 중에는 약 15GB의 여유 공간을 권장한다. |
| 인터넷 | 첫 설치, 재설치 또는 런타임 업데이트 때 필요하다. 설치가 끝난 뒤 일반적인 영상 분리·저장에는 필요하지 않다. |
| GitHub 인증 | 공개 Release에서는 필요 없다. Release가 비공개이면 GitHub CLI가 필요하고, 설치 프로그램이 필요한 경우 GitHub 웹 인증을 시작한다. |
| Python·FFmpeg | 최종 사용자가 별도로 설치할 필요가 없다. 설치 프로그램이 고정된 AI Python 실행환경과 BtbN 공식 최신 FFmpeg 8.1 LGPL 공유 빌드를 내려받는다. |
| 설치 위치 | ZIP 안에서 직접 실행하지 말고, 문서 폴더처럼 사용자가 쓸 수 있는 일반 폴더에 전체 압축을 푼다. |

#### 2. Windows 설치 파일 다운로드

[Video Music Separator Windows Installer Release](https://github.com/Fabio-Cannavaro/video-music-separator/releases/tag/installer-v0.2.0-r5)

위 릴리스의 `Assets`에서 설치 ZIP 하나만 내려받으면 된다.

- 필수 설치 ZIP: `video-music-separator-0.2.0-windows-x64.zip`
- 선택 사항(무결성 확인용): `video-music-separator-0.2.0-windows-x64.zip.sha256`

GitHub가 자동으로 추가하는 `Source code (zip)`과 `Source code (tar.gz)`는 설치 파일이 아니므로 받지 않는다.

설치 ZIP에는 `video-music-separator-setup.exe`와 `video-music-separator.exe`가 함께 들어 있다. 두 EXE는 반드시 같은 폴더에 두며, AI Python 환경·AV-CASS 코드·모델·FFmpeg는 설치 프로그램이 별도로 내려받는다.

#### 3. 설치 순서

1. 배포자가 제공한 기본 앱 ZIP을 새 폴더에 **전부 압축 해제**한다.
2. 위의 두 EXE가 같은 폴더에 있는지 확인한다.
3. 무결성을 직접 확인하려면 선택 파일인 `.sha256`도 받아 ZIP의 체크섬과 비교한다. 이 확인은 설치 필수 단계가 아니며, 확인한 값이 다르면 실행하지 않는다.
4. **`video-music-separator-setup.exe`를 먼저 실행한다.**
5. 설치 화면 오른쪽 위에서 `한국어 / English`를 선택할 수 있다. 약 5.9GB의 다운로드 용량, 다운로드 출처, 모델 이용조건, 개인정보 안내와 사용자 책임을 읽고 동의한 뒤 `설치 시작`을 누른다.
6. AI 실행환경 Release가 비공개이고 로그인이 없거나 만료되었다면 설치 프로그램이 여는 GitHub CLI 창과 웹브라우저에서 이 저장소에 접근할 수 있는 계정으로 인증한다. 일회용 코드는 클립보드에 자동 복사된다. 공개 Release에서는 이 단계가 생략된다.
7. 모든 항목의 다운로드와 SHA-256 검증이 완료될 때까지 기다린다.
8. 설치 완료 안내가 나오면 `video-music-separator.exe`를 실행한다.

현재 실행 파일은 유료 코드 서명 인증서를 적용하지 않은 **미서명 빌드**일 수 있다. Windows SmartScreen에 `알 수 없는 게시자` 경고가 나오면 저장소·배포 주소와 SHA-256을 먼저 확인하고, 두 정보가 맞을 때에만 `추가 정보`에서 실행한다. 체크섬이 다르거나 출처가 불명확한 파일은 실행하지 않는다.

> **현재 배포 상태:** 이 저장소는 비공개 배포 준비 단계다. 공개 Release 전에는 AV-CASS 체크포인트 자동 다운로드에 대한 서면 허가와 공개 다운로드·새 Windows 계정 설치 검사를 완료해야 한다. 진행 상태는 [배포 체크리스트](docs/DISTRIBUTION_CHECKLIST.md)에서 관리한다.

#### 4. 설치 프로그램이 내려받는 항목

1. 다음 항목을 지정 배포처에서 내려받는다.
   - AI Python 실행환경: 이 프로젝트의 Release에 고정된 두 분할 파일. 공개 Release는 인증 없이 받고, 공개 접근이 거부된 비공개 Release만 로컬 GitHub CLI 인증을 사용한다.
   - AV-CASS `av_cass_checkpoint.pt`: AV-CASS 공식 Google Drive
   - CAVP `cavp_epoch66.ckpt`: Diff-Foley 공식 Hugging Face의 고정 커밋
   - FFmpeg: BtbN 공식 `latest` Release의 FFmpeg 8.1 LGPL 공유 빌드
2. AI 실행환경과 모델은 고정된 크기·SHA-256을 확인한다. FFmpeg는 공식 GitHub Release API에서 현재 파일의 크기·SHA-256을 받아 검증하고, 버전·빌드 옵션도 확인한다.
3. 공개 배포처의 중단된 다운로드는 `.part` 파일에서 이어받는다. 비공개 GitHub Release 다운로드는 다시 시작하며, 모든 파일은 검증이 끝난 뒤에만 실제 설치 위치로 교체한다.

설치 화면에는 다운로드 출처, 적용되는 이용조건, 외부 통신 정보와 사용자 책임이 표시된다. 사용자가 이를 확인하고 동의해야 설치를 시작할 수 있다. Video Music Separator는 AV-CASS 연구진 또는 관련 기관의 공식 앱이 아니며 제휴하거나 보증받지 않았다.

설치 파일은 모델이나 FFmpeg를 이 저장소 또는 별도 서버에서 재배포하지 않는다. AI 실행환경·모델의 파일 내용이 고정 체크섬과 다르거나, FFmpeg가 공식 Release의 체크섬·LGPL 공유 빌드 조건과 다르면 설치를 중단한다. 다운로드, GitHub 인증, 분할 파일 결합, 무결성 확인, 압축 해제, 파일 배치, 최종 검증은 단계별 퍼센트로 표시한다. 설치 결과와 실제 버전·출처·체크섬은 앱 폴더의 `docs/runtime-assets.json`에 기록한다.

공개 앱 ZIP과 별도 AI 실행환경 자산은 예전 AudioSep/BandIt 코드·가중치와 해당 GPL 의존성인 `pedalboard`를 포함하지 않는다. 실제 설치되는 Python 패키지 목록은 앱 ZIP 안의 `docs/PYTHON_PACKAGES_NOTICES.md`, 기계 판독 목록은 `docs/PYTHON_PACKAGES_INVENTORY.json`, 각 라이선스 전문은 `docs/licenses/python/`에서 확인할 수 있다.

#### 5. 설치 문제 해결

- 공개 Release에서는 GitHub CLI가 필요 없다. 비공개 상태에서 `GitHub CLI를 찾을 수 없습니다` 오류가 나오면 GitHub CLI를 설치한 뒤 설치 프로그램을 다시 실행한다. 로그인이 없거나 만료된 경우에는 설치 프로그램이 웹 인증을 자동으로 시작하며, `Fabio-Cannavaro/video-music-separator`를 볼 수 있는 계정이어야 한다.
- 설치 파일을 ZIP 안에서 직접 실행했거나 `Program Files`처럼 쓰기가 제한된 위치에 두었다면, 폴더 전체를 문서 폴더 같은 사용자 쓰기 가능 위치로 옮긴 뒤 다시 실행한다.
- 다운로드가 중단되면 같은 설치 파일을 다시 실행한다. 검증된 파일은 재사용하고 완료되지 않은 `.part` 다운로드는 이어받는다.
- 체크섬 불일치는 파일을 임의로 사용하지 않기 위한 정상적인 중단이다. 검증을 우회하지 말고 배포 안내의 주소·버전이 최신인지 확인한다.
- `NVIDIA GPU가 필요합니다` 오류가 나오면 지원되는 NVIDIA GPU와 정상 설치된 드라이버가 필요하다. 현재 CPU 전용 대체 실행은 제공하지 않는다.

#### 6. 설치 후 폴더 사용과 이동

설치가 끝나면 앱 폴더 안에 다음 구성요소가 생긴다.

- 앱 실행 파일: `video-music-separator.exe`
- 필수 구성요소 설치 파일: `video-music-separator-setup.exe`
- LGPL 공유 FFmpeg 실행 파일과 DLL: `ffmpeg/`
- AI Python 환경: `audiosep/env/`
- AV-CASS 코드와 구성요소: `audiosep/avcass/repo/`, `audiosep/avcass/deps/`
- AV-CASS 모델: `audiosep/avcass/model/av_cass_checkpoint.pt`
- CAVP 모델: `audiosep/avcass/model/cavp/cavp_epoch66.ckpt`

같은 PC에서는 이 앱 폴더를 영상 폴더마다 복사할 필요가 없다. 한곳에 그대로 두고 `video-music-separator.exe`의 바로가기만 바탕화면에 만든다. 앱에서 `영상 열기`를 누르면 어느 폴더의 영상이든 선택할 수 있으며, 작업 폴더와 결과 사본은 선택한 원본 영상 옆에 생긴다.

앱 자체의 위치를 바꾸려면 EXE만 따로 옮기지 말고 설치된 앱 폴더 전체를 함께 옮긴다. `audiosep`라는 폴더명은 기존 휴대용 런타임과의 호환성을 위해 유지했다.

### 사용 방법

1. `영상 열기`로 클립을 선택한다.
2. `영상에서 음악 분리`를 누른다.
3. 각 행의 `듣기`를 누르면 앱 맨 위의 작은 화면에서 영상과 해당 트랙이 함께 재생된다. 같은 버튼을 다시 누르면 정지한다. 미리보기 아래 슬라이더를 움직이면 원하는 재생 위치로 바로 이동한다.
4. `음악 (BGM)` 행의 `뮤트`를 누른다.
5. `전체 영상 재생`으로 음악이 빠진 영상과 목소리·효과음을 확인한다. 영상 프레임은 소리 재생 시계를 기준으로 맞춰 장시간 재생해도 싱크가 누적해서 벌어지지 않게 한다.
6. 창 아래의 `사본 저장`을 누르면 `<원본이름>_음악제거.mp4`를 만든다.

영상 미리보기 오른쪽의 `한국어 / English`를 선택하면 창 제목, 버튼, 상태 안내, 결과 표, 경고창과 라이선스·출처 창의 안내 표기가 즉시 해당 언어로 바뀐다.

전체 볼륨 슬라이더는 앱을 시작할 때 100으로 설정되며 원본·뮤트 믹스·두 분리본에 공통 적용된다. AV-CASS 실행 경로는 휴대용 폴더 안에서 자동으로 관리된다.

영상 옆에는 처리 중 `<영상이름>_sound_work` 임시 폴더가 생긴다. 원본 WAV는 한 번만 추출하며, `models/avcass` 아래에 `stems`, `previews`, `sounds.json`을 저장한다. 최종 MP4 저장과 파일 확인이 성공하면 이 임시 폴더 전체가 자동으로 삭제된다. 저장 실패·취소 또는 폴더 정리 실패 시에는 진단과 재시도를 위해 남겨 둔다.

### 처리 구조

1. FFmpeg가 영상 오디오를 44.1kHz 스테레오 WAV로 추출한다.
2. CAVP가 영상 장면의 시각 특징을 추출하고, AV-CASS가 이 특징과 오디오를 함께 분석해 음악과 비음악을 분리한다.
3. AI 분리 결과에서 부드러운 음악 마스크를 만든 뒤 원본 44.1kHz 스테레오에 적용한다.
4. `music`은 음악 행으로, `dialog + effects`는 음악 아님 행으로 저장한다.
5. AV-CASS 결과는 전용 캐시 폴더에 보관한다.
6. 음악과 음악 아님을 합치면 원본과 정확히 같아지도록 만들어 채널 수, 공간감, 원본 위상을 유지한다.
7. 음악이 원본 전체와 사실상 같고 음악 아님이 거의 무음인 붕괴 결과는 `검토 필요`로 표시한다.
8. 음악 뮤트 저장은 `음악 아님` 트랙을 영상에 직접 결합한다.
9. 음악과 음악 아님을 모두 유지한 전체 재생은 원본 오디오를 사용한다.

처리 시간은 영상 길이와 GPU 상태에 따라 달라진다.

### 저장소에 포함되지 않는 파일

이 저장소에는 앱 소스, 테스트, 빌드·배포 스크립트, 문서와 라이선스 전문이 들어 있다. 다음 항목은 크기와 재배포 조건 때문에 포함하지 않는다.

- AV-CASS와 CAVP 모델 가중치
- 각 모델의 원본 저장소 사본과 Python 추론 환경
- FFmpeg 실행 파일
- 개인 영상·오디오, 분리 결과, 임시 작업 폴더와 로그

모델과 외부 도구의 이용·재배포 조건은 [MODEL_LICENSES.md](docs/MODEL_LICENSES.md)와 [THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md)를 먼저 확인해야 한다.

### 개발자용 저장소 구조

- `app/`: 앱, 분리 워커와 런타임 설치 코드
- `tests/`: 단위·통합 테스트
- `scripts/`: 개발 실행, 빌드, 배포 및 라이선스 검사 도구
- `docs/`: 개인정보, 모델, FFmpeg 및 제3자 고지 문서
- `licenses/`: 앱에 포함하는 라이선스 전문
- `build/`, `dist/`: Git에서 제외되는 빌드 중간물과 배포 결과

루트의 `video-music-separator.exe`와 `video-music-separator-setup.exe`는 `scripts/build_executables.ps1`로 만드는 로컬 실행 파일이며 Git에는 포함하지 않는다. GitHub 표시와 라이선스 확인을 위해 `README.md`, `LICENSE`, `requirements.txt`는 루트에 유지한다.

### 개발 실행

GUI 자체는 가벼운 Python 환경으로 실행하고, AI 추론은 휴대용 폴더의 별도 환경을 사용한다.

```powershell
cd video-music-separator
py -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\sound_separator_app.py
```

`py`가 설치된 Python을 찾지 못하면 설치된 Python 실행 파일의 전체 경로로 첫 명령을 실행한다. AI 추론 기능을 사용하려면 별도로 준비한 휴대용 런타임과 모델 파일이 필요하다.

### 빌드와 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\scripts\prepare_ffmpeg_lgpl.ps1
.\scripts\build_executables.ps1
.\scripts\build_runtime_installer.ps1
.\scripts\build_portable.ps1
```

`build_executables.ps1`는 루트에 단일 파일형 앱 EXE와 설치 EXE를 만든다. `build_runtime_installer.ps1`는 설치 EXE와 대응하는 `.sha256` 파일만 만든다. 기본 `build_portable.ps1` 결과에는 AV-CASS·CAVP 가중치와 FFmpeg를 넣지 않고 설치 파일을 포함한다. 내부용 오프라인 묶음이 필요하면 `build_portable.ps1 -BundleRuntimeAssets`를 사용한다. 인증서 지문을 `-CodeSigningCertificateThumbprint`로 제공한 경우에만 Authenticode 서명을 적용하며, 인증서가 없으면 미서명 상태로 빌드한다.

`prepare_ffmpeg_lgpl.ps1`는 개발·오프라인 빌드용 BtbN 공식 `latest` FFmpeg 8.1 LGPL 공유 빌드를 찾고, 해당 Release의 SHA-256과 빌드 옵션을 검증한다. 설치된 정확한 버전과 체크섬은 `docs/runtime-assets.json`에 기록하며, 검증 방식과 출처는 [FFMPEG_BUILD.md](docs/FFMPEG_BUILD.md)에 설명한다.

휴대용 실동작 검사는 다음처럼 실행한다.

```powershell
.\dist\package\video-music-separator.exe --portable-smoke-test `
  ..\sample.mp4 `
  ..\test-output\portable_avcass_smoke.json
```

### 한계

- 음악/비음악 분리는 세부 소리 이름별 독립 추출보다 안정적이지만 AI 분리이므로 100% 무누출을 보장하지 않는다.
- 매우 작은 음악, 음악처럼 반복되는 효과음, 노래·신음처럼 음악과 사람 발성의 경계가 애매한 소리는 반대 트랙에 일부 남을 수 있다.
- AV-CASS는 16kHz 모노로 장면과 소리를 판단하지만, 최종 출력은 그 판정 마스크를 원본 스테레오에 적용한다. 모델이 판단할 수 없는 8kHz 이상은 음악 아님 쪽에 보존한다.
- 저장 전에는 반드시 음악 행과 음악 아님 행을 각각 들어보고, 음악 뮤트 전체 재생까지 확인해야 한다.

### 입력 파일과 결과물 책임

이 앱은 사용자가 선택한 파일을 로컬 PC에서 처리한다. 사용자는 입력 영상·음악·음성에 필요한 권리를 확보하고, 생성된 결과물을 이용하거나 배포할 권한이 있는지 직접 확인해야 한다. AI 분리는 완벽한 대사·효과음 보존이나 음악 제거를 보장하지 않으므로 저장 전에 결과를 직접 검토해야 한다.

앱은 영상·음원·결과물·파일명 또는 사용 통계를 개발자에게 전송하지 않는다. 설치할 때만 Google Drive, Hugging Face와 GitHub/BtbN에 HTTPS 다운로드 요청을 보낸다. 전송되는 일반 접속 정보와 로컬 파일 처리 범위는 [PRIVACY.md](docs/PRIVACY.md)에 기록한다.

영상 미리보기 왼쪽의 `라이선스·출처` 버튼을 누르면 한 화면에서 AV-CASS와 CAVP의 출처·논문, FFmpeg LGPL 빌드 정보와 제3자 고지를 한국어로 확인할 수 있다. 그 아래에는 GPL·LGPL·MIT·Apache의 변경되지 않은 공식 영문 원문이 이어진다.

### 라이선스

자체 코드의 저작권 표시는 `Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)`이다. 자세한 식별 정보와 적용 범위는 [저작권 고지](docs/COPYRIGHT.md)에 기록한다.

이 저장소에서 자체 제작한 코드는 표준 **GNU General Public License version 3 only (`GPL-3.0-only`)**로 제공된다. 사용·열람·수정·무료 재배포와 유료 판매를 허용한다. 실행 파일이나 수정본을 배포할 때는 저작권·라이선스 고지를 유지하고, 그 배포본과 정확히 대응하는 전체 소스를 GPLv3로 함께 제공해야 하며 추가적인 사용 제한을 붙일 수 없다.

수정자는 자신이 새로 작성한 변경분의 저작권을 가질 수 있지만 원본 코드의 저작권을 취득하지 않는다. GPL 조건을 지켜 배포된 원본과 수정본을 다른 사용자가 계속 사용·수정·재배포할 권리를 수정자가 임의로 취소하거나 금지할 수 없다. 정확한 조건은 공식 전문을 그대로 수록한 [LICENSE](LICENSE)를 따른다.

AV-CASS, CAVP, FFmpeg, Python 패키지와 모델 가중치 같은 외부 구성요소 자체에는 각 원 저작권자와 원 라이선스가 계속 적용된다. 실행 파일을 공개 배포하기 전에는 포함한 각 파일의 라이선스와 소스 제공 의무를 다시 확인하고, 해당 실행 파일과 정확히 대응하는 자체 코드의 Git 태그 또는 소스 ZIP을 같은 Release에서 제공해야 한다.

공개 Release를 만들기 전에는 [DISTRIBUTION_CHECKLIST.md](docs/DISTRIBUTION_CHECKLIST.md)를 순서대로 확인한다.

---

## English

A Windows GUI for reducing or removing background music mixed into video audio. AV-CASS separates the original audio into `Music` and `Non-Music (Voice & Effects)` tracks so users can compare the results and save a copy with the music muted beside the source video. The source video remains unchanged, and separation quality is prioritized over processing speed.

- Current application version: `0.2.0`
- Created by [@ms-0606](https://www.youtube.com/@ms-0606) × OpenAI Codex

### Installation Guide

For the first installation, keep the following two executables in the same folder and **run the installer first**.

#### 1. Before Installation

| Item | Requirement |
| --- | --- |
| Operating system | 64-bit Windows. The current build and runtime checks were performed on Windows 11. |
| GPU | An NVIDIA GPU with CUDA support is required. CPU-only execution is not supported. A verified minimum VRAM requirement has not yet been established. |
| Disk space | The first installation downloads approximately 5.9 GB. Approximately 15 GB of free space is recommended while downloading, extracting, and installing. |
| Internet | Required for the first installation, reinstallation, or runtime updates. Normal separation and saving do not require an internet connection after installation. |
| GitHub authentication | Not required for a public Release. If the Release is private, GitHub CLI is required and the installer starts GitHub web authentication when necessary. |
| Python and FFmpeg | End users do not need to install them separately. The installer downloads the pinned AI Python runtime and the current official BtbN FFmpeg 8.1 LGPL shared build. |
| Installation location | Do not run the application from inside the ZIP. Extract the entire ZIP into a normal user-writable folder such as Documents. |

#### 2. Download the Windows Installer

[Video Music Separator Windows Installer Release](https://github.com/Fabio-Cannavaro/video-music-separator/releases/tag/installer-v0.2.0-r5)

Under `Assets` in the Release above, only the installer ZIP is required.

- Required installer ZIP: `video-music-separator-0.2.0-windows-x64.zip`
- Optional integrity check: `video-music-separator-0.2.0-windows-x64.zip.sha256`

The automatically generated `Source code (zip)` and `Source code (tar.gz)` files are not installers and should not be downloaded for installation.

The installation ZIP contains both `video-music-separator-setup.exe` and `video-music-separator.exe`. Keep both EXE files in the same folder. The installer separately downloads the AI Python environment, AV-CASS code, model files, and FFmpeg.

#### 3. Installation Steps

1. **Extract the entire application ZIP** supplied by the distributor into a new folder.
2. Confirm that both EXE files listed above are in that folder.
3. To verify integrity yourself, optionally download the `.sha256` file and compare it with the ZIP checksum. This is not required for installation; if the values differ, do not run the file.
4. **Run `video-music-separator-setup.exe` first.**
5. Select `한국어 / English` in the upper-right corner of the installer. Review the approximately 5.9 GB download size, download sources, model terms, privacy notice, and user responsibilities; then accept the notice and select `Start Installation`.
6. If the AI runtime Release is private and the GitHub login is missing or expired, authenticate with an account that can access this repository in the GitHub CLI window and browser opened by the installer. The one-time code is copied to the clipboard automatically. This step is skipped for a public Release.
7. Wait for all downloads and SHA-256 verification to finish.
8. After the completion message appears, run `video-music-separator.exe`.

The executables may be **unsigned builds** without a paid code-signing certificate. If Windows SmartScreen displays an `Unknown publisher` warning, first verify the repository, distribution URL, and SHA-256 value. Use `More info` to continue only when those details match. Do not run a file with a mismatched checksum or unclear origin.

> **Current distribution status:** This repository is in the private distribution-preparation stage. Before a public Release, written permission for automatic AV-CASS checkpoint downloads and clean installation tests with a new Windows account must be completed. Progress is tracked in the [distribution checklist](docs/DISTRIBUTION_CHECKLIST.md).

#### 4. Components Downloaded by the Installer

1. The installer downloads the following items from their specified distributors.
   - AI Python runtime: two pinned split files from this project's Release. A public Release is downloaded without authentication; only a private Release that rejects public access uses local GitHub CLI authentication.
   - AV-CASS `av_cass_checkpoint.pt`: the official AV-CASS Google Drive location
   - CAVP `cavp_epoch66.ckpt`: the pinned commit in the official Diff-Foley Hugging Face repository
   - FFmpeg: the FFmpeg 8.1 LGPL shared build from BtbN's official `latest` Release
2. It verifies the pinned sizes and SHA-256 values of the AI runtime and models. For FFmpeg, it obtains the current asset size and SHA-256 from the official GitHub Release API and also verifies the version and build options.
3. Interrupted downloads from public distributors resume from their `.part` files. Private GitHub Release downloads restart. Files replace their installation targets only after verification succeeds.

The installer displays the download sources, applicable terms, network-access information, and user responsibilities. Installation begins only after the user reviews and accepts them. Video Music Separator is not an official application of, affiliated with, or endorsed by the AV-CASS researchers or their institutions.

The installer does not redistribute the model files or FFmpeg from this repository or a separate project server. Installation stops if the AI runtime or models no longer match their pinned checksums, or if FFmpeg does not match its official Release checksum and LGPL shared-build requirements. Downloads, GitHub authentication, split-file combining, integrity checks, extraction, file placement, and final verification display a percentage for each stage. Actual versions, sources, and checksums are recorded in `docs/runtime-assets.json` inside the application folder.

The public application ZIP and separate AI runtime assets exclude the former AudioSep/BandIt code and weights and their GPL dependency, `pedalboard`. The exact installed Python package list is available in `docs/PYTHON_PACKAGES_NOTICES.md` inside the application ZIP, the machine-readable inventory in `docs/PYTHON_PACKAGES_INVENTORY.json`, and full license texts in `docs/licenses/python/`.

#### 5. Installation Troubleshooting

- GitHub CLI is not required for a public Release. If a private Release reports `GitHub CLI was not found`, install GitHub CLI and rerun the installer. If the login is missing or expired, the installer starts web authentication automatically. The account must be able to access `Fabio-Cannavaro/video-music-separator`.
- If the installer was run from inside the ZIP or from a write-restricted location such as `Program Files`, move the entire folder to a user-writable location such as Documents and try again.
- If a download is interrupted, rerun the same installer. Verified files are reused, and incomplete `.part` downloads resume where supported.
- A checksum mismatch is an intentional safety stop. Do not bypass verification; confirm that the distribution URL and pinned version are current.
- The `An NVIDIA GPU is required` error means a supported NVIDIA GPU and a correctly installed driver are required. No CPU-only fallback is currently provided.

#### 6. Using and Moving the Installed Folder

After installation, the application folder contains:

- Application executable: `video-music-separator.exe`
- Required-components installer: `video-music-separator-setup.exe`
- LGPL shared FFmpeg executables and DLLs: `ffmpeg/`
- AI Python environment: `audiosep/env/`
- AV-CASS code and components: `audiosep/avcass/repo/`, `audiosep/avcass/deps/`
- AV-CASS model: `audiosep/avcass/model/av_cass_checkpoint.pt`
- CAVP model: `audiosep/avcass/model/cavp/cavp_epoch66.ckpt`

On the same PC, do not copy this application folder beside every video. Keep it in one location and create a desktop shortcut to `video-music-separator.exe`. `Open Video` can select a video from any folder, and the work folder and saved copy are created beside the selected source video.

To move the application itself, move the entire installed folder rather than either EXE alone. The `audiosep` folder name is retained for compatibility with the former portable runtime layout.

### Usage

1. Select a clip with `Open Video`.
2. Select `Separate Music from Video`.
3. Select `Listen` on either row to play the video with that separated track in the preview at the top of the application. Select the same button again to stop. Move the slider below the preview to seek directly to the desired position.
4. Select `Mute` on the `Music (BGM)` row.
5. Use `Play Full Video` to review the video with the music removed and the voice and effects preserved. Video frames follow the audio playback clock so sync does not drift during long playback.
6. Select `Save Copy` at the bottom of the window to create `<source name>_music-removed.mp4`.

Selecting `한국어 / English` to the right of the video preview immediately changes the window title, buttons, status messages, result table, warnings, and license/source window to the selected language.

The master volume slider starts at 100 and applies to the source, muted mix, and both separated tracks. AV-CASS runtime paths are managed automatically inside the portable folder.

During processing, a temporary `<video name>_sound_work` folder is created beside the video. The source WAV is extracted only once, and `stems`, `previews`, and `sounds.json` are stored under `models/avcass`. The entire temporary folder is deleted after the final MP4 is saved and verified successfully. It remains available for diagnosis and retry if saving is cancelled, fails, or cleanup fails.

### Processing Pipeline

1. FFmpeg extracts the video audio as a 44.1 kHz stereo WAV file.
2. CAVP extracts visual features from the video frames, and AV-CASS analyzes those features together with the audio to separate music from non-music.
3. A smooth music mask is derived from the AI result and applied to the original 44.1 kHz stereo signal.
4. `music` is saved as the Music row, and `dialog + effects` as the Non-Music row.
5. AV-CASS results are retained in a dedicated cache folder.
6. Music and non-music are constructed to sum exactly to the source, preserving channel count, spatial image, and source phase.
7. A collapsed result in which music is effectively identical to the full source and non-music is nearly silent is marked `Review Needed`.
8. Music-muted export directly combines the non-music track with the video.
9. Full playback with both tracks enabled uses the original audio.

Processing time depends on video duration and GPU performance.

### Files Not Included in the Repository

This repository contains the application source, tests, build and distribution scripts, documentation, and full license texts. The following files are excluded because of their size and redistribution terms:

- AV-CASS and CAVP model weights
- Copies of the original model repositories and the Python inference environment
- FFmpeg executables
- Personal video/audio files, separation results, temporary work folders, and logs

Review [MODEL_LICENSES.en.md](docs/MODEL_LICENSES.en.md) and [THIRD_PARTY_NOTICES.en.md](docs/THIRD_PARTY_NOTICES.en.md) before using or redistributing models and external tools.

### Repository Layout for Developers

- `app/`: application, separation worker, and runtime installer code
- `tests/`: unit and integration tests
- `scripts/`: development, build, distribution, and license-audit tools
- `docs/`: privacy, model, FFmpeg, and third-party notices
- `licenses/`: full license texts included with the application
- `build/`, `dist/`: Git-ignored intermediate build and distribution output

The root `video-music-separator.exe` and `video-music-separator-setup.exe` files are local executables produced by `scripts/build_executables.ps1` and are not committed to Git. `README.md`, `LICENSE`, and `requirements.txt` remain in the root for GitHub presentation and license verification.

### Development

The GUI runs in a lightweight Python environment, while AI inference uses a separate environment in the portable folder.

```powershell
cd video-music-separator
py -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\sound_separator_app.py
```

If `py` cannot find the installed Python interpreter, use the full path to the installed Python executable for the first command. AI inference requires a separately prepared portable runtime and model files.

### Build and Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\scripts\prepare_ffmpeg_lgpl.ps1
.\scripts\build_executables.ps1
.\scripts\build_runtime_installer.ps1
.\scripts\build_portable.ps1
```

`build_executables.ps1` creates the single-file application EXE and installer EXE in the repository root. `build_runtime_installer.ps1` creates only the installer EXE and its matching `.sha256` file. The default `build_portable.ps1` result excludes AV-CASS/CAVP weights and FFmpeg and includes the installer. Use `build_portable.ps1 -BundleRuntimeAssets` for an internal offline bundle. Authenticode signing is applied only when a certificate thumbprint is supplied with `-CodeSigningCertificateThumbprint`; otherwise the build remains unsigned.

`prepare_ffmpeg_lgpl.ps1` resolves the official BtbN `latest` FFmpeg 8.1 LGPL shared build for development and offline builds, then verifies the SHA-256 supplied by that Release and the build options. The installed version and checksum are recorded in `docs/runtime-assets.json`; the source and verification method are described in [FFMPEG_BUILD.en.md](docs/FFMPEG_BUILD.en.md).

Run the portable smoke test as follows:

```powershell
.\dist\package\video-music-separator.exe --portable-smoke-test `
  ..\sample.mp4 `
  ..\test-output\portable_avcass_smoke.json
```

### Limitations

- Music/non-music separation is more stable than independent extraction by detailed sound name, but no AI separation can guarantee zero leakage.
- Very quiet music, rhythmically repeated effects, and sounds near the boundary between music and human vocalization—such as singing or moaning—may partially remain in the opposite track.
- AV-CASS analyzes the scene and audio at 16 kHz mono, but the final output applies its decision mask to the original stereo signal. Frequencies above 8 kHz that the model cannot evaluate are preserved in the non-music track.
- Always listen to both the Music and Non-Music rows and review full playback with music muted before saving.

### Input and Output Responsibility

The application processes user-selected files locally on the PC. Users must obtain the necessary rights to the input video, music, and speech and independently confirm their right to use or distribute generated results. AI separation does not guarantee perfect preservation of dialogue and effects or complete music removal, so review results before saving.

The application does not transmit video, audio, output, file names, or usage analytics to the developer. HTTPS download requests are sent only to Google Drive, Hugging Face, and GitHub/BtbN during installation. Ordinary connection information transmitted and the scope of local file processing are documented in [PRIVACY.en.md](docs/PRIVACY.en.md).

The `Licenses & Sources` button to the left of the video preview opens one scrollable page. In Korean mode, Korean notices and sources appear first, followed by the unmodified official GPL, LGPL, MIT, and Apache license texts.

### License

Copyright for the original project code is identified as `Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)`. See the [copyright notice](docs/COPYRIGHT.en.md) for the detailed identity and scope.

Original code created for this repository is provided under the standard **GNU General Public License version 3 only (`GPL-3.0-only`)**. Use, inspection, modification, free redistribution, and commercial sale are permitted. Distribution of an executable or modified version must preserve copyright and license notices, provide the complete corresponding source under GPLv3, and impose no additional restrictions.

A modifier may own copyright in newly authored changes but does not acquire copyright in the original code. A modifier cannot revoke or prohibit another user's continuing right to use, modify, or redistribute the original and modified code distributed in compliance with the GPL. The exact terms are governed by the unmodified official [LICENSE](LICENSE) text.

External components such as AV-CASS, CAVP, FFmpeg, Python packages, and model weights remain governed by their respective copyright holders and licenses. Before publicly distributing an executable, verify the license and source-provision obligations for every included file and provide the Git tag or source ZIP exactly corresponding to that executable in the same Release.

Before creating a public Release, follow [DISTRIBUTION_CHECKLIST.md](docs/DISTRIBUTION_CHECKLIST.md) in order.

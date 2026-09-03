# 영상 음악 분리·제거기

영상에 섞인 배경음악을 줄이거나 제거하기 위한 Windows GUI다. AV-CASS가 같은 원본을 각각 `음악`과 `음악 아님(목소리·효과음)` 두 트랙으로 나누고, 결과를 번갈아 들어본 뒤 저장한다. 처리 속도보다 분리 품질을 우선한다.

원본 영상은 바꾸지 않는다. 음악만 뮤트하면 원본 옆에 `<원본이름>_음악제거.mp4`를 만들며, 같은 이름의 사본은 덮어쓴다.

- 현재 앱 버전: `0.2.0`
- 제작: [@ms-0606](https://www.youtube.com/@ms-0606) × OpenAI Codex

## 설치 안내

처음 설치할 때는 아래의 두 실행 파일을 같은 폴더에 두고 **설치 파일을 먼저 실행**한다.

### 1. 설치 전 확인

| 항목 | 요구사항 |
| --- | --- |
| 운영체제 | Windows 64비트. 현재 빌드와 동작 확인 환경은 Windows 11이다. |
| GPU | CUDA를 사용할 수 있는 NVIDIA GPU가 필요하다. CPU 전용 실행은 지원하지 않는다. 최소 VRAM은 아직 검증된 지원 기준을 정하지 않았다. |
| 저장 공간 | 첫 설치 때 약 5.9GB를 내려받으며, 압축 해제와 설치 중에는 약 15GB의 여유 공간을 권장한다. |
| 인터넷 | 첫 설치, 재설치 또는 런타임 업데이트 때 필요하다. 설치가 끝난 뒤 일반적인 영상 분리·저장에는 필요하지 않다. |
| Python·FFmpeg | 최종 사용자가 별도로 설치할 필요가 없다. 설치 프로그램이 고정된 AI Python 실행환경과 LGPL FFmpeg를 내려받는다. |
| 설치 위치 | ZIP 안에서 직접 실행하지 말고, 문서 폴더처럼 사용자가 쓸 수 있는 일반 폴더에 전체 압축을 푼다. |

### 2. 설치에 필요한 두 파일

| 파일 | 용도 |
| --- | --- |
| `video-music-separator-setup.exe` | 처음 한 번 실행해 AI 실행환경, 모델과 FFmpeg를 설치한다. |
| `video-music-separator.exe` | 설치가 끝난 뒤 영상에서 음악을 분리할 때 실행한다. |

두 EXE는 반드시 같은 폴더에 둔다. 기본 앱 ZIP에는 AI Python 환경·AV-CASS 코드·모델·FFmpeg가 들어 있지 않다.

### 3. 설치 순서

1. 배포자가 제공한 기본 앱 ZIP을 새 폴더에 **전부 압축 해제**한다.
2. 위의 두 EXE가 같은 폴더에 있는지 확인한다.
3. 함께 제공된 SHA-256 값과 내려받은 파일의 체크섬이 같은지 확인한다. 값이 다르면 실행하지 않는다.
4. **`video-music-separator-setup.exe`를 먼저 실행한다.**
5. 설치 화면에서 약 5.9GB의 다운로드 용량, 다운로드 출처, 모델 이용조건, 개인정보 안내와 사용자 책임을 읽고 동의한 뒤 `설치 시작`을 누른다.
6. 모든 항목의 다운로드와 SHA-256 검증이 완료될 때까지 기다린다.
7. 설치 완료 안내가 나오면 `video-music-separator.exe`를 실행한다.

현재 실행 파일은 유료 코드 서명 인증서를 적용하지 않은 **미서명 빌드**일 수 있다. Windows SmartScreen에 `알 수 없는 게시자` 경고가 나오면 저장소·배포 주소와 SHA-256을 먼저 확인하고, 두 정보가 맞을 때에만 `추가 정보`에서 실행한다. 체크섬이 다르거나 출처가 불명확한 파일은 실행하지 않는다.

> **현재 배포 상태:** 이 저장소는 비공개 배포 준비 단계다. 공개 Release 전에는 AV-CASS 체크포인트 자동 다운로드에 대한 서면 허가와 공개 다운로드·새 Windows 계정 설치 검사를 완료해야 한다. 진행 상태는 [배포 체크리스트](docs/DISTRIBUTION_CHECKLIST.md)에서 관리한다.

### 4. 설치 프로그램이 내려받는 항목

1. 다음 항목을 지정 배포처에서 내려받는다.
   - AI Python 실행환경: 이 프로젝트의 GitHub Release에 고정된 두 분할 파일
   - AV-CASS `av_cass_checkpoint.pt`: AV-CASS 공식 Google Drive
   - CAVP `cavp_epoch66.ckpt`: Diff-Foley 공식 Hugging Face의 고정 커밋
   - FFmpeg: BtbN의 고정 LGPL 공유 빌드
2. 각 파일의 크기와 SHA-256, FFmpeg의 버전·빌드 옵션을 확인한다.
3. 중단된 다운로드는 `.part` 파일에서 이어받으며 검증이 끝난 파일만 실제 설치 위치로 교체한다.

설치 화면에는 다운로드 출처, 적용되는 이용조건, 외부 통신 정보와 사용자 책임이 표시된다. 사용자가 이를 확인하고 동의해야 설치를 시작할 수 있다. Video Music Separator는 AV-CASS 연구진 또는 관련 기관의 공식 앱이 아니며 제휴하거나 보증받지 않았다.

설치 파일은 모델이나 FFmpeg를 이 저장소 또는 별도 서버에서 재배포하지 않는다. 공식 주소가 변경되거나 파일 내용이 바뀌어 체크섬이 맞지 않으면 설치를 중단한다. 설치 결과와 출처는 앱 폴더의 `docs/runtime-assets.json`에 기록한다.

공개 앱 ZIP과 별도 AI 실행환경 자산은 예전 AudioSep/BandIt 코드·가중치와 해당 GPL 의존성인 `pedalboard`를 포함하지 않는다. 실제 설치되는 Python 패키지 목록은 앱 ZIP 안의 `docs/PYTHON_PACKAGES_NOTICES.md`, 기계 판독 목록은 `docs/PYTHON_PACKAGES_INVENTORY.json`, 각 라이선스 전문은 `docs/licenses/python/`에서 확인할 수 있다.

### 5. 설치 문제 해결

- 설치 파일을 ZIP 안에서 직접 실행했거나 `Program Files`처럼 쓰기가 제한된 위치에 두었다면, 폴더 전체를 문서 폴더 같은 사용자 쓰기 가능 위치로 옮긴 뒤 다시 실행한다.
- 다운로드가 중단되면 같은 설치 파일을 다시 실행한다. 검증된 파일은 재사용하고 완료되지 않은 `.part` 다운로드는 이어받는다.
- 체크섬 불일치는 파일을 임의로 사용하지 않기 위한 정상적인 중단이다. 검증을 우회하지 말고 배포 안내의 주소·버전이 최신인지 확인한다.
- `NVIDIA GPU가 필요합니다` 오류가 나오면 지원되는 NVIDIA GPU와 정상 설치된 드라이버가 필요하다. 현재 CPU 전용 대체 실행은 제공하지 않는다.

### 6. 설치 후 폴더 사용과 이동

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

## 사용 방법

1. `영상 열기`로 클립을 선택한다.
2. `영상에서 음악 분리`를 누른다.
3. 각 행의 `듣기`를 누르면 앱 맨 위의 작은 화면에서 영상과 해당 트랙이 함께 재생된다. 같은 버튼을 다시 누르면 정지한다. 미리보기 아래 슬라이더를 움직이면 원하는 재생 위치로 바로 이동한다.
4. `음악 (BGM)` 행의 `뮤트`를 누른다.
5. `전체 영상 재생`으로 음악이 빠진 영상과 목소리·효과음을 확인한다. 영상 프레임은 소리 재생 시계를 기준으로 맞춰 장시간 재생해도 싱크가 누적해서 벌어지지 않게 한다.
6. 창 아래의 `사본 저장`을 누르면 `<원본이름>_음악제거.mp4`를 만든다.

영상 미리보기 오른쪽의 `한국어 / English`를 선택하면 창 제목, 버튼, 상태 안내, 결과 표, 경고창과 라이선스·출처 창의 안내 표기가 즉시 해당 언어로 바뀐다.

전체 볼륨 슬라이더는 앱을 시작할 때 100으로 설정되며 원본·뮤트 믹스·두 분리본에 공통 적용된다. AV-CASS 실행 경로는 휴대용 폴더 안에서 자동으로 관리된다.

영상 옆에는 처리 중 `<영상이름>_sound_work` 임시 폴더가 생긴다. 원본 WAV는 한 번만 추출하며, `models/avcass` 아래에 `stems`, `previews`, `sounds.json`을 저장한다. 최종 MP4 저장과 파일 확인이 성공하면 이 임시 폴더 전체가 자동으로 삭제된다. 저장 실패·취소 또는 폴더 정리 실패 시에는 진단과 재시도를 위해 남겨 둔다.

## 처리 구조

1. FFmpeg가 영상 오디오를 44.1kHz 스테레오 WAV로 추출한다.
2. AV-CASS가 오디오와 영상 장면을 함께 분석해 분리를 실행한다.
3. AI 분리 결과에서 부드러운 음악 마스크를 만든 뒤 원본 44.1kHz 스테레오에 적용한다.
4. `music`은 음악 행으로, `dialog + effects`는 음악 아님 행으로 저장한다.
5. AV-CASS 결과는 전용 캐시 폴더에 보관한다.
6. 음악과 음악 아님을 합치면 원본과 정확히 같아지도록 만들어 채널 수, 공간감, 원본 위상을 유지한다.
7. 음악이 원본 전체와 사실상 같고 음악 아님이 거의 무음인 붕괴 결과는 `검토 필요`로 표시한다.
8. 음악 뮤트 저장은 `음악 아님` 트랙을 영상에 직접 결합한다.
9. 음악과 음악 아님을 모두 유지한 전체 재생은 원본 오디오를 사용한다.

처리 시간은 영상 길이와 GPU 상태에 따라 달라진다.

## 저장소에 포함되지 않는 파일

이 저장소에는 앱 소스와 테스트만 들어 있다. 다음 항목은 크기와 재배포 조건 때문에 포함하지 않는다.

- AV-CASS와 CAVP 모델 가중치
- 각 모델의 원본 저장소 사본과 Python 추론 환경
- FFmpeg 실행 파일
- 개인 영상·오디오, 분리 결과, 임시 작업 폴더와 로그

모델과 외부 도구의 이용·재배포 조건은 [MODEL_LICENSES.md](docs/MODEL_LICENSES.md)와 [THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md)를 먼저 확인해야 한다.

## 개발자용 저장소 구조

- `app/`: 앱, 분리 워커와 런타임 설치 코드
- `tests/`: 단위·통합 테스트
- `scripts/`: 개발 실행, 빌드, 배포 및 라이선스 검사 도구
- `docs/`: 개인정보, 모델, FFmpeg 및 제3자 고지 문서
- `licenses/`: 앱에 포함하는 라이선스 전문
- `build/`, `dist/`: Git에서 제외되는 빌드 중간물과 배포 결과

루트의 `video-music-separator.exe`와 `video-music-separator-setup.exe`는 `scripts/build_executables.ps1`로 만드는 로컬 실행 파일이며 Git에는 포함하지 않는다. GitHub 표시와 라이선스 확인을 위해 `README.md`, `LICENSE`, `requirements.txt`는 루트에 유지한다.

## 개발 실행

GUI 자체는 가벼운 Python 환경으로 실행하고, AI 추론은 휴대용 폴더의 별도 환경을 사용한다.

```powershell
cd video-music-separator
py -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\sound_separator_app.py
```

`py`가 설치된 Python을 찾지 못하면 설치된 Python 실행 파일의 전체 경로로 첫 명령을 실행한다. AI 추론 기능을 사용하려면 별도로 준비한 휴대용 런타임과 모델 파일이 필요하다.

## 빌드와 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\scripts\prepare_ffmpeg_lgpl.ps1
.\scripts\build_executables.ps1
.\scripts\build_runtime_installer.ps1
.\scripts\build_portable.ps1
```

`build_executables.ps1`는 루트에 단일 파일형 앱 EXE와 설치 EXE를 만든다. `build_runtime_installer.ps1`는 설치 EXE와 대응하는 `.sha256` 파일만 만든다. 기본 `build_portable.ps1` 결과에는 AV-CASS·CAVP 가중치와 FFmpeg를 넣지 않고 설치 파일을 포함한다. 내부용 오프라인 묶음이 필요하면 `build_portable.ps1 -BundleRuntimeAssets`를 사용한다. 인증서 지문을 `-CodeSigningCertificateThumbprint`로 제공한 경우에만 Authenticode 서명을 적용하며, 인증서가 없으면 미서명 상태로 빌드한다.

`prepare_ffmpeg_lgpl.ps1`는 개발·오프라인 빌드용으로 고정된 BtbN FFmpeg 8.1 LGPL 공유 빌드를 내려받고 SHA-256을 검증한다. 정확한 버전, 소스 커밋과 빌드 설정은 [FFMPEG_BUILD.md](docs/FFMPEG_BUILD.md)에 기록한다.

휴대용 실동작 검사는 다음처럼 실행한다.

```powershell
.\dist\package\video-music-separator.exe --portable-smoke-test `
  ..\sample.mp4 `
  ..\test-output\portable_avcass_smoke.json
```

## 한계

- 음악/비음악 분리는 세부 소리 이름별 독립 추출보다 안정적이지만 AI 분리이므로 100% 무누출을 보장하지 않는다.
- 매우 작은 음악, 음악처럼 반복되는 효과음, 노래·신음처럼 음악과 사람 발성의 경계가 애매한 소리는 반대 트랙에 일부 남을 수 있다.
- AV-CASS는 16kHz 모노로 장면과 소리를 판단하지만, 최종 출력은 그 판정 마스크를 원본 스테레오에 적용한다. 모델이 판단할 수 없는 8kHz 이상은 음악 아님 쪽에 보존한다.
- 저장 전에는 반드시 음악 행과 음악 아님 행을 각각 들어보고, 음악 뮤트 전체 재생까지 확인해야 한다.

## 입력 파일과 결과물 책임

이 앱은 사용자가 선택한 파일을 로컬 PC에서 처리한다. 사용자는 입력 영상·음악·음성에 필요한 권리를 확보하고, 생성된 결과물을 이용하거나 배포할 권한이 있는지 직접 확인해야 한다. AI 분리는 완벽한 대사·효과음 보존이나 음악 제거를 보장하지 않으므로 저장 전에 결과를 직접 검토해야 한다.

앱은 영상·음원·결과물·파일명 또는 사용 통계를 개발자에게 전송하지 않는다. 설치할 때만 Google Drive, Hugging Face와 GitHub/BtbN에 HTTPS 다운로드 요청을 보낸다. 전송되는 일반 접속 정보와 로컬 파일 처리 범위는 [PRIVACY.md](docs/PRIVACY.md)에 기록한다.

영상 미리보기 왼쪽의 `라이선스·출처` 버튼에서 AV-CASS와 CAVP의 출처·논문, FFmpeg LGPL 빌드 정보, 제3자 고지와 포함된 라이선스 전문을 확인할 수 있다.

## 라이선스

이 저장소의 자체 코드는 **Video Music Separator No-Resale Share-Alike License 1.0**으로 제공된다. 사용·열람·수정·무료 재배포를 허용하지만, 원본이나 사소하게만 바꾼 복사본을 포장해 판매하는 것은 금지한다. 수정본을 배포할 때는 같은 라이선스와 대응 소스를 제공해야 하며, 수정자는 자신이 새로 작성한 부분의 권리만 주장할 수 있고 원본 코드의 후속 사용·수정·무료 재배포를 막을 수 없다.

이 조건은 독자적인 대규모 개발, 통합, 자문·지원 또는 별도로 연동되는 제품에 비용을 받는 것까지 금지하지 않는다. 표준 오픈소스 라이선스가 아니라 사용자 정의 **source-available** 라이선스이며, 정확한 조건은 [LICENSE](LICENSE)를 따른다.

외부 프로젝트의 코드, 모델 가중치, FFmpeg에는 각각의 원 라이선스가 적용되며 이 저장소의 라이선스로 바뀌지 않는다. 실행 파일을 공개 배포하기 전에는 포함한 각 파일의 라이선스와 소스 제공 의무를 다시 확인해야 한다.

공개 Release를 만들기 전에는 [DISTRIBUTION_CHECKLIST.md](docs/DISTRIBUTION_CHECKLIST.md)를 순서대로 확인한다.

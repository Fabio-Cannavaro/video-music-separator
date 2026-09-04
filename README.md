# 영상 음악 분리·제거기 / Video Music Separator

[한국어](#한국어) | [English](#english)

## 한국어

영상에 섞인 배경음악을 줄이거나 제거하기 위한 Windows GUI다. AV-CASS가 원본 오디오를 `음악`과 `음악 아님` 두 트랙으로 나누며, 결과를 번갈아 듣고 음악을 뮤트한 사본을 원본 옆에 저장할 수 있다. 원본 영상은 바꾸지 않으며 처리 속도보다 분리 품질을 우선한다.

- 현재 앱·설치본 버전: `0.2.7` (미서명 공개 테스트 프리릴리스)
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
| GitHub 계정·CLI | 필요하지 않다. 설치 프로그램은 공개 Release 자산을 인증 없이 내려받는다. |
| Python·FFmpeg | 최종 사용자가 별도로 설치할 필요가 없다. 설치 프로그램이 고정된 AI Python 실행환경과 Gyan FFmpeg 9.0.1 GPL Essentials 정적 빌드를 내려받는다. |
| 설치 위치 | ZIP 안에서 직접 실행하지 말고, 문서 폴더처럼 사용자가 쓸 수 있는 일반 폴더에 전체 압축을 푼다. |

#### 2. Windows 설치 파일 다운로드

현재 Windows 설치본은 [`installer-v0.2.7`](https://github.com/Fabio-Cannavaro/video-music-separator/releases/tag/installer-v0.2.7)에서 미서명 공개 테스트 프리릴리스로 제공한다. `Assets`의 `video-music-separator-0.2.7-windows-x64.zip`과 같은 이름의 `.sha256` 파일을 받는다. 이전 미서명 `0.2.3` 검증 자산, 깨끗한 설치 검증에 실패한 `0.2.5` 자산과 원본 영상보다 오디오가 짧을 때 끝 프레임을 자르던 `0.2.6` 자산은 GitHub Draft로 전환했으며 설치용으로 제공하지 않는다.

이 `0.2.7` 프리릴리스는 Authenticode 코드 서명이 없으므로 Windows가 게시자를 확인할 수 없고 Windows SmartScreen 경고가 나타날 수 있다. 공식 GitHub Release 주소에서만 받고 `.sha256` 파일로 ZIP 무결성을 확인한다. 코드 서명 부재와 별개로 앱 ZIP 안의 `docs/SHA256SUMS.txt`에서 두 EXE의 해시도 확인할 수 있다.

GitHub가 자동으로 추가하는 `Source code (zip)`과 `Source code (tar.gz)`는 설치 파일이 아니므로 받지 않는다.

설치 ZIP에는 `video-music-separator-setup.exe`와 `video-music-separator.exe`가 함께 들어 있다. 두 EXE는 반드시 같은 폴더에 두며, AI Python 환경·AV-CASS 코드·모델·FFmpeg는 설치 프로그램이 별도로 내려받는다.

#### 3. 설치 순서

1. 배포자가 제공한 기본 앱 ZIP을 새 폴더에 **전부 압축 해제**한다.
2. 위의 두 EXE가 같은 폴더에 있는지 확인한다.
3. 같은 Release의 `.sha256` 파일을 받아 ZIP의 체크섬과 비교한다. 확인한 값이 다르면 실행하지 않는다.
4. **`video-music-separator-setup.exe`를 먼저 실행한다.**
5. 설치 화면 오른쪽 위에서 `한국어 / English`를 선택할 수 있다. 약 5.9GB의 다운로드 용량, 다운로드 출처, 모델 이용조건, 개인정보 안내와 사용자 책임을 읽고 동의한 뒤 `설치 시작`을 누른다.
6. 모든 항목의 다운로드와 SHA-256 검증이 완료될 때까지 기다린다.
7. 설치 완료 안내가 나오면 `video-music-separator.exe`를 실행한다.

공개 ZIP 빌드는 인증서가 있으면 앱 EXE와 설치 EXE의 Authenticode 서명·서명자·타임스탬프를 검증한다. 인증서가 없으면 두 파일이 미서명임을 확인하고 `docs/SIGNING_STATUS.txt`, 두 EXE의 `docs/SHA256SUMS.txt`, ZIP의 별도 `.sha256` 파일을 생성한다. 미서명 사실을 서명된 것처럼 표시하지 않는다.

> **현재 배포 상태:** `0.2.7` Windows 설치 자산은 기능 확인을 위한 미서명 공개 프리릴리스다. AV-CASS 체크포인트 자동 다운로드에 대한 연구진의 서면 허가와 깨끗한 새 Windows 사용자 계정 검사가 아직 끝나지 않았으므로, 일반 사용이 승인된 최종 배포판이나 AV-CASS 연구진의 공식 앱으로 표현하지 않는다. 진행 상태는 [배포 체크리스트](docs/DISTRIBUTION_CHECKLIST.md)에서 관리한다.

#### 4. 설치 프로그램이 내려받는 항목

1. 다음 항목을 지정 배포처에서 내려받는다.
   - AI Python 실행환경: 이 프로젝트의 공개 Release에 고정된 두 분할 파일. GitHub 인증 없이 내려받는다.
   - AV-CASS `av_cass_checkpoint.pt`: AV-CASS 공식 Google Drive
   - CAVP `cavp_epoch66.ckpt`: Diff-Foley 공식 Hugging Face의 고정 커밋
   - FFmpeg: Gyan FFmpeg 9.0.1 release essentials GPLv3 정적 빌드의 고정 URL
2. AI 실행환경과 모델은 고정된 크기·SHA-256을 확인한다. FFmpeg는 앱에 고정된 아카이브 URL·크기·SHA-256과 세 실행 파일 각각의 크기·SHA-256을 실행 전에 확인하고, 그 뒤 빌드 옵션도 검증한다.
3. 중단된 다운로드는 `.part` 파일에서 이어받으며, 모든 파일은 검증이 끝난 뒤에만 실제 설치 위치로 교체한다.

설치 화면에는 다운로드 출처, 적용되는 이용조건, 외부 통신 정보와 사용자 책임이 표시된다. 사용자가 이를 확인하고 동의해야 설치를 시작할 수 있다. Video Music Separator는 AV-CASS 연구진 또는 관련 기관의 공식 앱이 아니며 제휴하거나 보증받지 않았다.

설치 파일은 모델이나 FFmpeg를 이 저장소 또는 별도 서버에서 재배포하지 않는다. AI 실행환경·모델의 파일 내용이 고정 체크섬과 다르거나, FFmpeg가 고정된 9.0.1 아카이브 및 실행 파일 해시·GPL Essentials 빌드 조건과 다르면 설치를 중단한다. AI 실행환경은 앱 소스에 고정한 전체 보호 파일 트리 지문과 비교하고, Python 작업자를 시작할 때마다 다시 해시한다. 수정 가능한 사용자별 기록은 신뢰 기준으로 사용하지 않는다. 모델 파일은 각각의 고정 크기·SHA-256으로 별도 검증한다. 설치 결과와 실제 버전·출처·체크섬은 앱 폴더의 `docs/runtime-assets.json`에 기록한다.

앱은 검증된 체크포인트를 읽을 때도 PyTorch의 제한된 `weights_only` 모드를 사용하며, 각 공식 체크포인트에 필요한 최소 메타데이터 형식만 허용한다. 따라서 일반 Python 객체를 제한 없이 역직렬화하지 않는다.

공개 앱 ZIP과 별도 AI 실행환경 자산은 예전 AudioSep/BandIt 코드·가중치와 해당 GPL 의존성인 `pedalboard`를 포함하지 않는다. 실제 설치되는 Python 패키지 목록은 앱 ZIP 안의 `docs/PYTHON_PACKAGES_NOTICES.md`, 기계 판독 목록은 `docs/PYTHON_PACKAGES_INVENTORY.json`, 각 라이선스 전문은 `docs/licenses/python/`에서 확인할 수 있다.

#### 5. 설치 문제 해결

- AI 실행환경 파일에 접근할 수 없다는 오류가 나오면 저장소와 `runtime-v0.2.0` Release가 공개 상태인지, 배포 주소와 파일명이 바뀌지 않았는지 확인한다. 설치 프로그램은 비공개 Release와 GitHub 로그인을 지원하지 않는다.
- 설치 파일을 ZIP 안에서 직접 실행했거나 `Program Files`처럼 쓰기가 제한된 위치에 두었다면, 폴더 전체를 문서 폴더 같은 사용자 쓰기 가능 위치로 옮긴 뒤 다시 실행한다.
- 다운로드가 중단되면 같은 설치 파일을 다시 실행한다. 검증된 파일은 재사용하고 완료되지 않은 `.part` 다운로드는 이어받는다.
- 체크섬 불일치는 파일을 임의로 사용하지 않기 위한 정상적인 중단이다. 검증을 우회하지 말고 배포 안내의 주소·버전이 최신인지 확인한다.
- 보안 보완 버전에서 AI 실행환경 무결성 오류가 나오면 새 `video-music-separator-setup.exe`를 다시 실행해 검증된 아카이브에서 런타임을 재설치한다. 수정 가능한 표식 파일만으로는 런타임을 신뢰하지 않는다.
- `NVIDIA GPU가 필요합니다` 오류가 나오면 지원되는 NVIDIA GPU와 정상 설치된 드라이버가 필요하다. 현재 CPU 전용 대체 실행은 제공하지 않는다.

#### 6. 설치 후 폴더 사용과 이동

설치가 끝나면 앱 폴더 안에 다음 구성요소가 생긴다.

- 앱 실행 파일: `video-music-separator.exe`
- 필수 구성요소 설치 파일: `video-music-separator-setup.exe`
- GPL Essentials FFmpeg 실행 파일: `ffmpeg/`
- AI Python 환경: `audiosep/env/`
- AV-CASS 코드와 구성요소: `audiosep/avcass/repo/`, `audiosep/avcass/deps/`
- AV-CASS 모델: `audiosep/avcass/model/av_cass_checkpoint.pt`
- CAVP 모델: `audiosep/avcass/model/cavp/cavp_epoch66.ckpt`

같은 PC에서는 이 앱 폴더를 영상 폴더마다 복사할 필요가 없다. 한곳에 그대로 두고 `video-music-separator.exe`의 바로가기만 바탕화면에 만든다. 앱에서 `영상 열기`를 누르면 어느 폴더의 영상이든 선택할 수 있으며, 작업 폴더와 결과 사본은 선택한 원본 영상 옆에 생긴다.

앱 자체의 위치를 바꾸려면 EXE만 따로 옮기지 말고 설치된 앱 폴더 전체를 함께 옮긴다. 런타임 검증은 설치 경로가 아니라 고정 트리 지문을 기준으로 하므로, 모든 구성요소가 그대로 이동했다면 경로 갱신용 재설치는 필요하지 않다. `audiosep`라는 폴더명은 기존 휴대용 런타임과의 호환성을 위해 유지했다.

### 사용 방법

1. `영상 열기`로 클립을 선택한다.
2. `영상에서 음악 분리`를 누른다.
3. 각 행의 `듣기`를 누르면 앱 맨 위의 작은 화면에서 영상과 해당 트랙이 함께 재생된다. 같은 버튼을 다시 누르면 정지한다. 미리보기 아래 슬라이더를 움직이면 원하는 재생 위치로 바로 이동한다. 미리보기 영상은 처음 한 번 420×236·24fps의 가벼운 프록시로 준비하고 이후 재사용한다.
4. `음악 (BGM)` 행의 `뮤트`를 누른다.
5. `전체 영상 재생`으로 음악을 뮤트한 결과와 남은 `음악 아님` 오디오를 직접 확인한다. 소리를 기준 시계로 삼고, 영상 디코딩은 화면 처리와 분리하며 늦은 영상 프레임은 건너뛰어 소리 싱크와 UI 반응성을 우선한다.
6. 창 아래의 `사본 저장`을 누르면 `<원본이름>_음악제거.mp4`를 만든다. 같은 이름의 파일이 있으면 `_2`, `_3`처럼 번호를 붙여 기존 사본을 보존한다. 재생용 프록시는 저장본에 쓰지 않으며, 저장본의 영상 스트림은 원본 그대로 복사한다.

영상 미리보기 오른쪽의 `한국어 / English`를 선택하면 창 제목, 버튼, 상태 안내, 결과 표, 경고창과 앱 정보·라이선스·출처 창의 안내 표기가 즉시 해당 언어로 바뀐다.

전체 볼륨 슬라이더는 앱을 시작할 때 100으로 설정되며 원본·뮤트 믹스·두 분리본에 공통 적용된다. AV-CASS 실행 경로는 휴대용 폴더 안에서 자동으로 관리된다.

영상 옆에는 처리 중 `<영상이름>_sound_work_<난수>` 임시 폴더가 생긴다. 앱은 실행별 난수와 원본 영상 경로가 든 소유 표식을 만들며, 둘이 일치하는 이번 실행의 폴더만 삭제한다. 기존 `<영상이름>_sound_work` 폴더나 다른 파일은 재사용하거나 삭제하지 않는다. 최종 MP4 저장과 파일 확인이 성공하면 소유한 임시 폴더를 삭제하고, 저장 실패·취소 또는 표식 불일치 시에는 남겨 둔다.

입력은 로컬 고정 디스크의 지원 미디어 형식만 허용하며 UNC·네트워크 드라이브·재분석 지점·재생목록 형식을 거부한다. 한 번의 입력은 최대 10분, 영상은 최대 7680×4320, 오디오는 최대 8채널·192kHz다. FFmpeg 메모리 할당과 분석량, 외부 도구 로그 크기, 작업자 로그 한 줄·대기 큐에도 상한을 적용한다.

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

### 이 앱의 음악·비음악 분리 방식

이 앱은 AV-CASS의 공식 audio-visual 체크포인트와 CAVP 체크포인트를 사용해 다음
순서로 음악과 비음악을 만든다. 핵심은 CAVP 전체 장면 입력,
`speech`·`sfx`·`music` 3개 생성 결과의 음악 마스크화, 원본 44.1kHz 스테레오 보존,
1초 cosine-squared OLA 결합이다.

1. 원본 오디오는 최종 출력용 44.1kHz 스테레오로 보관한다. AI 분석용으로는 좌우
   채널을 모노로 합치고 16kHz로 변환한다.
2. 영상은 초당 4프레임으로 추출하고 각 프레임을 224×224 중앙 크롭으로 만든다.
   현재 앱은 이 전체 장면 프레임을 CAVP scene encoder에 전달하며 얼굴 검출이나
   별도의 facial encoder는 사용하지 않는다.
3. AV-CASS의 조건부 flow-matching 모델은 약 8.18초 단위로 혼합음과 장면 특징을
   분석해 `speech`, `sfx`, `music` 추정치 세 개를 동시에 생성한다. 각 청크는 기본
   250단계로 추론하고, 청크 사이를 1초 겹친 뒤 cosine-squared OLA로 부드럽게 합친다.
4. `speech + sfx`를 비음악 추정치로 합치고, 음악과 비음악 추정치의 에너지 비율에서
   부드러운 시간-주파수 음악 마스크를 만든다. AI가 생성한 파형을 최종 출력으로 직접
   사용하지 않고, 이 마스크를 보관해 둔 원본 44.1kHz 스테레오에 동일하게 적용한다.
5. 마스크가 선택한 원본 성분을 음악으로 만들고, 비음악은 `원본 - 음악`으로 만든다.
   따라서 두 트랙의 합은 원본과 정확히 같으며 원본 채널 수·스테레오 공간감·위상·길이를
   유지한다.
6. 16kHz 모델이 직접 판단할 수 있는 대역은 8kHz까지다. 기본 고역 확장값 0%에서는
   8kHz를 넘는 원본 성분을 비음악에 보존한다.

이 방식은 독립된 대사·효과음·음악 3트랙 추출보다 음악 제거와 원본 충실도를 우선한다.
대사와 효과음 사이의 오분류는 둘 다 비음악에 남지만, 음악으로 오분류된 소리는 제거될
수 있다. 8kHz 초과 대역을 보존하면 원본의 선명함을 유지할 수 있지만 심벌처럼 높은
음악 성분이 비음악에 일부 남을 수 있다. 결과는 AI 추정이므로 저장 전에 음악과 비음악을
각각 듣고 음악 뮤트 전체 재생도 확인해야 한다.

기반 연구와 모델은 [AV-CASS 프로젝트 페이지](https://cass-flowmatching.github.io/),
[논문](https://mm.kaist.ac.kr/pubs/pdfs/zhang26a.pdf)과
[공개 소스 코드](https://github.com/pantheon5100/AVCASS)에서 확인할 수 있다. 이
프로젝트는 AV-CASS 연구진의 공식 앱이 아니며 연구진의 제휴나 보증을 받지 않았다.

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

GUI 자체는 가벼운 격리 Python 환경으로 실행하고, AI 추론은 휴대용 폴더의 별도 환경을 사용한다.

```powershell
cd video-music-separator
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.txt
.\.venv\Scripts\python.exe app\sound_separator_app.py
```

`py`가 설치된 Python을 찾지 못하면 설치된 Python 실행 파일의 전체 경로로 첫 명령을 실행한다. AI 추론 기능을 사용하려면 별도로 준비한 휴대용 런타임과 모델 파일이 필요하다.

### 빌드와 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\scripts\prepare_ffmpeg_gpl.ps1
.\scripts\build_executables.ps1
.\scripts\build_runtime_installer.ps1
.\scripts\build_portable.ps1 -AIRuntimeDirectory .\audiosep
# 인증서가 있는 경우에만 선택적으로 추가:
.\scripts\build_portable.ps1 -AIRuntimeDirectory .\audiosep -CodeSigningCertificateThumbprint <인증서지문>
```

`build_executables.ps1`와 `build_runtime_installer.ps1`는 인증서가 지정되면 서명하고, 없으면 미서명 EXE를 만든다. 공개 ZIP 경계인 `build_portable.ps1`는 CPython이 빌드 시스템용으로 제공하는 공식 Python 3.13.7 NuGet CI 패키지와 Python.org Tcl/Tk MSI를 고정 크기·SHA-256으로 확인하고 핵심 실행 파일과 Tcl/Tk MSI의 PSF Authenticode 서명을 검증한 뒤 새 격리 환경을 만든다. Tcl/Tk MSI는 관리 추출(`/a`)만 하므로 시스템에 설치된 Python은 변경하지 않으며, NuGet 패키지에 포함된 pip 25.2와 해시 잠금된 wheel만 사용한다. 인증서가 지정되면 두 EXE의 서명·서명자·RFC 3161 타임스탬프를 검증하고, 없으면 두 EXE가 `NotSigned` 상태인지 확인한 뒤 그 사실과 SHA-256을 패키지에 기록한다. 기본 ZIP에는 AV-CASS·CAVP 가중치와 FFmpeg를 넣지 않으며, 새 스테이징 폴더에서 Git 추적 문서와 명시된 파일만 조립한 뒤 압축 전후 파일 목록을 대조한다.

AI 기본 런타임이나 내부용 오프라인 묶음을 만들 때는 검토한 정확한 파일 허용 목록이 필요하다. 목록은 UTF-8 텍스트로 작성하고 `audiosep` 아래의 파일 상대 경로를 슬래시(`/`) 형식으로 한 줄에 하나씩 적는다. 빈 줄과 `#`으로 시작하는 주석은 허용한다. 빌드 스크립트는 목록에 없는 파일을 복사하지 않고, 절대 경로·상위 폴더 이동·중복 경로·링크와 필수 런타임 파일 누락을 거부한다. 현재 설치 폴더를 자동 승인하지 말고 캐시, 모델 가중치, 로그와 개인 파일이 없는 정리된 런타임을 기준으로 목록을 검토해야 한다.

```powershell
.\scripts\build_ai_runtime_archive.ps1 `
  -AIRuntimeDirectory .\clean-runtime\audiosep `
  -AllowlistPath .\runtime-release-allowlist.txt

.\scripts\build_portable.ps1 `
  -AIRuntimeDirectory .\clean-runtime\audiosep `
  -BundleRuntimeAssets `
  -RuntimeAllowlistPath .\runtime-release-allowlist.txt
```

`prepare_ffmpeg_gpl.ps1`는 개발·오프라인 빌드용 Gyan FFmpeg 9.0.1 GPL Essentials 정적 빌드를 고정 URL에서 받고, 아카이브와 세 실행 파일의 고정 크기·SHA-256을 실행 전에 확인한 뒤 빌드 옵션을 검증한다. 검증 방식과 출처는 [FFMPEG_BUILD.md](docs/FFMPEG_BUILD.md)에 설명한다.

휴대용 실동작 검사는 다음처럼 실행한다.

```powershell
.\dist\package\video-music-separator.exe --portable-smoke-test `
  ..\sample.mp4 `
  ..\test-output\portable_avcass_smoke.json
```

### 한계

- 로컬 일반 파일만 입력할 수 있고 FFmpeg 계열 입력 프로토콜은 `file`로 제한된다. 한 번에 처리할 수 있는 영상은 최대 10분이며, 더 긴 영상은 나눠야 한다. 처리 전에 예상 임시 공간과 2GB 안전 여유를 확인한다.
- 음악/비음악 분리는 세부 소리 이름별 독립 추출보다 안정적이지만 AI 분리이므로 100% 무누출을 보장하지 않는다.
- 매우 작은 음악, 음악처럼 반복되는 효과음, 노래·신음처럼 음악과 사람 발성의 경계가 애매한 소리는 반대 트랙에 일부 남을 수 있다.
- AV-CASS는 16kHz 모노로 장면과 소리를 판단하지만, 최종 출력은 그 판정 마스크를 원본 스테레오에 적용한다. 모델이 판단할 수 없는 8kHz 이상은 음악 아님 쪽에 보존한다.
- 저장 전에는 반드시 음악 행과 음악 아님 행을 각각 들어보고, 음악 뮤트 전체 재생까지 확인해야 한다.

### 입력 파일과 결과물 책임

이 앱은 사용자가 선택한 파일을 로컬 PC에서 처리한다. 사용자는 입력 영상·음악·음성에 필요한 권리를 확보하고, 생성된 결과물을 이용하거나 배포할 권한이 있는지 직접 확인해야 한다. AI 분리는 음악의 완전한 제거 또는 음악 외 소리의 보존을 보장하지 않으므로 저장 전에 결과를 직접 검토해야 한다.

앱은 영상·음원·결과물·파일명 또는 사용 통계를 개발자에게 전송하지 않는다. 설치할 때만 Google Drive, Hugging Face, GitHub와 Gyan에 HTTPS 다운로드 요청을 보낸다. 전송되는 일반 접속 정보와 로컬 파일 처리 범위는 [PRIVACY.md](docs/PRIVACY.md)에 기록한다.

영상 미리보기 왼쪽의 `앱 정보·라이선스` 버튼을 누르면 `앱 정보·라이선스·출처` 창에서 AV-CASS와 CAVP의 출처·논문, FFmpeg GPL 빌드 정보와 제3자 고지를 한국어로 확인할 수 있다. 그 아래에는 GPL·LGPL·MIT·Apache의 변경되지 않은 공식 영문 원문이 이어진다.

### 라이선스

자체 코드의 저작권 표시는 `Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)`이다. 자세한 식별 정보와 적용 범위는 [저작권 고지](docs/COPYRIGHT.md)에 기록한다.

이 저장소에서 자체 제작한 코드는 표준 **GNU General Public License version 3 only (`GPL-3.0-only`)**로 제공된다. 사용·열람·수정·무료 재배포와 유료 판매를 허용한다. 실행 파일이나 수정본을 배포할 때는 저작권·라이선스 고지를 유지하고, 그 배포본과 정확히 대응하는 전체 소스를 GPLv3로 함께 제공해야 하며 추가적인 사용 제한을 붙일 수 없다.

수정자는 자신이 새로 작성한 변경분의 저작권을 가질 수 있지만 원본 코드의 저작권을 취득하지 않는다. GPL 조건을 지켜 배포된 원본과 수정본을 다른 사용자가 계속 사용·수정·재배포할 권리를 수정자가 임의로 취소하거나 금지할 수 없다. 정확한 조건은 공식 전문을 그대로 수록한 [LICENSE](LICENSE)를 따른다.

AV-CASS, CAVP, FFmpeg, Python 패키지와 모델 가중치 같은 외부 구성요소 자체에는 각 원 저작권자와 원 라이선스가 계속 적용된다. 실행 파일을 공개 배포하기 전에는 포함한 각 파일의 라이선스와 소스 제공 의무를 다시 확인하고, 해당 실행 파일과 정확히 대응하는 자체 코드의 Git 태그 또는 소스 ZIP을 같은 Release에서 제공해야 한다.

공개 Release를 만들기 전에는 [DISTRIBUTION_CHECKLIST.md](docs/DISTRIBUTION_CHECKLIST.md)를 순서대로 확인한다.

---

## English

A Windows GUI for reducing or removing background music mixed into video audio. AV-CASS separates the original audio into `Music` and `Non-Music` tracks so users can compare the results and save a copy with the music muted beside the source video. The source video remains unchanged, and separation quality is prioritized over processing speed.

- Current application and installer version: `0.2.7` (unsigned public testing prerelease)
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
| GitHub account and CLI | Not required. The installer downloads public Release assets without authentication. |
| Python and FFmpeg | End users do not need to install them separately. The installer downloads the pinned AI Python runtime and the pinned Gyan FFmpeg 9.0.1 GPL Essentials static build. |
| Installation location | Do not run the application from inside the ZIP. Extract the entire ZIP into a normal user-writable folder such as Documents. |

#### 2. Download the Windows Installer

The Windows installer is available as an unsigned public testing prerelease at [`installer-v0.2.7`](https://github.com/Fabio-Cannavaro/video-music-separator/releases/tag/installer-v0.2.7). Download `video-music-separator-0.2.7-windows-x64.zip` and its matching `.sha256` file from `Assets`. The older unsigned `0.2.3` validation assets, the `0.2.5` assets that failed clean-install validation, and the `0.2.6` assets that trimmed trailing video frames when the source audio was shorter than the video were moved to GitHub Drafts and are not offered for installation.

This `0.2.7` prerelease has no Authenticode code signature, so Windows cannot verify its publisher and Windows SmartScreen may display a warning. Download it only from the official GitHub Release and verify the ZIP against the `.sha256` file. The package also provides hashes for both EXEs in `docs/SHA256SUMS.txt` and records the unsigned state in `docs/SIGNING_STATUS.txt`.

The automatically generated `Source code (zip)` and `Source code (tar.gz)` files are not installers and should not be downloaded for installation.

The installation ZIP contains both `video-music-separator-setup.exe` and `video-music-separator.exe`. Keep both EXE files in the same folder. The installer separately downloads the AI Python environment, AV-CASS code, model files, and FFmpeg.

#### 3. Installation Steps

1. **Extract the entire application ZIP** supplied by the distributor into a new folder.
2. Confirm that both EXE files listed above are in that folder.
3. Download the matching `.sha256` file and compare it with the ZIP checksum. Do not run the files if the values differ.
4. **Run `video-music-separator-setup.exe` first.**
5. Select `한국어 / English` in the upper-right corner of the installer. Review the approximately 5.9 GB download size, download sources, model terms, privacy notice, and user responsibilities; then accept the notice and select `Start Installation`.
6. Wait for all downloads and SHA-256 verification to finish.
7. After the completion message appears, run `video-music-separator.exe`.

When a certificate is provided, the public ZIP build verifies both EXEs' Authenticode signatures, signer, and timestamp. Without a certificate, it verifies that both files are unsigned and creates `docs/SIGNING_STATUS.txt`, `docs/SHA256SUMS.txt` for the EXEs, and a separate `.sha256` file for the ZIP. It never presents an unsigned build as signed.

> **Current distribution status:** The `0.2.7` Windows installer assets are an unsigned public prerelease for functional testing. Written permission from the AV-CASS researchers for automatic checkpoint downloads and clean installation testing with a new Windows user account are still pending. This is not represented as an approved final general-use release or an official AV-CASS application. Progress is tracked in the [distribution checklist](docs/DISTRIBUTION_CHECKLIST.md).

#### 4. Components Downloaded by the Installer

1. The installer downloads the following items from their specified distributors.
   - AI Python runtime: two pinned split files from this project's public Release, downloaded without GitHub authentication.
   - AV-CASS `av_cass_checkpoint.pt`: the official AV-CASS Google Drive location
   - CAVP `cavp_epoch66.ckpt`: the pinned commit in the official Diff-Foley Hugging Face repository
   - FFmpeg: Gyan FFmpeg 9.0.1 release essentials GPLv3 static build at an immutable URL
2. It verifies the pinned sizes and SHA-256 values of the AI runtime and models. For FFmpeg, it checks the archive URL, size, SHA-256, and the size and SHA-256 of all three executables before running them, then verifies the build options.
3. Interrupted downloads resume from their `.part` files. Files replace their installation targets only after verification succeeds.

The installer displays the download sources, applicable terms, network-access information, and user responsibilities. Installation begins only after the user reviews and accepts them. Video Music Separator is not an official application of, affiliated with, or endorsed by the AV-CASS researchers or their institutions.

The installer does not redistribute the model files or FFmpeg from this repository or a separate project server. Installation stops on any pinned hash or GPL build mismatch. The installer compares the AI runtime with the complete protected-tree fingerprint pinned in the application source, and the application re-hashes that tree before every Python worker launch. Editable per-user records are not trust anchors. Model files are verified separately against their pinned sizes and SHA-256 values. Actual versions, sources, and checksums are recorded in `docs/runtime-assets.json` inside the application folder.

Even after checksum verification, the application reads checkpoints through PyTorch's restricted `weights_only` mode and allowlists only the minimal metadata types required by each official checkpoint. It does not deserialize arbitrary Python objects without restriction.

The public application ZIP and separate AI runtime assets exclude the former AudioSep/BandIt code and weights and their GPL dependency, `pedalboard`. The exact installed Python package list is available in `docs/PYTHON_PACKAGES_NOTICES.md` inside the application ZIP, the machine-readable inventory in `docs/PYTHON_PACKAGES_INVENTORY.json`, and full license texts in `docs/licenses/python/`.

#### 5. Installation Troubleshooting

- If the installer reports that an AI runtime file cannot be accessed, confirm that the repository and the `runtime-v0.2.0` Release are public and that the distribution URL and asset names have not changed. Private Releases and GitHub login are not supported.
- If the installer was run from inside the ZIP or from a write-restricted location such as `Program Files`, move the entire folder to a user-writable location such as Documents and try again.
- If a download is interrupted, rerun the same installer. Verified files are reused, and incomplete `.part` downloads resume where supported.
- A checksum mismatch is an intentional safety stop. Do not bypass verification; confirm that the distribution URL and pinned version are current.
- If the hardened version reports an AI runtime integrity error, rerun the new `video-music-separator-setup.exe` to reinstall it from the verified archive. An editable marker file alone is not trusted.
- The `An NVIDIA GPU is required` error means a supported NVIDIA GPU and a correctly installed driver are required. No CPU-only fallback is currently provided.

#### 6. Using and Moving the Installed Folder

After installation, the application folder contains:

- Application executable: `video-music-separator.exe`
- Required-components installer: `video-music-separator-setup.exe`
- GPL Essentials FFmpeg executables: `ffmpeg/`
- AI Python environment: `audiosep/env/`
- AV-CASS code and components: `audiosep/avcass/repo/`, `audiosep/avcass/deps/`
- AV-CASS model: `audiosep/avcass/model/av_cass_checkpoint.pt`
- CAVP model: `audiosep/avcass/model/cavp/cavp_epoch66.ckpt`

On the same PC, do not copy this application folder beside every video. Keep it in one location and create a desktop shortcut to `video-music-separator.exe`. `Open Video` can select a video from any folder, and the work folder and saved copy are created beside the selected source video.

To move the application itself, move the entire installed folder rather than either EXE alone. Runtime verification uses the pinned tree fingerprint rather than an installation-path record, so reinstalling only to update a path is unnecessary when every component was moved intact. The `audiosep` folder name is retained for compatibility with the former portable runtime layout.

### Usage

1. Select a clip with `Open Video`.
2. Select `Separate Music from Video`.
3. Select `Listen` on either row to play the video with that separated track in the preview at the top of the application. Select the same button again to stop. Move the slider below the preview to seek directly to the desired position. On first use, the app prepares a lightweight 420×236, 24 fps preview proxy and reuses it afterward.
4. Select `Mute` on the `Music (BGM)` row.
5. Use `Play Full Video` to review the music-muted result and the remaining `Non-Music` audio directly. Audio is the master clock; video decoding runs separately from UI work, and late video frames are skipped to prioritize audio sync and responsiveness.
6. Select `Save Copy` at the bottom of the window to create `<source name>_music-removed.mp4`. If that name already exists, the app adds `_2`, `_3`, and so on to preserve earlier copies. Preview proxies are never used for the saved copy; its encoded video stream is copied unchanged from the source.

Selecting `한국어 / English` to the right of the video preview immediately changes the window title, buttons, status messages, result table, warnings, and license/source window to the selected language.

The master volume slider starts at 100 and applies to the source, muted mix, and both separated tracks. AV-CASS runtime paths are managed automatically inside the portable folder.

During processing, a random `<video name>_sound_work_<nonce>` folder is created beside the video. The application creates an ownership marker containing the per-run nonce and canonical source path, and deletes only the folder owned by that run. It never reuses or deletes a pre-existing predictable work folder. The owned folder remains for diagnosis if saving is cancelled, fails, or its marker no longer matches.

Inputs are restricted to supported media formats on fixed local disks. UNC paths, network drives, reparse points, and playlist formats are rejected. Each input is limited to 10 minutes, video to 7680×4320, and audio to 8 channels at 192 kHz. FFmpeg allocation and probing, external-tool output, worker log-line length, and the pending log queue are also bounded.

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

### How This Application Separates Music and Non-Music

This application uses the official audio-visual AV-CASS checkpoint and CAVP checkpoint to create
music and non-music through the following pipeline. Its key characteristics are CAVP full-scene
conditioning, conversion of three generated speech, sfx, and music estimates into a music mask,
preservation of the original 44.1 kHz stereo signal, and one-second cosine-squared overlap-add.

1. The source audio is retained as 44.1 kHz stereo for final output. For AI analysis, the left and
   right channels are mixed to mono and resampled to 16 kHz.
2. The video is sampled at 4 fps and each frame is center-cropped to 224×224. The application
   currently sends these full-scene frames to the CAVP scene encoder. It does not perform face
   detection or run a separate facial encoder.
3. In approximately 8.18-second chunks, the AV-CASS conditional flow-matching model analyzes the
   mixture and scene features and generates `speech`, `sfx`, and `music` estimates simultaneously.
   Each chunk uses 250 inference steps by default. Adjacent chunks overlap by one second and are
   combined with cosine-squared overlap-add.
4. The application combines `speech + sfx` as the non-music estimate and derives a smooth
   time-frequency music mask from the energy ratio between the music and non-music estimates.
   Rather than using the AI-generated waveforms directly as final output, it applies this mask
   consistently to the retained 44.1 kHz stereo source.
5. Source components selected by the mask form the music track, and non-music is constructed as
   `source - music`. The two tracks therefore sum exactly to the source while preserving channel
   count, stereo image, phase, and duration.
6. A 16 kHz model can directly evaluate frequencies only up to 8 kHz. With the default 0% high-band
   extension, source content above 8 kHz is preserved in non-music.

This design prioritizes music removal and fidelity to the source over extraction of three clean,
independent speech, effects, and music tracks. Confusion between speech and effects remains in
non-music, while a sound misclassified as music may be removed. Preserving content above 8 kHz
retains source clarity but can also leave some high-frequency music such as cymbals in non-music.
Because the result is an AI estimate, users should listen to both tracks and review full playback
with music muted before saving.

See the [AV-CASS project page](https://cass-flowmatching.github.io/),
[paper](https://mm.kaist.ac.kr/pubs/pdfs/zhang26a.pdf), and
[public source code](https://github.com/pantheon5100/AVCASS) for the underlying research and model.
This project is not an official AV-CASS application and is not affiliated with or endorsed by the
AV-CASS researchers.

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
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.txt
.\.venv\Scripts\python.exe app\sound_separator_app.py
```

If `py` cannot find the installed Python interpreter, use the full path to the installed Python executable for the first command. AI inference requires a separately prepared portable runtime and model files.

### Build and Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\scripts\prepare_ffmpeg_gpl.ps1
.\scripts\build_executables.ps1
.\scripts\build_runtime_installer.ps1
.\scripts\build_portable.ps1 -AIRuntimeDirectory .\audiosep
# Optional only when a certificate is available:
.\scripts\build_portable.ps1 -AIRuntimeDirectory .\audiosep -CodeSigningCertificateThumbprint <thumbprint>
```

`build_executables.ps1` and `build_runtime_installer.ps1` sign when a certificate is supplied and otherwise create unsigned EXEs. The public boundary, `build_portable.ps1`, verifies the official Python 3.13.7 NuGet CI package provided by CPython for build systems and the Python.org Tcl/Tk MSI against pinned size and SHA-256 values, then verifies PSF Authenticode signatures on the critical executables and the Tcl/Tk MSI before creating a fresh isolated environment. The Tcl/Tk MSI is administratively extracted (`/a`), so the build does not modify a system Python installation. It uses only the NuGet package's pip 25.2 and hash-locked wheels. With a certificate, it verifies both EXEs' signature, signer, and RFC 3161 timestamp. Without one, it requires both EXEs to report `NotSigned` and records that state and their SHA-256 values in the package. The package is assembled in a fresh staging directory from tracked documentation and explicitly selected files, with exact pre- and post-ZIP file-set checks.

Building the base AI runtime or an internal offline bundle requires a reviewed exact-file allowlist. Save it as UTF-8 text with one slash-separated file path relative to `audiosep` per line; blank lines and comments beginning with `#` are allowed. Files not listed are not copied, and the scripts reject absolute paths, parent traversal, duplicates, links, and missing required runtime files. Do not automatically approve the current installed folder. Review the list against a clean runtime that contains no caches, model weights, logs, or personal files.

```powershell
.\scripts\build_ai_runtime_archive.ps1 `
  -AIRuntimeDirectory .\clean-runtime\audiosep `
  -AllowlistPath .\runtime-release-allowlist.txt

.\scripts\build_portable.ps1 `
  -AIRuntimeDirectory .\clean-runtime\audiosep `
  -BundleRuntimeAssets `
  -RuntimeAllowlistPath .\runtime-release-allowlist.txt
```

`prepare_ffmpeg_gpl.ps1` downloads the pinned Gyan FFmpeg 9.0.1 GPL Essentials static build from an immutable URL. It verifies the archive and all three executables against first-party size and SHA-256 locks before executing them, then checks the build options. See [FFMPEG_BUILD.en.md](docs/FFMPEG_BUILD.en.md).

Run the portable smoke test as follows:

```powershell
.\dist\package\video-music-separator.exe --portable-smoke-test `
  ..\sample.mp4 `
  ..\test-output\portable_avcass_smoke.json
```

### Limitations

- Inputs must be local regular files, and FFmpeg-family input protocols are restricted to `file`. A single job is limited to 10 minutes; split longer media first. The application checks estimated scratch use plus a 2 GB safety reserve before extraction.
- Music/non-music separation is more stable than independent extraction by detailed sound name, but no AI separation can guarantee zero leakage.
- Very quiet music, rhythmically repeated effects, and sounds near the boundary between music and human vocalization—such as singing or moaning—may partially remain in the opposite track.
- AV-CASS analyzes the scene and audio at 16 kHz mono, but the final output applies its decision mask to the original stereo signal. Frequencies above 8 kHz that the model cannot evaluate are preserved in the non-music track.
- Always listen to both the Music and Non-Music rows and review full playback with music muted before saving.

### Input and Output Responsibility

The application processes user-selected files locally on the PC. Users must obtain the necessary rights to the input video, music, and speech and independently confirm their right to use or distribute generated results. AI separation does not guarantee complete music removal or preservation of non-music audio, so review results before saving.

The application does not transmit video, audio, output, file names, or usage analytics to the developer. HTTPS download requests are sent only to Google Drive, Hugging Face, GitHub, and Gyan during installation. Ordinary connection information transmitted and the scope of local file processing are documented in [PRIVACY.en.md](docs/PRIVACY.en.md).

The `App Info & Licenses` button to the left of the video preview opens the `App Information, Licenses & Sources` page. In Korean mode, Korean notices and sources appear first, followed by the unmodified official GPL, LGPL, MIT, and Apache license texts.

### License

Copyright for the original project code is identified as `Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)`. See the [copyright notice](docs/COPYRIGHT.en.md) for the detailed identity and scope.

Original code created for this repository is provided under the standard **GNU General Public License version 3 only (`GPL-3.0-only`)**. Use, inspection, modification, free redistribution, and commercial sale are permitted. Distribution of an executable or modified version must preserve copyright and license notices, provide the complete corresponding source under GPLv3, and impose no additional restrictions.

A modifier may own copyright in newly authored changes but does not acquire copyright in the original code. A modifier cannot revoke or prohibit another user's continuing right to use, modify, or redistribute the original and modified code distributed in compliance with the GPL. The exact terms are governed by the unmodified official [LICENSE](LICENSE) text.

External components such as AV-CASS, CAVP, FFmpeg, Python packages, and model weights remain governed by their respective copyright holders and licenses. Before publicly distributing an executable, verify the license and source-provision obligations for every included file and provide the Git tag or source ZIP exactly corresponding to that executable in the same Release.

Before creating a public Release, follow [DISTRIBUTION_CHECKLIST.md](docs/DISTRIBUTION_CHECKLIST.md) in order.

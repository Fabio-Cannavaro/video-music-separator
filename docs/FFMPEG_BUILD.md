# FFmpeg GPL 빌드 정보

이 앱은 FFmpeg를 앱 코드에 링크하지 않고 별도 명령줄 프로그램으로 실행한다. 기본 온라인 설치본에는 FFmpeg 바이너리가 들어 있지 않으며, 설치할 때 Gyan의 공식 배포 서버에서 사용자 PC로 직접 내려받는다.

## 설치 대상

- 배포자: Gyan Doshi의 Windows용 FFmpeg 빌드
- 버전: `9.0.1 release essentials`
- 고정 아카이브: <https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.1-essentials_build.zip>
- 아카이브 크기: `111253802` 바이트
- 아카이브 SHA-256: `fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9`
- 배포 안내: <https://www.gyan.dev/ffmpeg/builds/>
- FFmpeg 소스: <https://github.com/FFmpeg/FFmpeg>
- 적용 라이선스: GNU General Public License version 3

버전·주소·크기·SHA-256은 이 저장소의 검토된 first-party 잠금값이다. 새 upstream 릴리스는 코드와 테스트의 잠금값을 명시적으로 갱신하기 전에는 자동 채택하지 않는다. 설치 프로그램은 다운로드 아카이브를 검증하고, 압축을 푼 `ffmpeg`, `ffprobe`, `ffplay` 각각의 고정 크기·SHA-256을 실행 전에 먼저 확인한다. 그 뒤 `-version` 출력에서 다음 조건을 모두 검증한다.

- 세 실행 파일 모두 정확히 9.0.1 버전이다.
- Gyan의 `essentials_build` 식별자가 포함되어 있다.
- `--enable-gpl`, `--enable-version3`, `--enable-static`이 포함되어 있다.
- `--enable-nonfree`가 포함되어 있지 않다.

검증을 통과한 세 실행 파일만 앱의 `ffmpeg/` 폴더에 설치한다. 정확히 설치된 버전, 최종 다운로드 URL, 파일 크기와 SHA-256은 앱 폴더의 `docs/runtime-assets.json`에 기록되며 앱의 `앱 정보·라이선스` 화면에서도 확인할 수 있다.

개발·내부 오프라인 빌드에서는 `scripts/prepare_ffmpeg_gpl.ps1`가 같은 고정 자산을 내려받아 동일한 검증을 수행한다.

## 배포 범위와 의무

기본 온라인 설치 ZIP은 FFmpeg 바이너리를 포함하지 않는다. 사용자의 설치 프로그램이 Gyan에서 직접 받는 구조이므로 이 프로젝트의 기본 ZIP이 FFmpeg 바이너리를 재배포하는 것은 아니다.

`build_portable.ps1 -BundleRuntimeAssets`로 만드는 내부 오프라인 묶음은 FFmpeg 바이너리를 실제로 포함한다. 이를 공개 배포하려면 GPLv3 전문과 저작권 고지를 유지하고, 포함한 바이너리에 정확히 대응하는 FFmpeg 및 빌드 의존성의 완전한 소스와 빌드 방법을 제공하는 등 GPL 의무를 별도로 충족해야 한다.

## 수정 내역

이 프로젝트는 내려받은 FFmpeg 바이너리와 소스를 수정하지 않는다. 내부 오프라인 묶음에서도 원 배포본의 세 실행 파일을 그대로 사용한다.

# FFmpeg LGPL 빌드 정보

이 앱은 FFmpeg를 앱 코드에 링크하지 않고 별도 명령줄 프로그램으로 실행한다. 온라인 설치본에는 FFmpeg 바이너리가 들어 있지 않으며, 설치할 때 BtbN의 공식 GitHub Release에서 직접 내려받는다.

## 설치 대상

- 배포자: BtbN/FFmpeg-Builds
- Release: `latest`
- 파일: `ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip`
- 버전 계열: FFmpeg 8.1
- 적용 라이선스: GNU Lesser General Public License version 3
- Release 정보: <https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest>
- 바이너리 다운로드: <https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip>
- 배포 프로젝트: <https://github.com/BtbN/FFmpeg-Builds>
- FFmpeg 소스: <https://github.com/FFmpeg/FFmpeg>

`latest`가 가리키는 실제 바이너리 버전과 체크섬은 BtbN의 빌드 갱신에 따라 달라질 수 있다. 설치 프로그램은 공식 GitHub Release API에서 선택한 파일의 실제 크기와 `sha256` digest를 읽은 뒤 다운로드 결과와 대조한다. 이어서 `ffmpeg -version`을 실행해 다음 조건을 모두 확인한다.

- 출력 버전이 `ffmpeg version n8.1` 계열이다.
- `--enable-shared`가 포함되어 있다.
- `--enable-gpl`과 `--enable-nonfree`가 포함되어 있지 않다.
- 필요한 실행 파일과 공유 DLL이 모두 존재한다.

검증을 통과한 파일만 앱의 `ffmpeg/` 폴더에 설치한다. 정확히 설치된 버전, 다운로드 URL, 파일 크기와 SHA-256은 앱 폴더의 `docs/runtime-assets.json`에 기록되며 앱의 `라이선스·출처` 화면에서도 확인할 수 있다.

개발·오프라인 빌드에서는 `scripts/prepare_ffmpeg_lgpl.ps1`가 같은 공식 Release 자산을 찾아 SHA-256과 빌드 옵션을 검증한다.

## 수정 내역

이 프로젝트는 내려받은 FFmpeg 바이너리와 소스를 수정하지 않는다. 내부용 오프라인 묶음을 만들 때에도 원 배포본의 `bin` 폴더에 있던 실행 파일과 공유 라이브러리를 그대로 사용한다.

FFmpeg 바이너리를 포함하는 공개 배포본을 별도로 만들 경우에는 이 문서, LGPL·GPL 전문, 제3자 고지와 해당 바이너리에 정확히 대응하는 FFmpeg 및 빌드 의존성 소스 제공 의무를 다시 확인해야 한다.

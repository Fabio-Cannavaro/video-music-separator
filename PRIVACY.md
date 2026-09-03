# 개인정보 및 외부 통신 안내

Video Music Separator는 사용자가 선택한 영상과 음원을 로컬 PC에서 처리한다. 앱과 설치 프로그램은 영상, 음원, 분리 결과, 파일명 또는 사용 통계를 개발자에게 업로드하지 않는다.

## 설치 중 발생하는 외부 통신

필수 구성요소 설치 프로그램은 다음 배포처에 HTTPS 다운로드 요청을 보낸다.

| 내려받는 항목 | 접속 대상 | 용도 |
| --- | --- | --- |
| AI Python 실행환경과 AV-CASS 실행 코드 | `github.com`, `objects.githubusercontent.com` 등 GitHub가 사용하는 다운로드 호스트 | 이 프로젝트의 고정 Release 자산 다운로드 |
| AV-CASS 체크포인트 | `drive.usercontent.google.com` | AV-CASS 공식 제공 파일 다운로드 |
| CAVP 체크포인트 | `huggingface.co` | Diff-Foley 공식 모델 저장소 다운로드 |
| FFmpeg LGPL 공유 빌드 | `github.com`, `objects.githubusercontent.com` 등 GitHub가 사용하는 다운로드 호스트 | BtbN GitHub Release 다운로드 |

설치 프로그램에 고정된 다운로드 주소:

- AI Python 실행환경: `https://github.com/Fabio-Cannavaro/video-music-separator/releases/download/runtime-v0.2.0/` 아래의 두 분할 파일
- AV-CASS: `https://drive.usercontent.google.com/download?id=1_d-RCP111No-wS-wrmxyK-zH87Sm2xzf&export=download&confirm=t`
- CAVP: `https://huggingface.co/SimianLuo/Diff-Foley/resolve/b17ddbe76e6d42f4b4135eeb443b1c1644267e3e/diff_foley_ckpt/cavp_epoch66.ckpt?download=true`
- FFmpeg: `https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-20-13-45/ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip`

서버 운영자는 일반적인 웹 다운로드 과정에서 IP 주소, 요청 시각, 다운로드 URL, HTTP User-Agent, 이어받기용 Range 헤더와 같은 접속 정보를 수신하거나 기록할 수 있다. 각 서버의 개인정보 처리방침과 이용조건은 해당 운영자가 정한다.

설치 파일은 AI 실행환경·모델·FFmpeg의 URL, 예상 파일 크기와 SHA-256을 고정해 확인한다. 설치 완료 후 일반적인 영상 처리에는 인터넷 연결이 필요하지 않다.

## 로컬 파일

- 원본 영상과 음원은 사용자가 선택한 위치에서 읽는다.
- 임시 분리 파일은 원본 영상 옆의 `<영상이름>_sound_work` 폴더에 저장한다.
- 정상적으로 사본 저장과 검증이 끝나면 임시 작업 폴더를 삭제한다.
- 저장 실패나 검증 실패가 발생하면 복구와 진단을 위해 임시 파일이 남을 수 있다.
- 설치된 구성요소의 출처·버전·체크섬은 앱 폴더의 `runtime-assets.json`에 기록한다.

## 사용자 책임

사용자는 처리할 영상·음원의 저작권과 이용 권리를 확인하고, 생성된 결과물을 이용·공유·배포할 권한이 있는지 직접 확인해야 한다.

마지막 갱신: 2026-09-03

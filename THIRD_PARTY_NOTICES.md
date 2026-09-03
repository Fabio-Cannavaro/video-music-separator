# Third-party notices

이 저장소에는 아래 프로젝트의 소스, 모델 가중치 또는 실행 파일을 직접 포함하지 않는다. 앱을 실행하거나 휴대용 배포본을 만들 때 별도로 결합하는 외부 구성요소에는 각 원 저작권자와 원 라이선스의 조건이 그대로 적용된다.

## AV-CASS

- 프로젝트: <https://cass-flowmatching.github.io/>
- 소스: <https://github.com/pantheon5100/AVCASS>
- 공식 저장소의 `LICENSE.txt`: MIT License

## TIGER / TIGER-DnR

- 소스: <https://github.com/JusperLee/TIGER>
- 모델: <https://huggingface.co/JusperLee/TIGER-DnR>
- 공식 소스 저장소: MIT License
- 공식 TIGER-DnR 모델 카드: Apache License 2.0

## Diff-Foley CAVP

- 모델: <https://huggingface.co/SimianLuo/Diff-Foley>
- 공식 모델 페이지: MIT License
- AV-CASS의 영상 인코더가 사용하는 별도 체크포인트다. 다운로드·이용·재배포 전 모델 카드와 저장소의 최신 조건을 확인해야 한다.

## AudioSep and BandIt

- AudioSep: <https://github.com/Audio-AGI/AudioSep>
- BandIt: <https://github.com/kwatcharasupat/bandit-v2>
- AudioSep 공식 소스 저장소: MIT License
- BandIt v2 공식 소스 저장소: Apache License 2.0
- 현재 사용자 화면에는 노출되지 않는 호환 작업자 코드가 남아 있다. 이 저장소는 해당 프로젝트의 소스나 가중치를 포함하지 않는다.

## FFmpeg

- 홈페이지와 법적 안내: <https://ffmpeg.org/legal.html>

이 앱은 FFmpeg 명령줄 프로그램을 외부 프로세스로 실행한다. 이 소스 저장소에는 FFmpeg 바이너리가 없다. 휴대용 실행 파일과 함께 FFmpeg를 배포하면 실제 빌드 구성에 따라 LGPL 또는 GPL 의무가 생길 수 있다. 공개 배포본은 사용한 바이너리의 정확한 구성, 해당 소스, 빌드 방법, 라이선스 문구를 함께 준비해야 한다.

## Python packages

`requirements.txt`와 휴대용 AI 환경에서 설치되는 Python 패키지는 각 패키지의 자체 라이선스를 따른다. 공개 배포 전에 실제 잠금 버전 기준으로 고지 목록을 다시 생성해야 한다.

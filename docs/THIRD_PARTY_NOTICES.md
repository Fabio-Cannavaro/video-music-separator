# 제3자 고지, 출처 및 논문

Video Music Separator의 자체 코드는 루트 `LICENSE`를 따른다. 아래 외부 구성요소의 코드·모델·실행 파일에는 각 원 저작권자와 원 라이선스가 적용되며, 앱의 라이선스로 바뀌지 않는다.

## AV-CASS

이 앱의 음악/비음악 분리에 AV-CASS를 사용한다.

Video Music Separator는 AV-CASS 연구진 또는 관련 기관의 공식 앱이 아니며, 해당 연구진과 제휴하거나 보증받지 않았다.

- 프로젝트: <https://cass-flowmatching.github.io/>
- 소스: <https://github.com/pantheon5100/AVCASS>
- 체크포인트 안내: AV-CASS 공식 저장소의 README
- 코드 라이선스: MIT License
- 원 라이선스 고지: Copyright (c) Meta Platforms, Inc. and affiliates.
- 라이선스 전문: `licenses/MIT.txt`

논문:

> Kang Zhang, Suyeon Lee, Arda Senocak, and Joon Son Chung. “Cinematic Audio Source Separation Using Visual Cues.” CVPR 2026. <https://arxiv.org/abs/2603.26113>

AV-CASS 공식 저장소는 코드에 MIT License를 표시하지만, README에서 링크한 사전학습 체크포인트에 별도의 재배포 조건을 명시하지 않았다. 권리자의 명시적 확인 전에는 체크포인트를 공개 저장소에 올리지 않는다.

온라인 설치에서는 `video-music-separator-setup.exe`가 AV-CASS 프로젝트가 안내한 Google Drive에서 `av_cass_checkpoint.pt`를 사용자 PC로 직접 내려받고, 공개 설치 파일이나 이 저장소에는 체크포인트를 포함하지 않는다.

## CAVP / Diff-Foley

AV-CASS의 영상 특징 추출에 Diff-Foley의 CAVP 체크포인트와 관련 코드를 사용한다.

- 모델: <https://huggingface.co/SimianLuo/Diff-Foley>
- 소스: <https://github.com/luosiallen/Diff-Foley>
- 프로젝트: <https://diff-foley.github.io/>
- CAVP 모델 페이지 라이선스 표기: MIT
- Diff-Foley 소스 저장소 라이선스: Apache License 2.0
- 라이선스 전문: `licenses/MIT.txt`, `licenses/Apache-2.0.txt`

온라인 설치에서는 Diff-Foley 공식 Hugging Face 저장소의 고정 커밋에서 `cavp_epoch66.ckpt`를 사용자 PC로 직접 내려받고 SHA-256을 확인한다.

논문:

> Simian Luo, Chuanhao Yan, Chenxu Hu, and Hang Zhao. “Diff-Foley: Synchronized Video-to-Audio Synthesis with Latent Diffusion Models.” NeurIPS 2023. <https://arxiv.org/abs/2306.17203>

## AudioSep and BandIt compatibility source

소스 저장소에는 사용자 화면에 노출되지 않는 이전 호환 작업자 코드가 남아 있지만, 공개 Windows ZIP에는 AudioSep/BandIt 코드·가중치와 `pedalboard`를 포함하지 않는다. 관련 기능을 다시 배포할 때는 실제 포함 버전의 고지와 라이선스를 별도로 확인해야 한다.

- AudioSep: <https://github.com/Audio-AGI/AudioSep> — MIT License
- BandIt v2: <https://github.com/kwatcharasupat/bandit-v2> — Apache License 2.0
- 라이선스 전문: `licenses/MIT.txt`, `licenses/Apache-2.0.txt`

## FFmpeg

이 앱은 FFmpeg 명령줄 프로그램을 외부 프로세스로 실행한다.

- 프로젝트 및 법적 안내: <https://ffmpeg.org/legal.html>
- 현재 휴대용 배포본: BtbN `n8.1.2-44-g7c533d0f86-20260820` Windows x64 LGPL shared build
- 적용 라이선스: GNU Lesser General Public License version 3
- 바이너리와 정확한 출처·체크섬·빌드 설정: `FFMPEG_BUILD.md`
- 라이선스 전문: `licenses/LGPL-3.0.txt`, `licenses/GPL-3.0.txt`

이 빌드는 공유 라이브러리를 사용하며 `--enable-gpl`과 `--enable-nonfree`를 사용하지 않는다. 공개 배포 전에는 포함한 바이너리의 정확한 빌드 설정과 일치하는 FFmpeg 및 빌드 의존성 소스, 빌드 방법, 저작권 고지와 라이선스 전문을 같은 Release에 함께 제공해야 한다.

기본 온라인 설치 파일은 FFmpeg 바이너리를 포함하지 않는다. 설치 시 BtbN의 고정 LGPL 공유 빌드를 공식 GitHub Release에서 사용자 PC로 직접 내려받고, 압축 파일의 SHA-256과 FFmpeg의 버전·빌드 옵션을 검사한다.

## Python packages

`requirements.txt`와 별도 GitHub Release 자산으로 설치되는 AI Python 환경의 패키지는 각 패키지의 자체 라이선스를 따른다. 공개 Windows ZIP을 만들 때 실제 런타임 원본을 검사해 `PYTHON_PACKAGES_NOTICES.md`, `PYTHON_PACKAGES_INVENTORY.json`과 `licenses/python/`을 자동 생성한다.

## User-provided media

이 앱은 사용자가 선택한 영상·음원을 로컬 PC에서 처리한다. 사용자는 입력 파일의 저작권과 이용 권리를 확인하고, 처리 결과를 사용·공유·배포할 책임을 진다. 이 앱은 입력 파일이나 결과물에 대한 권리를 부여하지 않는다.

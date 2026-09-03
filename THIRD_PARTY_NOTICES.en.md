# Third-party notices, sources, and papers

Video Music Separator's own code is governed by the root `LICENSE`. The code, models, and executables of the external components below remain governed by their respective copyright holders and original licenses; the application's license does not replace them.

## AV-CASS

This application uses AV-CASS for music/non-music separation.

Video Music Separator is not an official AV-CASS application and is not affiliated with or endorsed by the AV-CASS researchers or their institutions.

- Project: <https://cass-flowmatching.github.io/>
- Source: <https://github.com/pantheon5100/AVCASS>
- Checkpoint information: README in the official AV-CASS repository
- Code license: MIT License
- Original copyright notice: Copyright (c) Meta Platforms, Inc. and affiliates.
- Full license text: `licenses/MIT.txt`

Paper:

> Kang Zhang, Suyeon Lee, Arda Senocak, and Joon Son Chung. “Cinematic Audio Source Separation Using Visual Cues.” CVPR 2026. <https://arxiv.org/abs/2603.26113>

The official AV-CASS repository identifies the code as MIT-licensed, but it does not specify separate redistribution terms for the pretrained checkpoint linked from its README. Do not upload the checkpoint to a public repository before receiving explicit confirmation from the rights holder.

For online installation, `video-music-separator-setup.exe` downloads `av_cass_checkpoint.pt` directly from the Google Drive location identified by the AV-CASS project. The checkpoint is not included in this repository or in the public installer binary.

## CAVP / Diff-Foley

AV-CASS uses the Diff-Foley CAVP checkpoint and related code to extract visual features.

- Model: <https://huggingface.co/SimianLuo/Diff-Foley>
- Source: <https://github.com/luosiallen/Diff-Foley>
- Project: <https://diff-foley.github.io/>
- License shown on the CAVP model page: MIT
- Diff-Foley source repository license: Apache License 2.0
- Full license texts: `licenses/MIT.txt`, `licenses/Apache-2.0.txt`

For online installation, `cavp_epoch66.ckpt` is downloaded directly from a pinned commit in the official Diff-Foley Hugging Face repository and verified with SHA-256.

Paper:

> Simian Luo, Chuanhao Yan, Chenxu Hu, and Hang Zhao. “Diff-Foley: Synchronized Video-to-Audio Synthesis with Latent Diffusion Models.” NeurIPS 2023. <https://arxiv.org/abs/2306.17203>

## AudioSep and BandIt compatibility source

Legacy compatibility worker code that is not exposed in the user interface remains in the source tree. The public Windows ZIP excludes AudioSep/BandIt code, weights, and `pedalboard`. Recheck the notices and licenses for the exact versions before distributing those components again.

- AudioSep: <https://github.com/Audio-AGI/AudioSep> — MIT License
- BandIt v2: <https://github.com/kwatcharasupat/bandit-v2> — Apache License 2.0
- Full license texts: `licenses/MIT.txt`, `licenses/Apache-2.0.txt`

## FFmpeg

This application runs the FFmpeg command-line programs as external processes.

- Project and legal information: <https://ffmpeg.org/legal.html>
- Current portable distribution: BtbN `n8.1.2-44-g7c533d0f86-20260820` Windows x64 LGPL shared build
- Applicable license: GNU Lesser General Public License version 3
- Binary source, checksums, and build configuration: `FFMPEG_BUILD.en.md`
- Full license texts: `licenses/LGPL-3.0.txt`, `licenses/GPL-3.0.txt`

This build uses shared libraries and does not use `--enable-gpl` or `--enable-nonfree`. Before a public release, provide the exact corresponding FFmpeg and build-dependency sources, build instructions, copyright notices, and full license texts alongside the binary.

The online installer does not contain the FFmpeg binary. During installation it downloads a pinned LGPL shared build directly from BtbN's official GitHub Release and verifies the archive SHA-256 together with the FFmpeg version and build options.

## Python packages

The Python packages listed in `requirements.txt` and installed in the portable AI environment are governed by their own licenses. The public Windows ZIP build scans the exact distribution folder and generates `PYTHON_PACKAGES_NOTICES.md`, `PYTHON_PACKAGES_INVENTORY.json`, and `licenses/python/`.

## User-provided media

This application processes user-selected video and audio locally on the user's PC. The user is responsible for confirming the copyright and usage rights of input files and for using, sharing, or distributing the results. This application does not grant rights to the input files or generated results.

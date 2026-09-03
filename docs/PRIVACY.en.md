# Privacy and Network Access Notice

Video Music Separator processes user-selected video and audio locally on the user's PC. The application and installer do not upload media, separation results, file names, or usage analytics to the developer.

## Network access during installation

The required-components installer sends HTTPS download requests to the following distributors.

| Download | Destination | Purpose |
| --- | --- | --- |
| AI Python runtime and AV-CASS runtime code | `github.com`, `objects.githubusercontent.com`, and other download hosts used by GitHub | Download pinned assets from this project's GitHub Release |
| AV-CASS checkpoint | `drive.usercontent.google.com` | Download the file provided by the AV-CASS project |
| CAVP checkpoint | `huggingface.co` | Download from the official Diff-Foley model repository |
| FFmpeg LGPL shared build | `github.com`, `objects.githubusercontent.com`, and other download hosts used by GitHub | Download the BtbN GitHub Release |

Download URLs pinned in the installer:

- AI Python runtime: two split files below `https://github.com/Fabio-Cannavaro/video-music-separator/releases/download/runtime-v0.2.0/`
- AV-CASS: `https://drive.usercontent.google.com/download?id=1_d-RCP111No-wS-wrmxyK-zH87Sm2xzf&export=download&confirm=t`
- CAVP: `https://huggingface.co/SimianLuo/Diff-Foley/resolve/b17ddbe76e6d42f4b4135eeb443b1c1644267e3e/diff_foley_ckpt/cavp_epoch66.ckpt?download=true`
- FFmpeg: `https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-20-13-45/ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip`

As part of an ordinary web download, each server operator may receive or log connection data such as the IP address, request time, download URL, HTTP User-Agent, and Range header used to resume a download. Each operator controls its own privacy policy and terms.

The installer first attempts to download the AI Python runtime from the GitHub Release without authentication. A public Release requires neither a GitHub account nor GitHub CLI. If public access is denied, the installer treats the Release as private and uses the GitHub CLI login on this PC. If that login is missing or expired, the installer starts GitHub CLI web authentication and copies the one-time authentication code to the clipboard. The installer does not embed, directly read, or store the GitHub token; authentication and credential storage are handled by GitHub CLI. GitHub may then receive the signed-in account identity and ordinary authentication request data.

The installer pins and verifies the URL, expected size, and SHA-256 of the AI runtime, each model, and the FFmpeg archive. Normal video processing does not require an internet connection after installation.

## Local files

- Source media is read from the location selected by the user.
- Temporary separation files are stored beside the source in `<video name>_sound_work`.
- The temporary work folder is deleted after a copy is saved and verified successfully.
- Temporary files may remain for recovery and diagnosis after a save or verification failure.
- Sources, versions, and checksums of installed components are recorded in `runtime-assets.json` in the application folder.

## User responsibility

The user is responsible for confirming the copyright and usage rights of input media and the right to use, share, or distribute generated results.

Last updated: 2026-09-03

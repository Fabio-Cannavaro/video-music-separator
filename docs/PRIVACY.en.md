# Privacy and Network Access Notice

Video Music Separator processes user-selected video and audio locally on the user's PC. The application and installer do not upload media, separation results, file names, or usage analytics to the developer.

## Network access during installation

The required-components installer sends HTTPS download requests to the following distributors.

| Download | Destination | Purpose |
| --- | --- | --- |
| AI Python runtime and AV-CASS runtime code | `github.com`, `objects.githubusercontent.com`, and other download hosts used by GitHub | Download pinned assets from this project's GitHub Release |
| AV-CASS checkpoint | `drive.usercontent.google.com` | Download the file provided by the AV-CASS project |
| CAVP checkpoint | `huggingface.co` | Download from the official Diff-Foley model repository |
| FFmpeg GPL Essentials build | `www.gyan.dev` | Download the pinned Gyan FFmpeg 9.0.1 distribution file |

Download URLs used by the installer:

- AI Python runtime: two split files below `https://github.com/Fabio-Cannavaro/video-music-separator/releases/download/runtime-v0.2.0/`
- AV-CASS: `https://drive.usercontent.google.com/download?id=1_d-RCP111No-wS-wrmxyK-zH87Sm2xzf&export=download&confirm=t`
- CAVP: `https://huggingface.co/SimianLuo/Diff-Foley/resolve/b17ddbe76e6d42f4b4135eeb443b1c1644267e3e/diff_foley_ckpt/cavp_epoch66.ckpt?download=true`
- FFmpeg 9.0.1: `https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.1-essentials_build.zip`

As part of an ordinary web download, each server operator may receive or log connection data such as the IP address, request time, download URL, HTTP User-Agent, and Range header used to resume a download. Each operator controls its own privacy policy and terms.

The installer downloads the AI Python runtime from the public GitHub Release without authentication. No GitHub account or GitHub CLI is required. The installer does not start GitHub login, read or store GitHub credentials, or copy an authentication code to the clipboard.

The installer verifies first-party pinned URLs, expected sizes, and SHA-256 values for the AI runtime, each model, and FFmpeg 9.0.1. It also checks each FFmpeg executable's pinned size and SHA-256 before execution, then verifies the GPL Essentials static-build options. Normal video processing does not require an internet connection after installation.

Normal media-processing inputs are restricted to supported container formats on fixed local disks. UNC paths, network drives, reparse points, playlists, and FFmpeg network protocols are not accepted as inputs.

## Local files

- Source media is read from the location selected by the user.
- Temporary separation files are stored beside the source in a per-run `<video name>_sound_work_<nonce>` folder.
- The temporary work folder is deleted after a copy is saved and verified successfully.
- Temporary files may remain for recovery and diagnosis after a save or verification failure.
- Sources, versions, and checksums of installed components are recorded in `docs/runtime-assets.json` in the application folder.

## User responsibility

The user is responsible for confirming the copyright and usage rights of input media and the right to use, share, or distribute generated results.

Last updated: 2026-09-05

# FFmpeg LGPL build information

This application runs FFmpeg as a separate command-line program and does not link FFmpeg into the application code. The online installer does not contain FFmpeg binaries; it downloads them directly from BtbN's official GitHub Release during installation.

## Installation target

- Distributor: BtbN/FFmpeg-Builds
- Release: `latest`
- File: `ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip`
- Version family: FFmpeg 8.1
- Applicable license: GNU Lesser General Public License version 3
- Release metadata: <https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest>
- Binary download: <https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip>
- Distribution project: <https://github.com/BtbN/FFmpeg-Builds>
- FFmpeg source: <https://github.com/FFmpeg/FFmpeg>

The exact binary version and checksum referenced by `latest` may change when BtbN publishes a new build. The installer reads the selected asset's actual size and `sha256` digest from the official GitHub Release API and compares them with the downloaded file. It then runs `ffmpeg -version` and verifies all of the following conditions:

- The output belongs to the `ffmpeg version n8.1` family.
- `--enable-shared` is present.
- `--enable-gpl` and `--enable-nonfree` are absent.
- All required executables and shared DLLs are present.

Only files that pass these checks are installed into the application's `ffmpeg/` directory. The exact installed version, download URL, file size, and SHA-256 are written to `docs/runtime-assets.json` in the application folder and can also be viewed in the application's `License & Sources` screen.

For development and internal offline builds, `scripts/prepare_ffmpeg_lgpl.ps1` resolves the same official Release asset and verifies its SHA-256 and build options.

## Modifications

This project does not modify the downloaded FFmpeg binary or source. Internal offline bundles also use the executables and shared libraries exactly as distributed in the original build's `bin` folder.

If a separate public distribution includes FFmpeg binaries, re-check the obligation to provide this document, the full LGPL and GPL texts, third-party notices, and source corresponding exactly to FFmpeg and its build dependencies.

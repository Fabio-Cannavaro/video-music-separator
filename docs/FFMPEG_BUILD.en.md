# FFmpeg GPL build information

This application runs FFmpeg as separate command-line programs and does not link FFmpeg into the application code. The default online installer does not contain FFmpeg binaries; it downloads them directly from Gyan's official distribution server to the user's PC during installation.

## Installation target

- Distributor: Gyan Doshi's FFmpeg builds for Windows
- Version: `9.0.1 release essentials`
- Immutable archive: <https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.1-essentials_build.zip>
- Archive size: `111253802` bytes
- Archive SHA-256: `fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9`
- Distribution information: <https://www.gyan.dev/ffmpeg/builds/>
- FFmpeg source: <https://github.com/FFmpeg/FFmpeg>
- Applicable license: GNU General Public License version 3

The version, URL, size, and SHA-256 are reviewed first-party locks in this repository. A new upstream release is not adopted automatically; the code and tests must be explicitly updated. The installer verifies the archive, then checks the pinned size and SHA-256 of `ffmpeg`, `ffprobe`, and `ffplay` before running any of them. It then checks `-version` for all of the following conditions:

- All three executables report exactly version 9.0.1.
- Gyan's `essentials_build` identifier is present.
- `--enable-gpl`, `--enable-version3`, and `--enable-static` are present.
- `--enable-nonfree` is absent.

Only the three executables that pass these checks are installed into the application's `ffmpeg/` directory. The exact installed version, final download URL, file size, and SHA-256 are written to `docs/runtime-assets.json` in the application folder and can also be viewed in the application's `App Info & Licenses` screen.

For development and internal offline builds, `scripts/prepare_ffmpeg_gpl.ps1` downloads the same immutable asset and performs the same checks.

## Distribution scope and obligations

The default online installation ZIP does not contain FFmpeg binaries. The user's installer downloads them directly from Gyan, so the project's default ZIP does not itself redistribute the FFmpeg binaries.

An internal offline bundle made with `build_portable.ps1 -BundleRuntimeAssets` does contain FFmpeg binaries. Before distributing such a bundle publicly, separately satisfy the GPL obligations, including preserving the GPLv3 text and copyright notices and providing the complete corresponding source and build instructions for the included FFmpeg binary and its build dependencies.

## Modifications

This project does not modify the downloaded FFmpeg binary or source. Internal offline bundles use the three executables exactly as distributed.

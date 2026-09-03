# FFmpeg GPL build information

This application runs FFmpeg as separate command-line programs and does not link FFmpeg into the application code. The default online installer does not contain FFmpeg binaries; it downloads them directly from Gyan's official distribution server to the user's PC during installation.

## Installation target

- Distributor: Gyan Doshi's FFmpeg builds for Windows
- Channel: current `release essentials`
- Stable entry URL: <https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip>
- Version metadata: <https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.ver>
- SHA-256 metadata: <https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256>
- Distribution information: <https://www.gyan.dev/ffmpeg/builds/>
- FFmpeg source: <https://github.com/FFmpeg/FFmpeg>
- Applicable license: GNU General Public License version 3

The exact binary version and checksum referenced by the stable entry URL change when Gyan publishes a new release. The installer first reads `.ver` and `.sha256`, then verifies that the final redirect is exactly `packages/ffmpeg-<version>-essentials_build.zip` and obtains its response size. After download, it compares SHA-256 and checks the `-version` output of `ffmpeg`, `ffprobe`, and `ffplay` for all of the following conditions:

- All three executables report the exact version in `.ver`.
- Gyan's `essentials_build` identifier is present.
- `--enable-gpl`, `--enable-version3`, and `--enable-static` are present.
- `--enable-nonfree` is absent.

Only the three executables that pass these checks are installed into the application's `ffmpeg/` directory. The exact installed version, final download URL, file size, and SHA-256 are written to `docs/runtime-assets.json` in the application folder and can also be viewed in the application's `Licenses & Sources` screen.

For development and internal offline builds, `scripts/prepare_ffmpeg_gpl.ps1` downloads the same current official asset and performs the same checks.

## Distribution scope and obligations

The default online installation ZIP does not contain FFmpeg binaries. The user's installer downloads them directly from Gyan, so the project's default ZIP does not itself redistribute the FFmpeg binaries.

An internal offline bundle made with `build_portable.ps1 -BundleRuntimeAssets` does contain FFmpeg binaries. Before distributing such a bundle publicly, separately satisfy the GPL obligations, including preserving the GPLv3 text and copyright notices and providing the complete corresponding source and build instructions for the included FFmpeg binary and its build dependencies.

## Modifications

This project does not modify the downloaded FFmpeg binary or source. Internal offline bundles use the three executables exactly as distributed.

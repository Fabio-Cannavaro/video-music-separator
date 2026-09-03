# FFmpeg LGPL build information

The Windows portable distribution runs FFmpeg as a separate command-line program and does not link FFmpeg into the application code.

## Included build

- Distributor: BtbN/FFmpeg-Builds
- Release: `autobuild-2026-08-20-13-45`
- File: `ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip`
- Binary version: `n8.1.2-44-g7c533d0f86-20260820`
- Applicable license: GNU Lesser General Public License version 3
- SHA-256: `d311c8c7b86e06b54588e442652f963bae165bd4d8393e73cc9ebb445b025547`
- Binary download: <https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-20-13-45/ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip>
- Corresponding FFmpeg source commit: <https://github.com/FFmpeg/FFmpeg/commit/7c533d0f86>
- Corresponding build-system commit: <https://github.com/BtbN/FFmpeg-Builds/tree/48576f197ad1c2afb2e0b8efe204919a1afbff54>

During application builds, `prepare_ffmpeg_lgpl.ps1` downloads the pinned archive above and verifies its SHA-256 checksum. `build_portable.ps1` then verifies that the build has `--enable-shared` and does not have `--enable-gpl` or `--enable-nonfree` before copying the EXE and required DLLs together.

## FFmpeg configure line

```text
--prefix=/ffbuild/prefix --pkg-config-flags=--static --pkg-config=pkg-config --cross-prefix=x86_64-w64-mingw32- --arch=x86_64 --target-os=mingw32 --enable-version3 --disable-debug --enable-shared --disable-static --disable-w32threads --enable-pthreads --enable-iconv --enable-zlib --enable-libxml2 --enable-libvmaf --enable-fontconfig --enable-libharfbuzz --enable-libfreetype --enable-libfribidi --enable-vulkan --enable-libshaderc --enable-libvorbis --disable-libxcb --disable-xlib --disable-libpulse --enable-gmp --enable-lzma --enable-liblcevc-dec --enable-opencl --enable-amf --enable-libaom --enable-libaribb24 --disable-avisynth --enable-chromaprint --enable-libdav1d --disable-libdavs2 --disable-libdvdread --disable-libdvdnav --disable-libfdk-aac --enable-ffnvcodec --enable-cuda-llvm --disable-frei0r --enable-libgme --enable-libkvazaar --enable-libaribcaption --enable-libass --enable-libbluray --enable-libjxl --enable-libmp3lame --enable-libopus --enable-libplacebo --enable-librist --enable-libssh --enable-libtheora --enable-libvpx --enable-libwebp --enable-libzmq --enable-lv2 --enable-libvpl --enable-openal --enable-liboapv --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 --enable-libopenjpeg --enable-libopenmpt --enable-librav1e --disable-librubberband --enable-schannel --enable-sdl2 --enable-libsnappy --enable-libsoxr --enable-libsrt --enable-libsvtav1 --enable-libtwolame --enable-libuavs3d --disable-libdrm --enable-vaapi --disable-libvidstab --enable-libvvenc --disable-whisper --disable-libx264 --disable-libx265 --disable-libxavs2 --disable-libxvid --enable-libzimg --enable-libzvbi --extra-cflags=-DLIBTWOLAME_STATIC --extra-cxxflags= --extra-libs=-lgomp --extra-ldflags=-pthread --extra-ldexeflags= --cc=x86_64-w64-mingw32-gcc --cxx=x86_64-w64-mingw32-g++ --ar=x86_64-w64-mingw32-gcc-ar --ranlib=x86_64-w64-mingw32-gcc-ranlib --nm=x86_64-w64-mingw32-gcc-nm --extra-version=20260820
```

## Modifications

This project does not modify the FFmpeg binary or source above. The portable folder includes the executables and shared libraries exactly as distributed in the original build's `bin` folder.

A public Release must include this document, the full LGPL and GPL texts, third-party notices, and a source bundle for FFmpeg and its build dependencies that corresponds exactly to the included binary.

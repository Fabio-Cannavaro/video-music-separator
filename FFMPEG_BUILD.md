# FFmpeg LGPL 빌드 정보

이 앱의 Windows 휴대용 배포본은 FFmpeg를 앱 코드에 링크하지 않고 별도 명령줄 프로그램으로 실행한다.

## 포함 빌드

- 배포자: BtbN/FFmpeg-Builds
- Release: `autobuild-2026-08-20-13-45`
- 파일: `ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip`
- 바이너리 버전: `n8.1.2-44-g7c533d0f86-20260820`
- 적용 라이선스: GNU Lesser General Public License version 3
- SHA-256: `d311c8c7b86e06b54588e442652f963bae165bd4d8393e73cc9ebb445b025547`
- 바이너리 다운로드: <https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-20-13-45/ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip>
- FFmpeg 대응 소스 커밋: <https://github.com/FFmpeg/FFmpeg/commit/7c533d0f86>
- 빌드 시스템 대응 커밋: <https://github.com/BtbN/FFmpeg-Builds/tree/48576f197ad1c2afb2e0b8efe204919a1afbff54>

온라인 설치 시 `video-music-separator-setup.exe`가 위 고정 파일을 공식 GitHub Release에서 직접 내려받고 SHA-256을 확인한다. 압축을 푼 뒤 `--enable-shared`가 있고 `--enable-gpl`, `--enable-nonfree`가 없는지 다시 검사한 파일만 앱의 `ffmpeg/` 폴더에 설치한다. 개발·오프라인 빌드에서는 `prepare_ffmpeg_lgpl.ps1`와 `build_portable.ps1 -BundleRuntimeAssets`가 같은 검증을 수행한다.

## FFmpeg configure line

```text
--prefix=/ffbuild/prefix --pkg-config-flags=--static --pkg-config=pkg-config --cross-prefix=x86_64-w64-mingw32- --arch=x86_64 --target-os=mingw32 --enable-version3 --disable-debug --enable-shared --disable-static --disable-w32threads --enable-pthreads --enable-iconv --enable-zlib --enable-libxml2 --enable-libvmaf --enable-fontconfig --enable-libharfbuzz --enable-libfreetype --enable-libfribidi --enable-vulkan --enable-libshaderc --enable-libvorbis --disable-libxcb --disable-xlib --disable-libpulse --enable-gmp --enable-lzma --enable-liblcevc-dec --enable-opencl --enable-amf --enable-libaom --enable-libaribb24 --disable-avisynth --enable-chromaprint --enable-libdav1d --disable-libdavs2 --disable-libdvdread --disable-libdvdnav --disable-libfdk-aac --enable-ffnvcodec --enable-cuda-llvm --disable-frei0r --enable-libgme --enable-libkvazaar --enable-libaribcaption --enable-libass --enable-libbluray --enable-libjxl --enable-libmp3lame --enable-libopus --enable-libplacebo --enable-librist --enable-libssh --enable-libtheora --enable-libvpx --enable-libwebp --enable-libzmq --enable-lv2 --enable-libvpl --enable-openal --enable-liboapv --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 --enable-libopenjpeg --enable-libopenmpt --enable-librav1e --disable-librubberband --enable-schannel --enable-sdl2 --enable-libsnappy --enable-libsoxr --enable-libsrt --enable-libsvtav1 --enable-libtwolame --enable-libuavs3d --disable-libdrm --enable-vaapi --disable-libvidstab --enable-libvvenc --disable-whisper --disable-libx264 --disable-libx265 --disable-libxavs2 --disable-libxvid --enable-libzimg --enable-libzvbi --extra-cflags=-DLIBTWOLAME_STATIC --extra-cxxflags= --extra-libs=-lgomp --extra-ldflags=-pthread --extra-ldexeflags= --cc=x86_64-w64-mingw32-gcc --cxx=x86_64-w64-mingw32-g++ --ar=x86_64-w64-mingw32-gcc-ar --ranlib=x86_64-w64-mingw32-gcc-ranlib --nm=x86_64-w64-mingw32-gcc-nm --extra-version=20260820
```

## 수정 내역

이 프로젝트는 위 FFmpeg 바이너리와 소스를 수정하지 않는다. 휴대용 폴더에는 원 배포본의 `bin` 폴더에 있던 실행 파일과 공유 라이브러리를 그대로 포함한다.

공개 Release에는 앱 바이너리와 함께 이 문서, LGPL·GPL 전문, 제3자 고지 및 해당 바이너리에 정확히 대응하는 FFmpeg와 빌드 의존성 소스 묶음을 첨부해야 한다.

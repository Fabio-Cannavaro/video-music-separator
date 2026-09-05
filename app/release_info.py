from __future__ import annotations


APP_VERSION = "0.2.8"

BASE_RUNTIME_VERSION = "0.2.0"
BASE_RUNTIME_ARCHIVE = "video-music-separator-ai-runtime-0.2.0.zip"
BASE_RUNTIME_ARCHIVE_SIZE = 3_764_354_481
BASE_RUNTIME_ARCHIVE_SHA256 = "70e521a80ce24f530238ef95973130f8f17b6f8c8254a94822109dcb4adb995f"
BASE_RUNTIME_TREE_SHA256 = "90b531ea3fc5282a547f977e3d2cc3a625cf23348c2460492f0b4f7f4b05f7ab"
BASE_RUNTIME_TREE_FILES = 32_801
BASE_RUNTIME_TREE_BYTES = 8_182_471_124
BASE_RUNTIME_SOURCE = "https://github.com/Fabio-Cannavaro/video-music-separator"
BASE_RUNTIME_RELEASE_TAG = "runtime-v0.2.0"
BASE_RUNTIME_RELEASE_BASE_URL = (
    "https://github.com/Fabio-Cannavaro/video-music-separator/releases/download/"
    + BASE_RUNTIME_RELEASE_TAG
)
BASE_RUNTIME_PARTS = (
    {
        "name": "video-music-separator-ai-runtime-0.2.0.zip.001",
        "size": 1_992_294_400,
        "sha256": "053db87a8406f8cf23d15157860d98173cd2026b8a6cac658572add011364c37",
    },
    {
        "name": "video-music-separator-ai-runtime-0.2.0.zip.002",
        "size": 1_772_060_081,
        "sha256": "8679f1930015a4768c5a977cfbc42d05ab14eb538b5c671e875471c01560bb33",
    },
)

AVCASS_VERSION = "official audio-visual checkpoint (unversioned)"
AVCASS_SHA256 = "66a8a3b9de317d2c508edae6bbd2d727bfd4faa6aec10c7c5ed02f5966e29b64"
AVCASS_SIZE = 738_312_597
AVCASS_SOURCE = "https://github.com/pantheon5100/AVCASS"
AVCASS_DOWNLOAD_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=1_d-RCP111No-wS-wrmxyK-zH87Sm2xzf&export=download&confirm=t"
)

CAVP_VERSION = "Diff-Foley commit b17ddbe76e6d42f4b4135eeb443b1c1644267e3e"
CAVP_SHA256 = "3472c2217a9481f530a96e32611c9e4611766f10b7f0d185a1ce35be7b7f9c80"
CAVP_SIZE = 1_361_483_035
CAVP_SOURCE = "https://huggingface.co/SimianLuo/Diff-Foley"
CAVP_DOWNLOAD_URL = (
    "https://huggingface.co/SimianLuo/Diff-Foley/resolve/"
    "b17ddbe76e6d42f4b4135eeb443b1c1644267e3e/"
    "diff_foley_ckpt/cavp_epoch66.ckpt?download=true"
)

FFMPEG_VERSION = "9.0.1"
FFMPEG_SHA256 = "fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9"
FFMPEG_SIZE = 111_253_802
FFMPEG_SOURCE = "https://www.gyan.dev/ffmpeg/builds/"
FFMPEG_ASSET_NAME = "ffmpeg-9.0.1-essentials_build.zip"
FFMPEG_DOWNLOAD_URL = FFMPEG_SOURCE + "packages/" + FFMPEG_ASSET_NAME
FFMPEG_EXECUTABLES = {
    "ffmpeg.exe": {
        "size": 102_856_192,
        "sha256": "72a489eccd008c2ec2c0a5856c5c75bc3d8bbfa90166c4566865c246445e6aa3",
    },
    "ffplay.exe": {
        "size": 104_339_968,
        "sha256": "39a9ba4f207fe9eecfb094e632998c29e1da88a5d5d23d0b8b71a357a7c47eb5",
    },
    "ffprobe.exe": {
        "size": 102_652_416,
        "sha256": "19202b23c0043f15ad1b7bce2344f406fd52bd6efd8f995ce02e7392a1cec52f",
    },
}


RUNTIME_COMPONENTS = (
    {
        "name": "AI Python runtime",
        "version": BASE_RUNTIME_VERSION,
        "sha256": BASE_RUNTIME_ARCHIVE_SHA256,
        "size": BASE_RUNTIME_ARCHIVE_SIZE,
        "source": BASE_RUNTIME_SOURCE,
        "download_url": BASE_RUNTIME_RELEASE_BASE_URL,
    },
    {
        "name": "AV-CASS",
        "version": AVCASS_VERSION,
        "sha256": AVCASS_SHA256,
        "size": AVCASS_SIZE,
        "source": AVCASS_SOURCE,
        "download_url": AVCASS_DOWNLOAD_URL,
    },
    {
        "name": "CAVP",
        "version": CAVP_VERSION,
        "sha256": CAVP_SHA256,
        "size": CAVP_SIZE,
        "source": CAVP_SOURCE,
        "download_url": CAVP_DOWNLOAD_URL,
    },
    {
        "name": "FFmpeg",
        "version": FFMPEG_VERSION,
        "sha256": FFMPEG_SHA256,
        "size": FFMPEG_SIZE,
        "source": FFMPEG_SOURCE,
        "download_url": FFMPEG_DOWNLOAD_URL,
    },
)

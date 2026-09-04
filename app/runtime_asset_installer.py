from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from release_info import (
    APP_VERSION,
    BASE_RUNTIME_ARCHIVE,
    BASE_RUNTIME_ARCHIVE_SHA256,
    BASE_RUNTIME_ARCHIVE_SIZE,
    BASE_RUNTIME_PARTS,
    BASE_RUNTIME_RELEASE_BASE_URL,
    BASE_RUNTIME_SOURCE,
    BASE_RUNTIME_VERSION,
    AVCASS_DOWNLOAD_URL,
    AVCASS_SHA256,
    AVCASS_SIZE,
    AVCASS_SOURCE,
    AVCASS_VERSION,
    CAVP_DOWNLOAD_URL,
    CAVP_SHA256,
    CAVP_SIZE,
    CAVP_SOURCE,
    CAVP_VERSION,
    FFMPEG_DOWNLOAD_URL,
    FFMPEG_ASSET_NAME,
    FFMPEG_CHECKSUM_URL,
    FFMPEG_SHA256,
    FFMPEG_SIZE,
    FFMPEG_SOURCE,
    FFMPEG_VERSION,
    FFMPEG_VERSION_URL,
)


APP_TITLE = "영상 음악 분리·제거기 필수 구성요소 설치"
APP_TITLES = {
    "ko": APP_TITLE,
    "en": "Video Music Separator Component Installer",
}
CHUNK_SIZE = 4 * 1024 * 1024
USER_AGENT = f"video-music-separator-runtime-installer/{APP_VERSION}"


@dataclass(frozen=True)
class DownloadAsset:
    asset_id: str
    label: str
    url: str
    relative_path: str
    sha256: str
    size: int
    source: str
    version: str = ""


MODEL_ASSETS = (
    DownloadAsset(
        asset_id="avcass",
        label="AV-CASS 분리 모델",
        url=AVCASS_DOWNLOAD_URL,
        relative_path="audiosep/avcass/model/av_cass_checkpoint.pt",
        sha256=AVCASS_SHA256,
        size=AVCASS_SIZE,
        source=AVCASS_SOURCE,
    ),
    DownloadAsset(
        asset_id="cavp",
        label="CAVP 영상 인식 모델",
        url=CAVP_DOWNLOAD_URL,
        relative_path="audiosep/avcass/model/cavp/cavp_epoch66.ckpt",
        sha256=CAVP_SHA256,
        size=CAVP_SIZE,
        source=CAVP_SOURCE,
    ),
)

BASE_RUNTIME_ASSETS = tuple(
    DownloadAsset(
        asset_id=f"base-runtime-{index}",
        label=f"AI Python 실행환경 {index}/{len(BASE_RUNTIME_PARTS)}",
        url=f"{BASE_RUNTIME_RELEASE_BASE_URL}/{part['name']}",
        relative_path=f".downloads/{part['name']}",
        sha256=part["sha256"],
        size=part["size"],
        source=BASE_RUNTIME_SOURCE,
    )
    for index, part in enumerate(BASE_RUNTIME_PARTS, start=1)
)

FFMPEG_ARCHIVE = DownloadAsset(
    asset_id="ffmpeg",
    label="FFmpeg GPL Essentials 빌드",
    url=FFMPEG_DOWNLOAD_URL,
    relative_path=f".downloads/{FFMPEG_ASSET_NAME}",
    sha256=FFMPEG_SHA256,
    size=FFMPEG_SIZE,
    source=FFMPEG_SOURCE,
)
FFMPEG_REQUIRED_FILES = (
    "ffmpeg.exe",
    "ffprobe.exe",
    "ffplay.exe",
)

ProgressCallback = Callable[[str, int, int], None]


INSTALLATION_DISCLOSURE = f"""Video Music Separator {APP_VERSION}

이 앱은 AV-CASS 연구진 또는 관련 기관의 공식 앱이 아니며, 해당 연구진과 제휴하거나 보증받지 않았습니다.

설치할 항목 (총 다운로드 약 5.9GB, 설치 중 여유 공간 약 15GB 권장)
• AI Python 실행환경 약 3.76GB — github.com/Fabio-Cannavaro
  {BASE_RUNTIME_RELEASE_BASE_URL}
• AV-CASS 약 704MB — drive.usercontent.google.com
  {AVCASS_DOWNLOAD_URL}
• CAVP 약 1.27GB — huggingface.co
  {CAVP_DOWNLOAD_URL}
• FFmpeg GPL Essentials 빌드 약 106MB — www.gyan.dev
  {FFMPEG_DOWNLOAD_URL}

이용조건
각 모델·프로그램에는 원 권리자의 라이선스와 이용조건이 적용됩니다. AV-CASS 체크포인트에는 별도 재배포 조건이 명시되어 있지 않으므로 이 설치 파일은 모델을 포함하지 않고 공식 제공 주소에서 직접 내려받습니다.

개인정보와 외부 통신
영상과 음원은 PC에서만 처리되며 설치 프로그램이나 앱이 업로드하지 않습니다. 설치 중 위 서버에 HTTPS 다운로드 요청을 보냅니다. 서버 운영자는 IP 주소, 요청 시각, 다운로드 URL, User-Agent와 이어받기용 Range 헤더 같은 일반 접속 정보를 받을 수 있습니다. 파일명, 영상·음원 내용 및 사용 통계는 전송하지 않습니다.

AI Python 실행환경은 공개 GitHub Release에서 인증 없이 받습니다. GitHub 계정이나 GitHub CLI는 필요하지 않으며 설치 프로그램이 GitHub 로그인을 시작하거나 인증 정보를 읽고 저장하지 않습니다.

사용자 책임
처리할 영상·음원의 저작권과 이용 권리를 확인하고 결과물을 사용하는 책임은 사용자에게 있습니다.
"""


INSTALLATION_DISCLOSURE_EN = f"""Video Music Separator {APP_VERSION}

This is not an official application of, affiliated with, or endorsed by the AV-CASS researchers or their institutions.

Components to install (approximately 5.9 GB total download; approximately 15 GB of free disk space recommended during installation)
• AI Python runtime, approximately 3.76 GB — github.com/Fabio-Cannavaro
  {BASE_RUNTIME_RELEASE_BASE_URL}
• AV-CASS, approximately 704 MB — drive.usercontent.google.com
  {AVCASS_DOWNLOAD_URL}
• CAVP, approximately 1.27 GB — huggingface.co
  {CAVP_DOWNLOAD_URL}
• FFmpeg GPL Essentials build, approximately 106 MB — www.gyan.dev
  {FFMPEG_DOWNLOAD_URL}

Terms of use
Each model and program is governed by the original rights holder's license and terms. The AV-CASS checkpoint does not state separate redistribution terms, so this installer does not include the model and downloads it directly from the location provided by the project.

Privacy and network access
Video and audio are processed only on this PC and are not uploaded by the installer or application. During installation, HTTPS download requests are sent to the servers listed above. Their operators may receive ordinary connection information such as the IP address, request time, download URL, User-Agent, and Range header used to resume a download. File names, media contents, and usage analytics are not transmitted.

The AI Python runtime is downloaded from the public GitHub Release without authentication. No GitHub account or GitHub CLI is required, and the installer does not start GitHub login or read or store GitHub credentials.

User responsibility
The user is responsible for confirming the copyright and usage rights of the video and audio being processed and for the use of generated results.
"""


INSTALLER_UI = {
    "ko": {
        "ready": "설치를 시작할 준비가 됐습니다.",
        "documents": "전체 라이선스·개인정보 문서 보기",
        "accept": "위 이용조건, 외부 통신, 사용자 책임 안내를 확인하고 동의합니다.",
        "start": "설치 시작",
        "checking": "필수 구성요소를 확인하는 중…",
        "warning": "안내를 확인하고 동의한 뒤 설치를 시작해 주세요.",
        "failed": "설치에 실패했습니다.",
        "completed": "필수 구성요소 설치와 검증이 완료됐습니다.",
        "completed_dialog": "설치가 완료됐습니다. 이제 앱을 실행할 수 있습니다.",
        "close": "닫기",
        "legal_title": "라이선스·개인정보 문서",
        "document_missing": "문서를 찾을 수 없습니다: {name}",
    },
    "en": {
        "ready": "Ready to begin installation.",
        "documents": "View all license and privacy documents",
        "accept": "I have reviewed and accept the terms, network access,\nand user responsibility notices above.",
        "start": "Start Installation",
        "checking": "Checking required components…",
        "warning": "Review and accept the notices before starting installation.",
        "failed": "Installation failed.",
        "completed": "Required components were installed and verified.",
        "completed_dialog": "Installation is complete. The application is ready to run.",
        "close": "Close",
        "legal_title": "License and Privacy Documents",
        "document_missing": "Document not found: {name}",
    },
}


PROGRESS_TRANSLATIONS = (
    ("필수 구성요소 설치 완료", "Required components installed"),
    ("최신 배포 정보 확인 중", "Checking latest release information"),
    ("분할 파일을 결합하는 중", "Combining split files"),
    ("결합 파일 무결성 확인 중", "Verifying combined-file integrity"),
    ("무결성 확인 중", "Verifying integrity"),
    ("다운로드 중단", "Download interrupted"),
    ("압축을 푸는 중", "Extracting"),
    ("파일을 배치하는 중", "Placing files"),
    ("설치 검증 중", "Verifying installation"),
    ("필수 구성요소", "Required components"),
    ("이미 설치됨", "Already installed"),
    ("설치 완료", "Installation complete"),
    ("AI Python 실행환경", "AI Python runtime"),
    ("AV-CASS 분리 모델", "AV-CASS separation model"),
    ("CAVP 영상 인식 모델", "CAVP visual recognition model"),
    ("FFmpeg GPL Essentials 빌드", "FFmpeg GPL Essentials build"),
)


ERROR_TRANSLATIONS = (
    ("공개 AI 실행환경 파일에 접근할 수 없습니다.", "The public AI runtime file could not be accessed."),
    ("배포 주소와 Release의 공개 상태를 확인해 주세요.", "Check the distribution URL and the public status of the Release."),
    ("Gyan 공식 최신 FFmpeg GPL Essentials 정보를 확인하지 못했습니다.", "The latest official Gyan FFmpeg GPL Essentials information could not be read."),
    ("Gyan FFmpeg 배포 정보가 올바르지 않습니다.", "The Gyan FFmpeg release information is invalid."),
    ("다운로드한 FFmpeg 압축 파일의 구조가 예상과 다릅니다.", "The downloaded FFmpeg archive has an unexpected structure."),
    ("지정된 GPL Essentials FFmpeg 빌드를 확인하지 못했습니다.", "The specified GPL Essentials FFmpeg build could not be verified."),
    ("기본 앱이 없습니다.", "The main application is missing."),
    ("설치 후 검증에 실패했습니다.", "Post-installation verification failed."),
    ("설치 또는 검증 필요", "Installation or verification required"),
    ("기본 파일 없음", "Required file missing"),
)


def installation_disclosure_text(language: str = "ko") -> str:
    disclosure = INSTALLATION_DISCLOSURE_EN if language == "en" else INSTALLATION_DISCLOSURE
    return disclosure.strip()


def translate_progress_label(label: str, language: str) -> str:
    if language != "en":
        return label
    translated = label
    for korean, english in PROGRESS_TRANSLATIONS:
        translated = translated.replace(korean, english)
    return translated


def translate_error_message(message: str, language: str) -> str:
    if language != "en":
        return message
    translated = message
    for korean, english in ERROR_TRANSLATIONS:
        translated = translated.replace(korean, english)
    return translated


def localized_document_names(language: str) -> tuple[str, ...]:
    suffix = ".en.md" if language == "en" else ".md"
    return (
        f"COPYRIGHT{suffix}",
        "LICENSE",
        f"MODEL_LICENSES{suffix}",
        f"THIRD_PARTY_NOTICES{suffix}",
        f"PRIVACY{suffix}",
        f"FFMPEG_BUILD{suffix}",
    )


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def sha256_file(
    path: Path,
    progress: ProgressCallback | None = None,
    label: str = "무결성 확인 중",
) -> str:
    digest = hashlib.sha256()
    total = path.stat().st_size
    current = 0
    if progress is not None:
        progress(label, 0, max(total, 1))
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
            current += len(chunk)
            if progress is not None:
                progress(label, current, max(total, 1))
    return digest.hexdigest()


def asset_is_valid(
    path: Path,
    asset: DownloadAsset,
    progress: ProgressCallback | None = None,
) -> bool:
    if not path.is_file() or path.stat().st_size != asset.size:
        return False
    actual_hash = sha256_file(
        path,
        progress,
        f"{asset.label} · 무결성 확인 중",
    )
    return actual_hash.lower() == asset.sha256.lower()


def _open_download(asset: DownloadAsset, offset: int):
    headers = {"User-Agent": USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(asset.url, headers=headers)
    return urllib.request.urlopen(request, timeout=60)


def download_asset(
    asset: DownloadAsset,
    destination: Path,
    progress: ProgressCallback,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if asset_is_valid(destination, asset, progress):
        progress(f"{asset.label} · 이미 설치됨", asset.size, asset.size)
        return

    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.is_file() else 0
    if offset >= asset.size:
        partial.unlink()
        offset = 0

    response = _open_download(asset, offset)
    status = getattr(response, "status", response.getcode())
    append = bool(offset and status == 206)
    if not append:
        offset = 0

    mode = "ab" if append else "wb"
    downloaded = offset
    try:
        with response, partial.open(mode) as stream:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                stream.write(chunk)
                downloaded += len(chunk)
                progress(asset.label, downloaded, asset.size)
    except BaseException:
        progress(f"{asset.label} · 다운로드 중단", downloaded, asset.size)
        raise

    if partial.stat().st_size != asset.size:
        raise RuntimeError(
            f"{asset.label} 파일 크기가 올바르지 않습니다: "
            f"{partial.stat().st_size:,} / {asset.size:,} 바이트"
        )
    actual_hash = sha256_file(
        partial,
        progress,
        f"{asset.label} · 무결성 확인 중",
    )
    if actual_hash.lower() != asset.sha256.lower():
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"{asset.label} SHA-256이 일치하지 않습니다.\n"
            f"예상: {asset.sha256}\n실제: {actual_hash}"
        )
    os.replace(partial, destination)


def download_base_runtime_asset(
    asset: DownloadAsset,
    destination: Path,
    progress: ProgressCallback,
) -> None:
    try:
        download_asset(asset, destination, progress)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403, 404):
            raise RuntimeError(
                "공개 AI 실행환경 파일에 접근할 수 없습니다. "
                "배포 주소와 Release의 공개 상태를 확인해 주세요."
            ) from error
        raise


def resolve_ffmpeg_archive() -> DownloadAsset:
    def read_metadata(url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(4097)
        if len(payload) > 4096:
            raise ValueError("metadata response is too large")
        return payload.decode("utf-8").strip()

    try:
        digest = read_metadata(FFMPEG_CHECKSUM_URL).lower()
        version = read_metadata(FFMPEG_VERSION_URL)
        head_request = urllib.request.Request(
            FFMPEG_DOWNLOAD_URL,
            headers={"User-Agent": USER_AGENT},
            method="HEAD",
        )
        with urllib.request.urlopen(head_request, timeout=60) as response:
            url = response.geturl()
            size = int(response.headers["Content-Length"])
    except (
        KeyError,
        UnicodeDecodeError,
        ValueError,
        OSError,
    ) as error:
        raise RuntimeError(
            "Gyan 공식 최신 FFmpeg GPL Essentials 정보를 확인하지 못했습니다."
        ) from error
    expected_url = f"{FFMPEG_SOURCE}packages/ffmpeg-{version}-essentials_build.zip"
    if (
        not re.fullmatch(r"[0-9a-f]{64}", digest)
        or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version)
        or size <= 0
        or url != expected_url
    ):
        raise RuntimeError("Gyan FFmpeg 배포 정보가 올바르지 않습니다.")
    return DownloadAsset(
        asset_id="ffmpeg",
        label="FFmpeg GPL Essentials 빌드",
        url=url,
        relative_path=f".downloads/ffmpeg-{version}-essentials_build.zip",
        sha256=digest,
        size=size,
        source=FFMPEG_SOURCE,
        version=version,
    )


def validate_ffmpeg(directory: Path, expected_version: str = "") -> bool:
    if any(not (directory / name).is_file() for name in FFMPEG_REQUIRED_FILES):
        return False
    for program in FFMPEG_REQUIRED_FILES:
        try:
            result = subprocess.run(
                [str(directory / program), "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        version_text = result.stdout + result.stderr
        lines = version_text.splitlines()
        first_line = lines[0] if lines else ""
        if (
            result.returncode != 0
            or "-essentials_build-www.gyan.dev" not in first_line
            or "--enable-gpl" not in version_text
            or "--enable-version3" not in version_text
            or "--enable-static" not in version_text
            or "--enable-nonfree" in version_text
            or (
                expected_version
                and not first_line.startswith(
                    f"{Path(program).stem} version {expected_version}-"
                )
            )
        ):
            return False
    return True


def _extract_zip_with_progress(
    archive: Path,
    destination: Path,
    label: str,
    progress: ProgressCallback,
) -> None:
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        items = package.infolist()
        for item in items:
            target = (destination / item.filename).resolve()
            try:
                target.relative_to(destination_resolved)
            except ValueError as error:
                raise RuntimeError(
                    f"압축 파일에 안전하지 않은 경로가 있습니다: {item.filename}"
                ) from error
        total = max(sum(item.file_size for item in items), 1)
        current = 0
        progress(label, 0, total)
        update_step = max(total // 500, 1)
        next_update = update_step
        for item in items:
            package.extract(item, destination)
            current += item.file_size
            if current >= next_update or current >= total:
                progress(label, current, total)
                next_update = current + update_step
        progress(label, total, total)


def _copy_directory_with_progress(
    source: Path,
    destination: Path,
    label: str,
    progress: ProgressCallback,
) -> None:
    files = [path for path in source.rglob("*") if path.is_file()]
    total = max(sum(path.stat().st_size for path in files), 1)
    current = 0
    destination.mkdir(parents=True, exist_ok=False)
    progress(label, 0, total)
    for source_file in files:
        relative = source_file.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target)
        current += source_file.stat().st_size
        progress(label, current, total)
    progress(label, total, total)


def install_ffmpeg(root: Path, progress: ProgressCallback) -> DownloadAsset | None:
    destination = root / "ffmpeg"
    progress("FFmpeg · 최신 배포 정보 확인 중", 0, 1)
    ffmpeg_archive = resolve_ffmpeg_archive()
    progress("FFmpeg · 최신 배포 정보 확인 중", 1, 1)
    progress("FFmpeg · 설치 검증 중", 0, 1)
    if validate_ffmpeg(destination, ffmpeg_archive.version):
        progress("FFmpeg · 설치 검증 중", 1, 1)
        progress("FFmpeg GPL Essentials 빌드 · 이미 설치됨", 1, 1)
        return ffmpeg_archive
    archive = root / ffmpeg_archive.relative_path
    download_asset(ffmpeg_archive, archive, progress)
    downloads = archive.parent
    downloads.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ffmpeg-extract-", dir=downloads) as temp_name:
        extraction = Path(temp_name)
        _extract_zip_with_progress(
            archive,
            extraction,
            "FFmpeg · 압축을 푸는 중",
            progress,
        )
        candidates = list(extraction.glob("*/bin/ffmpeg.exe"))
        if len(candidates) != 1:
            raise RuntimeError("다운로드한 FFmpeg 압축 파일의 구조가 예상과 다릅니다.")
        source_bin = candidates[0].parent
        pending = root / f"ffmpeg-new-{uuid.uuid4().hex}"
        _copy_directory_with_progress(
            source_bin,
            pending,
            "FFmpeg · 파일을 배치하는 중",
            progress,
        )
        progress("FFmpeg · 설치 검증 중", 0, 1)
        if not validate_ffmpeg(pending, ffmpeg_archive.version):
            shutil.rmtree(pending, ignore_errors=True)
            raise RuntimeError("지정된 GPL Essentials FFmpeg 빌드를 확인하지 못했습니다.")
        progress("FFmpeg · 설치 검증 중", 1, 1)

        previous = root / f"ffmpeg-old-{uuid.uuid4().hex}"
        try:
            if destination.exists():
                destination.rename(previous)
            pending.rename(destination)
        except BaseException:
            if not destination.exists() and previous.exists():
                previous.rename(destination)
            shutil.rmtree(pending, ignore_errors=True)
            raise
        shutil.rmtree(previous, ignore_errors=True)
    archive.unlink(missing_ok=True)
    progress("FFmpeg GPL Essentials 빌드 · 설치 완료", 1, 1)
    return ffmpeg_archive


def _safe_extract_zip(
    archive: Path,
    destination: Path,
    progress: ProgressCallback,
) -> None:
    _extract_zip_with_progress(
        archive,
        destination,
        "AI Python 실행환경 · 압축을 푸는 중",
        progress,
    )


def install_base_runtime(root: Path, progress: ProgressCallback) -> None:
    if base_runtime_is_current(root):
        progress("AI Python 실행환경 · 이미 설치됨", 1, 1)
        return

    downloads = root / ".downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    part_paths: list[Path] = []
    for asset in BASE_RUNTIME_ASSETS:
        part_path = root / asset.relative_path
        download_base_runtime_asset(asset, part_path, progress)
        part_paths.append(part_path)

    archive = downloads / BASE_RUNTIME_ARCHIVE
    pending_archive = archive.with_name(archive.name + ".part")
    combine_label = "AI Python 실행환경 · 분할 파일을 결합하는 중"
    combined = 0
    progress(combine_label, 0, BASE_RUNTIME_ARCHIVE_SIZE)
    with pending_archive.open("wb") as output:
        for part_path in part_paths:
            with part_path.open("rb") as source:
                while chunk := source.read(CHUNK_SIZE):
                    output.write(chunk)
                    combined += len(chunk)
                    progress(combine_label, combined, BASE_RUNTIME_ARCHIVE_SIZE)
    if pending_archive.stat().st_size != BASE_RUNTIME_ARCHIVE_SIZE:
        pending_archive.unlink(missing_ok=True)
        raise RuntimeError("AI Python 실행환경 결합 파일의 크기가 올바르지 않습니다.")
    if sha256_file(
        pending_archive,
        progress,
        "AI Python 실행환경 · 결합 파일 무결성 확인 중",
    ).lower() != BASE_RUNTIME_ARCHIVE_SHA256.lower():
        pending_archive.unlink(missing_ok=True)
        raise RuntimeError("AI Python 실행환경 결합 파일의 SHA-256이 일치하지 않습니다.")
    os.replace(pending_archive, archive)

    with tempfile.TemporaryDirectory(prefix="runtime-extract-", dir=downloads) as temp_name:
        extraction = Path(temp_name)
        _safe_extract_zip(archive, extraction, progress)
        extracted_runtime = extraction / "audiosep"
        if not extracted_runtime.is_dir():
            raise RuntimeError("AI 실행환경 압축 파일의 구조가 예상과 다릅니다.")
        if validate_base_runtime(extraction):
            raise RuntimeError("압축을 푼 AI 실행환경의 필수 파일이 없습니다.")

        destination = root / "audiosep"
        previous = root / f"audiosep-old-{uuid.uuid4().hex}"
        try:
            if destination.exists():
                destination.rename(previous)
            extracted_runtime.rename(destination)
        except BaseException:
            if not destination.exists() and previous.exists():
                previous.rename(destination)
            raise
        shutil.rmtree(previous, ignore_errors=True)
        (destination / "base-runtime.json").write_text(
            json.dumps(
                {
                    "version": BASE_RUNTIME_VERSION,
                    "archive": BASE_RUNTIME_ARCHIVE,
                    "size": BASE_RUNTIME_ARCHIVE_SIZE,
                    "sha256": BASE_RUNTIME_ARCHIVE_SHA256,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    archive.unlink(missing_ok=True)
    for part_path in part_paths:
        part_path.unlink(missing_ok=True)
    progress("AI Python 실행환경 · 설치 완료", 1, 1)


def validate_base_runtime(root: Path) -> list[Path]:
    required = (
        root / "audiosep" / "env" / "python.exe",
        root / "audiosep" / "avcass" / "repo" / "models_avdnr_zero_conv_2vid.py",
        root / "audiosep" / "avcass" / "deps" / "diffusers" / "__init__.py",
    )
    return [path for path in required if not path.exists()]


def base_runtime_is_current(root: Path) -> bool:
    if validate_base_runtime(root):
        return False
    marker = root / "audiosep" / "base-runtime.json"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    return (
        data.get("version") == BASE_RUNTIME_VERSION
        and data.get("archive") == BASE_RUNTIME_ARCHIVE
        and data.get("size") == BASE_RUNTIME_ARCHIVE_SIZE
        and str(data.get("sha256", "")).lower() == BASE_RUNTIME_ARCHIVE_SHA256.lower()
    )


def verify_installation(
    root: Path,
    progress: ProgressCallback | None = None,
    full_hash: bool = True,
) -> list[str]:
    problems = []
    progress_callback = progress or (lambda *_: None)
    label = "필수 구성요소 · 설치 검증 중"
    total_steps = 4
    current_step = 0
    progress_callback(label, current_step, total_steps)
    app = root / "video-music-separator.exe"
    if not app.is_file():
        problems.append(f"기본 파일 없음: {app}")
    problems.extend(f"기본 파일 없음: {path}" for path in validate_base_runtime(root))
    if not validate_base_runtime(root) and not base_runtime_is_current(root):
        problems.append("AI Python 실행환경 버전 확인 또는 재설치 필요")
    current_step += 1
    progress_callback(label, current_step, total_steps)
    for asset in MODEL_ASSETS:
        target = root / asset.relative_path
        valid = (
            asset_is_valid(target, asset, progress)
            if full_hash
            else target.is_file() and target.stat().st_size == asset.size
        )
        if not valid:
            problems.append(f"설치 또는 검증 필요: {target}")
        current_step += 1
        progress_callback(label, current_step, total_steps)
    if not validate_ffmpeg(root / "ffmpeg"):
        problems.append("설치 또는 검증 필요: FFmpeg GPL Essentials 빌드")
    current_step += 1
    progress_callback(label, current_step, total_steps)
    return problems


def _installed_ffmpeg_version(directory: Path) -> str:
    try:
        result = subprocess.run(
            [str(directory / "ffmpeg.exe"), "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return FFMPEG_VERSION
    first_line = (result.stdout or result.stderr).splitlines()
    return first_line[0].strip() if first_line else FFMPEG_VERSION


def write_install_record(
    root: Path,
    ffmpeg_archive: DownloadAsset | None = None,
) -> None:
    record_path = root / "docs" / "runtime-assets.json"
    existing_record: dict = {}
    try:
        existing_record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        pass
    ffmpeg_record = (
        asdict(ffmpeg_archive)
        if ffmpeg_archive is not None
        else existing_record.get("ffmpeg", asdict(FFMPEG_ARCHIVE))
    )
    record = {
        "app_version": APP_VERSION,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "base_runtime": {
            "version": BASE_RUNTIME_VERSION,
            "archive": BASE_RUNTIME_ARCHIVE,
            "size": BASE_RUNTIME_ARCHIVE_SIZE,
            "sha256": BASE_RUNTIME_ARCHIVE_SHA256,
            "source": BASE_RUNTIME_SOURCE,
            "parts": [asdict(asset) for asset in BASE_RUNTIME_ASSETS],
        },
        "models": [
            {
                **asdict(asset),
                "version": AVCASS_VERSION if asset.asset_id == "avcass" else CAVP_VERSION,
            }
            for asset in MODEL_ASSETS
        ],
        "ffmpeg": ffmpeg_record,
        "ffmpeg_version": _installed_ffmpeg_version(root / "ffmpeg"),
    }
    documents = root / "docs"
    documents.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def install_all(root: Path, progress: ProgressCallback) -> None:
    app = root / "video-music-separator.exe"
    if not app.is_file():
        raise RuntimeError(
            "기본 앱이 없습니다. 설치 파일을 앱 폴더에서 실행해 주세요.\n\n" + str(app)
        )
    install_base_runtime(root, progress)
    for asset in MODEL_ASSETS:
        download_asset(asset, root / asset.relative_path, progress)
    ffmpeg_archive = install_ffmpeg(root, progress)
    problems = verify_installation(root, progress, full_hash=False)
    if problems:
        raise RuntimeError("설치 후 검증에 실패했습니다.\n" + "\n".join(problems))
    write_install_record(root, ffmpeg_archive)
    progress("필수 구성요소 설치 완료", 1, 1)


class InstallerWindow:
    def __init__(self, root_directory: Path) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk
        from tkinter.scrolledtext import ScrolledText

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.ScrolledText = ScrolledText
        self.root_directory = root_directory
        self.window = tk.Tk()
        self.window.geometry("820x740")
        self.window.resizable(False, False)
        self.language = tk.StringVar(value="ko")
        self.status = tk.StringVar()
        self.accepted = tk.BooleanVar(value=False)
        self.status_key: str | None = "ready"
        self.last_progress_label: str | None = None
        self.last_progress_percent: int | None = None
        self.install_finished = False
        frame = ttk.Frame(self.window, padding=22)
        frame.pack(fill="both", expand=True)

        language_frame = ttk.Frame(frame)
        language_frame.pack(fill="x", pady=(0, 2))
        ttk.Radiobutton(
            language_frame,
            text="한국어",
            value="ko",
            variable=self.language,
            command=self._set_language,
        ).pack(side="right")
        ttk.Radiobutton(
            language_frame,
            text="English",
            value="en",
            variable=self.language,
            command=self._set_language,
        ).pack(side="right", padx=(0, 8))

        self.title_label = ttk.Label(frame, font=("맑은 고딕", 14, "bold"))
        self.title_label.pack(pady=(0, 10))
        self.disclosure = self.ScrolledText(
            frame,
            height=22,
            wrap="word",
            padx=10,
            pady=10,
            font=("맑은 고딕", 9),
        )
        self.disclosure.pack(fill="both", expand=True)
        self.documents_button = ttk.Button(
            frame,
            command=self.show_documents,
        )
        self.documents_button.pack(anchor="e", pady=(7, 0))
        self.accept_check = ttk.Checkbutton(
            frame,
            variable=self.accepted,
            command=self._update_button_state,
        )
        self.accept_check.pack(anchor="w", pady=(10, 8))
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        ttk.Label(frame, textvariable=self.status, wraplength=650).pack(pady=(8, 12))
        self.button = ttk.Button(frame, command=self.start, state="disabled")
        self.button.pack(ipadx=18, ipady=5)
        self._set_language()

    def _ui(self, key: str) -> str:
        return INSTALLER_UI[self.language.get()][key]

    def _set_status(self, key: str) -> None:
        self.status_key = key
        self.last_progress_label = None
        self.last_progress_percent = None
        self.status.set(self._ui(key))

    def _set_language(self) -> None:
        language = self.language.get()
        self.window.title(APP_TITLES[language])
        self.title_label.configure(text=APP_TITLES[language])
        self.documents_button.configure(text=self._ui("documents"))
        self.accept_check.configure(text=self._ui("accept"))
        self.button.configure(text=self._ui("close" if self.install_finished else "start"))
        self.disclosure.configure(state="normal")
        self.disclosure.delete("1.0", "end")
        self.disclosure.insert("1.0", installation_disclosure_text(language))
        self.disclosure.configure(state="disabled")
        if self.last_progress_label is not None:
            translated = translate_progress_label(self.last_progress_label, language)
            percent = self.last_progress_percent or 0
            self.status.set(f"{translated} · {percent}%")
        elif self.status_key is not None:
            self.status.set(self._ui(self.status_key))

    def show_documents(self) -> None:
        language = self.language.get()
        document_names = localized_document_names(language)
        sections: list[str] = []
        for name in document_names:
            path = self.root_directory / "docs" / name
            if not path.is_file():
                path = self.root_directory / name
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace").strip()
            else:
                content = self._ui("document_missing").format(name=name)
            sections.append(f"{name}\n{'=' * len(name)}\n\n{content}")

        window = self.tk.Toplevel(self.window)
        window.title(self._ui("legal_title"))
        window.geometry("850x680")
        window.minsize(650, 480)
        text = self.ScrolledText(window, wrap="word", padx=14, pady=14, font=("맑은 고딕", 9))
        text.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        text.insert("1.0", "\n\n\n".join(sections))
        text.configure(state="disabled")
        self.ttk.Button(window, text=self._ui("close"), command=window.destroy).pack(
            pady=(0, 10)
        )

    def _update_button_state(self) -> None:
        self.button.configure(state="normal" if self.accepted.get() else "disabled")

    def update_progress(self, label: str, current: int, total: int) -> None:
        percent = 100 if total <= 0 else max(0, min(100, round(current * 100 / total)))
        self.window.after(0, self._apply_progress, label, percent)

    def _apply_progress(self, label: str, percent: int) -> None:
        self.status_key = None
        self.last_progress_label = label
        self.last_progress_percent = percent
        translated = translate_progress_label(label, self.language.get())
        self.status.set(f"{translated} · {percent}%")
        self.progress.configure(value=percent)

    def start(self) -> None:
        if not self.accepted.get():
            self.messagebox.showwarning(APP_TITLES[self.language.get()], self._ui("warning"))
            return
        self.button.configure(state="disabled")
        self.progress.configure(value=0)
        self._set_status("checking")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            install_all(self.root_directory, self.update_progress)
        except BaseException as error:
            self.window.after(0, self._failed, str(error))
            return
        self.window.after(0, self._completed)

    def _failed(self, message: str) -> None:
        self._set_status("failed")
        self.button.configure(state="normal")
        self.messagebox.showerror(
            APP_TITLES[self.language.get()],
            translate_error_message(message, self.language.get()),
        )

    def _completed(self) -> None:
        self.install_finished = True
        self._set_status("completed")
        self.progress.configure(value=100)
        self.button.configure(
            text=self._ui("close"), state="normal", command=self.window.destroy
        )
        self.messagebox.showinfo(
            APP_TITLES[self.language.get()], self._ui("completed_dialog")
        )

    def run(self) -> None:
        self.window.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--install-dir", type=Path, default=application_directory())
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--accept-terms",
        action="store_true",
        help="비대화형 설치에서 이용조건과 외부 통신 안내를 확인했음을 표시합니다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.install_dir.resolve()
    if args.verify_only:
        problems = verify_installation(root)
        print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False))
        return 0 if not problems else 1
    if args.headless:
        if not args.accept_terms:
            print(
                "비대화형 설치에는 --accept-terms가 필요합니다. 먼저 설치 안내와 "
                "동봉된 라이선스·개인정보 문서를 확인해 주세요.",
                file=sys.stderr,
            )
            return 2
        install_all(root, lambda label, current, total: print(label, flush=True))
        return 0
    InstallerWindow(root).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

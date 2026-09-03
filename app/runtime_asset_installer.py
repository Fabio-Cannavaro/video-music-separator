from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
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
    FFMPEG_SHA256,
    FFMPEG_SIZE,
    FFMPEG_SOURCE,
    FFMPEG_VERSION,
)


APP_TITLE = "영상 음악 분리·제거기 필수 구성요소 설치"
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
    label="FFmpeg LGPL 공유 빌드",
    url=FFMPEG_DOWNLOAD_URL,
    relative_path=".downloads/ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip",
    sha256=FFMPEG_SHA256,
    size=FFMPEG_SIZE,
    source=FFMPEG_SOURCE,
)
FFMPEG_REQUIRED_FILES = (
    "ffmpeg.exe",
    "ffprobe.exe",
    "ffplay.exe",
    "avcodec-62.dll",
    "avformat-62.dll",
    "avfilter-11.dll",
    "avutil-60.dll",
    "swresample-6.dll",
    "swscale-9.dll",
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
• FFmpeg LGPL 공유 빌드 약 68MB — github.com/BtbN
  {FFMPEG_DOWNLOAD_URL}

이용조건
각 모델·프로그램에는 원 권리자의 라이선스와 이용조건이 적용됩니다. AV-CASS 체크포인트에는 별도 재배포 조건이 명시되어 있지 않으므로 이 설치 파일은 모델을 포함하지 않고 공식 제공 주소에서 직접 내려받습니다.

개인정보와 외부 통신
영상과 음원은 PC에서만 처리되며 설치 프로그램이나 앱이 업로드하지 않습니다. 설치 중 위 서버에 HTTPS 다운로드 요청을 보냅니다. 서버 운영자는 IP 주소, 요청 시각, 다운로드 URL, User-Agent와 이어받기용 Range 헤더 같은 일반 접속 정보를 받을 수 있습니다. 파일명, 영상·음원 내용 및 사용 통계는 전송하지 않습니다.

사용자 책임
처리할 영상·음원의 저작권과 이용 권리를 확인하고 결과물을 사용하는 책임은 사용자에게 있습니다.
"""


def installation_disclosure_text() -> str:
    return INSTALLATION_DISCLOSURE.strip()


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def asset_is_valid(path: Path, asset: DownloadAsset) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == asset.size
        and sha256_file(path).lower() == asset.sha256.lower()
    )


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
    if asset_is_valid(destination, asset):
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
    progress(f"{asset.label} · 무결성 확인 중", asset.size, asset.size)
    actual_hash = sha256_file(partial)
    if actual_hash.lower() != asset.sha256.lower():
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"{asset.label} SHA-256이 일치하지 않습니다.\n"
            f"예상: {asset.sha256}\n실제: {actual_hash}"
        )
    os.replace(partial, destination)


def validate_ffmpeg(directory: Path) -> bool:
    if any(not (directory / name).is_file() for name in FFMPEG_REQUIRED_FILES):
        return False
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
        return False
    version_text = result.stdout + result.stderr
    return (
        result.returncode == 0
        and FFMPEG_VERSION in version_text
        and "--enable-shared" in version_text
        and "--enable-gpl" not in version_text
        and "--enable-nonfree" not in version_text
    )


def install_ffmpeg(root: Path, progress: ProgressCallback) -> None:
    destination = root / "ffmpeg"
    if validate_ffmpeg(destination):
        progress("FFmpeg LGPL 공유 빌드 · 이미 설치됨", 1, 1)
        return

    archive = root / FFMPEG_ARCHIVE.relative_path
    download_asset(FFMPEG_ARCHIVE, archive, progress)
    downloads = archive.parent
    downloads.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ffmpeg-extract-", dir=downloads) as temp_name:
        extraction = Path(temp_name)
        progress("FFmpeg · 압축을 푸는 중", 0, 1)
        with zipfile.ZipFile(archive) as package:
            package.extractall(extraction)
        candidates = list(extraction.glob("*/bin/ffmpeg.exe"))
        if len(candidates) != 1:
            raise RuntimeError("다운로드한 FFmpeg 압축 파일의 구조가 예상과 다릅니다.")
        source_bin = candidates[0].parent
        pending = root / f"ffmpeg-new-{uuid.uuid4().hex}"
        shutil.copytree(source_bin, pending)
        if not validate_ffmpeg(pending):
            shutil.rmtree(pending, ignore_errors=True)
            raise RuntimeError("지정된 LGPL 공유 FFmpeg 빌드를 확인하지 못했습니다.")

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
    progress("FFmpeg LGPL 공유 빌드 · 설치 완료", 1, 1)


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            target = (destination / item.filename).resolve()
            try:
                target.relative_to(destination_resolved)
            except ValueError as error:
                raise RuntimeError(
                    f"AI 실행환경 압축에 안전하지 않은 경로가 있습니다: {item.filename}"
                ) from error
        package.extractall(destination)


def install_base_runtime(root: Path, progress: ProgressCallback) -> None:
    if base_runtime_is_current(root):
        progress("AI Python 실행환경 · 이미 설치됨", 1, 1)
        return

    downloads = root / ".downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    part_paths: list[Path] = []
    for asset in BASE_RUNTIME_ASSETS:
        part_path = root / asset.relative_path
        download_asset(asset, part_path, progress)
        part_paths.append(part_path)

    archive = downloads / BASE_RUNTIME_ARCHIVE
    pending_archive = archive.with_name(archive.name + ".part")
    progress("AI Python 실행환경 · 분할 파일을 결합하는 중", 0, 1)
    with pending_archive.open("wb") as output:
        for part_path in part_paths:
            with part_path.open("rb") as source:
                shutil.copyfileobj(source, output, length=CHUNK_SIZE)
    if pending_archive.stat().st_size != BASE_RUNTIME_ARCHIVE_SIZE:
        pending_archive.unlink(missing_ok=True)
        raise RuntimeError("AI Python 실행환경 결합 파일의 크기가 올바르지 않습니다.")
    if sha256_file(pending_archive).lower() != BASE_RUNTIME_ARCHIVE_SHA256.lower():
        pending_archive.unlink(missing_ok=True)
        raise RuntimeError("AI Python 실행환경 결합 파일의 SHA-256이 일치하지 않습니다.")
    os.replace(pending_archive, archive)

    with tempfile.TemporaryDirectory(prefix="runtime-extract-", dir=downloads) as temp_name:
        extraction = Path(temp_name)
        progress("AI Python 실행환경 · 압축을 푸는 중", 0, 1)
        _safe_extract_zip(archive, extraction)
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


def verify_installation(root: Path) -> list[str]:
    problems = []
    app = root / "video-music-separator.exe"
    if not app.is_file():
        problems.append(f"기본 파일 없음: {app}")
    problems.extend(f"기본 파일 없음: {path}" for path in validate_base_runtime(root))
    if not validate_base_runtime(root) and not base_runtime_is_current(root):
        problems.append("AI Python 실행환경 버전 확인 또는 재설치 필요")
    for asset in MODEL_ASSETS:
        target = root / asset.relative_path
        if not asset_is_valid(target, asset):
            problems.append(f"설치 또는 검증 필요: {target}")
    if not validate_ffmpeg(root / "ffmpeg"):
        problems.append("설치 또는 검증 필요: FFmpeg LGPL 공유 빌드")
    return problems


def write_install_record(root: Path) -> None:
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
        "ffmpeg": asdict(FFMPEG_ARCHIVE),
        "ffmpeg_version": FFMPEG_VERSION,
    }
    documents = root / "docs"
    documents.mkdir(parents=True, exist_ok=True)
    (documents / "runtime-assets.json").write_text(
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
    install_ffmpeg(root, progress)
    problems = verify_installation(root)
    if problems:
        raise RuntimeError("설치 후 검증에 실패했습니다.\n" + "\n".join(problems))
    write_install_record(root)
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
        self.window.title(APP_TITLE)
        self.window.geometry("780x700")
        self.window.resizable(False, False)
        self.status = tk.StringVar(value="설치를 시작할 준비가 됐습니다.")
        self.accepted = tk.BooleanVar(value=False)
        self.detail = tk.StringVar(
            value="AI 실행환경 약 3.76GB · AV-CASS 약 704MB · CAVP 약 1.27GB · FFmpeg 약 68MB"
        )
        frame = ttk.Frame(self.window, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=APP_TITLE, font=("맑은 고딕", 14, "bold")).pack(pady=(0, 10))
        disclosure = self.ScrolledText(
            frame,
            height=22,
            wrap="word",
            padx=10,
            pady=10,
            font=("맑은 고딕", 9),
        )
        disclosure.insert("1.0", installation_disclosure_text())
        disclosure.configure(state="disabled")
        disclosure.pack(fill="both", expand=True)
        ttk.Button(
            frame,
            text="전체 라이선스·개인정보 문서 보기",
            command=self.show_documents,
        ).pack(anchor="e", pady=(7, 0))
        ttk.Checkbutton(
            frame,
            text="위 이용조건, 외부 통신, 사용자 책임 안내를 확인하고 동의합니다.",
            variable=self.accepted,
            command=self._update_button_state,
        ).pack(anchor="w", pady=(10, 8))
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        ttk.Label(frame, textvariable=self.status, wraplength=650).pack(pady=(8, 12))
        self.button = ttk.Button(frame, text="설치 시작", command=self.start, state="disabled")
        self.button.pack(ipadx=18, ipady=5)

    def show_documents(self) -> None:
        document_names = (
            "COPYRIGHT.md",
            "LICENSE",
            "MODEL_LICENSES.md",
            "THIRD_PARTY_NOTICES.md",
            "PRIVACY.md",
            "FFMPEG_BUILD.md",
        )
        sections: list[str] = []
        for name in document_names:
            path = self.root_directory / "docs" / name
            if not path.is_file():
                path = self.root_directory / name
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace").strip()
            else:
                content = f"문서를 찾을 수 없습니다: {name}"
            sections.append(f"{name}\n{'=' * len(name)}\n\n{content}")

        window = self.tk.Toplevel(self.window)
        window.title("라이선스·개인정보 문서")
        window.geometry("850x680")
        window.minsize(650, 480)
        text = self.ScrolledText(window, wrap="word", padx=14, pady=14, font=("맑은 고딕", 9))
        text.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        text.insert("1.0", "\n\n\n".join(sections))
        text.configure(state="disabled")
        self.ttk.Button(window, text="닫기", command=window.destroy).pack(pady=(0, 10))

    def _update_button_state(self) -> None:
        self.button.configure(state="normal" if self.accepted.get() else "disabled")

    def update_progress(self, label: str, current: int, total: int) -> None:
        percent = 100 if total <= 0 else max(0, min(100, round(current * 100 / total)))
        self.window.after(0, self._apply_progress, label, percent)

    def _apply_progress(self, label: str, percent: int) -> None:
        self.status.set(label)
        self.progress.configure(value=percent)

    def start(self) -> None:
        if not self.accepted.get():
            self.messagebox.showwarning(APP_TITLE, "안내를 확인하고 동의한 뒤 설치를 시작해 주세요.")
            return
        self.button.configure(state="disabled")
        self.progress.configure(value=0)
        self.status.set("필수 구성요소를 확인하는 중…")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            install_all(self.root_directory, self.update_progress)
        except BaseException as error:
            self.window.after(0, self._failed, str(error))
            return
        self.window.after(0, self._completed)

    def _failed(self, message: str) -> None:
        self.status.set("설치에 실패했습니다.")
        self.button.configure(state="normal")
        self.messagebox.showerror(APP_TITLE, message)

    def _completed(self) -> None:
        self.status.set("필수 구성요소 설치와 검증이 완료됐습니다.")
        self.progress.configure(value=100)
        self.button.configure(text="닫기", state="normal", command=self.window.destroy)
        self.messagebox.showinfo(APP_TITLE, "설치가 완료됐습니다. 이제 앱을 실행할 수 있습니다.")

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

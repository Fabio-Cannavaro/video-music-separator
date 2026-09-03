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


APP_TITLE = "영상 음악 분리·제거기 필수 구성요소 설치"
CHUNK_SIZE = 4 * 1024 * 1024
USER_AGENT = "video-music-separator-runtime-installer/1.0"


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
        url=(
            "https://drive.usercontent.google.com/download"
            "?id=1_d-RCP111No-wS-wrmxyK-zH87Sm2xzf&export=download&confirm=t"
        ),
        relative_path="audiosep/avcass/model/av_cass_checkpoint.pt",
        sha256="66a8a3b9de317d2c508edae6bbd2d727bfd4faa6aec10c7c5ed02f5966e29b64",
        size=738_312_597,
        source="https://github.com/pantheon5100/AVCASS",
    ),
    DownloadAsset(
        asset_id="cavp",
        label="CAVP 영상 인식 모델",
        url=(
            "https://huggingface.co/SimianLuo/Diff-Foley/resolve/"
            "b17ddbe76e6d42f4b4135eeb443b1c1644267e3e/"
            "diff_foley_ckpt/cavp_epoch66.ckpt?download=true"
        ),
        relative_path="audiosep/avcass/model/cavp/cavp_epoch66.ckpt",
        sha256="3472c2217a9481f530a96e32611c9e4611766f10b7f0d185a1ce35be7b7f9c80",
        size=1_361_483_035,
        source="https://huggingface.co/SimianLuo/Diff-Foley",
    ),
)

FFMPEG_ARCHIVE = DownloadAsset(
    asset_id="ffmpeg",
    label="FFmpeg LGPL 공유 빌드",
    url=(
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
        "autobuild-2026-08-20-13-45/"
        "ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip"
    ),
    relative_path=".downloads/ffmpeg-n8.1.2-44-g7c533d0f86-win64-lgpl-shared-8.1.zip",
    sha256="d311c8c7b86e06b54588e442652f963bae165bd4d8393e73cc9ebb445b025547",
    size=70_835_392,
    source="https://github.com/BtbN/FFmpeg-Builds",
)

FFMPEG_VERSION = "n8.1.2-44-g7c533d0f86-20260820"
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


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


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


def validate_base_runtime(root: Path) -> list[Path]:
    required = (
        root / "video-music-separator.exe",
        root / "audiosep" / "env" / "python.exe",
        root / "audiosep" / "avcass" / "repo" / "models_avdnr_zero_conv_2vid.py",
        root / "audiosep" / "avcass" / "deps" / "diffusers" / "__init__.py",
    )
    return [path for path in required if not path.exists()]


def verify_installation(root: Path) -> list[str]:
    problems = [f"기본 파일 없음: {path}" for path in validate_base_runtime(root)]
    for asset in MODEL_ASSETS:
        target = root / asset.relative_path
        if not asset_is_valid(target, asset):
            problems.append(f"설치 또는 검증 필요: {target}")
    if not validate_ffmpeg(root / "ffmpeg"):
        problems.append("설치 또는 검증 필요: FFmpeg LGPL 공유 빌드")
    return problems


def write_install_record(root: Path) -> None:
    record = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "models": [asdict(asset) for asset in MODEL_ASSETS],
        "ffmpeg": asdict(FFMPEG_ARCHIVE),
        "ffmpeg_version": FFMPEG_VERSION,
    }
    (root / "runtime-assets.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def install_all(root: Path, progress: ProgressCallback) -> None:
    missing_base = validate_base_runtime(root)
    if missing_base:
        missing = "\n".join(str(path) for path in missing_base)
        raise RuntimeError(
            "기본 앱 또는 AI 실행환경이 없습니다. 설치 파일을 앱 폴더에서 실행해 주세요.\n\n"
            + missing
        )
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

        self.tk = tk
        self.messagebox = messagebox
        self.root_directory = root_directory
        self.window = tk.Tk()
        self.window.title(APP_TITLE)
        self.window.geometry("580x285")
        self.window.resizable(False, False)
        self.status = tk.StringVar(value="설치를 시작할 준비가 됐습니다.")
        self.detail = tk.StringVar(
            value="AV-CASS 약 704MB · CAVP 약 1.27GB · FFmpeg 약 68MB"
        )
        frame = ttk.Frame(self.window, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=APP_TITLE, font=("맑은 고딕", 14, "bold")).pack(pady=(0, 14))
        ttk.Label(
            frame,
            text="공식 배포처에서 파일을 직접 내려받고 SHA-256을 확인합니다.",
        ).pack()
        ttk.Label(frame, textvariable=self.detail).pack(pady=(6, 16))
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        ttk.Label(frame, textvariable=self.status, wraplength=530).pack(pady=(8, 15))
        self.button = ttk.Button(frame, text="설치 시작", command=self.start)
        self.button.pack(ipadx=18, ipady=5)

    def update_progress(self, label: str, current: int, total: int) -> None:
        percent = 100 if total <= 0 else max(0, min(100, round(current * 100 / total)))
        self.window.after(0, self._apply_progress, label, percent)

    def _apply_progress(self, label: str, percent: int) -> None:
        self.status.set(label)
        self.progress.configure(value=percent)

    def start(self) -> None:
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.install_dir.resolve()
    if args.verify_only:
        problems = verify_installation(root)
        print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False))
        return 0 if not problems else 1
    if args.headless:
        install_all(root, lambda label, current, total: print(label, flush=True))
        return 0
    InstallerWindow(root).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

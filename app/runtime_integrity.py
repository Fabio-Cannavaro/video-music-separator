from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Callable

from release_info import (
    BASE_RUNTIME_ARCHIVE_SHA256,
    BASE_RUNTIME_TREE_BYTES,
    BASE_RUNTIME_TREE_FILES,
    BASE_RUNTIME_TREE_SHA256,
    BASE_RUNTIME_VERSION,
)


CHUNK_SIZE = 4 * 1024 * 1024
INTEGRITY_SCHEMA = 1
_IGNORED_DIRECTORY_NAMES = {"__pycache__"}
_IGNORED_FILE_NAMES = {"base-runtime.json", "runtime-file-inventory.json"}
_IGNORED_PATH_PREFIXES = (
    ("cache",),
    ("avcass", "model"),
)
ProgressCallback = Callable[[str, int, int], None]


def _is_reparse_point(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & 0x400)
    except AttributeError:
        return path.is_symlink()


def _protected_files(runtime_root: Path) -> list[Path]:
    if not runtime_root.is_dir() or _is_reparse_point(runtime_root):
        raise RuntimeError(f"AI Python 실행환경이 안전한 폴더가 아닙니다: {runtime_root}")
    files: list[Path] = []
    for path in runtime_root.rglob("*"):
        relative = path.relative_to(runtime_root)
        lowered_parts = tuple(part.lower() for part in relative.parts)
        if any(part in _IGNORED_DIRECTORY_NAMES for part in lowered_parts[:-1]):
            continue
        if any(lowered_parts[: len(prefix)] == prefix for prefix in _IGNORED_PATH_PREFIXES):
            continue
        if path.is_symlink() or _is_reparse_point(path):
            raise RuntimeError(f"AI 실행환경에 링크 또는 재분석 지점이 있습니다: {path}")
        if path.is_file() and path.name.lower() not in _IGNORED_FILE_NAMES:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(runtime_root).as_posix().lower())


def runtime_tree_fingerprint(
    runtime_root: Path,
    progress: ProgressCallback | None = None,
) -> dict[str, int | str]:
    runtime_root = runtime_root.resolve()
    files = _protected_files(runtime_root)
    total = sum(path.stat().st_size for path in files)
    done = 0
    tree_digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(runtime_root).as_posix()
        size = path.stat().st_size
        file_digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(CHUNK_SIZE):
                file_digest.update(chunk)
                done += len(chunk)
                if progress is not None:
                    progress("AI Python 실행환경 · 무결성 확인 중", done, max(total, 1))
        tree_digest.update(relative.encode("utf-8"))
        tree_digest.update(b"\0")
        tree_digest.update(str(size).encode("ascii"))
        tree_digest.update(b"\0")
        tree_digest.update(file_digest.hexdigest().encode("ascii"))
        tree_digest.update(b"\n")
    return {"sha256": tree_digest.hexdigest(), "files": len(files), "bytes": total}


def _state_path(install_root: Path) -> Path:
    canonical = str(install_root.resolve()).casefold().encode("utf-8")
    install_id = hashlib.sha256(canonical).hexdigest()
    base = Path(
        os.environ.get(
            "LOCALAPPDATA",
            str(Path(tempfile.gettempdir()) / "VideoMusicSeparator-user"),
        )
    )
    return base / "VideoMusicSeparator" / "integrity" / f"{install_id}.json"


def record_runtime_integrity(
    install_root: Path,
    progress: ProgressCallback | None = None,
) -> Path:
    runtime_root = install_root.resolve() / "audiosep"
    fingerprint = runtime_tree_fingerprint(runtime_root, progress)
    _require_expected_fingerprint(fingerprint)
    record = {
        "schema": INTEGRITY_SCHEMA,
        "runtime_version": BASE_RUNTIME_VERSION,
        "archive_sha256": BASE_RUNTIME_ARCHIVE_SHA256,
        "install_root": str(install_root.resolve()),
        "tree": fingerprint,
    }
    state_path = _state_path(install_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    pending = state_path.with_name(f".{state_path.name}.{uuid.uuid4().hex}.tmp")
    pending.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(pending, state_path)
    return state_path


def verify_runtime_integrity(
    install_root: Path,
    progress: ProgressCallback | None = None,
) -> None:
    actual = runtime_tree_fingerprint(install_root.resolve() / "audiosep", progress)
    _require_expected_fingerprint(actual)


def _require_expected_fingerprint(fingerprint: dict[str, int | str]) -> None:
    expected = {
        "sha256": BASE_RUNTIME_TREE_SHA256,
        "files": BASE_RUNTIME_TREE_FILES,
        "bytes": BASE_RUNTIME_TREE_BYTES,
    }
    if fingerprint != expected:
        raise RuntimeError(
            "AI Python 실행환경 무결성 검증에 실패했습니다. 필수 구성요소를 다시 설치해 주세요."
        )


def runtime_integrity_is_valid(install_root: Path) -> bool:
    try:
        verify_runtime_integrity(install_root)
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def verify_runtime_integrity_once(
    install_root: Path,
    progress: ProgressCallback | None = None,
) -> None:
    # Kept for source compatibility: security-sensitive callers must verify on
    # every launch because the portable runtime is user-writable.
    verify_runtime_integrity(install_root, progress)

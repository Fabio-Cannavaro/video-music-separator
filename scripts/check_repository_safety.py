#!/usr/bin/env python3
"""Fail CI when unsafe files or sensitive text are tracked by Git."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


MAX_TRACKED_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_SCAN_BYTES = MAX_TRACKED_FILE_BYTES

FORBIDDEN_DIRECTORIES = {
    "analysis_outputs",
    "audiosep",
    "build",
    "dist",
    "exe-backups",
    "ffmpeg",
    "ffmpeg-backups",
    "media",
    "models",
    "test-output",
    "third_party",
    "video-music-separator-portable",
    "work",
}

FORBIDDEN_SUFFIXES = {
    ".7z",
    ".aac",
    ".avi",
    ".bin",
    ".ckpt",
    ".db",
    ".dll",
    ".dmp",
    ".exe",
    ".flac",
    ".gguf",
    ".gz",
    ".h5",
    ".kdbx",
    ".key",
    ".log",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".msi",
    ".npy",
    ".npz",
    ".ogg",
    ".onnx",
    ".opus",
    ".part",
    ".p12",
    ".pem",
    ".pfx",
    ".pth",
    ".pt",
    ".pyd",
    ".rar",
    ".safetensors",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tflite",
    ".wav",
    ".webm",
    ".whl",
    ".zip",
}

FORBIDDEN_FILENAMES = {
    ".env",
    "agents.local.md",
    "credentials.json",
    "runtime-assets.json",
}

FORBIDDEN_FILENAME_PATTERNS = (
    re.compile(r"\.env\..+", re.IGNORECASE),
    re.compile(r"client_secret.*\.json", re.IGNORECASE),
    re.compile(r"service-account.*\.json", re.IGNORECASE),
)

SENSITIVE_TEXT_PATTERNS = (
    (
        "private key",
        re.compile(r"-----BEGIN (?:DSA |EC |OPENSSH |RSA )?PRIVATE KEY-----"),
    ),
    (
        "GitHub token",
        re.compile(r"(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,})"),
    ),
    (
        "OpenAI API key",
        re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    ),
    (
        "Hugging Face token",
        re.compile(r"hf_[A-Za-z0-9]{20,}"),
    ),
    (
        "AWS access key",
        re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    ),
    (
        "Google API key",
        re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    ),
    (
        "local Windows user path",
        re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\r\n]+[\\/]"),
    ),
)


def tracked_files(repository: Path) -> list[str]:
    """Return all files currently tracked by Git."""
    result = subprocess.run(
        ["git", "-c", f"safe.directory={repository}", "ls-files", "-z"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _normalized_parts(relative_path: str) -> tuple[str, ...]:
    return tuple(part.lower() for part in PurePosixPath(relative_path.replace("\\", "/")).parts)


def _text_findings(path: Path, relative_path: str) -> list[str]:
    if path.stat().st_size > MAX_TEXT_SCAN_BYTES:
        return []

    try:
        data = path.read_bytes()
    except OSError:
        return []

    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            text = data.decode("utf-16")
        except UnicodeDecodeError:
            return []
    else:
        if b"\x00" in data:
            return []
        text = ""
        for encoding in ("utf-8-sig", "cp949"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if not text and data:
            return []

    findings: list[str] = []
    for label, pattern in SENSITIVE_TEXT_PATTERNS:
        if pattern.search(text):
            findings.append(f"{relative_path}: contains a possible {label}")
    return findings


def check_paths(repository: Path, paths: Iterable[str]) -> list[str]:
    """Return safety violations for the supplied repository-relative paths."""
    findings: list[str] = []

    for relative_path in paths:
        normalized = relative_path.replace("\\", "/")
        parts = _normalized_parts(normalized)
        path = repository / PurePosixPath(normalized)

        forbidden_part = next((part for part in parts[:-1] if part in FORBIDDEN_DIRECTORIES), None)
        if forbidden_part:
            findings.append(f"{normalized}: tracked from forbidden directory '{forbidden_part}/'")

        suffix = Path(parts[-1]).suffix.lower() if parts else ""
        if suffix in FORBIDDEN_SUFFIXES:
            findings.append(f"{normalized}: forbidden tracked file type '{suffix}'")

        filename = parts[-1] if parts else ""
        if filename in FORBIDDEN_FILENAMES or any(
            pattern.fullmatch(filename) for pattern in FORBIDDEN_FILENAME_PATTERNS
        ):
            findings.append(f"{normalized}: forbidden generated/runtime file")

        if not path.is_file():
            continue

        size = path.stat().st_size
        if size > MAX_TRACKED_FILE_BYTES:
            findings.append(
                f"{normalized}: tracked file is {size:,} bytes "
                f"(limit: {MAX_TRACKED_FILE_BYTES:,} bytes)"
            )

        findings.extend(_text_findings(path, normalized))

    return findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of scripts/)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repository = args.repository.resolve()

    try:
        paths = tracked_files(repository)
        findings = check_paths(repository, paths)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Repository safety check could not run: {exc}", file=sys.stderr)
        return 2

    if findings:
        print("Repository safety check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print(f"Repository safety check passed for {len(paths)} tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import math
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path


MAX_MEDIA_DURATION_SECONDS = 10 * 60
MIN_FREE_DISK_RESERVE_BYTES = 2 * 1024**3
MAX_FFMPEG_ALLOC_BYTES = 128 * 1024**2
MAX_FFMPEG_PROBE_BYTES = 32 * 1024**2
MAX_FFMPEG_ANALYZE_MICROSECONDS = 30 * 1_000_000
MAX_MEDIA_STREAMS = 16
MAX_VIDEO_WIDTH = 7680
MAX_VIDEO_HEIGHT = 4320
MAX_VIDEO_PIXELS = MAX_VIDEO_WIDTH * MAX_VIDEO_HEIGHT
MAX_AUDIO_CHANNELS = 8
MAX_AUDIO_SAMPLE_RATE = 192_000
WORK_MARKER_NAME = ".video-music-separator-work.json"
WORK_MARKER_SCHEMA = 1

_FORMAT_WHITELISTS = {
    ".aac": "aac",
    ".avi": "avi",
    ".flac": "flac",
    ".m4a": "mov,mp4,m4a,3gp,3g2,mj2",
    ".m4v": "mov,mp4,m4a,3gp,3g2,mj2",
    ".mkv": "matroska,webm",
    ".mov": "mov,mp4,m4a,3gp,3g2,mj2",
    ".mp3": "mp3",
    ".mp4": "mov,mp4,m4a,3gp,3g2,mj2",
    ".ogg": "ogg",
    ".opus": "ogg",
    ".wav": "wav",
    ".webm": "matroska,webm",
}


def _windows_drive_type(path: Path) -> int | None:
    if os.name != "nt" or not path.drive:
        return None
    import ctypes

    return int(ctypes.windll.kernel32.GetDriveTypeW(f"{path.drive}\\"))


def _reject_network_or_reparse_path(candidate: Path, label: str) -> None:
    raw = os.fspath(candidate)
    if raw.startswith(("\\\\", "//")):
        raise ValueError(f"{label}은 로컬 고정 디스크의 파일이어야 합니다.")
    absolute = Path(os.path.abspath(candidate))
    for item in (absolute, *absolute.parents):
        if item == Path(item.anchor):
            break
        try:
            if _is_reparse_point(item):
                raise ValueError(
                    f"{label} 경로에는 링크 또는 재분석 지점을 사용할 수 없습니다: {item}"
                )
        except OSError:
            continue
    drive_type = _windows_drive_type(absolute)
    if drive_type == 4:  # DRIVE_REMOTE
        raise ValueError(f"{label}은 네트워크 드라이브에서 읽을 수 없습니다.")


def require_local_media_file(path_value: str | Path, label: str = "미디어") -> Path:
    """Resolve a user-controlled input and reject protocols and non-files."""
    raw = os.fspath(path_value)
    if "\x00" in raw:
        raise ValueError(f"{label} 경로가 올바르지 않습니다.")
    candidate = Path(raw).expanduser()
    _reject_network_or_reparse_path(candidate, label)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise FileNotFoundError(f"{label} 파일을 찾을 수 없습니다: {candidate}") from error
    if not resolved.is_file():
        raise ValueError(f"{label}은 로컬 일반 파일이어야 합니다: {resolved}")
    _reject_network_or_reparse_path(resolved, label)
    return resolved


def ffmpeg_file_input(path_value: str | Path, label: str = "미디어") -> list[str]:
    path = require_local_media_file(path_value, label)
    format_whitelist = _FORMAT_WHITELISTS.get(path.suffix.lower())
    if format_whitelist is None:
        raise ValueError(f"지원하지 않는 {label} 파일 형식입니다: {path.suffix or '(없음)'}")
    return [
        "-protocol_whitelist",
        "file",
        "-format_whitelist",
        format_whitelist,
        "-i",
        str(path),
    ]


def ffmpeg_resource_args() -> list[str]:
    return [
        "-max_alloc",
        str(MAX_FFMPEG_ALLOC_BYTES),
        "-probesize",
        str(MAX_FFMPEG_PROBE_BYTES),
        "-analyzeduration",
        str(MAX_FFMPEG_ANALYZE_MICROSECONDS),
    ]


def validate_media_streams(streams: object) -> None:
    if not isinstance(streams, list) or not streams:
        raise ValueError("미디어 스트림 정보를 읽지 못했습니다.")
    if len(streams) > MAX_MEDIA_STREAMS:
        raise ValueError(f"미디어 스트림 수는 최대 {MAX_MEDIA_STREAMS}개까지 지원합니다.")
    for stream in streams:
        if not isinstance(stream, dict):
            raise ValueError("미디어 스트림 정보가 올바르지 않습니다.")
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            if (
                width <= 0
                or height <= 0
                or width > MAX_VIDEO_WIDTH
                or height > MAX_VIDEO_HEIGHT
                or width * height > MAX_VIDEO_PIXELS
            ):
                raise ValueError(
                    f"영상 해상도는 최대 {MAX_VIDEO_WIDTH}x{MAX_VIDEO_HEIGHT}까지 지원합니다."
                )
        elif codec_type == "audio":
            channels = int(stream.get("channels") or 0)
            sample_rate = int(stream.get("sample_rate") or 0)
            if channels <= 0 or channels > MAX_AUDIO_CHANNELS:
                raise ValueError(
                    f"오디오 채널 수는 최대 {MAX_AUDIO_CHANNELS}개까지 지원합니다."
                )
            if sample_rate <= 0 or sample_rate > MAX_AUDIO_SAMPLE_RATE:
                raise ValueError(
                    f"오디오 샘플레이트는 최대 {MAX_AUDIO_SAMPLE_RATE}Hz까지 지원합니다."
                )


def validate_media_duration(duration: float) -> float:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("미디어 길이가 올바르지 않습니다.")
    if duration > MAX_MEDIA_DURATION_SECONDS:
        raise ValueError(
            "한 번에 처리할 수 있는 영상은 최대 10분입니다. "
            "더 긴 영상은 10분 이하로 나눠 주세요."
        )
    return duration


def media_command_timeout(duration: float) -> float:
    """Generous finite bound for local FFmpeg operations."""
    return max(120.0, min(4 * 60 * 60.0, duration * 3.0 + 300.0))


def estimate_work_bytes(video_path: Path, duration: float) -> int:
    """Conservative scratch estimate for PCM stems, PNG frames, and previews."""
    validated = validate_media_duration(duration)
    source_size = require_local_media_file(video_path, "영상").stat().st_size
    pcm_and_frames_per_second = (176_400 * 4) + (224 * 224 * 3 * 4)
    return int(source_size * 3 + validated * pcm_and_frames_per_second)


def require_work_disk_space(video_path: Path, work_parent: Path, duration: float) -> int:
    required = estimate_work_bytes(video_path, duration) + MIN_FREE_DISK_RESERVE_BYTES
    free = shutil.disk_usage(work_parent).free
    if free < required:
        raise RuntimeError(
            "작업 공간이 부족합니다. "
            f"필요 약 {required / 1024**3:.1f}GB, 사용 가능 {free / 1024**3:.1f}GB"
        )
    return required


def _is_reparse_point(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & 0x400)
    except AttributeError:
        return path.is_symlink()


@dataclass(frozen=True)
class OwnedWorkDirectory:
    path: Path
    nonce: str
    video_identity: str


def allocate_owned_work_directory(video_path: Path) -> OwnedWorkDirectory:
    video = require_local_media_file(video_path, "영상")
    nonce = uuid.uuid4().hex
    path = video.parent / f"{video.stem}_sound_work_{nonce[:12]}"
    return OwnedWorkDirectory(path=path, nonce=nonce, video_identity=str(video))


def ensure_owned_work_directory(handle: OwnedWorkDirectory) -> Path:
    expected_prefix = f"{Path(handle.video_identity).stem}_sound_work_"
    if handle.path.parent.resolve() != Path(handle.video_identity).parent.resolve():
        raise RuntimeError("작업 폴더 위치가 영상 폴더와 일치하지 않습니다.")
    if not handle.path.name.startswith(expected_prefix):
        raise RuntimeError("작업 폴더 이름이 올바르지 않습니다.")
    if not handle.path.exists():
        handle.path.mkdir(parents=False, exist_ok=False)
        marker = {
            "schema": WORK_MARKER_SCHEMA,
            "nonce": handle.nonce,
            "video": handle.video_identity,
        }
        marker_path = handle.path / WORK_MARKER_NAME
        marker_path.write_text(
            json.dumps(marker, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    validate_owned_work_directory(handle)
    return handle.path


def validate_owned_work_directory(handle: OwnedWorkDirectory) -> None:
    if not handle.path.is_dir() or _is_reparse_point(handle.path):
        raise RuntimeError(f"안전하게 사용할 수 없는 작업 폴더입니다: {handle.path}")
    marker_path = handle.path / WORK_MARKER_NAME
    if not marker_path.is_file() or _is_reparse_point(marker_path):
        raise RuntimeError(f"작업 폴더 소유 표식이 없습니다: {handle.path}")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as error:
        raise RuntimeError(f"작업 폴더 소유 표식이 손상됐습니다: {handle.path}") from error
    expected = {
        "schema": WORK_MARKER_SCHEMA,
        "nonce": handle.nonce,
        "video": handle.video_identity,
    }
    if marker != expected:
        raise RuntimeError(f"이 실행이 소유한 작업 폴더가 아닙니다: {handle.path}")


def cleanup_owned_work_directory(handle: OwnedWorkDirectory) -> bool:
    if not handle.path.exists():
        return False
    validate_owned_work_directory(handle)
    shutil.rmtree(handle.path)
    return True

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from release_info import FFMPEG_EXECUTABLES
from security_policy import (
    ffmpeg_file_input,
    ffmpeg_resource_args,
    media_command_timeout,
    require_local_media_file,
    require_work_disk_space,
    validate_media_duration,
    validate_media_streams,
)


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MUSIC_PARTITION_IDS = {"music", "non-music"}
PREVIEW_VIDEO_FILTER = (
    "scale=420:236:force_original_aspect_ratio=decrease,"
    "pad=420:236:(ow-iw)/2:(oh-ih)/2:black,fps=24"
)
MAX_COMMAND_OUTPUT_BYTES = 1024 * 1024
COMMAND_POLL_SECONDS = 0.05


def application_root() -> Path:
    """Return the movable application folder in source and packaged builds."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


@dataclass
class SoundEvent:
    event_id: str
    label: str
    start: float
    end: float
    score: float
    query: str = ""
    muted: bool = False
    extracted_path: str = ""
    extraction_start: float = 0.0
    extracted_duration: float = 0.0
    extraction_quality: str = ""
    extraction_note: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def require_program(name: str) -> str:
    bundled = application_root() / "ffmpeg" / f"{name}.exe"
    if bundled.is_file():
        expected = FFMPEG_EXECUTABLES.get(bundled.name.lower())
        if expected is None or bundled.stat().st_size != expected["size"]:
            raise RuntimeError(f"{name} 실행 파일 무결성 검증에 실패했습니다.")
        digest = hashlib.sha256()
        with bundled.open("rb") as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest().lower() != expected["sha256"].lower():
            raise RuntimeError(f"{name} 실행 파일 무결성 검증에 실패했습니다.")
        return str(bundled)
    if getattr(sys, "frozen", False):
        raise RuntimeError(f"검증된 {name} 실행 파일을 찾을 수 없습니다.")
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} 실행 파일을 찾을 수 없습니다.")
    return path


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        taskkill = system_root / "System32" / "taskkill.exe"
        subprocess.run(
            [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _read_bounded_output(stream, size: int) -> str:
    stream.seek(0)
    return stream.read(min(size, MAX_COMMAND_OUTPUT_BYTES)).decode(
        "utf-8", errors="replace"
    )


def run_bounded_command(
    command: Sequence[str],
    *,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            list(command),
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            stdout_size = os.fstat(stdout_file.fileno()).st_size
            stderr_size = os.fstat(stderr_file.fileno()).st_size
            if stdout_size > MAX_COMMAND_OUTPUT_BYTES or stderr_size > MAX_COMMAND_OUTPUT_BYTES:
                _terminate_process_tree(process)
                raise RuntimeError(
                    "외부 미디어 도구의 출력이 안전 제한을 초과해 중단됐습니다."
                )
            if time.monotonic() >= deadline:
                _terminate_process_tree(process)
                raise RuntimeError("외부 미디어 도구가 시간 제한을 초과해 중단됐습니다.")
            time.sleep(COMMAND_POLL_SECONDS)
        return_code = process.wait(timeout=10)
        stdout_size = os.fstat(stdout_file.fileno()).st_size
        stderr_size = os.fstat(stderr_file.fileno()).st_size
        if stdout_size > MAX_COMMAND_OUTPUT_BYTES or stderr_size > MAX_COMMAND_OUTPUT_BYTES:
            raise RuntimeError("외부 미디어 도구의 출력이 안전 제한을 초과했습니다.")
        return subprocess.CompletedProcess(
            list(command),
            return_code,
            _read_bounded_output(stdout_file, stdout_size),
            _read_bounded_output(stderr_file, stderr_size),
        )


def run_command(command: Sequence[str], *, timeout: float = 4 * 60 * 60) -> None:
    completed = run_bounded_command(command, timeout=timeout)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"명령 실행 실패: {' '.join(command)}")


def ffmpeg_command_prefix(name: str) -> list[str]:
    return [
        require_program(name),
        "-hide_banner",
        "-loglevel",
        "error",
        *ffmpeg_resource_args(),
    ]


def extract_audio(video_path: Path, output_wav: Path) -> None:
    video_path = require_local_media_file(video_path, "영상")
    duration = probe_duration(video_path)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    require_work_disk_space(video_path, output_wav.parent, duration)
    run_command(
        [
            *ffmpeg_command_prefix("ffmpeg"),
            "-y",
            *ffmpeg_file_input(video_path, "영상"),
            "-t",
            f"{duration:.3f}",
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ],
        timeout=media_command_timeout(duration),
    )


def probe_duration(media_path: Path) -> float:
    media_path = require_local_media_file(media_path)
    completed = run_bounded_command(
        [
            *ffmpeg_command_prefix("ffprobe"),
            "-show_entries",
            "format=duration:stream=codec_type,width,height,sample_rate,channels",
            "-of",
            "json",
            *ffmpeg_file_input(media_path),
        ],
        timeout=120,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "미디어 길이를 읽지 못했습니다.")
    try:
        metadata = json.loads(completed.stdout)
        duration = float(metadata["format"]["duration"])
        validate_media_streams(metadata.get("streams"))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("미디어 스트림 정보가 올바르지 않습니다.") from error
    return validate_media_duration(duration)


def _preview_video_args() -> list[str]:
    return [
        "-vf",
        PREVIEW_VIDEO_FILTER,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "27",
        "-pix_fmt",
        "yuv420p",
    ]


def create_preview_proxy(video_path: Path, output_path: Path) -> None:
    """Create a small A/V proxy used only by the in-app player."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(video_path)
    command = [
        *ffmpeg_command_prefix("ffmpeg"),
        "-y",
        *ffmpeg_file_input(video_path, "영상"),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
    ]
    command.extend(_preview_video_args())
    command.extend(
        ["-c:a", "aac", "-b:a", "192k", "-shortest", str(output_path)]
    )
    run_command(command, timeout=media_command_timeout(duration))


def preview_proxy_is_current(video_path: Path, output_path: Path) -> bool:
    """Return whether a non-empty proxy is at least as new as its source video."""
    try:
        source_stat = video_path.stat()
        output_stat = output_path.stat()
    except OSError:
        return False
    return (
        output_stat.st_size > 0
        and output_stat.st_mtime_ns >= source_stat.st_mtime_ns
    )


def create_preview_video(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Create a small video proxy paired with a chosen audio track."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(video_path)
    command = [
        *ffmpeg_command_prefix("ffmpeg"),
        "-y",
        *ffmpeg_file_input(video_path, "영상"),
        *ffmpeg_file_input(audio_path, "오디오"),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
    ]
    command.extend(_preview_video_args())
    command.extend(
        ["-c:a", "aac", "-b:a", "192k", "-shortest", str(output_path)]
    )
    run_command(command, timeout=media_command_timeout(duration))


def extract_event_clip(
    source_wav: Path,
    output_wav: Path,
    start: float,
    end: float,
    padding: float = 0.25,
) -> float:
    source_wav = require_local_media_file(source_wav, "오디오")
    clip_start = max(0.0, start - padding)
    duration = max(0.05, end - clip_start + padding)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            *ffmpeg_command_prefix("ffmpeg"),
            "-y",
            "-ss",
            f"{clip_start:.3f}",
            "-t",
            f"{duration:.3f}",
            *ffmpeg_file_input(source_wav, "오디오"),
            "-ac",
            "1",
            "-ar",
            "32000",
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ],
        timeout=media_command_timeout(duration),
    )
    return clip_start


def merge_window_detections(
    detections: Iterable[tuple[str, float, float, float]],
    *,
    max_gap: float = 0.35,
    minimum_duration: float = 0.15,
) -> list[SoundEvent]:
    """Merge overlapping/adjacent detections of the same label."""
    grouped: dict[str, list[tuple[float, float, float]]] = {}
    for label, start, end, score in detections:
        if not label or not all(math.isfinite(v) for v in (start, end, score)):
            continue
        if end <= start:
            continue
        grouped.setdefault(label, []).append((max(0.0, start), end, score))

    merged: list[SoundEvent] = []
    serial = 1
    for label, spans in grouped.items():
        spans.sort(key=lambda item: (item[0], item[1]))
        current_start, current_end, best_score = spans[0]
        for start, end, score in spans[1:]:
            if start <= current_end + max_gap:
                current_end = max(current_end, end)
                best_score = max(best_score, score)
                continue
            if current_end - current_start >= minimum_duration:
                merged.append(
                    SoundEvent(
                        event_id=f"sound-{serial:04d}",
                        label=label,
                        start=current_start,
                        end=current_end,
                        score=best_score,
                    )
                )
                serial += 1
            current_start, current_end, best_score = start, end, score
        if current_end - current_start >= minimum_duration:
            merged.append(
                SoundEvent(
                    event_id=f"sound-{serial:04d}",
                    label=label,
                    start=current_start,
                    end=current_end,
                    score=best_score,
                )
            )
            serial += 1

    merged.sort(key=lambda event: (event.start, event.end, event.label))
    return merged


def save_manifest(path: Path, video_path: Path, events: Sequence[SoundEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "video_path": str(video_path),
        "events": [asdict(event) for event in events],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> tuple[Path, list[SoundEvent]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("지원하지 않는 분석 파일 버전입니다.")
    events: list[SoundEvent] = []
    for item in data["events"]:
        item.setdefault("query", item.get("label", ""))
        item.setdefault("extracted_duration", 0.0)
        event = SoundEvent(**item)
        if event.extracted_path:
            event.extracted_path = str(
                require_local_media_file(event.extracted_path, "분리 오디오")
            )
        events.append(event)
    return require_local_media_file(data["video_path"], "영상"), events


def build_mute_filter(events: Sequence[SoundEvent]) -> tuple[str, str]:
    muted = [event for event in events if event.muted and event.extracted_path]
    if not muted:
        return "[0:a]anull[aout]", "[aout]"

    parts: list[str] = []
    mix_inputs = ["[0:a]"]
    for index, event in enumerate(muted, start=1):
        duration = max(0.05, event.extracted_duration or event.duration + 0.5)
        fade_out_start = max(0.0, duration - 0.03)
        delay_ms = max(0, round(event.extraction_start * 1000))
        label = f"mute{index}"
        parts.append(
            f"[{index}:a]aresample=48000,"
            f"afade=t=in:st=0:d=0.03,"
            f"afade=t=out:st={fade_out_start:.3f}:d=0.03,"
            f"volume=-1,adelay={delay_ms}|{delay_ms}[{label}]"
        )
        mix_inputs.append(f"[{label}]")
    weights = " ".join("1" for _ in mix_inputs)
    parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:"
        f"weights='{weights}':normalize=0:duration=first,alimiter=limit=0.98[aout]"
    )
    return ";".join(parts), "[aout]"


def is_music_partition(events: Sequence[SoundEvent]) -> bool:
    return len(events) == 2 and {event.event_id for event in events} == MUSIC_PARTITION_IDS


def build_partition_filter(events: Sequence[SoundEvent]) -> tuple[str, str]:
    """Mix the separated music/non-music stems directly instead of subtracting."""
    kept_inputs = [
        f"[{index}:a]"
        for index, event in enumerate(events, start=1)
        if not event.muted
    ]
    if not kept_inputs:
        return "[0:a]volume=0[aout]", "[aout]"
    if len(kept_inputs) == 1:
        return f"{kept_inputs[0]}aresample=48000,alimiter=limit=0.98[aout]", "[aout]"
    joined = "".join(kept_inputs)
    return (
        f"{joined}amix=inputs={len(kept_inputs)}:normalize=0:duration=longest,"
        "aresample=48000,alimiter=limit=0.98[aout]",
        "[aout]",
    )


def _build_mixed_video_command(
    video_path: Path,
    output_path: Path,
    events: Sequence[SoundEvent],
    *,
    preview: bool,
) -> list[str]:
    muted = [event for event in events if event.muted]
    partition = is_music_partition(events)
    required = list(events) if partition else muted
    missing = [event.label for event in required if not event.extracted_path]
    if missing:
        raise ValueError("AI 추출이 끝나지 않은 뮤트 항목: " + ", ".join(missing))

    video_path = require_local_media_file(video_path, "영상")
    command = [
        *ffmpeg_command_prefix("ffmpeg"),
        "-y",
        *ffmpeg_file_input(video_path, "영상"),
    ]
    inputs = list(events) if partition else muted
    for event in inputs:
        command.extend(ffmpeg_file_input(event.extracted_path, "분리 오디오"))
    if partition:
        filter_graph, output_label = build_partition_filter(events)
    else:
        filter_graph, output_label = build_mute_filter(events)
    command.extend(
        ["-filter_complex", filter_graph, "-map", "0:v:0", "-map", output_label]
    )
    if preview:
        command.extend(_preview_video_args())
    else:
        command.extend(["-c:v", "copy"])
    command.extend(["-c:a", "aac", "-b:a", "192k" if preview else "320k"])
    if not preview and output_path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        command.extend(["-movflags", "+faststart"])
    command.extend(["-shortest", str(output_path)])
    return command


def create_muted_preview_video(
    video_path: Path, output_path: Path, events: Sequence[SoundEvent]
) -> None:
    """Create a lightweight preview with the selected separated sounds muted."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        _build_mixed_video_command(video_path, output_path, events, preview=True)
    )


def export_video(video_path: Path, output_path: Path, events: Sequence[SoundEvent]) -> None:
    """Save a final copy while preserving the original encoded video stream."""
    if output_path.exists():
        raise FileExistsError(f"기존 사본을 덮어쓸 수 없습니다: {output_path}")
    temporary_output = output_path.with_name(
        f".{output_path.stem}.{uuid.uuid4().hex}.tmp{output_path.suffix}"
    )
    try:
        command = _build_mixed_video_command(
            video_path, temporary_output, events, preview=False
        )
        run_command(command, timeout=media_command_timeout(probe_duration(video_path)))
        temporary_output.rename(output_path)
    finally:
        temporary_output.unlink(missing_ok=True)

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MUSIC_PARTITION_IDS = {"music", "non-music"}


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
        return str(bundled)
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} 실행 파일을 찾을 수 없습니다.")
    return path


def run_command(command: Sequence[str]) -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"명령 실행 실패: {' '.join(command)}")


def extract_audio(video_path: Path, output_wav: Path) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            require_program("ffmpeg"),
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ]
    )


def probe_duration(media_path: Path) -> float:
    completed = subprocess.run(
        [
            require_program("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "미디어 길이를 읽지 못했습니다.")
    return float(completed.stdout.strip())


def create_preview_video(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Create a lightweight preview using the clip picture and a chosen audio track."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            require_program("ffmpeg"),
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]
    )


def extract_event_clip(
    source_wav: Path,
    output_wav: Path,
    start: float,
    end: float,
    padding: float = 0.25,
) -> float:
    clip_start = max(0.0, start - padding)
    duration = max(0.05, end - clip_start + padding)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            require_program("ffmpeg"),
            "-y",
            "-ss",
            f"{clip_start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(source_wav),
            "-ac",
            "1",
            "-ar",
            "32000",
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ]
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
        events.append(SoundEvent(**item))
    return Path(data["video_path"]), events


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


def export_video(video_path: Path, output_path: Path, events: Sequence[SoundEvent]) -> None:
    muted = [event for event in events if event.muted]
    partition = is_music_partition(events)
    required = list(events) if partition else muted
    missing = [event.label for event in required if not event.extracted_path]
    if missing:
        raise ValueError("AI 추출이 끝나지 않은 뮤트 항목: " + ", ".join(missing))

    command = [require_program("ffmpeg"), "-y", "-i", str(video_path)]
    inputs = list(events) if partition else muted
    for event in inputs:
        command.extend(["-i", event.extracted_path])
    if partition:
        filter_graph, output_label = build_partition_filter(events)
    else:
        filter_graph, output_label = build_mute_filter(events)
    command.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "0:v:0",
            "-map",
            output_label,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
        ]
    )
    if output_path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        command.extend(["-movflags", "+faststart"])
    command.extend(["-shortest", str(output_path)])
    run_command(command)

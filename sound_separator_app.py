from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Sequence

import cv2
from PIL import Image, ImageTk

from audio_core import (
    VIDEO_EXTENSIONS,
    SoundEvent,
    application_root,
    create_preview_video,
    export_video,
    extract_audio,
    probe_duration,
    require_program,
    run_command,
    save_manifest,
)


APP_TITLE = "영상 음악 분리·제거기"
PREVIEW_WIDTH = 420
PREVIEW_HEIGHT = 236
PREVIEW_FPS = 30
PREVIEW_UPDATE_MS = 15
DEFAULT_VOLUME = 100
DEFAULT_MODEL_ID = "avcass"
MODEL_LABELS = {
    "avcass": "AV-CASS",
    "bandit": "BandIt",
    "audiosep": "AudioSep",
}
VISIBLE_MODEL_IDS = ("avcass",)
USER_CONTENT_NOTICE = (
    "처리할 영상·음원의 저작권과 이용 권리를 확인하고, 결과물을 사용하는 책임은 "
    "사용자에게 있습니다."
)
LEGAL_INFORMATION_FILES = (
    ("제3자 고지·출처·논문", "THIRD_PARTY_NOTICES.md"),
    ("FFmpeg LGPL 빌드 정보", "FFMPEG_BUILD.md"),
    ("Video Music Separator 라이선스", "LICENSE"),
    ("MIT License 전문", "licenses/MIT.txt"),
    ("Apache License 2.0 전문", "licenses/Apache-2.0.txt"),
    ("GNU LGPL v3 전문", "licenses/LGPL-3.0.txt"),
    ("GNU GPL v3 전문", "licenses/GPL-3.0.txt"),
)
AUDIOSEP_QUERIES = {
    "music": ("기본 음악", "music"),
    "background": ("배경음악", "background music"),
    "cinematic": ("영화 음악", "cinematic score"),
    "instrumental": ("악기 음악", "instrumental music"),
    "ambient": ("앰비언트 음악", "ambient music"),
}
AUDIOSEP_COMPARISON_QUERY_IDS = ("music", "background", "cinematic")


def clamp_volume(value: float) -> int:
    return max(0, min(100, round(value)))


def format_playback_time(seconds: float) -> str:
    total_seconds = max(0, round(seconds))
    minutes, second = divmod(total_seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


def playback_position(
    offset: float, started_at: float, now: float, duration: float
) -> float:
    return min(max(0.0, duration), max(0.0, offset + now - started_at))


def worker_progress_message(model_id: str, line: str) -> str | None:
    label = MODEL_LABELS.get(model_id, model_id)
    if model_id == "avcass":
        if line.startswith("[setup] 영상 프레임"):
            return f"{label} · 영상 장면을 준비하는 중…"
        if line.startswith("[setup] AV-CASS"):
            return f"{label} · 분리 모델을 불러오는 중…"
        if line.startswith("[setup] CAVP"):
            return f"{label} · 영상 인식 모델을 불러오는 중…"
        match = re.match(r"^\[run (\d+)/(\d+)\]", line)
        if match:
            return f"{label} · 구간 {match.group(1)}/{match.group(2)} 분리 중…"
    if line.startswith("[done]"):
        return f"{label} · 분리 결과를 정리하는 중…"
    return None


def load_legal_information(root: Path) -> str:
    sections = [f"사용자 콘텐츠 안내\n\n{USER_CONTENT_NOTICE}"]
    for title, relative_path in LEGAL_INFORMATION_FILES:
        path = root / relative_path
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
        else:
            content = f"파일을 찾을 수 없습니다: {relative_path}"
        sections.append(f"{title}\n{'=' * len(title)}\n\n{content}")
    return "\n\n\n".join(sections)


def run_worker_command(
    command: Sequence[str], on_output: Callable[[str], None]
) -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
        env=environment,
    )
    output: list[str] = []
    if process.stdout is not None:
        try:
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                output.append(line)
                on_output(line)
        finally:
            process.stdout.close()
    return_code = process.wait()
    if return_code:
        detail = "\n".join(output[-40:])
        raise RuntimeError(detail or f"분리 작업 실행 실패: {' '.join(command)}")


def build_ffplay_command(media_path: Path, volume: float, offset: float = 0.0) -> list[str]:
    command = [
        require_program("ffplay"),
        "-nodisp",
        "-autoexit",
        "-sync",
        "ext",
        "-volume",
        str(clamp_volume(volume)),
    ]
    if offset > 0.05:
        command.extend(["-ss", f"{offset:.3f}"])
    command.append(str(media_path))
    return command


def build_partition_events(
    duration: float,
    music_path: Path | None = None,
    non_music_path: Path | None = None,
    music_query: str = "music",
) -> list[SoundEvent]:
    return [
        SoundEvent(
            "music",
            "음악 (BGM)",
            0.0,
            duration,
            1.0,
            query=music_query,
            extracted_path=str(music_path) if music_path else "",
            extracted_duration=duration,
            extraction_quality="ok" if music_path else "",
        ),
        SoundEvent(
            "non-music",
            "음악 아님 (목소리·효과음)",
            0.0,
            duration,
            1.0,
            query="non-music",
            extracted_path=str(non_music_path) if non_music_path else "",
            extracted_duration=duration,
            extraction_quality="ok" if non_music_path else "",
        ),
    ]


def assess_partition_metrics(metrics: dict[str, float]) -> tuple[str, str]:
    reconstruction = float(metrics.get("reconstruction_source_correlation", 0.0))
    music_correlation = float(metrics.get("music_source_correlation", 0.0))
    non_music_ratio = float(metrics.get("non_music_rms_ratio", 0.0))
    if reconstruction < 0.98:
        return (
            "review",
            "두 분리본을 합쳐도 원본과 충분히 일치하지 않습니다. 다시 분리해 주세요.",
        )
    if music_correlation > 0.995 and non_music_ratio < 0.001:
        return (
            "review",
            "음악 트랙이 원본 전체와 사실상 같고 음악 아님 트랙은 거의 무음입니다. "
            "원본에 목소리나 효과음이 있다면 분리가 실패한 결과입니다.",
        )
    return "ok", ""


def preview_path_for_event(work_dir: Path, event: SoundEvent) -> Path:
    stem_name = Path(event.extracted_path).stem or event.event_id
    return work_dir / "previews" / f"{stem_name}_preview.mkv"


def muted_mix_preview_path(work_dir: Path) -> Path:
    return work_dir / "previews" / "muted_mix_preview.mkv"


def audiosep_result_key(query_id: str) -> str:
    if query_id not in AUDIOSEP_QUERIES:
        raise ValueError(f"지원하지 않는 AudioSep 질의입니다: {query_id}")
    return "audiosep" if query_id == "music" else f"audiosep-{query_id}"


def model_result_directory(work_dir: Path, result_key: str) -> Path:
    valid_keys = set(MODEL_LABELS) | {
        audiosep_result_key(query_id) for query_id in AUDIOSEP_QUERIES
    }
    if result_key not in valid_keys:
        raise ValueError(f"지원하지 않는 분리 결과입니다: {result_key}")
    return work_dir / "models" / result_key


def bandit_runtime_paths(runtime_root: Path) -> tuple[Path, Path, Path, Path]:
    bandit_root = runtime_root / "bandit"
    return (
        runtime_root / "env" / "python.exe",
        bandit_root / "repo",
        bandit_root / "hparams.yaml",
        bandit_root / "model" / "dnr-3s-mus64-l1snr-plus.ckpt",
    )


def audiosep_runtime_paths(runtime_root: Path) -> tuple[Path, Path, Path, Path]:
    audiosep_root = runtime_root / "audiosep"
    return (
        runtime_root / "env" / "python.exe",
        audiosep_root / "repo",
        audiosep_root / "model" / "pytorch_model.bin",
        audiosep_root,
    )


def avcass_runtime_paths(
    runtime_root: Path,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    avcass_root = runtime_root / "avcass"
    return (
        runtime_root / "env" / "python.exe",
        avcass_root / "repo",
        avcass_root / "deps",
        avcass_root / "model" / "av_cass_checkpoint.pt",
        avcass_root / "model" / "cavp" / "cavp_epoch66.ckpt",
        avcass_root,
    )


def muted_copy_output_path(video_path: Path, events: list[SoundEvent]) -> Path:
    muted_ids = {event.event_id for event in events if event.muted}
    suffix = {
        frozenset({"music"}): "음악제거",
        frozenset({"non-music"}): "음악만",
        frozenset({"music", "non-music"}): "전체소리제거",
    }.get(frozenset(muted_ids), "소리조정")
    return video_path.with_name(f"{video_path.stem}_{suffix}.mp4")


def cleanup_work_directory(video_path: Path, work_dir: Path) -> bool:
    expected = video_path.parent / f"{video_path.stem}_sound_work"
    if work_dir.resolve() != expected.resolve():
        raise RuntimeError(f"예상한 작업 폴더가 아니어서 삭제하지 않았습니다: {work_dir}")
    if not work_dir.exists():
        return False
    if not work_dir.is_dir() or work_dir.is_symlink():
        raise RuntimeError(f"안전하게 삭제할 수 없는 작업 폴더입니다: {work_dir}")
    shutil.rmtree(work_dir)
    return True


class SoundSeparatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x860")
        self.minsize(920, 740)
        self.video_path: Path | None = None
        self.work_dir: Path | None = None
        self.result_dir: Path | None = None
        self.source_wav: Path | None = None
        self.source_ready = False
        self.events: list[SoundEvent] = []
        self.model_results: dict[str, list[SoundEvent]] = {}
        self.model_preview_dirty: dict[str, bool] = {}
        self.active_model_id = DEFAULT_MODEL_ID
        self.player: subprocess.Popen[bytes] | None = None
        self.player_kind: str | None = None
        self.player_event_id: str | None = None
        self.player_source: Path | None = None
        self.player_started_at = 0.0
        self.player_offset = 0.0
        self.player_duration = 0.0
        self.player_poll_after_id: str | None = None
        self.volume_restart_after_id: str | None = None
        self.video_capture: cv2.VideoCapture | None = None
        self.video_position = 0.0
        self.video_poll_after_id: str | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_seek_var = tk.DoubleVar(value=0.0)
        self.preview_time_var = tk.StringVar(value="00:00 / 00:00")
        self.seek_dragging = False
        self.updating_seek_slider = False
        self.auto_extracting = False
        self.busy = False

        self.portable_runtime = application_root() / "audiosep"
        self.model_var = tk.StringVar(value=self.active_model_id)
        self.audiosep_query_var = tk.StringVar(value="music")
        self.audiosep_query_label_var = tk.StringVar(
            value=AUDIOSEP_QUERIES["music"][0]
        )
        self.model_status_var = tk.StringVar(
            value=f"선택 모델: {MODEL_LABELS[self.active_model_id]} · 분석 전"
        )
        self.volume_var = tk.DoubleVar(value=DEFAULT_VOLUME)
        self.status_var = tk.StringVar(value="영상을 선택해 주세요.")
        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        source = ttk.LabelFrame(root, text="1. 영상 선택", padding=10)
        source.grid(row=2, column=0, sticky="ew")
        source.columnconfigure(1, weight=1)
        ttk.Button(source, text="영상 열기", command=self.choose_video).grid(row=0, column=0, padx=(0, 8))
        self.video_var = tk.StringVar(value="선택된 영상 없음")
        ttk.Label(source, textvariable=self.video_var).grid(row=0, column=1, sticky="w")
        ttk.Button(source, text="AV-CASS로 분리", command=self.analyze).grid(
            row=0, column=2, padx=(8, 0)
        )
        self.audiosep_compare_button = ttk.Button(
            source,
            text="AudioSep 3종 비교",
            command=self.analyze_audiosep_comparison,
        )

        model_area = ttk.Frame(source)
        model_area.grid(row=1, column=0, columnspan=2, sticky="w", pady=(9, 0))
        ttk.Label(model_area, text="분리 모델: AV-CASS").pack(side="left")
        self.audiosep_query_combo = ttk.Combobox(
            model_area,
            state="disabled",
            width=13,
            textvariable=self.audiosep_query_label_var,
            values=tuple(label for label, _query in AUDIOSEP_QUERIES.values()),
        )
        self.audiosep_query_combo.bind(
            "<<ComboboxSelected>>", self.select_audiosep_query
        )
        self._update_audiosep_query_control()
        ttk.Label(source, textvariable=self.model_status_var, foreground="#555555").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(7, 0)
        )

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(actions, text="전체 영상 재생", command=self.preview_original).pack(side="left")
        ttk.Button(actions, text="전체 영상 정지", command=self.stop_original_preview).pack(side="left", padx=4)
        ttk.Separator(actions, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Label(actions, text="전체 재생 볼륨").pack(side="left")
        ttk.Scale(
            actions,
            from_=0,
            to=100,
            variable=self.volume_var,
            length=170,
            command=self._schedule_volume_update,
        ).pack(side="left", padx=(6, 4))
        self.volume_label = ttk.Label(actions, width=4, text=str(DEFAULT_VOLUME))
        self.volume_label.pack(side="left")

        preview_area = ttk.Frame(root)
        preview_area.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        preview_area.columnconfigure(0, weight=1)
        preview_area.columnconfigure(2, weight=1)

        ttk.Button(
            preview_area,
            text="라이선스·출처",
            command=self.show_legal_information,
        ).grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=(8, 0))

        preview_frame = ttk.LabelFrame(preview_area, text="영상 미리보기", padding=8)
        preview_frame.grid(row=0, column=1)
        preview_surface = tk.Frame(
            preview_frame,
            width=PREVIEW_WIDTH,
            height=PREVIEW_HEIGHT,
            background="#111111",
        )
        preview_surface.pack()
        preview_surface.pack_propagate(False)
        self.preview_label = tk.Label(
            preview_surface,
            text="재생하면 여기에 영상이 표시됩니다.",
            background="#111111",
            foreground="#D0D0D0",
        )
        self.preview_label.pack(fill="both", expand=True)

        playback_position_area = ttk.Frame(preview_frame)
        playback_position_area.pack(fill="x", pady=(7, 0))
        self.preview_seek_scale = ttk.Scale(
            playback_position_area,
            from_=0,
            to=1,
            variable=self.preview_seek_var,
            command=self._preview_seek_changed,
        )
        self.preview_seek_scale.pack(side="left", fill="x", expand=True)
        self.preview_seek_scale.state(["disabled"])
        self.preview_seek_scale.bind("<ButtonPress-1>", self._begin_preview_seek)
        self.preview_seek_scale.bind("<ButtonRelease-1>", self._commit_preview_seek)
        ttk.Label(
            playback_position_area,
            textvariable=self.preview_time_var,
            width=15,
            anchor="e",
        ).pack(side="left", padx=(8, 0))

        status_background = "#0B5EA8"
        status_area = tk.Frame(
            root,
            background=status_background,
            highlightbackground="#073E70",
            highlightthickness=1,
        )
        status_area.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        status_area.columnconfigure(0, weight=1)
        tk.Label(
            status_area,
            textvariable=self.status_var,
            foreground="#FFFFFF",
            background=status_background,
            anchor="center",
            font=("Segoe UI", 12, "bold"),
            padx=16,
            pady=9,
        ).grid(row=0, column=0, sticky="ew")

        table_frame = ttk.LabelFrame(root, text="2. 음악 / 음악 아님 분리 결과", padding=8)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(table_frame, padding=(6, 3))
        header.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="소리 구분", anchor="w").grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="AI 분리", width=16, anchor="center").grid(row=0, column=1)
        ttk.Label(header, text="영상과 듣기", width=13, anchor="center").grid(row=0, column=2)
        ttk.Label(header, text="전체 재생에서", width=13, anchor="center").grid(row=0, column=3)

        self.rows_canvas = tk.Canvas(table_frame, highlightthickness=0)
        self.rows_canvas.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.rows_canvas.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.rows_canvas.configure(yscrollcommand=scroll.set)
        self.rows_frame = ttk.Frame(self.rows_canvas)
        self.rows_window = self.rows_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>", self._update_rows_scrollregion)
        self.rows_canvas.bind("<Configure>", self._resize_rows_frame)

        footer = ttk.Frame(root)
        footer.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(2, weight=1)
        self.save_button = ttk.Button(
            footer,
            text="사본 저장",
            command=self.save_video,
            width=16,
        )
        self.save_button.grid(row=0, column=1, ipadx=6, ipady=4)
        ttk.Label(
            root,
            text=USER_CONTENT_NOTICE,
            foreground="#666666",
            anchor="center",
            wraplength=900,
        ).grid(row=6, column=0, sticky="ew", pady=(7, 0))

    def show_legal_information(self) -> None:
        window = tk.Toplevel(self)
        window.title("라이선스·출처·사용자 책임")
        window.geometry("860x680")
        window.minsize(650, 480)
        window.transient(self)

        text = ScrolledText(
            window,
            wrap="word",
            padx=14,
            pady=14,
            font=("Segoe UI", 10),
        )
        text.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        text.insert("1.0", load_legal_information(application_root()))
        text.configure(state="disabled")
        ttk.Button(window, text="닫기", command=window.destroy).pack(pady=(0, 10))

    def choose_video(self) -> None:
        if self.busy:
            messagebox.showinfo(APP_TITLE, "현재 작업이 끝날 때까지 기다려 주세요.")
            return
        selected = filedialog.askopenfilename(
            title="영상 선택",
            filetypes=[("영상 파일", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"), ("모든 파일", "*.*")],
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            messagebox.showerror(APP_TITLE, "지원하지 않는 영상 형식입니다.")
            return
        self.video_path = path
        self.work_dir = path.parent / f"{path.stem}_sound_work"
        self.result_dir = model_result_directory(
            self.work_dir, self._active_result_key()
        )
        self.source_wav = self.work_dir / "source_44k.wav"
        self.source_ready = False
        self.model_results.clear()
        self.model_preview_dirty.clear()
        self.stop_preview(refresh=False)
        self.video_var.set(str(path))
        self.events.clear()
        self.refresh_rows()
        self.model_status_var.set(
            f"선택 모델: {MODEL_LABELS[self.active_model_id]} · 분석 전"
        )
        self.status_var.set("영상을 열었습니다. AV-CASS 분리를 실행해 주세요.")

    def _bandit_is_available(self) -> bool:
        return all(path.exists() for path in bandit_runtime_paths(self.portable_runtime))

    def _audiosep_is_available(self) -> bool:
        python_path, repo, checkpoint, runtime_root = audiosep_runtime_paths(
            self.portable_runtime
        )
        return all(
            path.exists()
            for path in (
                python_path,
                repo,
                checkpoint,
                runtime_root / "roberta-base" / "model.safetensors",
            )
        )

    def _avcass_is_available(self) -> bool:
        python_path, repo, deps, checkpoint, cavp_checkpoint, _runtime_root = (
            avcass_runtime_paths(self.portable_runtime)
        )
        return all(
            path.exists()
            for path in (python_path, repo, deps, checkpoint, cavp_checkpoint)
        )

    def _model_is_available(self, model_id: str) -> bool:
        if model_id == "avcass":
            return self._avcass_is_available()
        if model_id == "bandit":
            return self._bandit_is_available()
        if model_id == "audiosep":
            return self._audiosep_is_available()
        return False

    def select_model(self) -> None:
        requested = self.model_var.get()
        if self.busy:
            self.model_var.set(self.active_model_id)
            messagebox.showinfo(APP_TITLE, "현재 작업이 끝날 때까지 모델을 바꿀 수 없습니다.")
            return
        if not self._model_is_available(requested):
            self.model_var.set(self.active_model_id)
            messagebox.showwarning(APP_TITLE, "선택한 모델의 실행 환경이 설치되지 않았습니다.")
            return

        self.stop_preview(refresh=False)
        self.active_model_id = requested
        self._update_audiosep_query_control()
        result_key = self._active_result_key()
        if self.work_dir is not None:
            self.result_dir = model_result_directory(self.work_dir, result_key)
        else:
            self.result_dir = None
        self.events = self.model_results.get(result_key, [])
        self.refresh_rows()
        if self.events:
            state = "분석 완료 · 저장 후보로 선택됨"
            self.status_var.set(
                f"{self._active_result_label()}의 기존 분리 결과를 불러왔습니다."
            )
        else:
            state = "분석 전"
            self.status_var.set(
                f"{self._active_result_label()}을 선택했습니다. 선택 모델로 분리를 실행해 주세요."
            )
        self.model_status_var.set(f"선택 모델: {self._active_result_label()} · {state}")

    def _active_result_key(self) -> str:
        if self.active_model_id == "audiosep":
            return audiosep_result_key(self.audiosep_query_var.get())
        return self.active_model_id

    def _active_audiosep_query(self) -> str:
        query_id = self.audiosep_query_var.get()
        if query_id not in AUDIOSEP_QUERIES:
            raise ValueError(f"지원하지 않는 AudioSep 질의입니다: {query_id}")
        return AUDIOSEP_QUERIES[query_id][1]

    def _active_result_label(self) -> str:
        if self.active_model_id != "audiosep":
            return MODEL_LABELS[self.active_model_id]
        label = AUDIOSEP_QUERIES[self.audiosep_query_var.get()][0]
        return f"AudioSep · {label}"

    def _update_audiosep_query_control(self) -> None:
        if not hasattr(self, "audiosep_query_combo"):
            return
        if self.active_model_id == "audiosep" and self._audiosep_is_available():
            self.audiosep_query_combo.configure(state="readonly")
            self.audiosep_compare_button.state(["!disabled"])
        else:
            self.audiosep_query_combo.configure(state="disabled")
            self.audiosep_compare_button.state(["disabled"])

    def select_audiosep_query(self, _event=None) -> None:
        if self.busy:
            self.audiosep_query_label_var.set(
                AUDIOSEP_QUERIES[self.audiosep_query_var.get()][0]
            )
            messagebox.showinfo(APP_TITLE, "현재 작업이 끝날 때까지 음악 유형을 바꿀 수 없습니다.")
            return
        if self.active_model_id != "audiosep":
            return
        selected_label = self.audiosep_query_label_var.get()
        selected_id = next(
            (
                query_id
                for query_id, (label, _query) in AUDIOSEP_QUERIES.items()
                if label == selected_label
            ),
            None,
        )
        if selected_id is None:
            self.audiosep_query_label_var.set(
                AUDIOSEP_QUERIES[self.audiosep_query_var.get()][0]
            )
            return
        self.audiosep_query_var.set(selected_id)
        self.stop_preview(refresh=False)
        result_key = self._active_result_key()
        self.result_dir = (
            model_result_directory(self.work_dir, result_key)
            if self.work_dir is not None
            else None
        )
        self.events = self.model_results.get(result_key, [])
        self.refresh_rows()
        state = "분석 완료 · 저장 후보로 선택됨" if self.events else "분석 전"
        self.model_status_var.set(
            f"선택 모델: {self._active_result_label()} · {state}"
        )
        if self.events:
            self.status_var.set(
                f"{self._active_result_label()}의 기존 분리 결과를 불러왔습니다."
            )
        else:
            self.status_var.set(
                f"{self._active_result_label()}을 선택했습니다. 분리를 실행해 주세요."
            )

    def _run_background(self, label: str, operation) -> None:
        if self.busy:
            messagebox.showinfo(APP_TITLE, "현재 작업이 끝날 때까지 기다려 주세요.")
            return
        self.busy = True
        self.status_var.set(label)

        def runner() -> None:
            try:
                operation()
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda: messagebox.showerror(APP_TITLE, message))
                self.after(0, lambda: self.status_var.set("작업에 실패했습니다."))
            finally:
                self.busy = False

        threading.Thread(target=runner, daemon=True).start()

    def _show_progress(self, message: str) -> None:
        self.after(0, lambda text=message: self.status_var.set(text))

    def analyze(self) -> None:
        if not self.video_path or not self.source_wav or not self.work_dir:
            messagebox.showwarning(APP_TITLE, "먼저 영상을 선택해 주세요.")
            return

        video_path = self.video_path
        source_wav = self.source_wav
        work_dir = self.work_dir
        model_id = self.active_model_id
        result_key = self._active_result_key()
        audiosep_query = (
            self._active_audiosep_query() if model_id == "audiosep" else "music"
        )
        result_dir = model_result_directory(work_dir, result_key)
        runtime_paths = self._validated_model_paths(model_id)
        if runtime_paths is None:
            return
        model_label = self._active_result_label()

        def operation() -> None:
            if not self.source_ready:
                self._show_progress(f"{model_label} · 영상에서 소리를 준비하는 중…")
                extract_audio(video_path, source_wav)
                self.source_ready = True
            self._show_progress(f"{model_label} · 분리 작업을 준비하는 중…")
            duration = probe_duration(source_wav)
            pending_events = build_partition_events(
                duration, music_query=audiosep_query
            )
            save_manifest(result_dir / "sounds.json", video_path, pending_events)
            self.auto_extracting = True

            def show_pending() -> None:
                if self._active_result_key() == result_key:
                    self.result_dir = result_dir
                    self.events = pending_events
                    self.refresh_rows()

            self.after(0, show_pending)
            self.after(
                0,
                lambda: self.status_var.set(
                    f"{model_label}로 음악과 음악 아닌 소리를 분리하는 중입니다…"
                ),
            )
            try:
                completed_events = self._separate_partition(
                    model_id,
                    duration,
                    video_path,
                    source_wav,
                    result_dir,
                    runtime_paths,
                    audiosep_query,
                )
                save_manifest(result_dir / "sounds.json", video_path, completed_events)
            except Exception:
                def restore_previous() -> None:
                    if self._active_result_key() == result_key:
                        self.events = self.model_results.get(result_key, [])
                        self.refresh_rows()
                        state = "기존 결과 유지" if self.events else "분석 실패"
                        self.model_status_var.set(
                            f"선택 모델: {model_label} · {state}"
                        )

                self.after(0, restore_previous)
                raise
            finally:
                self.auto_extracting = False

            def finish() -> None:
                self.model_results[result_key] = completed_events
                self.model_preview_dirty[result_key] = True
                if self._active_result_key() == result_key:
                    self.result_dir = result_dir
                    self.events = completed_events
                    self.refresh_rows()
                    self.model_status_var.set(
                        f"선택 모델: {model_label} · 분석 완료 · 저장 후보로 선택됨"
                    )
                    self.status_var.set(
                        f"{model_label} 분리 완료. 다른 모델과 비교하거나 음악 행을 뮤트해 확인해 주세요."
                    )

            self.after(0, finish)

        self._run_background(f"{model_label} 분리를 시작합니다…", operation)

    def analyze_audiosep_comparison(self) -> None:
        if not self.video_path or not self.source_wav or not self.work_dir:
            messagebox.showwarning(APP_TITLE, "먼저 영상을 선택해 주세요.")
            return
        if not self._audiosep_is_available():
            messagebox.showerror(APP_TITLE, "AudioSep 실행 환경이 설치되지 않았습니다.")
            return

        video_path = self.video_path
        source_wav = self.source_wav
        work_dir = self.work_dir
        runtime_paths = self._validated_model_paths("audiosep")
        if runtime_paths is None:
            return
        python_path, repo, checkpoint, runtime_root = runtime_paths

        def operation() -> None:
            if not self.source_ready:
                self._show_progress("AudioSep · 영상에서 소리를 준비하는 중…")
                extract_audio(video_path, source_wav)
                self.source_ready = True
            self._show_progress("AudioSep · 분리 작업을 준비하는 중…")
            duration = probe_duration(source_wav)
            jobs = []
            result_specs = []
            for query_id in AUDIOSEP_COMPARISON_QUERY_IDS:
                label, query = AUDIOSEP_QUERIES[query_id]
                result_key = audiosep_result_key(query_id)
                result_dir = model_result_directory(work_dir, result_key)
                stem_dir = result_dir / "stems"
                music_path = stem_dir / "music.wav"
                non_music_path = stem_dir / "non-music.wav"
                jobs.append(
                    {
                        "query": query,
                        "music_output": str(music_path.resolve()),
                        "non_music_output": str(non_music_path.resolve()),
                    }
                )
                result_specs.append(
                    (result_key, result_dir, label, query, music_path, non_music_path)
                )

            jobs_path = work_dir / "audiosep_comparison_jobs.json"
            jobs_path.parent.mkdir(parents=True, exist_ok=True)
            jobs_path.write_text(
                json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            command = [
                str(python_path),
                str(application_root() / "audiosep_worker.py"),
                "--repo",
                str(repo),
                "--model",
                str(checkpoint),
                "--runtime-root",
                str(runtime_root),
                "--input",
                str(source_wav),
                "--jobs-json",
                str(jobs_path),
            ]
            run_command(command)

            completed_results: dict[str, list[SoundEvent]] = {}
            for result_key, result_dir, _label, query, music_path, non_music_path in result_specs:
                events = self._load_partition_results(
                    duration,
                    video_path,
                    result_dir,
                    music_path,
                    non_music_path,
                    query,
                )
                save_manifest(result_dir / "sounds.json", video_path, events)
                completed_results[result_key] = events

            def finish() -> None:
                self.model_results.update(completed_results)
                for result_key in completed_results:
                    self.model_preview_dirty[result_key] = True
                active_key = self._active_result_key()
                if active_key in completed_results:
                    self.result_dir = model_result_directory(work_dir, active_key)
                    self.events = completed_results[active_key]
                    self.refresh_rows()
                self.model_status_var.set(
                    f"선택 모델: {self._active_result_label()} · 분석 완료 · 저장 후보로 선택됨"
                )
                self.status_var.set(
                    "AudioSep 기본 음악·배경음악·영화 음악 비교가 완료됐습니다. "
                    "음악 유형을 바꿔 각 결과를 들어보세요."
                )

            self.after(0, finish)

        self._run_background(
            "AudioSep 모델을 한 번 불러 3가지 음악 유형을 비교하는 중입니다…",
            operation,
        )

    def _update_rows_scrollregion(self, _event=None) -> None:
        self.rows_canvas.configure(scrollregion=self.rows_canvas.bbox("all"))

    def _resize_rows_frame(self, event) -> None:
        self.rows_canvas.itemconfigure(self.rows_window, width=event.width)

    def refresh_rows(self) -> None:
        for child in self.rows_frame.winfo_children():
            child.destroy()
        if not self.events:
            ttk.Label(
                self.rows_frame,
                text="영상을 연 뒤 선택한 모델로 분리를 실행해 주세요.",
                padding=12,
            ).pack(anchor="w")
            return
        for event in self.events:
            row = ttk.Frame(self.rows_frame, padding=(6, 5))
            row.pack(fill="x")
            row.columnconfigure(0, weight=1)
            ttk.Label(row, text=event.label, anchor="w").grid(row=0, column=0, sticky="ew")
            if event.extracted_path:
                extraction_state = {
                    "ok": "완료",
                    "review": "검토 필요",
                    "failed": "추출 실패",
                }.get(event.extraction_quality, "완료")
            elif self.auto_extracting:
                extraction_state = "자동 추출 중…"
            else:
                extraction_state = "미추출"
            ttk.Label(row, text=extraction_state, width=16, anchor="center").grid(row=0, column=1)
            playing = self._player_is_running() and self.player_kind == "extracted" and self.player_event_id == event.event_id
            listen_button = ttk.Button(
                row,
                text="정지" if playing else "듣기",
                width=9,
                command=lambda event_id=event.event_id: self.toggle_event_preview(event_id),
            )
            listen_button.grid(row=0, column=2, padx=4)
            if not event.extracted_path:
                listen_button.state(["disabled"])
            ttk.Button(
                row,
                text="뮤트 해제" if event.muted else "뮤트",
                width=9,
                command=lambda event_id=event.event_id: self.toggle_event_mute(event_id),
            ).grid(row=0, column=3)
            ttk.Separator(self.rows_frame, orient="horizontal").pack(fill="x")
        self._update_rows_scrollregion()

    def _event_by_id(self, event_id: str) -> SoundEvent | None:
        return next((event for event in self.events if event.event_id == event_id), None)

    def toggle_event_mute(self, event_id: str) -> None:
        if self.busy:
            messagebox.showinfo(APP_TITLE, "현재 작업이 끝날 때까지 기다려 주세요.")
            return
        event = self._event_by_id(event_id)
        if event is None:
            return
        if event.extraction_quality == "failed":
            messagebox.showwarning(APP_TITLE, event.extraction_note or "분리본이 없습니다.")
            return
        if (
            event.extraction_quality == "review"
            and not event.muted
            and not messagebox.askyesno(
                APP_TITLE,
                f"{event.label}\n\n{event.extraction_note}\n\n그래도 이 소리를 뮤트할까요?",
            )
        ):
            return
        if self.player_kind == "original":
            self.stop_preview(refresh=False)
        event.muted = not event.muted
        self.model_preview_dirty[self._active_result_key()] = True
        self._persist_and_refresh()

    def _persist_and_refresh(self) -> None:
        if self.result_dir and self.video_path:
            save_manifest(self.result_dir / "sounds.json", self.video_path, self.events)
        self.refresh_rows()

    def _player_is_running(self) -> bool:
        return self.player is not None and self.player.poll() is None

    def _start_audio_preview(
        self,
        source: Path,
        kind: str,
        event_id: str | None = None,
        offset: float = 0.0,
    ) -> None:
        self.stop_preview(refresh=False)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        duration = probe_duration(source)
        offset = min(max(0.0, offset), duration)
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"영상 미리보기를 열 수 없습니다: {source}")
        capture.set(cv2.CAP_PROP_POS_MSEC, offset * 1000.0)
        self.video_capture = capture
        self.video_position = offset
        self.player_duration = duration
        self._configure_preview_seek(duration, offset)
        self._read_video_frame(offset, force_seek=True)
        self.player = subprocess.Popen(
            build_ffplay_command(source, self.volume_var.get(), offset),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        self.player_kind = kind
        self.player_event_id = event_id
        self.player_source = source
        self.player_offset = offset
        self.player_started_at = time.monotonic()
        self.refresh_rows()
        self.player_poll_after_id = self.after(250, self._poll_player)
        self.video_poll_after_id = self.after(PREVIEW_UPDATE_MS, self._poll_video_frame)

    def _configure_preview_seek(self, duration: float, position: float) -> None:
        self.preview_seek_scale.configure(to=max(duration, 0.001))
        self.preview_seek_scale.state(["!disabled"])
        self._set_preview_position(position)

    def _set_preview_position(self, position: float) -> None:
        self.updating_seek_slider = True
        try:
            self.preview_seek_var.set(position)
        finally:
            self.updating_seek_slider = False
        self.preview_time_var.set(
            f"{format_playback_time(position)} / "
            f"{format_playback_time(self.player_duration)}"
        )

    def _display_video_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((PREVIEW_WIDTH, PREVIEW_HEIGHT), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (PREVIEW_WIDTH, PREVIEW_HEIGHT), "black")
        canvas.paste(
            image,
            ((PREVIEW_WIDTH - image.width) // 2, (PREVIEW_HEIGHT - image.height) // 2),
        )
        self.preview_photo = ImageTk.PhotoImage(canvas)
        self.preview_label.configure(image=self.preview_photo, text="")

    def _read_video_frame(self, target: float, force_seek: bool = False) -> None:
        capture = self.video_capture
        if capture is None:
            return
        frame_tolerance = 0.5 / PREVIEW_FPS
        if not force_seek and self.video_position + frame_tolerance >= target:
            return
        if force_seek or target - self.video_position > 0.5:
            capture.set(cv2.CAP_PROP_POS_MSEC, target * 1000.0)
        newest = None
        for _ in range(PREVIEW_FPS):
            ok, frame = capture.read()
            if not ok:
                break
            newest = frame
            self.video_position = max(
                target if force_seek else 0.0,
                capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
            )
            if self.video_position + frame_tolerance >= target:
                break
        if newest is not None:
            self._display_video_frame(newest)

    def _poll_video_frame(self) -> None:
        self.video_poll_after_id = None
        if not self._player_is_running():
            return
        position = playback_position(
            self.player_offset,
            self.player_started_at,
            time.monotonic(),
            self.player_duration,
        )
        if not self.seek_dragging:
            self._read_video_frame(position)
            self._set_preview_position(position)
        self.video_poll_after_id = self.after(PREVIEW_UPDATE_MS, self._poll_video_frame)

    def _begin_preview_seek(self, _event=None) -> None:
        if self._player_is_running():
            self.seek_dragging = True

    def _preview_seek_changed(self, value: str) -> None:
        if self.updating_seek_slider:
            return
        position = float(value)
        self.preview_time_var.set(
            f"{format_playback_time(position)} / "
            f"{format_playback_time(self.player_duration)}"
        )

    def _commit_preview_seek(self, _event=None) -> None:
        if not self.seek_dragging:
            return
        self.seek_dragging = False
        if self.player_source is None or self.player_kind is None:
            return
        source = self.player_source
        kind = self.player_kind
        event_id = self.player_event_id
        offset = float(self.preview_seek_var.get())
        self._start_audio_preview(source, kind, event_id, offset)

    def preview_original(self) -> None:
        if not self.video_path or not self.video_path.exists():
            messagebox.showinfo(APP_TITLE, "먼저 영상을 선택해 주세요.")
            return
        muted = [event for event in self.events if event.muted]
        if not muted:
            self._start_audio_preview(self.video_path, "original")
            self.status_var.set("원본 전체 믹스를 영상과 함께 재생합니다.")
            return
        if not self.result_dir:
            return
        target = muted_mix_preview_path(self.result_dir)
        if target.exists() and not self.model_preview_dirty.get(
            self._active_result_key(), True
        ):
            self._start_audio_preview(target, "original")
            self.status_var.set(f"{len(muted)}개 소리를 뮤트한 전체 믹스를 재생합니다.")
            return
        video_path = self.video_path
        events = list(self.events)
        result_key = self._active_result_key()

        def operation() -> None:
            export_video(video_path, target, events)
            self.model_preview_dirty[result_key] = False
            self.after(0, lambda: self._start_audio_preview(target, "original"))
            self.after(0, lambda: self.status_var.set(f"{len(muted)}개 소리를 뮤트한 전체 믹스를 재생합니다."))

        self._run_background("선택한 소리만 뮤트한 전체 영상 미리보기를 준비하는 중입니다…", operation)

    def toggle_event_preview(self, event_id: str) -> None:
        event = self._event_by_id(event_id)
        if event is None or not event.extracted_path:
            return
        if self._player_is_running() and self.player_kind == "extracted" and self.player_event_id == event_id:
            self.stop_preview()
            return
        if not self.result_dir:
            return
        preview_path = preview_path_for_event(self.result_dir, event)
        if not preview_path.exists():
            messagebox.showinfo(APP_TITLE, "분리본 영상 미리보기를 찾을 수 없습니다. 다시 분석해 주세요.")
            return
        self._start_audio_preview(preview_path, "extracted", event_id)

    def stop_original_preview(self) -> None:
        if self.player_kind == "original":
            self.stop_preview()

    def stop_preview(self, refresh: bool = True) -> None:
        if self.player_poll_after_id:
            try:
                self.after_cancel(self.player_poll_after_id)
            except tk.TclError:
                pass
            self.player_poll_after_id = None
        if self.video_poll_after_id:
            try:
                self.after_cancel(self.video_poll_after_id)
            except tk.TclError:
                pass
            self.video_poll_after_id = None
        if self.video_capture is not None:
            self.video_capture.release()
        self.video_capture = None
        if self.player and self.player.poll() is None:
            self.player.terminate()
        self.player = None
        self.player_kind = None
        self.player_event_id = None
        self.player_source = None
        self.player_started_at = 0.0
        self.player_offset = 0.0
        self.player_duration = 0.0
        self.video_position = 0.0
        self.seek_dragging = False
        if hasattr(self, "preview_seek_scale"):
            self.preview_seek_scale.state(["disabled"])
            self._set_preview_position(0.0)
        self.preview_photo = None
        self.preview_label.configure(
            image="",
            text="재생하면 여기에 영상이 표시됩니다.",
        )
        if refresh:
            self.refresh_rows()

    def _poll_player(self) -> None:
        self.player_poll_after_id = None
        if not self._player_is_running():
            self.stop_preview()
            return
        self.player_poll_after_id = self.after(250, self._poll_player)

    def _schedule_volume_update(self, value: str) -> None:
        self.volume_label.configure(text=str(clamp_volume(float(value))))
        if self.volume_restart_after_id:
            self.after_cancel(self.volume_restart_after_id)
        self.volume_restart_after_id = self.after(180, self._apply_volume_to_current_preview)

    def _apply_volume_to_current_preview(self) -> None:
        self.volume_restart_after_id = None
        if not self._player_is_running() or self.player_source is None or self.player_kind is None:
            return
        source = self.player_source
        kind = self.player_kind
        event_id = self.player_event_id
        offset = self.player_offset + max(0.0, time.monotonic() - self.player_started_at)
        self._start_audio_preview(source, kind, event_id, offset)

    def _validated_model_paths(self, model_id: str) -> tuple[Path, ...] | None:
        if model_id == "avcass":
            (
                python_path,
                repo,
                deps,
                checkpoint,
                cavp_checkpoint,
                runtime_root,
            ) = avcass_runtime_paths(self.portable_runtime)
            required = (
                (python_path, "AI Python"),
                (repo, "AV-CASS 코드 폴더"),
                (deps, "AV-CASS 실행 구성요소"),
                (checkpoint, "AV-CASS 체크포인트"),
                (cavp_checkpoint, "CAVP 체크포인트"),
            )
            result = (
                python_path,
                repo,
                deps,
                checkpoint,
                cavp_checkpoint,
                runtime_root,
            )
        elif model_id == "bandit":
            python_path, repo, hparams, checkpoint = bandit_runtime_paths(
                self.portable_runtime
            )
            required = (
                (python_path, "AI Python"),
                (repo, "BandIt 폴더"),
                (hparams, "BandIt 설정"),
                (checkpoint, "BandIt 체크포인트"),
            )
            result = (python_path, repo, hparams, checkpoint)
        elif model_id == "audiosep":
            python_path, repo, checkpoint, runtime_root = audiosep_runtime_paths(
                self.portable_runtime
            )
            required = (
                (python_path, "AI Python"),
                (repo, "AudioSep 폴더"),
                (checkpoint, "AudioSep 상태 사전"),
                (
                    runtime_root / "roberta-base" / "model.safetensors",
                    "AudioSep 텍스트 인코더",
                ),
            )
            result = (python_path, repo, checkpoint, runtime_root)
        else:
            messagebox.showerror(APP_TITLE, "선택한 모델은 아직 설치되지 않았습니다.")
            return None

        for path, label in required:
            if not path.exists():
                messagebox.showerror(APP_TITLE, f"{label}을 찾을 수 없습니다.\n{path}")
                return None
        return result

    def _separate_partition(
        self,
        model_id: str,
        duration: float,
        video_path: Path,
        source_wav: Path,
        result_dir: Path,
        runtime_paths: tuple[Path, ...],
        audiosep_query: str = "music",
    ) -> list[SoundEvent]:
        stem_dir = result_dir / "stems"
        stem_dir.mkdir(parents=True, exist_ok=True)
        music_path = stem_dir / "music.wav"
        non_music_path = stem_dir / "non-music.wav"

        if model_id == "avcass":
            (
                python_path,
                repo,
                deps,
                checkpoint,
                cavp_checkpoint,
                runtime_root,
            ) = runtime_paths
            command = [
                str(python_path),
                str(application_root() / "avcass_worker.py"),
                "--repo",
                str(repo),
                "--deps",
                str(deps),
                "--checkpoint",
                str(checkpoint),
                "--cavp-checkpoint",
                str(cavp_checkpoint),
                "--runtime-root",
                str(runtime_root),
                "--ffmpeg",
                require_program("ffmpeg"),
                "--video",
                str(video_path),
                "--input",
                str(source_wav),
                "--music-output",
                str(music_path),
                "--non-music-output",
                str(non_music_path),
            ]
        elif model_id == "bandit":
            python_path, repo, hparams, checkpoint = runtime_paths
            command = [
                str(python_path),
                str(application_root() / "bandit_worker.py"),
                "--repo",
                str(repo),
                "--hparams",
                str(hparams),
                "--checkpoint",
                str(checkpoint),
                "--input",
                str(source_wav),
                "--music-output",
                str(music_path),
                "--non-music-output",
                str(non_music_path),
            ]
        elif model_id == "audiosep":
            python_path, repo, checkpoint, runtime_root = runtime_paths
            command = [
                str(python_path),
                str(application_root() / "audiosep_worker.py"),
                "--repo",
                str(repo),
                "--model",
                str(checkpoint),
                "--runtime-root",
                str(runtime_root),
                "--input",
                str(source_wav),
                "--query",
                audiosep_query,
                "--music-output",
                str(music_path),
                "--non-music-output",
                str(non_music_path),
            ]
        else:
            raise ValueError(f"지원하지 않는 분리 모델입니다: {model_id}")

        run_worker_command(
            command,
            lambda line: (
                self._show_progress(message)
                if (message := worker_progress_message(model_id, line))
                else None
            ),
        )
        self._show_progress(
            f"{MODEL_LABELS.get(model_id, model_id)} · 분리 결과를 확인하는 중…"
        )
        return self._load_partition_results(
            duration,
            video_path,
            result_dir,
            music_path,
            non_music_path,
            audiosep_query,
        )

    def _load_partition_results(
        self,
        duration: float,
        video_path: Path,
        result_dir: Path,
        music_path: Path,
        non_music_path: Path,
        music_query: str,
    ) -> list[SoundEvent]:
        events = build_partition_events(
            duration,
            music_path,
            non_music_path,
            music_query=music_query,
        )
        stem_dir = result_dir / "stems"
        metrics_path = stem_dir / "partition_metrics.json"
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            quality, note = assess_partition_metrics(metrics)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            quality = "review"
            note = "분리 품질 검증값을 읽지 못했습니다. 두 트랙을 직접 확인해 주세요."
        for event in events:
            event.extraction_quality = quality
            event.extraction_note = note
        progress_label = self._active_result_label()
        for index, event in enumerate(events, start=1):
            self._show_progress(
                f"{progress_label} · 미리보기 {index}/{len(events)} 만드는 중…"
            )
            create_preview_video(
                video_path,
                Path(event.extracted_path),
                preview_path_for_event(result_dir, event),
            )
        return events

    def save_video(self) -> None:
        if not self.video_path or not self.work_dir or not self.events:
            messagebox.showwarning(APP_TITLE, "먼저 영상을 분석해 주세요.")
            return
        muted = [event for event in self.events if event.muted]
        if not muted:
            messagebox.showinfo(APP_TITLE, "뮤트할 소리를 하나 이상 표시해 주세요.")
            return
        video_path = self.video_path
        work_dir = self.work_dir
        events = list(self.events)
        target = muted_copy_output_path(video_path, events)
        self.stop_preview()

        def operation() -> None:
            export_video(video_path, target, events)
            if not target.is_file() or target.stat().st_size <= 0:
                raise RuntimeError(f"저장된 MP4를 확인할 수 없습니다: {target}")

            try:
                if work_dir is not None:
                    cleanup_work_directory(video_path, work_dir)
            except (OSError, RuntimeError) as exc:
                message = (
                    f"영상은 저장했지만 작업 폴더를 삭제하지 못했습니다.\n\n"
                    f"저장 파일: {target}\n작업 폴더: {work_dir}\n\n{exc}"
                )
                self.after(0, lambda: self.status_var.set(f"저장 완료 · 작업 폴더 정리 실패: {target}"))
                self.after(0, lambda: messagebox.showwarning(APP_TITLE, message))
                return

            def finish() -> None:
                if self.video_path == video_path and self.work_dir == work_dir:
                    self.events.clear()
                    self.result_dir = model_result_directory(
                        work_dir, self._active_result_key()
                    )
                    self.model_results.clear()
                    self.model_preview_dirty.clear()
                    self.source_ready = False
                    self.refresh_rows()
                    self.model_status_var.set(
                        f"선택 모델: {self._active_result_label()} · 분석 전"
                    )
                self.status_var.set(f"저장 완료 · 작업 폴더 삭제 완료: {target}")
                messagebox.showinfo(
                    APP_TITLE,
                    f"저장했습니다.\n{target}\n\n임시 작업 폴더도 삭제했습니다.",
                )

            self.after(0, finish)

        self._run_background("뮤트한 소리를 제거하고 영상을 저장하는 중입니다…", operation)

    def destroy(self) -> None:
        if self.volume_restart_after_id:
            self.after_cancel(self.volume_restart_after_id)
            self.volume_restart_after_id = None
        self.stop_preview()
        super().destroy()


def run_portable_smoke_test(video_path: Path, result_path: Path) -> None:
    """Exercise packaged FFmpeg, AV-CASS inference, previews, and export."""
    def write_result(data: dict[str, object]) -> None:
        result_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    write_result({"stage": "started"})
    try:
        with tempfile.TemporaryDirectory(prefix="sound-separator-test-") as temp_dir:
            test_root = Path(temp_dir)
            source_wav = test_root / "source.wav"
            extract_audio(video_path, source_wav)
            duration = probe_duration(source_wav)
            write_result({"stage": "audio_extracted", "duration": duration})

            runtime_root = application_root() / "audiosep"
            python_path = runtime_root / "env" / "python.exe"
            avcass_root = runtime_root / "avcass"
            repo = avcass_root / "repo"
            deps = avcass_root / "deps"
            checkpoint = avcass_root / "model" / "av_cass_checkpoint.pt"
            cavp_checkpoint = avcass_root / "model" / "cavp" / "cavp_epoch66.ckpt"
            stem_dir = test_root / "stems"
            stem_dir.mkdir(parents=True, exist_ok=True)
            music_path = stem_dir / "music.wav"
            non_music_path = stem_dir / "non-music.wav"
            run_command(
                [
                    str(python_path),
                    str(application_root() / "avcass_worker.py"),
                    "--repo",
                    str(repo),
                    "--deps",
                    str(deps),
                    "--checkpoint",
                    str(checkpoint),
                    "--cavp-checkpoint",
                    str(cavp_checkpoint),
                    "--runtime-root",
                    str(avcass_root),
                    "--ffmpeg",
                    require_program("ffmpeg"),
                    "--video",
                    str(video_path),
                    "--input",
                    str(source_wav),
                    "--music-output",
                    str(music_path),
                    "--non-music-output",
                    str(non_music_path),
                ]
            )
            events = build_partition_events(duration, music_path, non_music_path)
            metrics_path = stem_dir / "partition_metrics.json"
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            quality, note = assess_partition_metrics(metrics)
            if quality != "ok":
                raise RuntimeError(f"분리 품질 검사 실패: {note}")
            write_result({"stage": "sounds_separated", "event_count": len(events)})
            for event in events:
                create_preview_video(
                    video_path,
                    Path(event.extracted_path),
                    test_root / "previews" / f"{event.event_id}.mkv",
                )
            events[0].muted = True
            music_removed = test_root / "music-removed.mp4"
            export_video(video_path, music_removed, events)
            export_ok = music_removed.is_file() and music_removed.stat().st_size > 0
        result = {
            "stage": "complete",
            "video": str(video_path.resolve()),
            "partition_count": len(events),
            "music_removed_export": export_ok,
            "partition_metrics": metrics,
            "events": [
                {
                    "label": event.label,
                    "query": event.query,
                    "quality": event.extraction_quality,
                }
                for event in events
            ],
        }
        write_result(result)
    except BaseException:
        write_result({"stage": "error", "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--portable-smoke-test":
        run_portable_smoke_test(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        SoundSeparatorApp().mainloop()

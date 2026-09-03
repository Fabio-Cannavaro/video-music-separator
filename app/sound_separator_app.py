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
import webbrowser
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
from release_info import APP_VERSION, RUNTIME_COMPONENTS


APP_TITLE = "영상 음악 분리·제거기"
PREVIEW_WIDTH = 420
PREVIEW_HEIGHT = 236
PREVIEW_FPS = 30
PREVIEW_PROCESS_STOP_TIMEOUT = 0.5
DEFAULT_VOLUME = 100
CREATOR_LINE_INDENT = 0
DEFAULT_MODEL_ID = "avcass"
CREATOR_YOUTUBE_URL = "https://www.youtube.com/@ms-0606"
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
ENGLISH_USER_CONTENT_NOTICE = (
    "You are responsible for confirming the copyright and usage rights of the video "
    "and audio you process, and for how you use the results."
)
LEGAL_INFORMATION_FILES = (
    ("개인정보 및 외부 통신 안내", "PRIVACY.md"),
    ("모델 파일 및 배포 정책", "MODEL_LICENSES.md"),
    ("제3자 고지·출처·논문", "THIRD_PARTY_NOTICES.md"),
    ("FFmpeg GPL 빌드 정보", "FFMPEG_BUILD.md"),
    ("Video Music Separator 저작권 고지", "COPYRIGHT.md"),
)
LICENSE_TEXT_FILES = (
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

TRANSLATIONS = {
    "ko": {
        "app_title": APP_TITLE,
        "language": "언어",
        "stage_video": "1. 영상 선택",
        "open_video": "영상 열기",
        "no_video": "선택된 영상 없음",
        "separate_music": "영상에서 음악 분리",
        "audiosep_compare": "AudioSep 3종 비교",
        "play_all": "전체 영상 재생",
        "stop_all": "전체 영상 정지",
        "playback_volume": "전체 재생 볼륨",
        "licenses_sources": "앱 정보·라이선스",
        "creator_prefix": "앱 제작: ",
        "creator_suffix": " × OpenAI Codex",
        "preview_title": "영상 미리보기",
        "preview_placeholder": "재생하면 여기에 영상이 표시됩니다.",
        "stage_results": "2. 음악 / 음악 아님 분리 결과",
        "column_sound": "소리 구분",
        "column_separation": "AI 분리",
        "column_listen": "영상과 듣기",
        "column_full_playback": "전체 재생에서",
        "save_copy": "사본 저장",
        "user_notice": USER_CONTENT_NOTICE,
        "legal_title": "앱 정보·라이선스·출처",
        "legal_license_intro": (
            "공식 라이선스 원문(영문)\n"
            "=========================\n\n"
            "아래 내용은 법적 정확성을 위해 번역하지 않은 공식 영문 라이선스 원문입니다."
        ),
        "legal_user_heading": "사용자 콘텐츠 안내",
        "legal_runtime_heading": "앱·모델 버전 및 체크섬",
        "legal_privacy": "개인정보 및 외부 통신 안내",
        "legal_model_policy": "모델 파일 및 배포 정책",
        "legal_third_party": "제3자 고지·출처·논문",
        "legal_ffmpeg": "FFmpeg GPL 빌드 정보",
        "legal_copyright": "Video Music Separator 저작권 고지",
        "legal_app_license": "Video Music Separator 라이선스 공식 영문 원문",
        "legal_mit": "MIT License 공식 영문 원문",
        "legal_apache": "Apache License 2.0 공식 영문 원문",
        "legal_lgpl": "GNU LGPL v3 공식 영문 원문",
        "legal_gpl": "GNU GPL v3 공식 영문 원문",
        "file_missing": "파일을 찾을 수 없습니다: {path}",
        "close": "닫기",
        "dialog_video_select": "영상 선택",
        "video_files": "영상 파일",
        "all_files": "모든 파일",
        "unsupported_video": "지원하지 않는 영상 형식입니다.",
        "busy_wait": "현재 작업이 끝날 때까지 기다려 주세요.",
        "model_busy": "현재 작업이 끝날 때까지 모델을 바꿀 수 없습니다.",
        "query_busy": "현재 작업이 끝날 때까지 음악 유형을 바꿀 수 없습니다.",
        "model_environment_missing": "선택한 모델의 실행 환경이 설치되지 않았습니다.",
        "audiosep_environment_missing": "AudioSep 실행 환경이 설치되지 않았습니다.",
        "model_not_installed": "선택한 모델은 아직 설치되지 않았습니다.",
        "required_missing": "{label}을 찾을 수 없습니다.\n{path}",
        "choose_video_first": "먼저 영상을 선택해 주세요.",
        "analyze_first": "먼저 영상을 분석해 주세요.",
        "select_mute_first": "뮤트할 소리를 하나 이상 표시해 주세요.",
        "status_choose_video": "영상을 선택해 주세요.",
        "status_video_opened": "영상을 열었습니다. 음악 분리를 실행해 주세요.",
        "status_loaded_existing": "기존 분리 결과를 불러왔습니다.",
        "status_model_selected": "분리 모델을 선택했습니다. 음악 분리를 실행해 주세요.",
        "status_model_selected_short": "분리 모델을 선택했습니다. 분리를 실행해 주세요.",
        "status_task_failed": "작업에 실패했습니다.",
        "status_prepare_audio": "영상에서 소리를 준비하는 중…",
        "status_prepare_separation": "분리 작업을 준비하는 중…",
        "status_separating": "음악과 음악 아닌 소리를 분리하는 중입니다…",
        "status_separation_started": "음악 분리를 시작합니다…",
        "status_separation_complete": "분리 완료. 음악 행을 뮤트해 결과를 확인해 주세요.",
        "status_audiosep_compare_complete": "AudioSep 기본 음악·배경음악·영화 음악 비교가 완료됐습니다. 음악 유형을 바꿔 각 결과를 들어보세요.",
        "status_audiosep_compare_running": "AudioSep 모델을 한 번 불러 3가지 음악 유형을 비교하는 중입니다…",
        "status_playing_original": "원본 전체 믹스를 영상과 함께 재생합니다.",
        "status_playing_muted": "{count}개 소리를 뮤트한 전체 믹스를 재생합니다.",
        "status_prepare_muted_preview": "선택한 소리만 뮤트한 전체 영상 미리보기를 준비하는 중입니다…",
        "status_save_cleanup_failed": "저장 완료 · 작업 폴더 정리 실패: {path}",
        "status_save_complete": "저장 완료 · 작업 폴더 삭제 완료: {path}",
        "status_saving": "뮤트한 소리를 제거하고 영상을 저장하는 중입니다…",
        "progress_video_frames": "영상 장면을 준비하는 중…",
        "progress_model_loading": "분리 모델을 불러오는 중…",
        "progress_visual_model_loading": "영상 인식 모델을 불러오는 중…",
        "progress_segment": "구간 {current}/{total} 분리 중…",
        "progress_finalize": "분리 결과를 정리하는 중…",
        "progress_check_results": "분리 결과를 확인하는 중…",
        "progress_create_preview": "미리보기 {current}/{total} 만드는 중…",
        "empty_results": "영상을 연 뒤 선택한 모델로 분리를 실행해 주세요.",
        "quality_ok": "완료",
        "quality_review": "검토 필요",
        "quality_failed": "추출 실패",
        "quality_extracting": "자동 추출 중…",
        "quality_not_extracted": "미추출",
        "listen": "듣기",
        "stop": "정지",
        "mute": "뮤트",
        "unmute": "뮤트 해제",
        "event_music": "음악 (BGM)",
        "event_non_music": "음악 아님 (목소리·효과음)",
        "no_separated_track": "분리본이 없습니다.",
        "confirm_mute_review": "{label}\n\n{note}\n\n그래도 이 소리를 뮤트할까요?",
        "preview_open_failed": "영상 미리보기를 열 수 없습니다: {path}",
        "preview_unavailable": "분리본 영상 미리보기를 찾을 수 없습니다. 다시 분석해 주세요.",
        "saved_file_invalid": "저장된 MP4를 확인할 수 없습니다: {path}",
        "save_cleanup_warning": "영상은 저장했지만 작업 폴더를 삭제하지 못했습니다.\n\n저장 파일: {target}\n작업 폴더: {work_dir}\n\n{error}",
        "save_complete_dialog": "저장했습니다.\n{path}\n\n임시 작업 폴더도 삭제했습니다.",
        "quality_reconstruction": "두 분리본을 합쳐도 원본과 충분히 일치하지 않습니다. 다시 분리해 주세요.",
        "quality_source_like": "음악 트랙이 원본 전체와 사실상 같고 음악 아님 트랙은 거의 무음입니다. 원본에 목소리나 효과음이 있다면 분리가 실패한 결과입니다.",
        "quality_unreadable": "분리 품질 검증값을 읽지 못했습니다. 두 트랙을 직접 확인해 주세요.",
        "query_music": "기본 음악",
        "query_background": "배경음악",
        "query_cinematic": "영화 음악",
        "query_instrumental": "악기 음악",
        "query_ambient": "앰비언트 음악",
        "required_avcass_repo": "AV-CASS 코드 폴더",
        "required_avcass_deps": "AV-CASS 실행 구성요소",
        "required_avcass_checkpoint": "AV-CASS 체크포인트",
        "required_cavp_checkpoint": "CAVP 체크포인트",
        "required_bandit_repo": "BandIt 폴더",
        "required_bandit_config": "BandIt 설정",
        "required_bandit_checkpoint": "BandIt 체크포인트",
        "required_audiosep_repo": "AudioSep 폴더",
        "required_audiosep_state": "AudioSep 상태 사전",
        "required_audiosep_encoder": "AudioSep 텍스트 인코더",
    },
    "en": {
        "app_title": "Video Music Separator",
        "language": "Language",
        "stage_video": "1. Select Video",
        "open_video": "Open Video",
        "no_video": "No video selected",
        "separate_music": "Separate Music from Video",
        "audiosep_compare": "Compare 3 AudioSep Types",
        "play_all": "Play Full Video",
        "stop_all": "Stop Full Video",
        "playback_volume": "Playback Volume",
        "licenses_sources": "App Info & Licenses",
        "creator_prefix": "Created by: ",
        "creator_suffix": " × OpenAI Codex",
        "preview_title": "Video Preview",
        "preview_placeholder": "The video will appear here during playback.",
        "stage_results": "2. Music / Non-Music Separation Results",
        "column_sound": "Sound Type",
        "column_separation": "AI Separation",
        "column_listen": "Listen with Video",
        "column_full_playback": "In Full Playback",
        "save_copy": "Save Copy",
        "user_notice": ENGLISH_USER_CONTENT_NOTICE,
        "legal_title": "App Information, Licenses & Sources",
        "legal_license_intro": (
            "Official License Texts\n"
            "======================\n\n"
            "The following texts are the official license terms included with the application."
        ),
        "legal_user_heading": "User Content Notice",
        "legal_runtime_heading": "Application and Runtime Versions & Checksums",
        "legal_privacy": "Privacy and Network Access Notice",
        "legal_model_policy": "Model Files and Distribution Policy",
        "legal_third_party": "Third-Party Notices, Sources & Papers",
        "legal_ffmpeg": "FFmpeg GPL Build Information",
        "legal_copyright": "Video Music Separator Copyright Notice",
        "legal_app_license": "Video Music Separator License",
        "legal_mit": "Full MIT License",
        "legal_apache": "Full Apache License 2.0",
        "legal_lgpl": "Full GNU LGPL v3",
        "legal_gpl": "Full GNU GPL v3",
        "file_missing": "File not found: {path}",
        "close": "Close",
        "dialog_video_select": "Select Video",
        "video_files": "Video files",
        "all_files": "All files",
        "unsupported_video": "This video format is not supported.",
        "busy_wait": "Please wait until the current task finishes.",
        "model_busy": "You cannot change models until the current task finishes.",
        "query_busy": "You cannot change the music type until the current task finishes.",
        "model_environment_missing": "The runtime for the selected model is not installed.",
        "audiosep_environment_missing": "The AudioSep runtime is not installed.",
        "model_not_installed": "The selected model is not installed yet.",
        "required_missing": "{label} was not found.\n{path}",
        "choose_video_first": "Select a video first.",
        "analyze_first": "Analyze a video first.",
        "select_mute_first": "Mark at least one sound to mute.",
        "status_choose_video": "Select a video.",
        "status_video_opened": "Video opened. Run music separation.",
        "status_loaded_existing": "Loaded the existing separation result.",
        "status_model_selected": "Selected a separation model. Run music separation.",
        "status_model_selected_short": "Selected a separation model. Run separation.",
        "status_task_failed": "The task failed.",
        "status_prepare_audio": "Preparing audio from the video…",
        "status_prepare_separation": "Preparing separation…",
        "status_separating": "Separating music from non-music…",
        "status_separation_started": "Starting music separation…",
        "status_separation_complete": "Separation complete. Mute the music row to review the result.",
        "status_audiosep_compare_complete": "The AudioSep music, background music, and cinematic score comparison is complete. Change the music type to listen to each result.",
        "status_audiosep_compare_running": "Loading AudioSep once to compare three music types…",
        "status_playing_original": "Playing the original full mix with video.",
        "status_playing_muted": "Playing the full mix with {count} sound(s) muted.",
        "status_prepare_muted_preview": "Preparing a full-video preview with the selected sounds muted…",
        "status_save_cleanup_failed": "Saved · Could not clean the work folder: {path}",
        "status_save_complete": "Saved · Deleted the work folder: {path}",
        "status_saving": "Removing muted sounds and saving the video…",
        "progress_video_frames": "Preparing video frames…",
        "progress_model_loading": "Loading the separation model…",
        "progress_visual_model_loading": "Loading the visual recognition model…",
        "progress_segment": "Separating segment {current}/{total}…",
        "progress_finalize": "Finalizing separation results…",
        "progress_check_results": "Checking separation results…",
        "progress_create_preview": "Creating preview {current}/{total}…",
        "empty_results": "Open a video, then run separation with the selected model.",
        "quality_ok": "Complete",
        "quality_review": "Review Needed",
        "quality_failed": "Extraction Failed",
        "quality_extracting": "Extracting…",
        "quality_not_extracted": "Not Extracted",
        "listen": "Listen",
        "stop": "Stop",
        "mute": "Mute",
        "unmute": "Unmute",
        "event_music": "Music (BGM)",
        "event_non_music": "Non-Music (Voice & Effects)",
        "no_separated_track": "No separated track is available.",
        "confirm_mute_review": "{label}\n\n{note}\n\nMute this sound anyway?",
        "preview_open_failed": "Could not open the video preview: {path}",
        "preview_unavailable": "The separated-track video preview was not found. Analyze the video again.",
        "saved_file_invalid": "The saved MP4 could not be verified: {path}",
        "save_cleanup_warning": "The video was saved, but the work folder could not be deleted.\n\nSaved file: {target}\nWork folder: {work_dir}\n\n{error}",
        "save_complete_dialog": "Saved.\n{path}\n\nThe temporary work folder was also deleted.",
        "quality_reconstruction": "The two separated tracks do not reconstruct the source closely enough. Run separation again.",
        "quality_source_like": "The music track is nearly identical to the full source while the non-music track is almost silent. If the source contains voices or effects, separation likely failed.",
        "quality_unreadable": "The separation quality metrics could not be read. Check both tracks directly.",
        "query_music": "Music",
        "query_background": "Background Music",
        "query_cinematic": "Cinematic Score",
        "query_instrumental": "Instrumental Music",
        "query_ambient": "Ambient Music",
        "required_avcass_repo": "AV-CASS code folder",
        "required_avcass_deps": "AV-CASS runtime components",
        "required_avcass_checkpoint": "AV-CASS checkpoint",
        "required_cavp_checkpoint": "CAVP checkpoint",
        "required_bandit_repo": "BandIt folder",
        "required_bandit_config": "BandIt configuration",
        "required_bandit_checkpoint": "BandIt checkpoint",
        "required_audiosep_repo": "AudioSep folder",
        "required_audiosep_state": "AudioSep state dictionary",
        "required_audiosep_encoder": "AudioSep text encoder",
    },
}

LEGAL_TITLE_KEYS = {
    "PRIVACY.md": "legal_privacy",
    "MODEL_LICENSES.md": "legal_model_policy",
    "THIRD_PARTY_NOTICES.md": "legal_third_party",
    "FFMPEG_BUILD.md": "legal_ffmpeg",
    "COPYRIGHT.md": "legal_copyright",
    "LICENSE": "legal_app_license",
    "licenses/MIT.txt": "legal_mit",
    "licenses/Apache-2.0.txt": "legal_apache",
    "licenses/LGPL-3.0.txt": "legal_lgpl",
    "licenses/GPL-3.0.txt": "legal_gpl",
}

ENGLISH_LEGAL_FILES = {
    "PRIVACY.md": "PRIVACY.en.md",
    "MODEL_LICENSES.md": "MODEL_LICENSES.en.md",
    "THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.en.md",
    "FFMPEG_BUILD.md": "FFMPEG_BUILD.en.md",
    "COPYRIGHT.md": "COPYRIGHT.en.md",
}

QUALITY_NOTE_KEYS = {
    TRANSLATIONS["ko"]["quality_reconstruction"]: "quality_reconstruction",
    TRANSLATIONS["ko"]["quality_source_like"]: "quality_source_like",
    TRANSLATIONS["ko"]["quality_unreadable"]: "quality_unreadable",
}


def translate(language: str, key: str, **values: object) -> str:
    table = TRANSLATIONS.get(language, TRANSLATIONS["ko"])
    template = table.get(key, TRANSLATIONS["ko"][key])
    return template.format(**values)


def open_creator_youtube_channel(_event: object | None = None) -> None:
    webbrowser.open_new_tab(CREATOR_YOUTUBE_URL)


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


def normalized_preview_fps(value: float) -> float:
    if 1.0 <= value <= 120.0:
        return value
    return float(PREVIEW_FPS)


def next_preview_delay_ms(started_at: float, now: float, fps: float) -> int:
    fps = normalized_preview_fps(fps)
    elapsed = max(0.0, now - started_at)
    next_frame = int(elapsed * fps) + 1
    deadline = started_at + next_frame / fps
    return max(1, round((deadline - now) * 1000.0))


def terminate_preview_process(
    process: subprocess.Popen[bytes] | None,
    timeout: float = PREVIEW_PROCESS_STOP_TIMEOUT,
) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=timeout)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        process.kill()
        process.wait(timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        pass


def worker_progress_key(
    model_id: str, line: str
) -> tuple[str, dict[str, object]] | None:
    label = MODEL_LABELS.get(model_id, model_id)
    if model_id == "avcass":
        if line.startswith("[setup] 영상 프레임"):
            return "progress_video_frames", {"model": label}
        if line.startswith("[setup] AV-CASS"):
            return "progress_model_loading", {"model": label}
        if line.startswith("[setup] CAVP"):
            return "progress_visual_model_loading", {"model": label}
        match = re.match(r"^\[run (\d+)/(\d+)\]", line)
        if match:
            return "progress_segment", {
                "model": label,
                "current": match.group(1),
                "total": match.group(2),
            }
    if line.startswith("[done]"):
        return "progress_finalize", {"model": label}
    return None


def worker_script_path(name: str) -> Path:
    """Locate a worker in the organized source or packaged application folder."""
    if getattr(sys, "frozen", False):
        return application_root() / "app" / name
    return Path(__file__).resolve().parent / name


def worker_progress_message(
    model_id: str, line: str, language: str = "ko"
) -> str | None:
    progress = worker_progress_key(model_id, line)
    if progress is not None:
        key, values = progress
        return translate(
            language,
            key,
            **values,
        )
    return None


def load_legal_information(root: Path, language: str = "ko") -> str:
    sections = [
        f"{translate(language, 'legal_user_heading')}\n\n"
        f"{translate(language, 'user_notice')}"
    ]
    record_path = root / "docs" / "runtime-assets.json"
    if not record_path.is_file():
        record_path = root / "runtime-assets.json"
    record: dict = {}
    if record_path.is_file():
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            pass

    component_lines = [f"Video Music Separator: {APP_VERSION}"]
    for component in RUNTIME_COMPONENTS:
        component_name = component["name"]
        version = component["version"]
        sha256 = component["sha256"]
        if language == "ko":
            component_name = {
                "AI Python runtime": "AI Python 실행환경",
                "AV-CASS": "AV-CASS",
                "CAVP": "CAVP",
                "FFmpeg": "FFmpeg",
            }.get(component_name, component_name)
            if component["name"] == "AV-CASS":
                version = "공식 영상 기반 체크포인트 (별도 버전 표기 없음)"
            elif component["name"] == "CAVP":
                version = version.replace("Diff-Foley commit", "Diff-Foley 커밋")
            elif component["name"] == "FFmpeg" and not record:
                version = "Gyan 최신 FFmpeg GPL Essentials 정적 빌드"
                sha256 = "설치 중 Gyan 공식 체크섬에서 확인"
        if component["name"] == "FFmpeg" and record:
            version = record.get("ffmpeg_version", version)
            ffmpeg_record = record.get("ffmpeg", {})
            sha256 = ffmpeg_record.get("sha256", sha256)
        source_label = "출처" if language == "ko" else "Source"
        component_lines.extend(
            (
                "",
                f"{component_name}: {version}",
                f"SHA-256: {sha256}",
                f"{source_label}: {component['source']}",
            )
        )
    installed_at = record.get("installed_at", "")
    if installed_at:
        label = "설치 기록" if language == "ko" else "Installation record"
        component_lines.extend(("", f"{label}: {installed_at}"))
    runtime_title = translate(language, "legal_runtime_heading")
    sections.append(
        f"{runtime_title}\n{'=' * len(runtime_title)}\n\n"
        + "\n".join(component_lines)
    )
    for title, relative_path in LEGAL_INFORMATION_FILES:
        title = translate(language, LEGAL_TITLE_KEYS[relative_path])
        display_path = (
            ENGLISH_LEGAL_FILES.get(relative_path, relative_path)
            if language == "en"
            else relative_path
        )
        path = root / "docs" / display_path
        if not path.is_file() and display_path != relative_path:
            path = root / "docs" / relative_path
        if not path.is_file():
            path = root / display_path
        if not path.is_file() and display_path != relative_path:
            path = root / relative_path
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
        else:
            content = translate(language, "file_missing", path=display_path)
        sections.append(f"{title}\n{'=' * len(title)}\n\n{content}")
    return "\n\n\n".join(sections)


def load_license_texts(root: Path, language: str = "ko") -> str:
    sections = [translate(language, "legal_license_intro")]
    for _title, relative_path in LICENSE_TEXT_FILES:
        title = translate(language, LEGAL_TITLE_KEYS[relative_path])
        path = root / "docs" / relative_path
        if not path.is_file():
            path = root / relative_path
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
        else:
            content = translate(language, "file_missing", path=relative_path)
        sections.append(f"{title}\n{'=' * len(title)}\n\n{content}")
    return "\n\n\n".join(sections)


def load_legal_display(root: Path, language: str = "ko") -> str:
    return "\n\n\n".join(
        (
            load_legal_information(root, language),
            load_license_texts(root, language),
        )
    )


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
        "-vn",
        "-sn",
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
        self.language_var = tk.StringVar(value="ko")
        self.title(self._t("app_title"))
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
        self.playback_generation = 0
        self.player_poll_after_id: str | None = None
        self.volume_restart_after_id: str | None = None
        self.video_capture: cv2.VideoCapture | None = None
        self.video_position = 0.0
        self.preview_fps = float(PREVIEW_FPS)
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
            value=self._query_label("music")
        )
        self.volume_var = tk.DoubleVar(value=DEFAULT_VOLUME)
        self.status_key = "status_choose_video"
        self.status_values: dict[str, object] = {}
        self.status_var = tk.StringVar(value=self._t(self.status_key))
        self.legal_window: tk.Toplevel | None = None
        self.legal_text: ScrolledText | None = None
        self.legal_close_button: ttk.Button | None = None
        self._build_ui()

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language_var.get(), key, **values)

    def _query_label(self, query_id: str) -> str:
        return self._t(f"query_{query_id}")

    def _event_label(self, event: SoundEvent) -> str:
        key = {
            "music": "event_music",
            "non-music": "event_non_music",
        }.get(event.event_id)
        return self._t(key) if key else event.label

    def _event_note(self, event: SoundEvent) -> str:
        key = QUALITY_NOTE_KEYS.get(event.extraction_note)
        return self._t(key) if key else event.extraction_note

    def _set_status(self, key: str, **values: object) -> None:
        self.status_key = key
        self.status_values = values
        self.status_var.set(self._t(key, **values))

    def change_language(self) -> None:
        self.title(self._t("app_title"))
        self.source_frame.configure(text=self._t("stage_video"))
        self.open_video_button.configure(text=self._t("open_video"))
        self.separate_button.configure(text=self._t("separate_music"))
        self.audiosep_compare_button.configure(text=self._t("audiosep_compare"))
        self.play_all_button.configure(text=self._t("play_all"))
        self.stop_all_button.configure(text=self._t("stop_all"))
        self.volume_title_label.configure(text=self._t("playback_volume"))
        self.legal_button.configure(text=self._t("licenses_sources"))
        self.creator_prefix_label.configure(text=self._t("creator_prefix"))
        self.creator_suffix_label.configure(text=self._t("creator_suffix"))
        self.language_frame.configure(text=self._t("language"))
        self.preview_frame.configure(text=self._t("preview_title"))
        self.table_frame.configure(text=self._t("stage_results"))
        for widget, key in self.table_header_labels:
            widget.configure(text=self._t(key))
        self.save_button.configure(text=self._t("save_copy"))
        self.user_notice_label.configure(text=self._t("user_notice"))
        if self.video_path is None:
            self.video_var.set(self._t("no_video"))
        if self.preview_photo is None:
            self.preview_label.configure(text=self._t("preview_placeholder"))
        self.audiosep_query_combo.configure(
            values=tuple(self._query_label(query_id) for query_id in AUDIOSEP_QUERIES)
        )
        self.audiosep_query_label_var.set(
            self._query_label(self.audiosep_query_var.get())
        )
        self.status_var.set(self._t(self.status_key, **self.status_values))
        self.refresh_rows()
        self._refresh_legal_information()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        self.source_frame = ttk.LabelFrame(root, text=self._t("stage_video"), padding=10)
        self.source_frame.grid(row=2, column=0, sticky="ew")
        self.source_frame.columnconfigure(1, weight=1)
        self.open_video_button = ttk.Button(
            self.source_frame, text=self._t("open_video"), command=self.choose_video
        )
        self.open_video_button.grid(row=0, column=0, padx=(0, 8))
        self.video_var = tk.StringVar(value=self._t("no_video"))
        ttk.Label(self.source_frame, textvariable=self.video_var).grid(row=0, column=1, sticky="w")
        self.separate_button = ttk.Button(
            self.source_frame, text=self._t("separate_music"), command=self.analyze
        )
        self.separate_button.grid(
            row=0, column=2, padx=(8, 0)
        )
        self.audiosep_compare_button = ttk.Button(
            self.source_frame,
            text=self._t("audiosep_compare"),
            command=self.analyze_audiosep_comparison,
        )

        self.audiosep_query_combo = ttk.Combobox(
            self.source_frame,
            state="disabled",
            width=13,
            textvariable=self.audiosep_query_label_var,
            values=tuple(self._query_label(query_id) for query_id in AUDIOSEP_QUERIES),
        )
        self.audiosep_query_combo.bind(
            "<<ComboboxSelected>>", self.select_audiosep_query
        )
        self._update_audiosep_query_control()

        actions = ttk.Frame(root, height=32)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 6))
        actions.grid_propagate(False)

        playback_actions = ttk.Frame(actions)
        playback_actions.place(relx=0.5, rely=0.5, anchor="center")
        self.play_all_button = ttk.Button(
            playback_actions, text=self._t("play_all"), command=self.preview_original
        )
        self.play_all_button.pack(side="left")
        self.stop_all_button = ttk.Button(
            playback_actions, text=self._t("stop_all"), command=self.stop_original_preview
        )
        self.stop_all_button.pack(side="left", padx=4)

        volume_actions = ttk.Frame(actions)
        volume_actions.place(relx=0.5, x=115, rely=0.5, anchor="w")
        ttk.Separator(volume_actions, orient="vertical").pack(
            side="left", fill="y", padx=(0, 8)
        )
        self.volume_title_label = ttk.Label(
            volume_actions, text=self._t("playback_volume")
        )
        self.volume_title_label.pack(side="left")
        ttk.Scale(
            volume_actions,
            from_=0,
            to=100,
            variable=self.volume_var,
            length=170,
            command=self._schedule_volume_update,
        ).pack(side="left", padx=(6, 4))
        self.volume_label = ttk.Label(
            volume_actions, width=4, text=str(DEFAULT_VOLUME)
        )
        self.volume_label.pack(side="left")

        legal_area = ttk.Frame(root)
        legal_area.grid(
            row=0,
            column=0,
            sticky="nw",
            padx=(2, 0),
            pady=(8, 0),
        )
        self.legal_button = ttk.Button(
            legal_area,
            text=self._t("licenses_sources"),
            command=self.show_legal_information,
            width=16,
        )
        self.legal_button.pack(anchor="w", ipadx=6, ipady=4)

        creator_area = ttk.Frame(legal_area)
        creator_area.pack(anchor="w", padx=(CREATOR_LINE_INDENT, 0), pady=(5, 0))
        self.creator_prefix_label = ttk.Label(
            creator_area,
            text=self._t("creator_prefix"),
        )
        self.creator_prefix_label.pack(side="left")
        self.creator_link_label = ttk.Label(
            creator_area,
            text="@ms-0606",
            foreground="#0563C1",
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
        )
        self.creator_link_label.pack(side="left")
        self.creator_link_label.bind("<Button-1>", open_creator_youtube_channel)
        self.creator_suffix_label = ttk.Label(
            creator_area,
            text=self._t("creator_suffix"),
        )
        self.creator_suffix_label.pack(side="left")

        self.language_frame = ttk.LabelFrame(
            root, text=self._t("language"), padding=(10, 6)
        )
        self.language_frame.grid(
            row=0, column=0, sticky="ne", padx=(0, 12), pady=(8, 0)
        )
        ttk.Radiobutton(
            self.language_frame,
            text="한국어",
            value="ko",
            variable=self.language_var,
            command=self.change_language,
        ).pack(anchor="w")
        ttk.Radiobutton(
            self.language_frame,
            text="English",
            value="en",
            variable=self.language_var,
            command=self.change_language,
        ).pack(anchor="w")

        self.preview_frame = ttk.LabelFrame(
            root, text=self._t("preview_title"), padding=8
        )
        self.preview_frame.grid(row=0, column=0, pady=(0, 8))
        preview_surface = tk.Frame(
            self.preview_frame,
            width=PREVIEW_WIDTH,
            height=PREVIEW_HEIGHT,
            background="#111111",
        )
        preview_surface.pack()
        preview_surface.pack_propagate(False)
        self.preview_label = tk.Label(
            preview_surface,
            text=self._t("preview_placeholder"),
            background="#111111",
            foreground="#D0D0D0",
        )
        self.preview_label.pack(fill="both", expand=True)

        playback_position_area = ttk.Frame(self.preview_frame)
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

        self.table_frame = ttk.LabelFrame(root, text=self._t("stage_results"), padding=8)
        self.table_frame.grid(row=4, column=0, sticky="nsew")
        self.table_frame.columnconfigure(0, weight=1)
        self.table_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.table_frame, padding=(6, 3))
        header.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        header.columnconfigure(0, weight=1)
        sound_header = ttk.Label(header, text=self._t("column_sound"), anchor="w")
        sound_header.grid(row=0, column=0, sticky="ew")
        separation_header = ttk.Label(header, text=self._t("column_separation"), width=16, anchor="center")
        separation_header.grid(row=0, column=1)
        listen_header = ttk.Label(header, text=self._t("column_listen"), width=16, anchor="center")
        listen_header.grid(row=0, column=2)
        playback_header = ttk.Label(header, text=self._t("column_full_playback"), width=16, anchor="center")
        playback_header.grid(row=0, column=3)
        self.table_header_labels = (
            (sound_header, "column_sound"),
            (separation_header, "column_separation"),
            (listen_header, "column_listen"),
            (playback_header, "column_full_playback"),
        )

        self.rows_canvas = tk.Canvas(self.table_frame, highlightthickness=0)
        self.rows_canvas.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.rows_canvas.yview)
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
            text=self._t("save_copy"),
            command=self.save_video,
            width=16,
        )
        self.save_button.grid(row=0, column=1, ipadx=6, ipady=4)
        self.user_notice_label = ttk.Label(
            root,
            text=self._t("user_notice"),
            foreground="#666666",
            anchor="center",
            wraplength=900,
        )
        self.user_notice_label.grid(row=6, column=0, sticky="ew", pady=(7, 0))

    def show_legal_information(self) -> None:
        if self.legal_window is not None and self.legal_window.winfo_exists():
            self.legal_window.lift()
            return
        window = tk.Toplevel(self)
        self.legal_window = window
        window.title(self._t("legal_title"))
        window.geometry("860x680")
        window.minsize(650, 480)
        window.transient(self)
        window.protocol("WM_DELETE_WINDOW", self._close_legal_information)

        self.legal_text = ScrolledText(
            window,
            wrap="word",
            padx=14,
            pady=14,
            font=("Segoe UI", 10),
        )
        self.legal_text.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        self.legal_close_button = ttk.Button(
            window, text=self._t("close"), command=self._close_legal_information
        )
        self.legal_close_button.pack(pady=(0, 10))
        self._refresh_legal_information()

    def _refresh_legal_information(self) -> None:
        if self.legal_window is None or not self.legal_window.winfo_exists():
            return
        self.legal_window.title(self._t("legal_title"))
        if self.legal_text is not None:
            self.legal_text.configure(state="normal")
            self.legal_text.delete("1.0", "end")
            self.legal_text.insert(
                "1.0",
                load_legal_display(application_root(), self.language_var.get()),
            )
            self.legal_text.configure(state="disabled")
        if self.legal_close_button is not None:
            self.legal_close_button.configure(text=self._t("close"))

    def _close_legal_information(self) -> None:
        if self.legal_window is not None and self.legal_window.winfo_exists():
            self.legal_window.destroy()
        self.legal_window = None
        self.legal_text = None
        self.legal_close_button = None

    def choose_video(self) -> None:
        if self.busy:
            messagebox.showinfo(self._t("app_title"), self._t("busy_wait"))
            return
        selected = filedialog.askopenfilename(
            title=self._t("dialog_video_select"),
            filetypes=[
                (self._t("video_files"), "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),
                (self._t("all_files"), "*.*"),
            ],
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            messagebox.showerror(self._t("app_title"), self._t("unsupported_video"))
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
        self._set_status("status_video_opened")

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
            messagebox.showinfo(self._t("app_title"), self._t("model_busy"))
            return
        if not self._model_is_available(requested):
            self.model_var.set(self.active_model_id)
            messagebox.showwarning(
                self._t("app_title"), self._t("model_environment_missing")
            )
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
            self._set_status(
                "status_loaded_existing", model=self._active_result_label()
            )
        else:
            self._set_status(
                "status_model_selected", model=self._active_result_label()
            )

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
        label = self._query_label(self.audiosep_query_var.get())
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
                self._query_label(self.audiosep_query_var.get())
            )
            messagebox.showinfo(self._t("app_title"), self._t("query_busy"))
            return
        if self.active_model_id != "audiosep":
            return
        selected_label = self.audiosep_query_label_var.get()
        selected_id = next(
            (
                query_id
                for query_id in AUDIOSEP_QUERIES
                if self._query_label(query_id) == selected_label
            ),
            None,
        )
        if selected_id is None:
            self.audiosep_query_label_var.set(
                self._query_label(self.audiosep_query_var.get())
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
        if self.events:
            self._set_status(
                "status_loaded_existing", model=self._active_result_label()
            )
        else:
            self._set_status(
                "status_model_selected_short", model=self._active_result_label()
            )

    def _run_background(
        self, label_key: str, operation, **label_values: object
    ) -> None:
        if self.busy:
            messagebox.showinfo(self._t("app_title"), self._t("busy_wait"))
            return
        self.busy = True
        self._set_status(label_key, **label_values)

        def runner() -> None:
            try:
                operation()
            except Exception as exc:
                message = str(exc)
                self.after(
                    0,
                    lambda: messagebox.showerror(self._t("app_title"), message),
                )
                self.after(0, lambda: self._set_status("status_task_failed"))
            finally:
                self.busy = False

        threading.Thread(target=runner, daemon=True).start()

    def _show_progress(self, key: str, **values: object) -> None:
        self.after(0, lambda: self._set_status(key, **values))

    def analyze(self) -> None:
        if not self.video_path or not self.source_wav or not self.work_dir:
            messagebox.showwarning(
                self._t("app_title"), self._t("choose_video_first")
            )
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
                self._show_progress("status_prepare_audio", model=model_label)
                extract_audio(video_path, source_wav)
                self.source_ready = True
            self._show_progress("status_prepare_separation", model=model_label)
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
                lambda: self._set_status("status_separating", model=model_label),
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
                    self._set_status(
                        "status_separation_complete", model=model_label
                    )

            self.after(0, finish)

        self._run_background(
            "status_separation_started", operation, model=model_label
        )

    def analyze_audiosep_comparison(self) -> None:
        if not self.video_path or not self.source_wav or not self.work_dir:
            messagebox.showwarning(
                self._t("app_title"), self._t("choose_video_first")
            )
            return
        if not self._audiosep_is_available():
            messagebox.showerror(
                self._t("app_title"), self._t("audiosep_environment_missing")
            )
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
                self._show_progress("status_prepare_audio", model="AudioSep")
                extract_audio(video_path, source_wav)
                self.source_ready = True
            self._show_progress("status_prepare_separation", model="AudioSep")
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
                str(worker_script_path("audiosep_worker.py")),
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
                self._set_status("status_audiosep_compare_complete")

            self.after(0, finish)

        self._run_background(
            "status_audiosep_compare_running",
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
                text=self._t("empty_results"),
                padding=12,
            ).pack(anchor="w")
            return
        for event in self.events:
            row = ttk.Frame(self.rows_frame, padding=(6, 5))
            row.pack(fill="x")
            row.columnconfigure(0, weight=1)
            ttk.Label(row, text=self._event_label(event), anchor="w").grid(row=0, column=0, sticky="ew")
            if event.extracted_path:
                extraction_state = {
                    "ok": self._t("quality_ok"),
                    "review": self._t("quality_review"),
                    "failed": self._t("quality_failed"),
                }.get(event.extraction_quality, self._t("quality_ok"))
            elif self.auto_extracting:
                extraction_state = self._t("quality_extracting")
            else:
                extraction_state = self._t("quality_not_extracted")
            ttk.Label(row, text=extraction_state, width=16, anchor="center").grid(row=0, column=1)
            playing = self._player_is_running() and self.player_kind == "extracted" and self.player_event_id == event.event_id
            listen_button = ttk.Button(
                row,
                text=self._t("stop") if playing else self._t("listen"),
                width=9,
                command=lambda event_id=event.event_id: self.toggle_event_preview(event_id),
            )
            listen_button.grid(row=0, column=2, padx=4)
            if not event.extracted_path:
                listen_button.state(["disabled"])
            ttk.Button(
                row,
                text=self._t("unmute") if event.muted else self._t("mute"),
                width=9,
                command=lambda event_id=event.event_id: self.toggle_event_mute(event_id),
            ).grid(row=0, column=3)
            ttk.Separator(self.rows_frame, orient="horizontal").pack(fill="x")
        self._update_rows_scrollregion()

    def _event_by_id(self, event_id: str) -> SoundEvent | None:
        return next((event for event in self.events if event.event_id == event_id), None)

    def toggle_event_mute(self, event_id: str) -> None:
        if self.busy:
            messagebox.showinfo(self._t("app_title"), self._t("busy_wait"))
            return
        event = self._event_by_id(event_id)
        if event is None:
            return
        if event.extraction_quality == "failed":
            messagebox.showwarning(
                self._t("app_title"),
                self._event_note(event) or self._t("no_separated_track"),
            )
            return
        if (
            event.extraction_quality == "review"
            and not event.muted
            and not messagebox.askyesno(
                self._t("app_title"),
                self._t(
                    "confirm_mute_review",
                    label=self._event_label(event),
                    note=self._event_note(event),
                ),
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
            raise RuntimeError(self._t("preview_open_failed", path=source))
        capture.set(cv2.CAP_PROP_POS_MSEC, offset * 1000.0)
        self.video_capture = capture
        self.video_position = offset
        self.preview_fps = normalized_preview_fps(capture.get(cv2.CAP_PROP_FPS))
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
        generation = self.playback_generation
        self.player_poll_after_id = self.after(
            250, lambda: self._poll_player(generation)
        )
        self.video_poll_after_id = self.after(
            next_preview_delay_ms(
                self.player_started_at, time.monotonic(), self.preview_fps
            ),
            lambda: self._poll_video_frame(generation),
        )

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
        image.thumbnail((PREVIEW_WIDTH, PREVIEW_HEIGHT), Image.Resampling.BILINEAR)
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
        preview_fps = normalized_preview_fps(
            getattr(self, "preview_fps", float(PREVIEW_FPS))
        )
        frame_tolerance = 0.5 / preview_fps
        if not force_seek and self.video_position + frame_tolerance >= target:
            return
        if force_seek or target - self.video_position > 0.5:
            capture.set(cv2.CAP_PROP_POS_MSEC, target * 1000.0)
        newest = None
        for _ in range(max(1, round(preview_fps))):
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

    def _poll_video_frame(self, generation: int | None = None) -> None:
        self.video_poll_after_id = None
        if generation is not None and generation != self.playback_generation:
            return
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
        self.video_poll_after_id = self.after(
            next_preview_delay_ms(
                self.player_started_at, time.monotonic(), self.preview_fps
            ),
            lambda: self._poll_video_frame(generation),
        )

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
            messagebox.showinfo(
                self._t("app_title"), self._t("choose_video_first")
            )
            return
        muted = [event for event in self.events if event.muted]
        if not muted:
            self._start_audio_preview(self.video_path, "original")
            self._set_status("status_playing_original")
            return
        if not self.result_dir:
            return
        target = muted_mix_preview_path(self.result_dir)
        if target.exists() and not self.model_preview_dirty.get(
            self._active_result_key(), True
        ):
            self._start_audio_preview(target, "original")
            self._set_status("status_playing_muted", count=len(muted))
            return
        video_path = self.video_path
        events = list(self.events)
        result_key = self._active_result_key()

        def operation() -> None:
            export_video(video_path, target, events)
            self.model_preview_dirty[result_key] = False
            self.after(0, lambda: self._start_audio_preview(target, "original"))
            self.after(
                0,
                lambda: self._set_status(
                    "status_playing_muted", count=len(muted)
                ),
            )

        self._run_background("status_prepare_muted_preview", operation)

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
            messagebox.showinfo(
                self._t("app_title"), self._t("preview_unavailable")
            )
            return
        self._start_audio_preview(preview_path, "extracted", event_id)

    def stop_original_preview(self) -> None:
        if self.player_kind == "original":
            self.stop_preview()

    def stop_preview(self, refresh: bool = True) -> None:
        self.playback_generation += 1
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
        if self.volume_restart_after_id:
            try:
                self.after_cancel(self.volume_restart_after_id)
            except tk.TclError:
                pass
            self.volume_restart_after_id = None
        if self.video_capture is not None:
            self.video_capture.release()
        self.video_capture = None
        previous_player = self.player
        self.player = None
        terminate_preview_process(previous_player)
        self.player_kind = None
        self.player_event_id = None
        self.player_source = None
        self.player_started_at = 0.0
        self.player_offset = 0.0
        self.player_duration = 0.0
        self.video_position = 0.0
        self.preview_fps = float(PREVIEW_FPS)
        self.seek_dragging = False
        if hasattr(self, "preview_seek_scale"):
            self.preview_seek_scale.state(["disabled"])
            self._set_preview_position(0.0)
        self.preview_photo = None
        self.preview_label.configure(
            image="",
            text=self._t("preview_placeholder"),
        )
        if refresh:
            self.refresh_rows()

    def _poll_player(self, generation: int | None = None) -> None:
        self.player_poll_after_id = None
        if generation is not None and generation != self.playback_generation:
            return
        if not self._player_is_running():
            self.stop_preview()
            return
        self.player_poll_after_id = self.after(
            250, lambda: self._poll_player(generation)
        )

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
                (repo, self._t("required_avcass_repo")),
                (deps, self._t("required_avcass_deps")),
                (checkpoint, self._t("required_avcass_checkpoint")),
                (cavp_checkpoint, self._t("required_cavp_checkpoint")),
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
                (repo, self._t("required_bandit_repo")),
                (hparams, self._t("required_bandit_config")),
                (checkpoint, self._t("required_bandit_checkpoint")),
            )
            result = (python_path, repo, hparams, checkpoint)
        elif model_id == "audiosep":
            python_path, repo, checkpoint, runtime_root = audiosep_runtime_paths(
                self.portable_runtime
            )
            required = (
                (python_path, "AI Python"),
                (repo, self._t("required_audiosep_repo")),
                (checkpoint, self._t("required_audiosep_state")),
                (
                    runtime_root / "roberta-base" / "model.safetensors",
                    self._t("required_audiosep_encoder"),
                ),
            )
            result = (python_path, repo, checkpoint, runtime_root)
        else:
            messagebox.showerror(
                self._t("app_title"), self._t("model_not_installed")
            )
            return None

        for path, label in required:
            if not path.exists():
                messagebox.showerror(
                    self._t("app_title"),
                    self._t("required_missing", label=label, path=path),
                )
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
                str(worker_script_path("avcass_worker.py")),
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
                str(worker_script_path("bandit_worker.py")),
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
                str(worker_script_path("audiosep_worker.py")),
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

        def show_worker_progress(line: str) -> None:
            progress = worker_progress_key(model_id, line)
            if progress is not None:
                key, values = progress
                self._show_progress(key, **values)

        run_worker_command(command, show_worker_progress)
        self._show_progress(
            "progress_check_results", model=MODEL_LABELS.get(model_id, model_id)
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
            note = TRANSLATIONS["ko"]["quality_unreadable"]
        for event in events:
            event.extraction_quality = quality
            event.extraction_note = note
        progress_label = self._active_result_label()
        for index, event in enumerate(events, start=1):
            self._show_progress(
                "progress_create_preview",
                model=progress_label,
                current=index,
                total=len(events),
            )
            create_preview_video(
                video_path,
                Path(event.extracted_path),
                preview_path_for_event(result_dir, event),
            )
        return events

    def save_video(self) -> None:
        if not self.video_path or not self.work_dir or not self.events:
            messagebox.showwarning(self._t("app_title"), self._t("analyze_first"))
            return
        muted = [event for event in self.events if event.muted]
        if not muted:
            messagebox.showinfo(
                self._t("app_title"), self._t("select_mute_first")
            )
            return
        video_path = self.video_path
        work_dir = self.work_dir
        events = list(self.events)
        target = muted_copy_output_path(video_path, events)
        self.stop_preview()

        def operation() -> None:
            export_video(video_path, target, events)
            if not target.is_file() or target.stat().st_size <= 0:
                raise RuntimeError(self._t("saved_file_invalid", path=target))

            try:
                if work_dir is not None:
                    cleanup_work_directory(video_path, work_dir)
            except (OSError, RuntimeError) as exc:
                message = self._t(
                    "save_cleanup_warning",
                    target=target,
                    work_dir=work_dir,
                    error=exc,
                )
                self.after(
                    0,
                    lambda: self._set_status(
                        "status_save_cleanup_failed", path=target
                    ),
                )
                self.after(
                    0,
                    lambda: messagebox.showwarning(self._t("app_title"), message),
                )
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
                self._set_status("status_save_complete", path=target)
                messagebox.showinfo(
                    self._t("app_title"),
                    self._t("save_complete_dialog", path=target),
                )

            self.after(0, finish)

        self._run_background("status_saving", operation)

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
            command = [
                    str(python_path),
                    str(worker_script_path("avcass_worker.py")),
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

            def record_worker_output(line: str) -> None:
                print(line, flush=True)
                write_result(
                    {
                        "stage": "separating",
                        "duration": duration,
                        "latest_log": line,
                    }
                )

            run_worker_command(command, record_worker_output)
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

from __future__ import annotations

import argparse
import faulthandler
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from collections.abc import Mapping
from pathlib import Path


AVCASS_SAMPLE_RATE = 16000
INFERENCE_LENGTH = 130816
DEFAULT_OVERLAP_SECONDS = 1.0
DEFAULT_OVERLAP_SAMPLES = round(DEFAULT_OVERLAP_SECONDS * AVCASS_SAMPLE_RATE)
DEFAULT_BLEND_MODE = "cosine"
INFERENCE_HOP = INFERENCE_LENGTH - DEFAULT_OVERLAP_SAMPLES
INFERENCE_STEPS = 250
VIDEO_FPS = 4
MODEL_BAND_LIMIT = 8000.0
MAX_MEDIA_DURATION_SECONDS = 10 * 60
MAX_VIDEO_FRAMES = MAX_MEDIA_DURATION_SECONDS * VIDEO_FPS
MAX_FFMPEG_OUTPUT_BYTES = 1024 * 1024
FFMPEG_RESOURCE_ARGS = (
    "-max_alloc",
    str(128 * 1024**2),
    "-probesize",
    str(32 * 1024**2),
    "-analyzeduration",
    str(30 * 1_000_000),
)
VIDEO_FORMAT_WHITELISTS = {
    ".avi": "avi",
    ".m4v": "mov,mp4,m4a,3gp,3g2,mj2",
    ".mkv": "matroska,webm",
    ".mov": "mov,mp4,m4a,3gp,3g2,mj2",
    ".mp4": "mov,mp4,m4a,3gp,3g2,mj2",
    ".webm": "matroska,webm",
}


def run_bounded_ffmpeg(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if (
                os.fstat(stdout_file.fileno()).st_size > MAX_FFMPEG_OUTPUT_BYTES
                or os.fstat(stderr_file.fileno()).st_size > MAX_FFMPEG_OUTPUT_BYTES
            ):
                process.kill()
                process.wait(timeout=10)
                raise RuntimeError("FFmpeg 로그가 안전 제한을 초과했습니다.")
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=10)
                raise RuntimeError("FFmpeg 영상 프레임 추출 시간이 제한을 초과했습니다.")
            time.sleep(0.05)
        return_code = process.wait(timeout=10)
        stdout_size = os.fstat(stdout_file.fileno()).st_size
        stderr_size = os.fstat(stderr_file.fileno()).st_size
        if stdout_size > MAX_FFMPEG_OUTPUT_BYTES or stderr_size > MAX_FFMPEG_OUTPUT_BYTES:
            raise RuntimeError("FFmpeg 로그가 안전 제한을 초과했습니다.")
        stdout_file.seek(0)
        stderr_file.seek(0)
        return subprocess.CompletedProcess(
            command,
            return_code,
            stdout_file.read(stdout_size).decode("utf-8", errors="replace"),
            stderr_file.read(stderr_size).decode("utf-8", errors="replace"),
        )


def load_avcass_ema_state(checkpoint: Path, torch_module):
    """Load only tensor weights and the small argparse metadata AV-CASS needs."""
    with torch_module.serialization.safe_globals([argparse.Namespace]):
        payload = torch_module.load(
            checkpoint,
            map_location="cpu",
            weights_only=True,
        )
    if not isinstance(payload, Mapping) or "ema" not in payload:
        raise RuntimeError("AV-CASS 체크포인트에 ema 가중치가 없습니다.")
    state = payload["ema"]
    if not isinstance(state, Mapping):
        raise RuntimeError("AV-CASS ema 가중치 형식이 올바르지 않습니다.")
    return state


def init_cavp_with_restricted_checkpoint(
    init_visual_encoder,
    torch_module,
    numpy_module,
):
    """Restrict the upstream CAVP loader to weights-only checkpoint contents."""
    safe_globals = [
        numpy_module.dtype,
        numpy_module.core.multiarray.scalar,
        type(numpy_module.dtype(numpy_module.float64)),
    ]
    original_load = torch_module.load

    def restricted_load(*args, **kwargs):
        kwargs["weights_only"] = True
        with torch_module.serialization.safe_globals(safe_globals):
            return original_load(*args, **kwargs)

    torch_module.load = restricted_load
    try:
        return init_visual_encoder("cavp")
    finally:
        torch_module.load = original_load


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AV-CASS 고품질 음악/비음악 분리 작업자")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--deps", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--cavp-checkpoint", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--music-output", required=True)
    parser.add_argument("--non-music-output", required=True)
    parser.add_argument("--steps", type=int, default=INFERENCE_STEPS)
    parser.add_argument(
        "--overlap-seconds",
        type=float,
        default=DEFAULT_OVERLAP_SECONDS,
        help="청크 사이 겹침 길이. 기본값은 청취 검증된 1초 OLA입니다.",
    )
    parser.add_argument(
        "--blend-mode",
        choices=("average", "cosine"),
        default=DEFAULT_BLEND_MODE,
        help="겹친 청크 결합 방식. 기본값은 cosine-squared OLA입니다.",
    )
    parser.add_argument(
        "--high-band-extension",
        type=float,
        default=0.0,
        help="8kHz 위 음악 마스크의 보수적 확장 강도(0~1). 기본값 0은 기존 결과입니다.",
    )
    parser.add_argument(
        "--diagnostic-trace-seconds",
        type=float,
        default=0.0,
        help="진단 시 지정 간격마다 현재 Python 스택을 출력합니다.",
    )
    parser.add_argument(
        "--comparison-output-dir",
        default="",
        help=(
            "후처리 A/B/C 진단 파일(raw/current/hybrid)을 저장할 폴더. "
            "비워 두면 기존 제품 출력만 생성합니다."
        ),
    )
    return parser.parse_args()


def require_file(path_text: str | Path, label: str) -> Path:
    path = Path(path_text).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label}을 찾을 수 없습니다: {path}")
    return path


def extract_video_frames(
    ffmpeg: Path, video: Path, frame_dir: Path, duration: float
) -> None:
    if not 0 < duration <= MAX_MEDIA_DURATION_SECONDS:
        raise ValueError("AV-CASS 영상은 최대 10분까지 처리할 수 있습니다.")
    video_format = VIDEO_FORMAT_WHITELISTS.get(video.suffix.lower())
    if video_format is None:
        raise ValueError("AV-CASS가 지원하지 않는 영상 컨테이너입니다.")
    frame_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        *FFMPEG_RESOURCE_ARGS,
        "-y",
        "-protocol_whitelist",
        "file",
        "-format_whitelist",
        video_format,
        "-i",
        str(video),
        "-t",
        f"{duration:.3f}",
        "-vf",
        (
            f"fps={VIDEO_FPS},"
            "scale=224:224:force_original_aspect_ratio=increase,"
            "crop=224:224"
        ),
        "-frames:v",
        str(MAX_VIDEO_FRAMES),
        str(frame_dir / "frame_%06d.png"),
    ]
    completed = run_bounded_ffmpeg(
        command,
        timeout=max(300.0, min(4 * 60 * 60.0, duration * 3.0 + 300.0)),
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "영상 프레임 추출에 실패했습니다.")


def frame_paths(frame_dir: Path) -> list[Path]:
    paths = sorted(frame_dir.glob("frame_*.png"))
    if not paths:
        raise RuntimeError("AV-CASS용 영상 프레임이 생성되지 않았습니다.")
    if len(paths) > MAX_VIDEO_FRAMES:
        raise RuntimeError("AV-CASS용 영상 프레임 수가 안전 한도를 초과했습니다.")
    return paths


def load_frame_chunk(paths: list[Path], start: int, count: int):
    import numpy as np
    import torch
    from PIL import Image

    if not paths:
        raise RuntimeError("AV-CASS용 영상 프레임이 생성되지 않았습니다.")
    selected = paths[start : start + count]
    if len(selected) < count:
        selected.extend([selected[-1] if selected else paths[-1]] * (count - len(selected)))
    frames = []
    for path in selected:
        with Image.open(path) as image:
            frames.append(
                np.asarray(image.convert("RGB"), dtype=np.uint8).transpose(2, 0, 1)
            )
    return torch.from_numpy(np.stack(frames))


def pcm_wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as source:
            duration = source.getnframes() / source.getframerate()
    except (OSError, wave.Error, ZeroDivisionError) as error:
        raise ValueError("입력 WAV 헤더를 안전하게 읽지 못했습니다.") from error
    if not 0 < duration <= MAX_MEDIA_DURATION_SECONDS:
        raise ValueError("AV-CASS 입력은 최대 10분까지 처리할 수 있습니다.")
    return duration


def centered_correlation(first, second) -> float:
    import torch

    left = first.reshape(-1).to(dtype=torch.float64)
    right = second.reshape(-1).to(dtype=torch.float64)
    left = left - left.mean()
    right = right - right.mean()
    denominator = torch.linalg.vector_norm(left) * torch.linalg.vector_norm(right)
    if float(denominator) <= 1e-12:
        return 0.0
    return float(torch.dot(left, right) / denominator)


def comparison_waveform_metrics(waveform, reference, sample_rate: int) -> dict:
    import torch

    waveform_rms = float(waveform.square().mean().sqrt())
    reference_rms = float(reference.square().mean().sqrt())
    metrics = {
        "rms_ratio_to_source": waveform_rms / reference_rms if reference_rms else 0.0,
        "source_correlation": centered_correlation(reference, waveform),
        "peak": float(waveform.abs().max()),
    }
    if waveform.shape[0] >= 2:
        left = waveform[0]
        right = waveform[1]
        mid_rms = float(((left + right) * 0.5).square().mean().sqrt())
        side_rms = float(((left - right) * 0.5).square().mean().sqrt())
        metrics["stereo_side_to_mid_ratio"] = (
            side_rms / mid_rms if mid_rms else 0.0
        )
        metrics["left_right_correlation"] = centered_correlation(left, right)
    else:
        metrics["stereo_side_to_mid_ratio"] = 0.0
        metrics["left_right_correlation"] = 1.0

    spectrum = torch.fft.rfft(waveform, dim=-1)
    frequencies = torch.fft.rfftfreq(
        waveform.shape[-1], d=1.0 / sample_rate, device=waveform.device
    )
    power = spectrum.abs().square()
    total_power = float(power.sum())
    high_power = float(power[:, frequencies > MODEL_BAND_LIMIT].sum())
    metrics["energy_above_8khz_fraction"] = (
        high_power / total_power if total_power else 0.0
    )
    return metrics


def configure_yapf_cache() -> Path:
    """Put YAPF's generated grammar cache in a writable per-user location."""
    cache_dir = Path(tempfile.gettempdir()) / "video-music-separator-yapf"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YAPF_CACHE_DIR"] = str(cache_dir)
    return cache_dir


def inference_starts(
    audio_length: int, overlap_samples: int = DEFAULT_OVERLAP_SAMPLES
) -> list[int]:
    if not 0 <= overlap_samples < INFERENCE_LENGTH:
        raise ValueError(
            f"청크 겹침은 0 이상 {INFERENCE_LENGTH} 미만이어야 합니다: "
            f"{overlap_samples}"
        )
    inference_hop = INFERENCE_LENGTH - overlap_samples
    starts: list[int] = []
    for index in range(0, audio_length, inference_hop):
        start = (
            audio_length - INFERENCE_LENGTH
            if index + INFERENCE_LENGTH >= audio_length
            else index
        )
        if not starts or starts[-1] != start:
            starts.append(start)
    return starts


def chunk_blend_weight(starts, index: int, *, device, dtype):
    """Return complementary cosine-squared fades for one inference chunk."""
    import torch

    start = starts[index]
    weight = torch.ones(INFERENCE_LENGTH, device=device, dtype=dtype)
    if index:
        left_overlap = starts[index - 1] + INFERENCE_LENGTH - start
        if left_overlap > 0:
            phase = torch.linspace(
                0.0, torch.pi / 2, left_overlap, device=device, dtype=dtype
            )
            weight[:left_overlap] *= torch.sin(phase).square()
    if index + 1 < len(starts):
        right_overlap = start + INFERENCE_LENGTH - starts[index + 1]
        if right_overlap > 0:
            phase = torch.linspace(
                0.0, torch.pi / 2, right_overlap, device=device, dtype=dtype
            )
            weight[-right_overlap:] *= torch.cos(phase).square()
    return weight


def sample_with_progress(transport, model, noise, *, chunk_number: int, **kwargs):
    """Run AV-CASS sampling while exposing each otherwise opaque Euler step."""
    completed_steps = 0
    total_steps = max(int(transport.infer_steps) - 1, 0)
    started_at = time.perf_counter()

    def forward_with_progress(*args, **model_kwargs):
        nonlocal completed_steps
        result = model.forward_with_cfg(*args, **model_kwargs)
        completed_steps += 1
        elapsed = time.perf_counter() - started_at
        print(
            f"[step {completed_steps}/{total_steps}] "
            f"청크 {chunk_number}, 누적 {elapsed:.1f}초",
            flush=True,
        )
        return result

    return transport.sample(forward_with_progress, noise, **kwargs)


def main() -> int:
    args = parse_args()
    if args.diagnostic_trace_seconds > 0:
        faulthandler.dump_traceback_later(
            args.diagnostic_trace_seconds, repeat=True
        )
    repo = Path(args.repo).resolve()
    deps = Path(args.deps).resolve()
    runtime_root = Path(args.runtime_root).resolve()
    if not repo.is_dir():
        raise FileNotFoundError(f"AV-CASS 코드 폴더를 찾을 수 없습니다: {repo}")
    if not deps.is_dir():
        raise FileNotFoundError(f"AV-CASS 실행 구성요소를 찾을 수 없습니다: {deps}")

    checkpoint = require_file(args.checkpoint, "AV-CASS 체크포인트")
    cavp_checkpoint = require_file(args.cavp_checkpoint, "CAVP 체크포인트")
    ffmpeg = require_file(args.ffmpeg, "FFmpeg")
    video = require_file(args.video, "입력 영상")
    input_path = require_file(args.input, "입력 오디오")
    music_output = Path(args.music_output).resolve()
    non_music_output = Path(args.non_music_output).resolve()
    music_output.parent.mkdir(parents=True, exist_ok=True)
    non_music_output.parent.mkdir(parents=True, exist_ok=True)
    duration_seconds = pcm_wav_duration(input_path)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    # YAPF is imported indirectly by MMCV while CAVP starts. Its grammar
    # cache uses exclusive temporary files and can spin forever when the
    # installed/runtime folder is read-only (for example Program Files or a
    # restricted launcher). Keep this small generated cache in the user's
    # writable temporary directory instead of beside the model assets.
    configure_yapf_cache()
    os.environ["CAVP_CKPT"] = str(cavp_checkpoint)
    sys.path.insert(0, str(deps))
    sys.path.insert(0, str(repo))

    import numpy as np
    import torch
    import torch.nn.functional as functional
    import torchaudio

    from models_avdnr_zero_conv_2vid import SiT_models
    from separation_quality import (
        apply_raw_anchored_hybrid,
        apply_stereo_consistent_mask,
    )
    from spec_utils import audio2spec, spec2audio
    from transport.RFM import ReFlow
    from visual_backbones import forward_video, init_visual_encoder

    if not torch.cuda.is_available():
        raise RuntimeError("AV-CASS 고품질 모드는 NVIDIA GPU가 필요합니다.")
    device = torch.device("cuda")
    print(
        "[cuda] "
        f"장치={torch.cuda.get_device_name(device)}, "
        f"capability={torch.cuda.get_device_capability(device)}, "
        f"torch={torch.__version__}, cuda={torch.version.cuda}",
        flush=True,
    )
    torch.manual_seed(0)
    torch.backends.cuda.matmul.allow_tf32 = True

    if args.overlap_seconds < 0:
        raise ValueError("청크 겹침 시간은 0 이상이어야 합니다.")
    overlap_samples = round(args.overlap_seconds * AVCASS_SAMPLE_RATE)
    if not 0.0 <= args.high_band_extension <= 1.0:
        raise ValueError("고역 확장 강도는 0 이상 1 이하여야 합니다.")

    reference, sample_rate = torchaudio.load(str(input_path))
    if reference.ndim != 2 or reference.shape[0] < 1:
        raise ValueError(f"지원하지 않는 오디오 모양입니다: {tuple(reference.shape)}")
    original_samples = reference.shape[-1]
    mono = reference.mean(dim=0, keepdim=True)
    mono_16k = torchaudio.functional.resample(
        mono, orig_freq=sample_rate, new_freq=AVCASS_SAMPLE_RATE
    ).squeeze(0)
    original_16k_length = mono_16k.shape[-1]
    if original_16k_length < INFERENCE_LENGTH:
        mono_16k = functional.pad(
            mono_16k, (0, INFERENCE_LENGTH - original_16k_length)
        )
    audio_length = mono_16k.shape[-1]

    with tempfile.TemporaryDirectory(
        prefix="avcass-frames-", dir=str(music_output.parent)
    ) as temporary:
        frame_dir = Path(temporary)
        print("[setup] 영상 프레임 분석 준비 중", flush=True)
        extract_video_frames(ffmpeg, video, frame_dir, duration_seconds)
        all_frame_paths = frame_paths(frame_dir)

        setup_started = time.perf_counter()
        print("[setup] AV-CASS 모델 구조 생성 중", flush=True)
        model = SiT_models["UNet2d_S2"](
            in_channels=8,
            out_channels=6,
            attention_head_dim=64,
            visual_feat_dim=512,
        )
        print(
            f"[setup] AV-CASS 체크포인트 읽는 중 ({time.perf_counter() - setup_started:.1f}초)",
            flush=True,
        )
        state = load_avcass_ema_state(checkpoint, torch)
        print(
            f"[setup] AV-CASS 가중치 적용 중 ({time.perf_counter() - setup_started:.1f}초)",
            flush=True,
        )
        model.load_state_dict(state, strict=True)
        print(
            f"[setup] AV-CASS 모델 CUDA 이동 중 ({time.perf_counter() - setup_started:.1f}초)",
            flush=True,
        )
        model = model.to(device).eval()
        del state

        print(
            f"[setup] CAVP 영상 인식기 생성·체크포인트 적용 중 "
            f"({time.perf_counter() - setup_started:.1f}초)",
            flush=True,
        )
        image_model, _ = init_cavp_with_restricted_checkpoint(
            init_visual_encoder,
            torch,
            np,
        )
        print(
            f"[setup] CAVP CUDA 이동 중 ({time.perf_counter() - setup_started:.1f}초)",
            flush=True,
        )
        image_model = image_model.to(device).eval()
        print(
            f"[setup] 모델 준비 완료 ({time.perf_counter() - setup_started:.1f}초)",
            flush=True,
        )
        transport = ReFlow(infer_steps=args.steps)

        overlap_count = torch.zeros(audio_length, device=device)
        prediction = torch.zeros(3, audio_length, device=device)
        starts = inference_starts(audio_length, overlap_samples)
        for chunk_index, start in enumerate(starts):
            chunk_number = chunk_index + 1
            end = start + INFERENCE_LENGTH
            print(
                f"[run {chunk_number}/{len(starts)}] "
                f"{start / AVCASS_SAMPLE_RATE:.2f}-{end / AVCASS_SAMPLE_RATE:.2f}초",
                flush=True,
            )
            mixture = mono_16k[start:end].unsqueeze(0).to(device)
            mixture_latents = audio2spec(mixture.unsqueeze(1)).reshape(
                1, 2, 256, 512
            ).contiguous()

            frame_start = int(start / AVCASS_SAMPLE_RATE * VIDEO_FPS)
            frame_count = int(INFERENCE_LENGTH / AVCASS_SAMPLE_RATE * VIDEO_FPS)
            video_chunk = load_frame_chunk(
                all_frame_paths, frame_start, frame_count
            )
            video_chunk = video_chunk.unsqueeze(0).to(device)

            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
                visual_features = forward_video(image_model, video_chunk, "cavp")
                noise = torch.randn(1, 6, 256, 512, device=device)
                samples = sample_with_progress(
                    transport,
                    model,
                    noise,
                    chunk_number=chunk_number,
                    mixture_latents=mixture_latents,
                    cfg_scale=0.0,
                    vid=visual_features.half(),
                )
                samples = spec2audio(samples)[0]

            if args.blend_mode == "cosine":
                blend_weight = chunk_blend_weight(
                    starts,
                    chunk_index,
                    device=device,
                    dtype=samples.dtype,
                )
            else:
                blend_weight = torch.ones(
                    INFERENCE_LENGTH, device=device, dtype=samples.dtype
                )
            prediction[:, start:end] += (
                samples[:, :INFERENCE_LENGTH] * blend_weight.unsqueeze(0)
            )
            overlap_count[start:end] += blend_weight
            del mixture, mixture_latents, video_chunk, visual_features, noise, samples
            torch.cuda.empty_cache()

    prediction /= overlap_count.clamp_min(1).unsqueeze(0)
    prediction = prediction[:, :original_16k_length].float().cpu()
    # AV-CASS output order is speech / sfx / music.  Preserve the exact
    # post-OLA 16 kHz mono tensors before any resampling or post-processing so
    # the comparison folder contains an official-model baseline.
    estimated_music = prediction[2:3]
    estimated_non_music = prediction[0:1] + prediction[1:2]
    raw_music = estimated_music
    raw_non_music = estimated_non_music
    estimated_music = torchaudio.functional.resample(
        estimated_music, orig_freq=AVCASS_SAMPLE_RATE, new_freq=sample_rate
    )
    estimated_non_music = torchaudio.functional.resample(
        estimated_non_music, orig_freq=AVCASS_SAMPLE_RATE, new_freq=sample_rate
    )

    def fit_length(waveform):
        if waveform.shape[-1] < original_samples:
            waveform = functional.pad(
                waveform, (0, original_samples - waveform.shape[-1])
            )
        return waveform[:, :original_samples]

    estimated_music = fit_length(estimated_music)
    estimated_non_music = fit_length(estimated_non_music)
    music, non_music = apply_stereo_consistent_mask(
        reference,
        estimated_music,
        estimated_non_music,
        sample_rate,
        model_band_limit=MODEL_BAND_LIMIT,
        high_band_extension=args.high_band_extension,
    )
    reconstruction = music + non_music

    comparison_dir = None
    hybrid_music = None
    hybrid_non_music = None
    if args.comparison_output_dir:
        comparison_dir = Path(args.comparison_output_dir).resolve()
        comparison_dir.mkdir(parents=True, exist_ok=True)
        print("[compare] raw/current/hybrid 후처리 비교 생성 중", flush=True)
        hybrid_music, hybrid_non_music = apply_raw_anchored_hybrid(
            reference,
            estimated_music,
            estimated_non_music,
            sample_rate,
            model_band_limit=MODEL_BAND_LIMIT,
        )

    source_rms = float(reference.square().mean().sqrt())
    metrics = {
        "mode": "av-cass-quality-stereo-mask",
        "inference_steps": int(args.steps),
        "overlap_seconds": float(args.overlap_seconds),
        "blend_mode": args.blend_mode,
        "high_band_extension": float(args.high_band_extension),
        "source_rms": source_rms,
        "music_rms_ratio": float(music.square().mean().sqrt()) / source_rms
        if source_rms
        else 0.0,
        "non_music_rms_ratio": float(non_music.square().mean().sqrt()) / source_rms
        if source_rms
        else 0.0,
        "music_source_correlation": centered_correlation(reference, music),
        "non_music_source_correlation": centered_correlation(reference, non_music),
        "reconstruction_source_correlation": centered_correlation(
            reference, reconstruction
        ),
        "reconstruction_error_ratio": float(
            (reference - reconstruction).square().mean().sqrt()
        )
        / source_rms
        if source_rms
        else 0.0,
        "channel_count": int(reference.shape[0]),
        "sample_rate": int(sample_rate),
    }
    save_kwargs = {
        "sample_rate": sample_rate,
        "encoding": "PCM_S",
        "bits_per_sample": 24,
    }
    torchaudio.save(str(music_output), music, **save_kwargs)
    torchaudio.save(str(non_music_output), non_music, **save_kwargs)
    if comparison_dir is not None:
        raw_save_kwargs = {
            "sample_rate": AVCASS_SAMPLE_RATE,
            "encoding": "PCM_S",
            "bits_per_sample": 24,
        }
        torchaudio.save(
            str(comparison_dir / "raw_music.wav"), raw_music, **raw_save_kwargs
        )
        torchaudio.save(
            str(comparison_dir / "raw_non_music.wav"),
            raw_non_music,
            **raw_save_kwargs,
        )
        torchaudio.save(
            str(comparison_dir / "current_music.wav"), music, **save_kwargs
        )
        torchaudio.save(
            str(comparison_dir / "current_non_music.wav"),
            non_music,
            **save_kwargs,
        )
        torchaudio.save(
            str(comparison_dir / "hybrid_music.wav"),
            hybrid_music,
            **save_kwargs,
        )
        torchaudio.save(
            str(comparison_dir / "hybrid_non_music.wav"),
            hybrid_non_music,
            **save_kwargs,
        )
        comparison_metrics = {
            "input": str(video),
            "stem_order": ["speech", "sfx", "music"],
            "raw": {
                "description": "prediction[2], post-OLA only, 16 kHz mono",
                "music": comparison_waveform_metrics(
                    raw_music,
                    mono_16k[:original_16k_length].unsqueeze(0),
                    AVCASS_SAMPLE_RATE,
                ),
            },
            "current": {
                "description": "existing stereo-consistent power mask",
                "music": comparison_waveform_metrics(music, reference, sample_rate),
                "reconstruction_error_ratio": float(
                    (reference - (music + non_music)).square().mean().sqrt()
                )
                / source_rms
                if source_rms
                else 0.0,
            },
            "hybrid": {
                "description": (
                    "raw Music anchor + smoothed stereo transfer + "
                    "conservative activity-gated high band"
                ),
                "high_band_strength": 0.35,
                "music": comparison_waveform_metrics(
                    hybrid_music, reference, sample_rate
                ),
                "reconstruction_error_ratio": float(
                    (
                        reference - (hybrid_music + hybrid_non_music)
                    ).square().mean().sqrt()
                )
                / source_rms
                if source_rms
                else 0.0,
            },
            "limitations": (
                "Speech/SFX leakage and musical naturalness require direct listening; "
                "these signal metrics are not source-separation scores."
            ),
        }
        (comparison_dir / "comparison_metrics.json").write_text(
            json.dumps(comparison_metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[compare] 비교 폴더: {comparison_dir}", flush=True)
    (music_output.parent / "partition_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[done] 음악: {music_output}", flush=True)
    print(f"[done] 음악 아님: {non_music_output}", flush=True)
    print(f"[metrics] {json.dumps(metrics, ensure_ascii=False)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


AVCASS_SAMPLE_RATE = 16000
INFERENCE_LENGTH = 130816
INFERENCE_HOP = INFERENCE_LENGTH - 256
INFERENCE_STEPS = 250
VIDEO_FPS = 4
MODEL_BAND_LIMIT = 8000.0


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
    return parser.parse_args()


def require_file(path_text: str | Path, label: str) -> Path:
    path = Path(path_text).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label}을 찾을 수 없습니다: {path}")
    return path


def extract_video_frames(ffmpeg: Path, video: Path, frame_dir: Path) -> None:
    frame_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vf",
        (
            f"fps={VIDEO_FPS},"
            "scale=224:224:force_original_aspect_ratio=increase,"
            "crop=224:224"
        ),
        str(frame_dir / "frame_%06d.png"),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "영상 프레임 추출에 실패했습니다.")


def load_frames(frame_dir: Path):
    import numpy as np
    import torch
    from PIL import Image

    paths = sorted(frame_dir.glob("frame_*.png"))
    if not paths:
        raise RuntimeError("AV-CASS용 영상 프레임이 생성되지 않았습니다.")
    frames = [
        np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8).transpose(2, 0, 1)
        for path in paths
    ]
    return torch.from_numpy(np.stack(frames))


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


def inference_starts(audio_length: int) -> list[int]:
    starts: list[int] = []
    for index in range(0, audio_length, INFERENCE_HOP):
        start = (
            audio_length - INFERENCE_LENGTH
            if index + INFERENCE_LENGTH >= audio_length
            else index
        )
        if not starts or starts[-1] != start:
            starts.append(start)
    return starts


def main() -> int:
    args = parse_args()
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

    cache_dir = runtime_root / "cache" / "yapf"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YAPF_CACHE_DIR"] = str(cache_dir)
    os.environ["CAVP_CKPT"] = str(cavp_checkpoint)
    sys.path.insert(0, str(deps))
    sys.path.insert(0, str(repo))

    import torch
    import torch.nn.functional as functional
    import torchaudio

    from models_avdnr_zero_conv_2vid import SiT_models
    from separation_quality import apply_stereo_consistent_mask
    from spec_utils import audio2spec, spec2audio
    from transport.RFM import ReFlow
    from visual_backbones import forward_video, init_visual_encoder

    if not torch.cuda.is_available():
        raise RuntimeError("AV-CASS 고품질 모드는 NVIDIA GPU가 필요합니다.")
    device = torch.device("cuda")
    torch.manual_seed(0)
    torch.backends.cuda.matmul.allow_tf32 = True

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
        extract_video_frames(ffmpeg, video, frame_dir)
        all_frames = load_frames(frame_dir)

        print("[setup] AV-CASS 분리 모델 준비 중", flush=True)
        model = SiT_models["UNet2d_S2"](
            in_channels=8,
            out_channels=6,
            attention_head_dim=64,
            visual_feat_dim=512,
        )
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)["ema"]
        model.load_state_dict(state, strict=True)
        model = model.to(device).eval()
        del state

        print("[setup] CAVP 영상 인식기 준비 중", flush=True)
        image_model, _ = init_visual_encoder("cavp")
        image_model = image_model.to(device).eval()
        transport = ReFlow(infer_steps=args.steps)

        overlap_count = torch.zeros(audio_length, device=device)
        prediction = torch.zeros(3, audio_length, device=device)
        starts = inference_starts(audio_length)
        for chunk_number, start in enumerate(starts, start=1):
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
            video_chunk = all_frames[frame_start : frame_start + frame_count]
            if len(video_chunk) < frame_count:
                pad_frame = video_chunk[-1:] if len(video_chunk) else all_frames[-1:]
                video_chunk = torch.cat(
                    [
                        video_chunk,
                        pad_frame.repeat(frame_count - len(video_chunk), 1, 1, 1),
                    ],
                    dim=0,
                )
            video_chunk = video_chunk.unsqueeze(0).to(device)

            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
                visual_features = forward_video(image_model, video_chunk, "cavp")
                noise = torch.randn(1, 6, 256, 512, device=device)
                samples = transport.sample(
                    model.forward_with_cfg,
                    noise,
                    mixture_latents=mixture_latents,
                    cfg_scale=0.0,
                    vid=visual_features.half(),
                )
                samples = spec2audio(samples)[0]

            prediction[:, start:end] += samples[:, :INFERENCE_LENGTH]
            overlap_count[start:end] += 1
            del mixture, mixture_latents, video_chunk, visual_features, noise, samples
            torch.cuda.empty_cache()

    prediction /= overlap_count.clamp_min(1).unsqueeze(0)
    prediction = prediction[:, :original_16k_length].float().cpu()
    estimated_music = prediction[2:3]
    estimated_non_music = prediction[0:1] + prediction[1:2]
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
    )
    reconstruction = music + non_music

    source_rms = float(reference.square().mean().sqrt())
    metrics = {
        "mode": "av-cass-quality-stereo-mask",
        "inference_steps": int(args.steps),
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
    (music_output.parent / "partition_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[done] 음악: {music_output}", flush=True)
    print(f"[done] 음악 아님: {non_music_output}", flush=True)
    print(f"[metrics] {json.dumps(metrics, ensure_ascii=False)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

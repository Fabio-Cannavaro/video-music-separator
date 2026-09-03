from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


QUALITY_WINDOW_SECONDS = 12.0
QUALITY_HOP_SECONDS = 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TIGER-DnR 음악/비음악 분리 작업자")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--music-output", required=True)
    parser.add_argument("--non-music-output", required=True)
    return parser.parse_args()


def require_file(path_text: str | Path, label: str) -> Path:
    path = Path(path_text).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label}을 찾을 수 없습니다: {path}")
    return path


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


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        raise FileNotFoundError(f"TIGER 폴더를 찾을 수 없습니다: {repo}")
    model_dir = Path(args.model).resolve()
    config_path = require_file(model_dir / "config.json", "TIGER 모델 설정")
    weights_path = require_file(
        model_dir / "model.safetensors", "TIGER 모델 체크포인트"
    )
    input_path = require_file(args.input, "입력 오디오")
    music_output = Path(args.music_output).resolve()
    non_music_output = Path(args.non_music_output).resolve()
    music_output.parent.mkdir(parents=True, exist_ok=True)
    non_music_output.parent.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(repo))

    import torch
    import torchaudio
    from safetensors.torch import load_file

    from look2hear.models import TIGERDNR

    torch.set_float32_matmul_precision("medium")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[setup] TIGER-DnR 모델 준비 중 ({device})", flush=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model = TIGERDNR(**config)
    model.load_state_dict(load_file(str(weights_path), device="cpu"), strict=True)
    model = model.to(device).eval()

    audio, sample_rate = torchaudio.load(str(input_path))
    if sample_rate != 44100:
        raise ValueError(
            f"입력 오디오는 44100Hz여야 합니다. 현재: {sample_rate}Hz. "
            "앱의 FFmpeg 오디오 추출 단계를 먼저 사용해 주세요."
        )
    if audio.ndim != 2 or audio.shape[0] < 1:
        raise ValueError(f"지원하지 않는 오디오 모양입니다: {tuple(audio.shape)}")

    dialog_channels = []
    effects_channels = []
    music_channels = []
    print(
        f"[run] 음악/비음악 분리 중 ({audio.shape[0]}채널)",
        flush=True,
    )
    with torch.inference_mode():
        # 품질 우선: 공식 12초 창은 유지하고 이동 간격을 4초에서 2초로
        # 줄여 경계마다 여섯 번의 추론 결과를 겹쳐 평균낸다.
        completed_steps = 0
        total_steps = audio.shape[0] * 3
        for channel_index in range(audio.shape[0]):
            channel_label = (
                ("왼쪽" if channel_index == 0 else "오른쪽")
                if audio.shape[0] == 2
                else f"{channel_index + 1}번 채널"
            )
            channel = audio[channel_index : channel_index + 1].unsqueeze(0).to(device)
            dialog = model.wav_chunk_inference(
                model.dialog,
                channel,
                target_length=QUALITY_WINDOW_SECONDS,
                hop_length=QUALITY_HOP_SECONDS,
            )[2]
            completed_steps += 1
            print(
                f"[progress {completed_steps}/{total_steps}] {channel_label} 대사 분석 완료",
                flush=True,
            )
            effects = model.wav_chunk_inference(
                model.effect,
                channel,
                target_length=QUALITY_WINDOW_SECONDS,
                hop_length=QUALITY_HOP_SECONDS,
            )[1]
            completed_steps += 1
            print(
                f"[progress {completed_steps}/{total_steps}] {channel_label} 효과음 분석 완료",
                flush=True,
            )
            music = model.wav_chunk_inference(
                model.music,
                channel,
                target_length=QUALITY_WINDOW_SECONDS,
                hop_length=QUALITY_HOP_SECONDS,
            )[0]
            completed_steps += 1
            print(
                f"[progress {completed_steps}/{total_steps}] {channel_label} 음악 분석 완료",
                flush=True,
            )
            dialog_channels.append(dialog.squeeze(0).detach().cpu())
            effects_channels.append(effects.squeeze(0).detach().cpu())
            music_channels.append(music.squeeze(0).detach().cpu())

    dialog = torch.stack(dialog_channels, dim=0)
    effects = torch.stack(effects_channels, dim=0)
    music = torch.stack(music_channels, dim=0)
    reference = audio.cpu()
    from separation_quality import apply_stereo_consistent_mask

    music, non_music = apply_stereo_consistent_mask(
        reference,
        music,
        dialog + effects,
        sample_rate,
    )
    reconstruction = music + non_music

    source_rms = float(reference.square().mean().sqrt())
    music_rms = float(music.square().mean().sqrt())
    non_music_rms = float(non_music.square().mean().sqrt())
    reconstruction_error = float((reference - reconstruction).square().mean().sqrt())
    metrics = {
        "mode": "tiger-quality-stereo-mask",
        "window_seconds": QUALITY_WINDOW_SECONDS,
        "hop_seconds": QUALITY_HOP_SECONDS,
        "source_rms": source_rms,
        "music_rms_ratio": music_rms / source_rms if source_rms else 0.0,
        "non_music_rms_ratio": non_music_rms / source_rms if source_rms else 0.0,
        "music_source_correlation": centered_correlation(reference, music),
        "non_music_source_correlation": centered_correlation(reference, non_music),
        "reconstruction_source_correlation": centered_correlation(
            reference, reconstruction
        ),
        "reconstruction_error_ratio": (
            reconstruction_error / source_rms if source_rms else 0.0
        ),
        "channel_count": int(reference.shape[0]),
    }

    save_kwargs = {
        "sample_rate": sample_rate,
        "encoding": "PCM_S",
        "bits_per_sample": 24,
    }
    torchaudio.save(str(music_output), music, **save_kwargs)
    torchaudio.save(str(non_music_output), non_music, **save_kwargs)
    metrics_path = music_output.parent / "partition_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[done] 음악: {music_output}", flush=True)
    print(f"[done] 음악 아님: {non_music_output}", flush=True)
    print(f"[metrics] {json.dumps(metrics, ensure_ascii=False)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

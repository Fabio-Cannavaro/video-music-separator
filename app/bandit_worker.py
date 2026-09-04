from __future__ import annotations

import argparse
import json
import os
import sys
import wave
from pathlib import Path


MINIMUM_PAD_SECONDS = 12.0
PCM16_SCALE = 32768.0
MAX_MEDIA_DURATION_SECONDS = 10 * 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BandIt 음악/비음악 분리 작업자")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--hparams", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--music-output", required=True)
    parser.add_argument("--non-music-output", required=True)
    return parser.parse_args()


def require_file(path_text: str, label: str) -> Path:
    path = Path(path_text).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label}을 찾을 수 없습니다: {path}")
    return path


def require_bounded_wav(path: Path) -> None:
    try:
        with wave.open(str(path), "rb") as source:
            duration = source.getnframes() / source.getframerate()
    except (OSError, wave.Error, ZeroDivisionError) as error:
        raise ValueError("입력 WAV 헤더를 안전하게 읽지 못했습니다.") from error
    if not 0 < duration <= MAX_MEDIA_DURATION_SECONDS:
        raise ValueError("입력 오디오는 최대 10분까지 처리할 수 있습니다.")


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
        raise FileNotFoundError(f"BandIt 폴더를 찾을 수 없습니다: {repo}")
    hparams = require_file(args.hparams, "BandIt 설정 파일")
    checkpoint = require_file(args.checkpoint, "BandIt 체크포인트")
    input_path = require_file(args.input, "입력 오디오")
    require_bounded_wav(input_path)
    music_output = Path(args.music_output).resolve()
    non_music_output = Path(args.non_music_output).resolve()
    music_output.parent.mkdir(parents=True, exist_ok=True)
    non_music_output.parent.mkdir(parents=True, exist_ok=True)

    os.environ["PROJECT_ROOT"] = str(repo)
    sys.path.insert(0, str(repo))

    import torch
    import torch.nn.functional as functional
    import torchaudio

    from core import LightningSystem
    from utils.config import read_nested_yaml

    torch.set_float32_matmul_precision("medium")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[setup] BandIt 모델 준비 중 ({device})", flush=True)
    config = read_nested_yaml(str(hparams))
    model = LightningSystem.load_from_checkpoint(
        str(checkpoint),
        config=config["system"],
        map_location="cpu",
    ).to(device)
    model.set_predict_output_path(str(music_output.parent))
    model.fader.__init__(**config["system"]["inference"]["fader"]["kwargs"])
    model.fader.to(model.device)
    model.eval()

    audio, sample_rate = torchaudio.load(str(input_path))
    target_rate = int(config["system"]["model"]["kwargs"]["fs"])
    if sample_rate != target_rate:
        raise ValueError(
            f"입력 오디오는 {target_rate}Hz여야 합니다. 현재: {sample_rate}Hz. "
            "앱의 FFmpeg 오디오 추출 단계를 먼저 사용해 주세요."
        )
    audio = torch.clamp(
        torch.round(audio * PCM16_SCALE),
        -PCM16_SCALE,
        PCM16_SCALE - 1,
    ) / PCM16_SCALE
    original_samples = audio.shape[-1]
    minimum_samples = round(MINIMUM_PAD_SECONDS * sample_rate)
    if original_samples < minimum_samples:
        audio = functional.pad(audio, (0, minimum_samples - original_samples))

    if audio.shape[0] == 1:
        model_input = audio[None, ...]
    else:
        model_input = audio[:, None, :]
    model_input = model_input.to(device)
    tracks = [input_path.stem for _ in range(model_input.shape[0])]

    print("[run] 음악/비음악 분리 중", flush=True)
    with torch.inference_mode():
        _, output = model.predtest_step(
            {
                "audio": {"mixture": model_input},
                "track": tracks,
            }
        )
    stems = output["audio"]
    music = stems["music"][:, 0, :original_samples].detach().cpu()
    non_music = (
        stems["speech"][:, 0, :original_samples]
        + stems["effects"][:, 0, :original_samples]
    ).detach().cpu()

    reference = audio[:, :original_samples].cpu()
    source_rms = float(reference.square().mean().sqrt())
    music_rms = float(music.square().mean().sqrt())
    non_music_rms = float(non_music.square().mean().sqrt())
    metrics = {
        "source_rms": source_rms,
        "music_rms_ratio": music_rms / source_rms if source_rms else 0.0,
        "non_music_rms_ratio": non_music_rms / source_rms if source_rms else 0.0,
        "music_source_correlation": centered_correlation(reference, music),
        "non_music_source_correlation": centered_correlation(reference, non_music),
        "reconstruction_source_correlation": centered_correlation(
            reference, music + non_music
        ),
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

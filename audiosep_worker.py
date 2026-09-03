from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


AUDIOSEP_SAMPLE_RATE = 32000
MINIMUM_CHUNK_SECONDS = 5.0


@contextlib.contextmanager
def skip_replaced_parameter_initialization(nn_module):
    layer_types = (
        nn_module.Conv1d,
        nn_module.Conv2d,
        nn_module.ConvTranspose1d,
        nn_module.ConvTranspose2d,
        nn_module.Linear,
        nn_module.BatchNorm1d,
        nn_module.BatchNorm2d,
        nn_module.Embedding,
        nn_module.LayerNorm,
    )
    originals = {layer_type: layer_type.reset_parameters for layer_type in layer_types}
    try:
        for layer_type in layer_types:
            layer_type.reset_parameters = lambda self: None
        yield
    finally:
        for layer_type, original in originals.items():
            layer_type.reset_parameters = original


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AudioSep 음악/비음악 분리 작업자")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--query", default="music")
    parser.add_argument("--music-output")
    parser.add_argument("--non-music-output")
    parser.add_argument(
        "--jobs-json",
        help="모델을 한 번만 불러 여러 음악 질의를 연속 처리할 JSON 파일",
    )
    return parser.parse_args()


def require_file(path_text: str, label: str) -> Path:
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


def load_jobs(args: argparse.Namespace) -> list[dict[str, str]]:
    if args.jobs_json:
        jobs_path = require_file(args.jobs_json, "AudioSep 일괄 작업 파일")
        raw_jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
        if not isinstance(raw_jobs, list) or not raw_jobs:
            raise ValueError("AudioSep 일괄 작업은 하나 이상의 목록이어야 합니다.")
        jobs = []
        for raw in raw_jobs:
            if not isinstance(raw, dict):
                raise ValueError("AudioSep 일괄 작업 항목 형식이 올바르지 않습니다.")
            job = {
                "query": str(raw.get("query", "")).strip(),
                "music_output": str(raw.get("music_output", "")).strip(),
                "non_music_output": str(raw.get("non_music_output", "")).strip(),
            }
            if not all(job.values()):
                raise ValueError("AudioSep 일괄 작업의 질의와 출력 경로가 필요합니다.")
            job["music_output"] = str(Path(job["music_output"]).resolve())
            job["non_music_output"] = str(Path(job["non_music_output"]).resolve())
            jobs.append(job)
        return jobs

    query = args.query.strip()
    if not query:
        raise ValueError("AudioSep 음악 질의가 비어 있습니다.")
    if not args.music_output or not args.non_music_output:
        raise ValueError("AudioSep 음악/비음악 출력 경로가 필요합니다.")
    return [
        {
            "query": query,
            "music_output": str(Path(args.music_output).resolve()),
            "non_music_output": str(Path(args.non_music_output).resolve()),
        }
    ]


def main() -> int:
    args = parse_args()
    jobs = load_jobs(args)
    repo = Path(args.repo).resolve()
    runtime_root = Path(args.runtime_root).resolve()
    if not repo.is_dir():
        raise FileNotFoundError(f"AudioSep 폴더를 찾을 수 없습니다: {repo}")
    if not (runtime_root / "roberta-base" / "model.safetensors").is_file():
        raise FileNotFoundError("AudioSep의 RoBERTa safetensors를 찾을 수 없습니다.")
    model_path = require_file(args.model, "AudioSep 상태 사전")
    input_path = require_file(args.input, "입력 오디오")

    os.chdir(runtime_root)
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    ascii_runtime = Path(tempfile.gettempdir()) / "video-sound-separator-audiosep"
    numba_cache = ascii_runtime / "numba-cache"
    numba_cache.mkdir(parents=True, exist_ok=True)
    os.environ["NUMBA_CACHE_DIR"] = str(numba_cache)

    # Numba's cache creation is pathologically slow when librosa is imported
    # from this app's Korean installation path.  Import the identical package
    # from an ASCII-only temporary path while keeping all dependencies in the
    # portable runtime.
    site_packages = Path(sys.executable).parent / "lib" / "site-packages"
    librosa_source = site_packages / "librosa"
    librosa_copy = ascii_runtime / "librosa"
    if not librosa_source.is_dir():
        raise FileNotFoundError(f"librosa 패키지를 찾을 수 없습니다: {librosa_source}")
    source_version = (librosa_source / "version.py").read_bytes()
    marker = ascii_runtime / "librosa-version.py"
    if (
        not librosa_copy.is_dir()
        or not marker.is_file()
        or marker.read_bytes() != source_version
    ):
        if librosa_copy.exists():
            shutil.rmtree(librosa_copy)
        shutil.copytree(librosa_source, librosa_copy)
        marker.write_bytes(source_version)
    sys.path.insert(0, str(ascii_runtime))
    sys.path.insert(0, str(repo))

    import torch
    import torch.nn as nn
    import torch.nn.functional as functional
    import torchaudio
    import numpy as np
    import numba

    # Some librosa functions request Numba's on-disk cache while they are
    # imported. On this Windows installation the cache writability probe can
    # loop on PermissionError for many minutes. This process is short-lived, so
    # compile without writing those cache files.
    for decorator_name in ("jit", "njit", "vectorize", "guvectorize"):
        decorator = getattr(numba, decorator_name)

        def without_disk_cache(*items, _decorator=decorator, **options):
            options["cache"] = False
            return _decorator(*items, **options)

        setattr(numba, decorator_name, without_disk_cache)

    from torchlibrosa.stft import DFTBase

    # torchlibrosa 0.1.x builds the same 2048-point DFT matrices with millions
    # of scalar complex powers.  On this Windows runtime that can take over
    # 20 minutes.  FFT of the identity matrix is mathematically equivalent and
    # constructs both matrices in well under a second.
    DFTBase.dft_matrix = lambda _self, n: np.fft.fft(np.eye(n), axis=1)
    DFTBase.idft_matrix = lambda _self, n: np.fft.ifft(np.eye(n), axis=1) * n

    from models import base as audiosep_base

    audiosep_base.init_layer = lambda _layer: None
    audiosep_base.init_bn = lambda _layer: None

    from models.clap_encoder import CLAP_Encoder
    from models.resunet import ResUNet30

    class AudioSepInference(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            # Every parameter is replaced by the downloaded state dict. Skipping
            # random initialization cuts first-load time by several minutes.
            with skip_replaced_parameter_initialization(nn):
                print("[setup] AudioSep 분리망 구성 중", flush=True)
                self.ss_model = ResUNet30(
                    input_channels=1,
                    output_channels=1,
                    condition_size=512,
                )
                # The downloaded AudioSep state dict replaces every CLAP weight.
                # Avoid loading the separate 2.35 GB CLAP initialization checkpoint.
                print("[setup] AudioSep 텍스트 인코더 구성 중", flush=True)
                self.query_encoder = CLAP_Encoder(pretrained_path="").eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[setup] AudioSep 모델 준비 중 ({device})", flush=True)
    model = AudioSepInference()
    print("[setup] AudioSep 상태 사전 읽는 중", flush=True)
    state = torch.load(model_path, map_location="cpu", weights_only=True)
    print("[setup] AudioSep 상태 사전 적용 중", flush=True)
    incompatible = model.load_state_dict(state, strict=True, assign=True)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise RuntimeError(f"AudioSep 상태 사전 불일치: {incompatible}")
    print("[setup] AudioSep 모델을 실행 장치로 이동 중", flush=True)
    model = model.eval().to(device)

    reference, sample_rate = torchaudio.load(str(input_path))
    original_samples = reference.shape[-1]
    audio_32k = torchaudio.functional.resample(
        reference,
        orig_freq=sample_rate,
        new_freq=AUDIOSEP_SAMPLE_RATE,
    )
    minimum_samples = round(MINIMUM_CHUNK_SECONDS * AUDIOSEP_SAMPLE_RATE) + 1
    padded_samples = audio_32k.shape[-1]
    if padded_samples < minimum_samples:
        audio_32k = functional.pad(audio_32k, (0, minimum_samples - padded_samples))

    source_rms = float(reference.square().mean().sqrt())
    save_kwargs = {
        "sample_rate": sample_rate,
        "encoding": "PCM_S",
        "bits_per_sample": 24,
    }
    for index, job in enumerate(jobs, start=1):
        query = job["query"]
        music_output = Path(job["music_output"]).resolve()
        non_music_output = Path(job["non_music_output"]).resolve()
        music_output.parent.mkdir(parents=True, exist_ok=True)
        non_music_output.parent.mkdir(parents=True, exist_ok=True)
        print(
            f"[run {index}/{len(jobs)}] 텍스트 질의 '{query}'로 음악 분리 중",
            flush=True,
        )
        with torch.inference_mode():
            condition = model.query_encoder.get_query_embed(
                modality="text",
                text=[query],
                device=device,
            ).to(device)
            separated_channels = []
            for channel in audio_32k:
                input_dict = {
                    "mixture": channel[None, None, :].to(device),
                    "condition": condition,
                }
                separated = model.ss_model.chunk_inference(input_dict)
                separated_channels.append(
                    torch.from_numpy(separated[0, :padded_samples])
                )

        music_32k = torch.stack(separated_channels).to(dtype=reference.dtype)
        music = torchaudio.functional.resample(
            music_32k,
            orig_freq=AUDIOSEP_SAMPLE_RATE,
            new_freq=sample_rate,
        )
        if music.shape[-1] < original_samples:
            music = functional.pad(music, (0, original_samples - music.shape[-1]))
        music = music[:, :original_samples]
        non_music = reference - music
        music_rms = float(music.square().mean().sqrt())
        non_music_rms = float(non_music.square().mean().sqrt())
        metrics = {
            "query": query,
            "source_rms": source_rms,
            "music_rms_ratio": music_rms / source_rms if source_rms else 0.0,
            "non_music_rms_ratio": non_music_rms / source_rms if source_rms else 0.0,
            "music_source_correlation": centered_correlation(reference, music),
            "non_music_source_correlation": centered_correlation(reference, non_music),
            "reconstruction_source_correlation": centered_correlation(
                reference, music + non_music
            ),
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

from __future__ import annotations


def apply_stereo_consistent_mask(
    reference,
    estimated_music,
    estimated_non_music,
    sample_rate: int,
    *,
    model_band_limit: float | None = None,
):
    """Apply a model's soft music mask to the original stereo waveform.

    The model estimates only the separation decision. The returned waveforms
    use the original phase, channel layout, sample rate, and full duration.
    """
    import torch
    import torch.nn.functional as functional

    if reference.ndim != 2:
        raise ValueError(f"원본 오디오 모양이 올바르지 않습니다: {tuple(reference.shape)}")
    if estimated_music.ndim != 2 or estimated_non_music.ndim != 2:
        raise ValueError("분리 추정치는 [채널, 샘플] 모양이어야 합니다.")

    target_length = reference.shape[-1]
    for name, estimate in (
        ("음악", estimated_music),
        ("음악 아님", estimated_non_music),
    ):
        if estimate.shape[-1] != target_length:
            raise ValueError(
                f"{name} 추정 길이가 원본과 다릅니다: "
                f"{estimate.shape[-1]} != {target_length}"
            )
        if estimate.shape[0] not in (1, reference.shape[0]):
            raise ValueError(
                f"{name} 추정 채널 수를 원본에 적용할 수 없습니다: "
                f"{estimate.shape[0]}"
            )

    n_fft = 4096
    hop_length = 1024
    window = torch.hann_window(n_fft, device=reference.device, dtype=reference.dtype)

    def stft(waveform):
        return torch.stft(
            waveform,
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=n_fft,
            window=window,
            center=True,
            return_complex=True,
        )

    reference_spec = stft(reference)
    music_spec = stft(estimated_music)
    non_music_spec = stft(estimated_non_music)
    music_power = music_spec.abs().square()
    non_music_power = non_music_spec.abs().square()
    # One shared decision for every original channel prevents the stereo image
    # from wandering when the model gives slightly different left/right masks.
    if music_power.shape[0] > 1:
        music_power = music_power.mean(dim=0, keepdim=True)
        non_music_power = non_music_power.mean(dim=0, keepdim=True)
    denominator = music_power + non_music_power
    mask = torch.where(
        denominator > 1e-10,
        music_power / denominator.clamp_min(1e-10),
        torch.zeros_like(denominator),
    )

    # Smooth isolated time-frequency decisions to reduce musical noise and
    # rapid stereo image movement without blurring transient timing heavily.
    mask = functional.avg_pool2d(
        mask.unsqueeze(1), kernel_size=(3, 5), stride=1, padding=(1, 2)
    ).squeeze(1)

    if model_band_limit is not None:
        frequencies = torch.fft.rfftfreq(
            n_fft, d=1.0 / sample_rate, device=reference.device
        )
        fade_width = min(1000.0, model_band_limit * 0.25)
        fade_start = max(0.0, model_band_limit - fade_width)
        band_weight = ((model_band_limit - frequencies) / max(fade_width, 1.0)).clamp(0, 1)
        band_weight = torch.where(
            frequencies <= fade_start,
            torch.ones_like(band_weight),
            band_weight,
        )
        mask = mask * band_weight.view(1, -1, 1)

    if mask.shape[0] == 1 and reference_spec.shape[0] > 1:
        mask = mask.expand(reference_spec.shape[0], -1, -1)

    separated_music = torch.istft(
        reference_spec * mask,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=n_fft,
        window=window,
        center=True,
        length=target_length,
    )
    separated_non_music = reference - separated_music
    return separated_music, separated_non_music

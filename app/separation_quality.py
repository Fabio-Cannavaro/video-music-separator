from __future__ import annotations


def _validate_separation_inputs(reference, estimated_music, estimated_non_music):
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


def apply_stereo_consistent_mask(
    reference,
    estimated_music,
    estimated_non_music,
    sample_rate: int,
    *,
    model_band_limit: float | None = None,
    high_band_extension: float = 0.0,
):
    """Apply a model's soft music mask to the original stereo waveform.

    The model estimates only the separation decision. The returned waveforms
    use the original phase, channel layout, sample rate, and full duration.
    """
    import torch
    import torch.nn.functional as functional

    if not 0.0 <= high_band_extension <= 1.0:
        raise ValueError("고역 확장 강도는 0 이상 1 이하여야 합니다.")

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
        limited_mask = mask * band_weight.view(1, -1, 1)
        if high_band_extension:
            # A 16 kHz model cannot directly estimate content above 8 kHz.
            # Reuse only the time envelope from its upper reliable band and
            # keep the optional extension deliberately weak. This can catch
            # cymbal/air energy, but may also affect speech sibilance.
            guide_bins = (frequencies >= model_band_limit * 0.70) & (
                frequencies <= model_band_limit * 0.875
            )
            if bool(guide_bins.any()):
                high_envelope = mask[:, guide_bins, :].mean(dim=1, keepdim=True)
                nyquist = sample_rate / 2
                high_curve = ((frequencies - fade_start) / max(fade_width, 1.0)).clamp(
                    0, 1
                )
                if nyquist > model_band_limit:
                    decay = 1.0 - 0.5 * (
                        (frequencies - model_band_limit)
                        / (nyquist - model_band_limit)
                    ).clamp(0, 1)
                    high_curve = high_curve * decay
                extension = (
                    high_envelope
                    * high_curve.view(1, -1, 1)
                    * high_band_extension
                )
                limited_mask = torch.maximum(limited_mask, extension)
        mask = limited_mask

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


def apply_raw_anchored_hybrid(
    reference,
    estimated_music,
    estimated_non_music,
    sample_rate: int,
    *,
    model_band_limit: float = 8000.0,
    high_band_strength: float = 0.35,
):
    """Spatialize raw AV-CASS Music and restore a conservative high band.

    Unlike :func:`apply_stereo_consistent_mask`, this does not use the model
    stems to make a time-frequency mask for the original signal.  The raw Music
    spectrum remains the low/mid-band anchor.  A slowly varying, regularized
    transfer function measured from the original stereo mid signal restores
    channel placement.  Above the model band, only a small amount of original
    high-frequency signal is admitted by a broadband Music activity envelope.

    This is intentionally an experimental comparison algorithm.  Its
    complement is always computed from the reference so the pair reconstructs
    the input exactly apart from floating-point rounding.
    """
    import torch
    import torch.nn.functional as functional

    if sample_rate <= 0:
        raise ValueError("샘플레이트는 0보다 커야 합니다.")
    if not 0.0 <= high_band_strength <= 1.0:
        raise ValueError("하이브리드 고역 복원 강도는 0 이상 1 이하여야 합니다.")
    if not 0.0 < model_band_limit <= sample_rate / 2:
        raise ValueError("모델 대역 상한은 0보다 크고 나이퀴스트 주파수 이하여야 합니다.")

    _validate_separation_inputs(reference, estimated_music, estimated_non_music)
    target_length = reference.shape[-1]
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

    def smooth_2d(tensor, kernel=(9, 17)):
        padding = (kernel[0] // 2, kernel[1] // 2)
        return functional.avg_pool2d(
            tensor.unsqueeze(1), kernel_size=kernel, stride=1, padding=padding
        ).squeeze(1)

    reference_spec = stft(reference)
    music_spec = stft(estimated_music).mean(dim=0, keepdim=True)
    non_music_spec = stft(estimated_non_music).mean(dim=0, keepdim=True)
    reference_mid = reference_spec.mean(dim=0, keepdim=True)

    # Estimate a deliberately slow stereo transfer from the original mid to
    # each original channel.  Smoothing and ridge regularization prevent the
    # raw Music stem from inheriting rapid speech/SFX-driven spatial movement.
    cross = reference_spec * reference_mid.conj()
    cross = torch.complex(smooth_2d(cross.real), smooth_2d(cross.imag))
    mid_power = smooth_2d(reference_mid.abs().square())
    ridge = mid_power.mean(dim=(-2, -1), keepdim=True).clamp_min(1e-10) * 1e-3
    transfer = cross / (mid_power + ridge)
    transfer_magnitude = transfer.abs()
    transfer = transfer / transfer_magnitude.clamp_min(1e-8)
    transfer = transfer * transfer_magnitude.clamp(0.0, 2.5)

    frequencies = torch.fft.rfftfreq(
        n_fft, d=1.0 / sample_rate, device=reference.device
    )
    transition_width = min(1000.0, model_band_limit * 0.25)
    transition_start = max(0.0, model_band_limit - transition_width)
    raw_band_weight = (
        (model_band_limit - frequencies) / max(transition_width, 1.0)
    ).clamp(0.0, 1.0)
    raw_band_weight = torch.where(
        frequencies <= transition_start,
        torch.ones_like(raw_band_weight),
        raw_band_weight,
    ).view(1, -1, 1)
    spatialized_raw = music_spec * transfer * raw_band_weight

    # The 16 kHz model cannot describe content above 8 kHz.  Use only a slow
    # broadband activity decision there; this avoids turning the raw stems into
    # the same per-bin Wiener mask used by the current algorithm.
    activity_bins = (frequencies >= 150.0) & (
        frequencies <= min(6500.0, transition_start)
    )
    if bool(activity_bins.any()) and high_band_strength:
        music_energy = music_spec[:, activity_bins, :].abs().square().mean(dim=1)
        non_music_energy = (
            non_music_spec[:, activity_bins, :].abs().square().mean(dim=1)
        )
        activity = music_energy / (music_energy + non_music_energy + 1e-10)
        activity = functional.avg_pool1d(
            activity.unsqueeze(1), kernel_size=25, stride=1, padding=12
        ).squeeze(1)
        activity = activity.square().clamp(0.0, 1.0).view(1, 1, -1)
        high_band_weight = (1.0 - raw_band_weight) * high_band_strength
        restored_high_band = reference_spec * activity * high_band_weight
    else:
        restored_high_band = torch.zeros_like(reference_spec)

    hybrid_spec = spatialized_raw + restored_high_band
    hybrid_music = torch.istft(
        hybrid_spec,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=n_fft,
        window=window,
        center=True,
        length=target_length,
    )
    hybrid_non_music = reference - hybrid_music
    return hybrid_music, hybrid_non_music

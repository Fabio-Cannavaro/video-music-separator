from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from separation_quality import apply_raw_anchored_hybrid


class RawAnchoredHybridTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_rate = 48000
        sample_count = 12000
        time = torch.arange(sample_count, dtype=torch.float32) / self.sample_rate
        raw_music = 0.18 * torch.sin(2 * torch.pi * 440 * time)
        non_music = 0.08 * torch.sin(2 * torch.pi * 1200 * time)
        high_music = 0.03 * torch.sin(2 * torch.pi * 10000 * time)
        self.reference = torch.stack(
            (
                raw_music * 1.35 + non_music + high_music,
                raw_music * 0.65 + non_music + high_music * 0.6,
            )
        )
        self.estimated_music = raw_music.unsqueeze(0)
        self.estimated_non_music = non_music.unsqueeze(0)

    def test_reconstructs_reference_and_restores_stereo_shape(self) -> None:
        music, non_music = apply_raw_anchored_hybrid(
            self.reference,
            self.estimated_music,
            self.estimated_non_music,
            self.sample_rate,
        )

        self.assertEqual(music.shape, self.reference.shape)
        self.assertTrue(torch.isfinite(music).all())
        self.assertTrue(torch.allclose(music + non_music, self.reference, atol=1e-6))
        self.assertGreater(float((music[0] - music[1]).abs().mean()), 1e-4)

    def test_high_band_strength_changes_only_experimental_result(self) -> None:
        without_high, _ = apply_raw_anchored_hybrid(
            self.reference,
            self.estimated_music,
            self.estimated_non_music,
            self.sample_rate,
            high_band_strength=0.0,
        )
        with_high, _ = apply_raw_anchored_hybrid(
            self.reference,
            self.estimated_music,
            self.estimated_non_music,
            self.sample_rate,
            high_band_strength=0.5,
        )

        frequencies = torch.fft.rfftfreq(
            without_high.shape[-1], d=1.0 / self.sample_rate
        )
        without_power = torch.fft.rfft(without_high).abs().square()
        with_power = torch.fft.rfft(with_high).abs().square()
        self.assertGreater(
            float(with_power[:, frequencies > 8000].sum()),
            float(without_power[:, frequencies > 8000].sum()),
        )

    def test_rejects_invalid_high_band_strength(self) -> None:
        with self.assertRaises(ValueError):
            apply_raw_anchored_hybrid(
                self.reference,
                self.estimated_music,
                self.estimated_non_music,
                self.sample_rate,
                high_band_strength=1.1,
            )


if __name__ == "__main__":
    unittest.main()

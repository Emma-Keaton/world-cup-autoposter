"""Audio analysis utilities for audio-reactive effects.

Uses librosa (already a project dependency) to extract:
- RMS energy envelope (volume over time)
- Spectral centroid (brightness)
- Onset times (beat/transient detection)
- Low-frequency energy (bass for shake effects)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class AudioAnalysis:
    """Pre-computed audio features for a clip."""

    duration: float
    sample_rate: int = 22050
    # RMS energy per frame (normalised 0–1)
    rms_envelope: List[float] = field(default_factory=list)
    # Spectral centroid per frame (Hz, normalised 0–1)
    spectral_centroid: List[float] = field(default_factory=list)
    # Onset frame indices
    onsets: List[int] = field(default_factory=list)
    # Bass energy per frame (0–200 Hz, normalised 0–1)
    bass_envelope: List[float] = field(default_factory=list)
    # Frames per second the analysis was computed at
    analysis_fps: float = 30.0

    def rms_at_time(self, t: float) -> float:
        """Get RMS energy at a specific time (seconds)."""
        idx = int(t * self.analysis_fps)
        idx = min(max(idx, 0), len(self.rms_envelope) - 1)
        return self.rms_envelope[idx] if self.rms_envelope else 0.0

    def bass_at_time(self, t: float) -> float:
        idx = int(t * self.analysis_fps)
        idx = min(max(idx, 0), len(self.bass_envelope) - 1)
        return self.bass_envelope[idx] if self.bass_envelope else 0.0

    def is_onset_near(self, t: float, window: float = 0.05) -> bool:
        """Check if an onset occurs within *window* seconds of *t*."""
        frame = int(t * self.analysis_fps)
        for onset_frame in self.onsets:
            if abs(onset_frame - frame) <= int(window * self.analysis_fps):
                return True
        return False


def analyze_audio(
    audio_path: str,
    analysis_fps: float = 30.0,
) -> AudioAnalysis:
    """Analyze an audio file and return AudioAnalysis with per-frame features."""
    import librosa

    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = len(y) / sr

    hop_length = int(sr / analysis_fps)

    # RMS energy
    rms = librosa.feature.rms(y=y, frame_length=hop_length * 2, hop_length=hop_length)[0]
    rms_norm = _normalize(rms)

    # Spectral centroid
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    centroid_norm = _normalize(centroid)

    # Onset detection
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
    onset_frames = onset_frames.tolist()

    # Bass energy (0–200 Hz)
    S = np.abs(librosa.stft(y, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr)
    bass_mask = freqs <= 200
    bass_energy = np.sum(S[bass_mask, :], axis=0)
    # Align length with rms
    min_len = min(len(bass_energy), len(rms_norm))
    bass_norm = _normalize(bass_energy[:min_len])
    # Pad to match rms length
    if len(bass_norm) < len(rms_norm):
        bass_norm = np.pad(bass_norm, (0, len(rms_norm) - len(bass_norm)))

    # Ensure all arrays same length
    length = min(len(rms_norm), len(centroid_norm), len(bass_norm))

    return AudioAnalysis(
        duration=duration,
        sample_rate=sr,
        rms_envelope=rms_norm[:length].tolist(),
        spectral_centroid=centroid_norm[:length].tolist(),
        onsets=onset_frames,
        bass_envelope=bass_norm[:length].tolist(),
        analysis_fps=analysis_fps,
    )


def _normalize(arr: np.ndarray) -> np.ndarray:
    """Normalize array to 0–1 range."""
    arr = np.asarray(arr, dtype=np.float64)
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-8:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


def smooth_envelope(
    values: List[float],
    smoothing: float = 0.3,
) -> List[float]:
    """Exponential moving average smoothing (React Spring velocity-preservation pattern).

    smoothing=0 → no smoothing, smoothing=0.8 → heavy smoothing.
    """
    result = []
    prev = 0.0
    for v in values:
        prev = smoothing * prev + (1 - smoothing) * v
        result.append(prev)
    return result

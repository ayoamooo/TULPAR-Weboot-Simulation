"""Shared MFCC summary extraction for the offline dataset baseline and voice pipeline."""

from __future__ import annotations

import io
import math


RATE = 16_000
N_FFT = 512
FRAME = 400
HOP = 160
MELS = 40
MFCCS = 13


def mfcc_summary(audio_bytes: bytes, *, target_seconds: float | None) -> "object":
    """Decode audio, resample to 16 kHz mono, then return MFCC means and deviations."""
    import numpy as np
    import scipy
    import scipy.fft
    import scipy.signal
    import soundfile as sf

    signal, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
    signal = signal.mean(axis=1)
    if sample_rate != RATE:
        divisor = math.gcd(int(sample_rate), RATE)
        signal = scipy.signal.resample_poly(signal, RATE // divisor, int(sample_rate) // divisor).astype(np.float32)
    if target_seconds is not None:
        length = int(RATE * target_seconds)
        signal = signal[:length]
        if len(signal) < length:
            signal = np.pad(signal, (0, length - len(signal)))
    if len(signal) == 0:
        raise ValueError("empty audio")

    hz = np.linspace(0, RATE / 2, N_FFT // 2 + 1)
    mel = 2595.0 * np.log10(1.0 + hz / 700.0)
    points = np.linspace(mel[0], mel[-1], MELS + 2)
    bank = np.zeros((MELS, len(hz)), dtype=np.float32)
    for index in range(MELS):
        left, centre, right = points[index : index + 3]
        bank[index] = np.maximum(
            0,
            np.minimum((mel - left) / (centre - left), (right - mel) / (right - centre)),
        )

    padded = np.pad(signal, (N_FFT // 2, N_FFT // 2))
    frames = np.lib.stride_tricks.sliding_window_view(padded, FRAME)[::HOP]
    window = np.hanning(FRAME).astype(np.float32)
    spectrum = np.fft.rfft(frames * window, n=N_FFT, axis=1)
    power = (spectrum.real**2 + spectrum.imag**2).astype(np.float32)
    mel_energy = np.maximum(power @ bank.T, 1e-10)
    coefficients = scipy.fft.dct(np.log(mel_energy), type=2, norm="ortho", axis=1)[:, :MFCCS]
    return np.concatenate([coefficients.mean(axis=0), coefficients.std(axis=0)]).astype(np.float32)


def pcm16_mono_to_wav(pcm: bytes, sample_rate: int = RATE) -> bytes:
    """Wrap transient microphone PCM in a WAV header for the common feature extractor."""
    if not pcm:
        raise ValueError("empty audio")
    import numpy as np
    import soundfile as sf

    buffer = io.BytesIO()
    samples = np.frombuffer(pcm, dtype="<i2")
    if samples.size == 0:
        raise ValueError("empty audio")
    sf.write(buffer, samples, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()

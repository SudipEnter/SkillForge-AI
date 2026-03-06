"""SkillForge AI — Audio Utilities for Nova 2 Sonic processing."""

import io
import struct
from typing import Optional

import numpy as np


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Convert raw PCM audio bytes to WAV format."""
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_bytes)

    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    return wav_header + pcm_bytes


def normalize_audio(pcm_bytes: bytes) -> bytes:
    """Normalize PCM audio to prevent clipping."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    max_val = np.abs(samples).max()
    if max_val > 0:
        samples = samples * (32767.0 / max_val) * 0.9
    return samples.astype(np.int16).tobytes()


def chunk_audio(pcm_bytes: bytes, chunk_size: int = 32768) -> list[bytes]:
    """Split audio into fixed-size chunks for streaming."""
    return [pcm_bytes[i:i + chunk_size] for i in range(0, len(pcm_bytes), chunk_size)]


def detect_silence(
    pcm_bytes: bytes,
    threshold: int = 500,
    min_silence_ms: int = 1500,
    sample_rate: int = 16000,
) -> bool:
    """Detect if an audio segment is silent (end-of-speech detection)."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    silence_samples = int(sample_rate * min_silence_ms / 1000)
    return bool(np.abs(samples[-silence_samples:]).mean() < threshold)


def resample_audio(
    pcm_bytes: bytes,
    source_rate: int,
    target_rate: int,
) -> bytes:
    """Resample PCM audio from source to target sample rate."""
    if source_rate == target_rate:
        return pcm_bytes

    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float64)
    ratio = target_rate / source_rate
    new_length = int(len(samples) * ratio)

    indices = np.linspace(0, len(samples) - 1, new_length)
    resampled = np.interp(indices, np.arange(len(samples)), samples)
    return resampled.astype(np.int16).tobytes()
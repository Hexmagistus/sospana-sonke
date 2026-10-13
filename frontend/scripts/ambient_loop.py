"""Original ambient loop for Sospana Sonke.

Synthesised from scratch (sine, a falling log-drum pitch, and noise).
No samples, no third-party recording, and no copied melody. The
composition and this recording are dedicated to the public domain
under CC0 1.0.
"""
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 22050
BPM = 112
BEAT = 60.0 / BPM
BARS = 8
ROOT = Path(__file__).resolve().parents[1] / "public" / "audio"


def place(buf, start, sig):
    i0 = int(start * SR)
    i1 = min(buf.size, i0 + sig.size)
    if i1 <= i0:
        return
    buf[i0:i1] += sig[: i1 - i0]


def log_drum(f0, f1, dur, vel):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    freq = f1 + (f0 - f1) * np.exp(-12.0 * t)
    phase = np.cumsum(freq) * (2 * np.pi / SR)
    y = np.sin(phase) + 0.22 * np.sin(2 * phase) * np.exp(-18 * t)
    y *= np.exp(-3.4 * t)
    y[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    peak = np.max(np.abs(y)) + 1e-9
    return (vel * y / peak).astype(np.float64)


def shaker(dur, vel, seed):
    n = max(1, int(SR * dur))
    rng = np.random.default_rng(seed)
    y = np.diff(rng.normal(0, 1, n + 1))
    t = np.arange(n) / SR
    y *= np.exp(-36 * t)
    peak = np.max(np.abs(y)) + 1e-9
    return vel * y / peak


def pad_note(freq, dur, vel):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t)
    y += 0.35 * np.sin(2 * np.pi * freq * 2 * t + 0.4)
    attack = int(0.18 * SR)
    release = int(0.22 * SR)
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] *= np.linspace(1, 0, release)
    y *= env * np.exp(-0.35 * t)
    peak = np.max(np.abs(y)) + 1e-9
    return vel * y / peak


def bass(freq, dur, vel):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(2 * np.pi * freq * 2 * t)
    y *= np.exp(-2.1 * t)
    y[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
    peak = np.max(np.abs(y)) + 1e-9
    return vel * y / peak


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def main():
    total = BARS * 4 * BEAT
    buf = np.zeros(int(SR * total) + 8, dtype=np.float64)
    # Two-bar chords, original voicings: Am9, Dm9, Em11, Am9.
    chords = [
        (57, 60, 64, 67, 71),
        (50, 53, 57, 60, 64),
        (52, 55, 59, 62, 65),
        (57, 60, 64, 67, 71),
    ]
    roots = [45, 38, 40, 45]
    for bar in range(BARS):
        origin = bar * 4 * BEAT
        chord = chords[(bar // 2) % len(chords)]
        for note in chord:
            place(buf, origin, pad_note(midi_hz(note), 2 * 4 * BEAT * 0.5, 0.045))
        place(buf, origin, bass(midi_hz(roots[bar // 2]), BEAT * 0.9, 0.22))
        place(buf, origin + 2 * BEAT, bass(midi_hz(roots[bar // 2] + 7), BEAT * 0.7, 0.12))
        # Log drum: downbeat, then three off-beats. The last sixteenth rests.
        place(buf, origin, log_drum(148, 52, 0.42, 0.34))
        place(buf, origin + 1.5 * BEAT, log_drum(168, 58, 0.28, 0.16))
        place(buf, origin + 2.5 * BEAT, log_drum(140, 48, 0.36, 0.22))
        place(buf, origin + 3.25 * BEAT, log_drum(180, 64, 0.18, 0.08))
        for step in range(8):
            place(buf, origin + step * (BEAT / 2), shaker(0.05, 0.035, 20261013 + bar * 16 + step))

    fade = int(0.08 * SR)
    ramp = np.linspace(0, 1, fade)
    body = buf[:-fade].copy()
    body[:fade] = body[:fade] * ramp + buf[-fade:] * (1 - ramp)
    peak = np.max(np.abs(body)) + 1e-9
    body = (0.85 * body / peak).astype(np.float32)

    wav_path = Path(tempfile.gettempdir()) / "sospana-ambient-source.wav"
    pcm = (np.clip(body, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(wav_path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())
    print(f"wrote {wav_path} samples={pcm.size} seconds={pcm.size / SR:.2f}")


if __name__ == "__main__":
    main()

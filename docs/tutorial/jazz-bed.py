"""Original background jazz bed for the Sospana Sonke tutorial.

Synthesised from scratch (sine, harmonics, and noise). No samples,
no third-party recording, and no copied melody. The composition and
this recording are dedicated to the public domain under CC0 1.0.
"""
import sys
import wave
import numpy as np

SR = 44100
BPM = 92
BEAT = 60.0 / BPM
BARS = 16  # one loop
# Swing: long eighth then short eighth.
SWING = 0.66


def midi_to_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a=0.012, d=0.08, s=0.55, r=0.12):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.ones(n)
    a_n = min(n, int(a * SR))
    if a_n:
        e[:a_n] = np.linspace(0, 1, a_n)
    d_n = min(n - a_n, int(d * SR))
    if d_n:
        e[a_n:a_n + d_n] = np.linspace(1, s, d_n)
    r_n = min(n, int(r * SR))
    if r_n and dur > r:
        e[-r_n:] *= np.linspace(1, 0, r_n)
    return e


def tone(freq, dur, vel=0.2, harmonics=(1.0, 0.45, 0.22, 0.1, 0.04), decay=2.4):
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    y = np.zeros(n)
    for i, h in enumerate(harmonics, start=1):
        y += h * np.sin(2 * np.pi * freq * i * t + 0.15 * i)
    y *= np.exp(-decay * t)
    y *= env_adsr(n, a=0.008, d=0.05, s=0.7, r=min(0.18, dur * 0.4))
    peak = np.max(np.abs(y)) + 1e-9
    return vel * y / peak


def noise_tick(dur, vel):
    n = max(1, int(SR * dur))
    y = np.random.default_rng(7).normal(0, 1, n)
    # High-pass-ish by differencing, then a fast decay.
    y = np.diff(y, prepend=0)
    t = np.arange(n) / SR
    y *= np.exp(-28 * t)
    peak = np.max(np.abs(y)) + 1e-9
    return vel * y / peak


def place(buf, start, sig, pan=0.0):
    """pan -1 left, +1 right. buf is (2, N)."""
    if sig.size == 0:
        return
    i0 = int(start * SR)
    i1 = min(buf.shape[1], i0 + sig.size)
    if i1 <= i0:
        return
    chunk = sig[: i1 - i0]
    left = np.sqrt(0.5 * (1 - pan))
    right = np.sqrt(0.5 * (1 + pan))
    buf[0, i0:i1] += left * chunk
    buf[1, i0:i1] += right * chunk


def main():
    total = BARS * 4 * BEAT
    buf = np.zeros((2, int(SR * total) + SR), dtype=np.float64)
    rng = np.random.default_rng(20261009)

    # 16 bars, two-bar chords. A plain jazz turnaround, not a copied tune.
    # Cmaj7 Am7 | Dm7 G7 | Em7 A7 | Dm7 G7 | and repeat.
    chords = [
        (60, 64, 67, 71),  # Cmaj7
        (57, 60, 64, 67),  # Am7
        (50, 53, 57, 60),  # Dm7
        (55, 59, 62, 65),  # G7
        (52, 55, 59, 62),  # Em7
        (57, 61, 64, 67),  # A7
        (50, 53, 57, 60),  # Dm7
        (55, 59, 62, 65),  # G7
    ]
    bass_roots = [48, 45, 50, 43, 40, 45, 50, 43]

    # Original pentatonic fragments, one note per bar, rests included.
    melody = [76, 0, 74, 72, 0, 79, 76, 0, 72, 74, 0, 71, 72, 0, 67, 0]

    for bar in range(BARS):
        chord = chords[bar % len(chords)]
        root = bass_roots[bar % len(bass_roots)]
        bar_t = bar * 4 * BEAT

        # Piano comp on beats 2 and 4, plus a light pickup.
        for beat_i, vel in ((1, 0.11), (3, 0.13)):
            when = bar_t + beat_i * BEAT
            for note in chord:
                place(buf, when, tone(midi_to_hz(note), BEAT * 0.92, vel=vel, decay=3.2), pan=0.15)
        # Soft shell on the downbeat, quieter.
        for note in chord[1:]:
            place(buf, bar_t, tone(midi_to_hz(note), BEAT * 1.4, vel=0.05, decay=2.2), pan=0.05)

        # Walking bass: root, fifth, root, leading tone toward the next root.
        nxt = bass_roots[(bar + 1) % len(bass_roots)]
        walk = [root, root + 7, root + 12, nxt - 1 if nxt > root else root + 10]
        for i, note in enumerate(walk):
            place(
                buf,
                bar_t + i * BEAT,
                tone(midi_to_hz(note), BEAT * 0.92, vel=0.22, harmonics=(1, 0.35, 0.08), decay=4.5),
                pan=-0.25,
            )

        # Brushes: swung eighths, accents on 2 and 4.
        for beat_i in range(4):
            long = BEAT * SWING
            short = BEAT * (1 - SWING)
            for k, off in enumerate((0.0, long)):
                accent = 0.045 if (beat_i in (1, 3) and k == 0) else 0.022
                place(buf, bar_t + beat_i * BEAT + off, noise_tick(0.06, accent), pan=0.45)

        # Soft kick on 1.
        place(buf, bar_t, tone(55, 0.12, vel=0.12, harmonics=(1, 0.2), decay=18), pan=0.0)

        # Sparse melody.
        m = melody[bar]
        if m:
            when = bar_t + BEAT * (0.15 if bar % 2 == 0 else SWING)
            place(
                buf,
                when,
                tone(midi_to_hz(m), BEAT * 1.6, vel=0.09, harmonics=(1, 0.25, 0.08), decay=1.8),
                pan=0.2,
            )

    # Gentle room: a short delayed copy.
    delay = int(0.045 * SR)
    wet = np.zeros_like(buf)
    wet[:, delay:] = 0.18 * buf[:, :-delay]
    buf += wet

    # Fade the loop edges so repeats do not click.
    fade = int(0.04 * SR)
    ramp = np.linspace(0, 1, fade)
    buf[:, :fade] *= ramp
    buf[:, -fade:] *= ramp[::-1]

    peak = np.max(np.abs(buf)) + 1e-9
    buf *= 0.55 / peak

    pcm = np.clip(buf, -1, 1)
    interleaved = np.empty(pcm.shape[1] * 2, dtype=np.int16)
    interleaved[0::2] = (pcm[0] * 32767).astype(np.int16)
    interleaved[1::2] = (pcm[1] * 32767).astype(np.int16)

    path = sys.argv[1] if len(sys.argv) > 1 else "jazz-bed.wav"
    with wave.open(path, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(interleaved.tobytes())
    print(path, "seconds", round(pcm.shape[1] / SR, 2))


if __name__ == "__main__":
    main()

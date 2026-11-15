"""Synthesises the noir music stems and rain ambience (original work, no third-party audio).

Run from the worktree root: tools/.venv/bin/python wings/noir/audio_src/gen_audio.py
Writes wings/noir/audio/*.ogg through ffmpeg (libvorbis).

Every loop is exactly L seconds. Partials sit on a 1/L Hz grid and events wrap modulo the loop,
so each file closes seamlessly and the stems stay in sync.
"""
import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 44100
L = 32.0
N = int(SR * L)
T = np.arange(N) / SR
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "audio")


def grid(f):
    return round(f * L) / L


def tri_weights(n_chords):
    # Piecewise-linear partition of unity over the loop: chord i is strongest at its slot.
    x = (T / L) * n_chords
    w = []
    for i in range(n_chords):
        d = np.abs(((x - i) + n_chords / 2.0) % n_chords - n_chords / 2.0)
        w.append(np.clip(1.0 - d, 0.0, 1.0))
    return w


CHORDS = [
    [110.0, 130.81, 164.81, 196.0, 246.94],   # Am
    [87.31, 110.0, 130.81, 164.81],           # Fmaj7
    [73.42, 110.0, 130.81, 174.61],           # Dm7
    [82.41, 103.83, 123.47, 146.83],          # E7
]
MELODY = [
    [440.0, 329.63, 523.25, 392.0],
    [349.23, 523.25, 440.0, 329.63],
    [293.66, 440.0, 349.23, 261.63],
    [329.63, 415.3, 493.88, 293.66],
]


def bed():
    out = np.zeros(N)
    for w, notes in zip(tri_weights(len(CHORDS)), CHORDS):
        pad = np.zeros(N)
        for f in notes:
            ff = grid(f)
            pad += 0.9 * np.sin(2 * np.pi * ff * T) + 0.25 * np.sin(2 * np.pi * 2 * ff * T)
        out += w * pad / len(notes)
    drone = 0.35 * np.sin(2 * np.pi * grid(55.0) * T)
    return out * 0.5 + drone * 0.6


def add_event(buf, start, dur, fn):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    idx = (int(round(start * SR)) + np.arange(n)) % N
    buf[idx] += fn(tt)


def pulse():
    buf = np.zeros(N)
    rng = np.random.default_rng(7)
    for k in range(40):  # heartbeat clicks every 0.8 s
        add_event(buf, k * 0.8, 0.12, lambda tt: 0.7 * np.exp(-tt / 0.012) * (np.sin(2 * np.pi * 180 * tt) + 0.5 * rng.standard_normal(len(tt))))
    for k in range(10):  # slow thump every 3.2 s
        add_event(buf, k * 3.2, 0.5, lambda tt: 0.9 * np.exp(-tt / 0.14) * np.sin(2 * np.pi * (60 - 20 * np.minimum(tt, 0.3) / 0.3) * tt))
    for k in range(80):  # brushed off-beat hats every 0.4 s
        add_event(buf, k * 0.4 + 0.4, 0.05, lambda tt: 0.18 * np.exp(-tt / 0.02) * rng.standard_normal(len(tt)))
    return buf


def strings():
    out = np.zeros(N)
    for w, notes in zip(tri_weights(len(CHORDS)), CHORDS):
        pad = np.zeros(N)
        vib = 1.0 + 0.004 * np.sin(2 * np.pi * grid(5.0) * T)
        for f in notes:
            ff = grid(f * 2.0)
            for h in range(1, 7):
                pad += (1.0 / h) * np.sin(2 * np.pi * h * ff * vib * T)
        out += w * pad / len(notes) * 0.12
    buf = np.zeros(N)
    for c, mel in enumerate(MELODY):
        for j, f in enumerate(mel):
            start = c * 8.0 + j * 2.0
            ff = grid(f)
            add_event(buf, start, 1.8, lambda tt, ff=ff: 0.5 * np.exp(-tt / 0.7) * (np.sin(2 * np.pi * ff * tt) + 0.2 * np.sin(4 * np.pi * ff * tt)))
    return out + buf


def rain():
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(N)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(N, 1.0 / SR)
    mask = np.where((freqs > 1800) & (freqs < 9000), 1.0 / np.maximum(freqs / 1800.0, 1.0), 0.0)
    hiss = np.fft.irfft(spec * mask, N)
    hiss = hiss / (np.max(np.abs(hiss)) + 1e-9)
    buf = 0.25 * hiss
    for _ in range(420):  # droplets
        s = rng.uniform(0, L)
        amp = rng.uniform(0.05, 0.2)
        add_event(buf, s, 0.02, lambda tt, amp=amp: amp * np.exp(-tt / 0.004) * rng.standard_normal(len(tt)))
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * grid(0.125) * T)
    buf += 0.12 * np.sin(2 * np.pi * grid(55.0) * T) * swell
    return buf


def normalise(x, peak=0.7):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def write_ogg(name, x):
    os.makedirs(OUT, exist_ok=True)
    ogg = os.path.join(OUT, name + ".ogg")
    with tempfile.TemporaryDirectory() as d:
        wav_path = os.path.join(d, name + ".wav")
        pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
        with wave.open(wav_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["/opt/homebrew/bin/oggenc", "-q", "4", "-o", ogg, wav_path], check=True)
    print("wrote", ogg, os.path.getsize(ogg), "bytes")


if __name__ == "__main__":
    write_ogg("noir_bed", normalise(bed(), 0.55))
    write_ogg("noir_pulse", normalise(pulse(), 0.6))
    write_ogg("noir_strings", normalise(strings(), 0.5))
    write_ogg("noir_rain", normalise(rain(), 0.5))

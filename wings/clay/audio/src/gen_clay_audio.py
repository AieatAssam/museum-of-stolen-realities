"""Synthesise the clay wing sound set into wings/clay/audio/*.ogg (needs numpy, scipy, oggenc).
Everything is synthesised here, so no third-party audio is in this wing. Deterministic (seeded).

  tools/.venv/bin/python wings/clay/audio/src/gen_clay_audio.py
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from scipy import signal

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
rng = np.random.default_rng(88)


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def noise(sec):
    return rng.standard_normal(int(sec * SR))


def lowpass(x, hz):
    b, a = signal.butter(2, hz / (SR / 2), "low")
    return signal.lpfilter(x) if False else signal.lfilter(b, a, x)


def bandpass(x, lo, hi):
    b, a = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / max(attack, 1e-4))) * np.exp(-t / max(decay, 1e-4))


def norm(x, peak=0.85):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def loopify(x, xfade=1.0):
    n = int(xfade * SR)
    fade = np.linspace(0, 1, n)
    x = x.copy()
    x[:n] = x[:n] * fade + x[-n:] * (1 - fade)
    return x[:-n]


def pull():
    # wet clay tearing up: a short low squelch with a rising tail
    n = int(0.45 * SR)
    x = bandpass(noise(0.45), 180, 900) * env(n, 0.02, 0.18)
    tone = np.sin(2 * np.pi * np.linspace(90, 160, n) * t_axis(0.45)) * env(n, 0.05, 0.25)
    return norm(0.8 * x + 0.3 * tone)


def press():
    # a thick, low thump with a soft slap
    n = int(0.35 * SR)
    x = np.sin(2 * np.pi * (70 - 30 * t_axis(0.35)) * t_axis(0.35)) * env(n, 0.005, 0.10)
    slap = bandpass(noise(0.35), 400, 1800) * env(n, 0.002, 0.03)
    return norm(0.9 * x + 0.35 * slap)


def step(i):
    # a soft footfall in clay: thud plus grit, slightly different each time
    n = int(0.22 * SR)
    f = 95 + 14 * i
    thud = np.sin(2 * np.pi * f * t_axis(0.22)) * env(n, 0.004, 0.06)
    grit = bandpass(noise(0.22), 900, 3200) * env(n, 0.002, 0.02) * 0.4
    return norm(0.9 * thud + grit, 0.7)


def reveal():
    # the stinger for the stop: a falling chord into silence
    dur = 3.6
    n = int(dur * SR)
    t = t_axis(dur)
    chord = sum(np.sin(2 * np.pi * f * t) for f in (146.8, 174.6, 220.0, 293.7)) / 4
    swell = np.clip(t / 1.2, 0, 1) * np.exp(-np.clip(t - 1.2, 0, None) / 0.9)
    tail = np.sin(2 * np.pi * (330 * np.exp(-t * 0.6)) * t) * np.exp(-t / 1.4) * 0.35
    shimmer = bandpass(noise(dur), 2500, 6000) * np.exp(-t / 0.6) * 0.08
    x = chord * swell * 0.6 + tail + shimmer
    return norm(x[:n])


def bed(freqs, sec, seed_off):
    t = t_axis(sec)
    x = np.zeros_like(t)
    for k, f in enumerate(freqs):
        vib = 1 + 0.002 * np.sin(2 * np.pi * (0.18 + 0.03 * k) * t + k)
        x += np.sin(2 * np.pi * f * vib * t) * (0.5 / (k + 1))
    x += 0.04 * bandpass(noise(sec), 300, 900)
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.08 * t + seed_off)
    return loopify(norm(x, 0.5), 1.5)


def wind():
    x = lowpass(noise(12.0), 500) * 0.6 + bandpass(noise(12.0), 800, 1600) * 0.04
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t_axis(12.0))
    return loopify(norm(x, 0.45), 1.0)


def write(name, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, name + ".wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        out = os.path.join(OUT, name + ".ogg")
        subprocess.run(["oggenc", "-Q", "-q", "4", "-o", out, wav], check=True)
    print("wrote", os.path.normpath(out), len(x) / SR, "s")


if __name__ == "__main__":
    write("pull", pull())
    write("press", press())
    for i in range(3):
        write("step_clay_%d" % (i + 1), step(i))
    write("reveal", reveal())
    write("bed_0", bed([55.0, 82.4, 110.0], 12.0, 0.0))
    write("bed_1", bed([110.0, 164.8, 220.0, 329.6], 12.0, 1.3))
    write("amb_wind", wind())
    sys.exit(0)

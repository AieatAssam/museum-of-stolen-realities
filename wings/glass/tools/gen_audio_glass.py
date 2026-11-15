#!/usr/bin/env python3
"""Synthesise the Vitrine Kingdom's own audio into wings/glass/audio/*.ogg.
Reuses the helpers in tools/gen_audio.py. Deterministic.

  tools/.venv/bin/python wings/glass/tools/gen_audio_glass.py [--only a,b]

The leitmotif ("For the Light Alone"): D  A  G  F  E  . D  C  D — glass harmonica, re-orchestrated
per area: cloister/nave (bright, gold), crypt (low, slow), rose (choir pad, minor), heist (pulse).
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_audio as ga  # noqa: E402

SR = ga.SR
OUT = os.path.join(ROOT, "wings", "glass", "audio")
rng = np.random.default_rng(214)
D4 = 293.66
MOTIF = [(0, 0.0, 1.5), (7, 1.5, 1.0), (5, 2.5, 1.0), (3, 3.5, 1.0), (2, 4.5, 2.0), (0, 7.0, 1.0), (-2, 8.0, 1.0), (0, 9.0, 3.0)]
BAR = 12.0  # motif length in beats-ish seconds at tempo 1


def st(n, base=D4):
    return base * 2 ** (n / 12)


def harmonica(f, sec, bright=0.4):
    """Glass harmonica: pure partials, slow attack, soft beating."""
    tt = ga.t_axis(sec)
    x = ga.tone(f, sec, ((1, 1.0), (2, 0.18 * bright), (3, 0.06 * bright)), vib=0.004, vib_rate=4.5)
    x += 0.4 * ga.tone(f * 1.003, sec, ((1, 1.0),))
    e = np.minimum(tt / 0.18, 1) * np.exp(-tt * 0.9 / max(sec, 0.5))
    e[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return x * e


def motif_line(sec, base=D4, speed=1.0, octave=0, voice="harmonica", gain=1.0):
    x = np.zeros(int(sec * SR))
    loop = BAR / speed
    k = 0.0
    while k < sec:
        for n, at, dur in MOTIF:
            t0 = k + at / speed
            if t0 >= sec:
                break
            f = st(n + 12 * octave, base)
            if voice == "harmonica":
                note = harmonica(f, dur / speed + 1.2)
            else:
                note = ga.bell(f, dur / speed + 2.5, decay=1.4, bright=0.5)
            ga.place(x, note, t0, gain)
        k += loop
    return x


def pad(freqs, sec, cutoff=1400, breath=0.07):
    tt = ga.t_axis(sec)
    x = np.zeros_like(tt)
    for f in freqs:
        x += ga.tone(f, sec, ((1, 1), (2, 0.35), (3, 0.15), (5, 0.05)), detune=0.002, vib=0.003, vib_rate=0.2)
    x = ga.lowpass(x, cutoff)
    return x * (0.8 + 0.2 * np.sin(2 * np.pi * breath * tt))


def shimmer(sec, freqs, n=40, seed=3, decay=1.2):
    r = np.random.default_rng(seed)
    x = np.zeros(int(sec * SR))
    for _ in range(n):
        f = r.choice(freqs) * r.choice([2, 4])
        ga.place(x, ga.bell(f, 3.5, decay=decay, bright=0.35), r.uniform(0, sec - 3.5), r.uniform(0.15, 0.4))
    return x


def loop(x, xf=3.0):
    return ga.loopify(x, xf)


L = 48.0  # all stems of a bed share this length so they loop in sync
DM = [st(-12), st(-5), st(0), st(3), st(7)]  # D minor-ish open voicing


def nave_0():
    return ga.norm(loop(ga.simple_reverb(pad([st(-24), st(-17), st(-12)], L + 3, 900), 5, 0.4)), 0.55)


def nave_1():
    return ga.norm(loop(ga.simple_reverb(shimmer(L + 3, DM, 34, 5), 4, 0.55)), 0.4)


def nave_2():
    return ga.norm(loop(ga.simple_reverb(motif_line(L + 3, D4, 1.0, 0) + 0.3 * motif_line(L + 3, D4, 1.0, -1), 5, 0.5)), 0.5)


def crypt_0():
    return ga.norm(loop(ga.simple_reverb(pad([st(-29), st(-24), st(-21)], L + 3, 500, 0.04), 6, 0.5)), 0.6)


def crypt_1():
    return ga.norm(loop(ga.simple_reverb(motif_line(L + 3, D4 / 2, 0.5, 0, "bell", 0.8), 6, 0.6)), 0.45)


def rose_0():
    tt = ga.t_axis(L + 3)
    x = pad([st(-12), st(-9), st(-5), st(0)], L + 3, 1100, 0.055)
    # formant 'ah' choir colour
    x = ga.bandpass(x, 300, 2600) * 1.4 + x * 0.3
    return ga.norm(loop(ga.simple_reverb(x * (0.7 + 0.3 * np.sin(2 * np.pi * tt / 16)), 6, 0.55)), 0.55)


def rose_1():
    x = motif_line(L + 3, D4, 0.75, 0) + motif_line(L + 3, st(3), 0.75, 0) * 0.5  # a minor-third ghost
    return ga.norm(loop(ga.simple_reverb(x, 6, 0.6)), 0.45)


def heist_0():
    tt = ga.t_axis(L + 3)
    pulse = np.zeros_like(tt)
    for k in range(int((L + 3) / 0.5)):
        ga.place(pulse, ga.lowpass(ga.tone(st(-24), 0.4, ((1, 1), (2, 0.5))), 600) * np.exp(-ga.t_axis(0.4) * 9), k * 0.5, 1.0 if k % 2 == 0 else 0.55)
    return ga.norm(loop(pulse + 0.5 * pad([st(-24), st(-17)], L + 3, 600)), 0.6)


def heist_1():
    return ga.norm(loop(ga.simple_reverb(motif_line(L + 3, D4, 2.0, 1) + 0.6 * shimmer(L + 3, DM, 60, 9, 2.0), 3, 0.4)), 0.45)


def beam_hum():
    sec = 6.0
    x = ga.tone(220, sec, ((1, 1), (2, 0.5), (3, 0.25), (4.01, 0.12)), vib=0.002, vib_rate=3)
    x += 0.6 * ga.tone(221.3, sec, ((1, 1), (2, 0.3)))
    x += 0.2 * ga.bandpass(ga.noise(sec, "pink"), 1800, 5000)
    return ga.norm(loop(x, 1.5), 0.6)


def beam_touch():
    x = ga.bell(1318.5, 1.6, 1.2, 0.5)
    ga.place(x, ga.bell(1975.5, 1.4, 1.6, 0.4), 0.0, 0.6)
    return ga.norm(ga.simple_reverb(x, 1.5, 0.3), 0.5)


def dial_turn():
    x = np.zeros(int(1.6 * SR))
    for k in range(6):
        click = ga.highpass(rng.standard_normal(1500), 2000) * np.exp(-ga.t_axis(1500 / SR) * 120)
        ga.place(x, click, k * 0.06, 0.5)
    ga.place(x, ga.bell(440, 1.4, 1.0, 0.7), 0.36, 0.7)
    ga.place(x, ga.bell(659.25, 1.2, 1.2, 0.5), 0.38, 0.4)
    return ga.norm(ga.simple_reverb(x, 1.6, 0.35), 0.7)


def mirror_turn():
    tt = ga.t_axis(1.2)
    sw = ga.bandpass(ga.noise(1.2), 1500, 6000) * np.sin(np.pi * np.minimum(tt / 0.5, 1)) * 0.3
    x = sw.copy()
    ga.place(x, ga.bell(1760, 1.0, 1.5, 0.4), 0.45, 0.5)
    return ga.norm(ga.simple_reverb(x, 1.2, 0.3), 0.55)


def gate_open():
    sec = 2.5
    tt = ga.t_axis(sec)
    f = 300 * (1 + tt / sec)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(tt / 0.3, 1) * np.exp(-tt * 1.2)
    x += shimmer(sec, [523.25, 659.25, 783.99], 10, 11, 2.0)
    return ga.norm(ga.simple_reverb(x, 2.5, 0.45), 0.6)


def gate_close():
    sec = 1.8
    tt = ga.t_axis(sec)
    f = 500 * (1 - 0.5 * tt / sec)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.0)
    return ga.norm(ga.simple_reverb(x, 1.8, 0.4), 0.45)


def pane_restore():
    x = np.zeros(int(7 * SR))
    for i, (n, at, dur) in enumerate(MOTIF[:5]):
        ga.place(x, harmonica(st(n + 12), dur * 0.5 + 1.5), at * 0.45, 0.7)
    ga.place(x, ga.chord_swell([D4, st(7), st(12)], 6, 0.7), 0.0, 0.7)
    return ga.norm(ga.simple_reverb(x, 4, 0.5), 0.7)


def shatter():
    sec = 6.0
    tt = ga.t_axis(sec)
    x = ga.highpass(ga.noise(sec), 1200) * np.exp(-tt * 3.5) * 0.9
    x += ga.lowpass(ga.noise(sec), 220) * np.exp(-tt * 2.0) * 1.2
    r = np.random.default_rng(5)
    for _ in range(140):
        ga.place(x, ga.bell(r.uniform(1800, 7000), 1.0, 2.5, 0.8), r.exponential(0.5), r.uniform(0.05, 0.3))
    return ga.norm(ga.simple_reverb(x, 4, 0.5), 0.95)


def wind_loop():
    sec = 30.0
    tt = ga.t_axis(sec)
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * tt / 7.5) * np.sin(2 * np.pi * tt / 3.1 + 1)
    x = ga.bandpass(ga.noise(sec, "pink"), 180, 1400) * gust
    whistle = ga.tone(780, sec, ((1, 1),), vib=0.03, vib_rate=0.4) * 0.05 * gust
    return ga.norm(loop(x + whistle, 4), 0.7)


def amb_glass():
    sec = 40.0
    x = ga.lowpass(ga.noise(sec, "pink"), 260) * 0.5
    x += shimmer(sec, [1046.5, 1318.5, 1567.98, 2093.0], 26, 21, 2.5) * 0.4
    return ga.norm(loop(ga.simple_reverb(x, 5, 0.5)), 0.5)


def amb_crypt():
    sec = 40.0
    x = ga.lowpass(ga.noise(sec, "pink"), 140) * 0.6
    r = np.random.default_rng(31)
    for _ in range(22):
        ga.place(x, ga.bell(r.uniform(1400, 2600), 0.6, 4.0, 0.3), r.uniform(0, sec - 1), r.uniform(0.1, 0.3))
    return ga.norm(loop(ga.simple_reverb(x, 6, 0.6)), 0.5)


def rose_breath():
    sec = 6.0
    tt = ga.t_axis(sec)
    x = ga.bandpass(ga.noise(sec, "pink"), 200, 900) * np.sin(np.pi * tt / sec) ** 2
    x += pad([st(-12), st(-5)], sec, 700) * np.sin(np.pi * tt / sec) ** 2 * 0.5
    return ga.norm(ga.simple_reverb(x, 4, 0.5), 0.5)


def lantern_loop():
    sec = 8.0
    x = ga.bandpass(ga.noise(sec), 400, 3000) * 0.15
    r = np.random.default_rng(41)
    for _ in range(40):
        ga.place(x, ga.highpass(r.standard_normal(600), 3000) * np.exp(-ga.t_axis(600 / SR) * 200), r.uniform(0, sec - 0.1), r.uniform(0.1, 0.4))
    return ga.norm(loop(x, 1.0), 0.4)


def going_dark():
    sec = 3.0
    tt = ga.t_axis(sec)
    f = 880 * np.exp(-tt * 0.8)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.0) * 0.5
    x += ga.lowpass(ga.noise(sec), 300) * np.exp(-tt * 2) * 0.4
    return ga.norm(ga.simple_reverb(x, 3, 0.5), 0.6)


def sky_reveal():
    return ga.chord_swell([st(-12), st(-5), st(0), st(7), st(12)], 10, 0.8)


def step_glass(i):
    r = np.random.default_rng(300 + i)
    tt = ga.t_axis(0.5)
    click = ga.highpass(r.standard_normal(len(tt)), 2500) * np.exp(-tt * 160)
    ring = sum(np.sin(2 * np.pi * r.uniform(2600, 4800) * tt) * np.exp(-tt * r.uniform(25, 45)) * 0.12 for _ in range(3))
    body = ga.lowpass(r.standard_normal(len(tt)), 700) * np.exp(-tt * 50) * 0.5
    return ga.norm(click * 0.7 + ring + body, 0.75)


SOUNDS = {
    "nave_0": (nave_0, 0.6), "nave_1": (nave_1, 0.8), "nave_2": (nave_2, 0.6),
    "crypt_0": (crypt_0, 0.6), "crypt_1": (crypt_1, 0.7),
    "rose_0": (rose_0, 0.7), "rose_1": (rose_1, 0.7),
    "heist_0": (heist_0, 0.4), "heist_1": (heist_1, 0.8),
    "beam_hum": (beam_hum, 0.3), "beam_touch": (beam_touch, 0.4), "dial_turn": (dial_turn, 0.3),
    "mirror_turn": (mirror_turn, 0.3), "gate_open": (gate_open, 0.5), "gate_close": (gate_close, 0.4),
    "pane_restore": (pane_restore, 0.7), "shatter": (shatter, 0.8), "wind_loop": (wind_loop, 0.8),
    "amb_glass": (amb_glass, 0.8), "amb_crypt": (amb_crypt, 0.8), "rose_breath": (rose_breath, 0.6),
    "lantern_loop": (lantern_loop, 0.2), "going_dark": (going_dark, 0.6), "sky_reveal": (sky_reveal, 0.8),
    **{"step_glass_%d" % i: ((lambda i=i: step_glass(i)), 0.0) for i in range(1, 7)},
}

if __name__ == "__main__":
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    os.makedirs(OUT, exist_ok=True)
    for name, (fn, width) in SOUNDS.items():
        if only and name not in only:
            continue
        if os.path.exists(os.path.join(OUT, name + ".ogg")) and not only:
            continue
        try:
            ga.write(OUT, name, fn(), stereo_width=width)
        except Exception as e:  # keep going; report at the end
            print("FAILED", name, e)

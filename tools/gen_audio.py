#!/usr/bin/env python3
"""Procedurally synthesise the core/hub audio set into assets/audio/*.ogg (needs `oggenc`).

  tools/.venv/bin/python tools/gen_audio.py [out_dir] [--only name1,name2]

Wing engineers: copy the helpers (tone, bell, noise, lowpass, loopify, write) into
wings/<id>/tools/ and write your own generator; output into wings/<id>/audio/.
Everything is deterministic (seeded).
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from scipy import signal

SR = 44100
rng = np.random.default_rng(1729)


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def env_adsr(n, a=0.01, d=0.1, s=0.7, r=0.3):
    e = np.ones(n) * s
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    e[:ai] = np.linspace(0, 1, ai)
    e[ai:ai + di] = np.linspace(1, s, di)
    if ri:
        e[-ri:] *= np.linspace(1, 0, ri)
    return e


def noise(sec, color="white"):
    n = rng.standard_normal(int(sec * SR))
    if color == "pink":
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        n = signal.lfilter(b, a, n)
    return n / (np.abs(n).max() + 1e-9)


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def tone(freq, sec, partials=((1, 1.0),), detune=0.0, vib=0.0, vib_rate=5.0):
    t = t_axis(sec)
    out = np.zeros_like(t)
    for mult, amp in partials:
        f = freq * mult * (1 + detune * rng.uniform(-1, 1))
        ph = 2 * np.pi * f * t + vib * np.sin(2 * np.pi * vib_rate * t + rng.uniform(0, 6.28))
        out += amp * np.sin(ph)
    return out


def bell(freq, sec, decay=2.5, bright=1.0):
    """Inharmonic bell/glass partials with individual decays."""
    t = t_axis(sec)
    out = np.zeros_like(t)
    for ratio, amp, dk in ((0.5, 0.35, 0.6), (1.0, 1.0, 1.0), (2.0, 0.5 * bright, 1.6),
                           (2.76, 0.4 * bright, 2.2), (5.40, 0.18 * bright, 3.5), (8.93, 0.08 * bright, 5.0)):
        out += amp * np.sin(2 * np.pi * freq * ratio * t + rng.uniform(0, 6.28)) * np.exp(-t * dk * decay / sec * 3)
    out *= np.minimum(t / 0.004, 1)
    return out


def place(buf, x, at_sec, gain=1.0):
    i = int(at_sec * SR)
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i] * gain


def loopify(x, xfade=3.0):
    """Make a seamless loop by crossfading the tail into the head."""
    n = int(xfade * SR)
    head, tail = x[:n], x[-n:]
    f = np.linspace(0, 1, n)
    mixed = tail * (1 - f) + head * f
    return np.concatenate([mixed, x[n:-n]])


def simple_reverb(x, sec=3.0, mix=0.35, seed=7):
    r = np.random.default_rng(seed)
    t = t_axis(sec)
    ir = r.standard_normal(len(t)) * np.exp(-t * 6.9 / sec)
    ir = lowpass(ir, 6000)
    ir /= np.sqrt((ir ** 2).sum())
    wet = signal.fftconvolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix * 3


def norm(x, peak=0.89):
    return x / (np.abs(x).max() + 1e-9) * peak


def write(out_dir, name, x, quality=5, stereo_width=0.0):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        if stereo_width > 0:
            d = int(0.011 * SR)
            r = np.concatenate([np.zeros(d), x[:-d]])
            x = np.stack([x * (1 - stereo_width * 0.3) + r * stereo_width * 0.3, x * (1 - stereo_width * 0.3) + np.roll(r, d) * stereo_width * 0.3], 1)
        else:
            x = np.stack([x, x], 1)
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, name + ".wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        out = os.path.join(out_dir, name + ".ogg")
        subprocess.run(["oggenc", "-Q", "-q", str(quality), "-o", out, wav], check=True)
    print(out)


# ---- the sounds ------------------------------------------------------------------

def hub_bed_0():  # low string drone, D aeolian, slow breathing
    sec = 64
    x = np.zeros(int(sec * SR))
    for f, g in ((73.42, 1.0), (110.0, 0.6), (146.83, 0.35), (174.61, 0.22), (55.0, 0.5)):
        x += g * tone(f, sec, ((1, 1), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.08)), vib=0.004, vib_rate=0.2)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * t_axis(sec) / 16)
    x = lowpass(x * lfo, 900)
    return norm(loopify(simple_reverb(x, 4, 0.4)), 0.6)


def hub_bed_1():  # sparse glass bells, pentatonic, high
    sec = 64
    x = np.zeros(int(sec * SR))
    notes = [587.33, 698.46, 880.0, 1046.5, 1174.66, 1396.9]
    t = 0.5
    while t < sec - 8:
        place(x, bell(rng.choice(notes), 7, decay=1.2, bright=0.7), t, rng.uniform(0.25, 0.6))
        t += rng.uniform(2.5, 6.0)
    return norm(loopify(simple_reverb(x, 5, 0.6)), 0.45)


def hub_bed_2():  # uneasy choir-ish formant pad + slow sub pulse
    sec = 64
    tt = t_axis(sec)
    x = np.zeros_like(tt)
    for f in (146.83, 155.56, 220.0, 233.08):  # semitone rubs = unease
        saw = signal.sawtooth(2 * np.pi * f * tt * (1 + 0.002 * np.sin(2 * np.pi * 0.13 * tt)))
        x += bandpass(saw, 500, 1100) * 0.5 + bandpass(saw, 2300, 2900) * 0.15
    x *= 0.5 + 0.5 * np.sin(2 * np.pi * tt / 32) ** 2
    pulse = np.sin(2 * np.pi * 41.2 * tt) * np.exp(-((tt % 4.0)) * 3.0)
    return norm(loopify(simple_reverb(x * 0.6 + pulse * 0.5, 4, 0.5)), 0.5)


def amb_hub():  # vast room tone
    sec = 48
    x = lowpass(noise(sec, "pink"), 300) * 0.5 + bandpass(noise(sec), 2000, 6000) * 0.02
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * t_axis(sec) / 12)
    return norm(loopify(x), 0.35)


def distant_movement():  # something enormous shifting far away
    sec = 9
    tt = t_axis(sec)
    groan = signal.sawtooth(2 * np.pi * (31 + 6 * np.sin(2 * np.pi * 0.11 * tt)) * tt)
    groan = lowpass(groan, 180, 4)
    scrape = bandpass(noise(sec), 120, 600) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * tt) ** 8)
    e = np.sin(np.pi * tt / sec) ** 2
    thud = np.zeros_like(tt)
    place(thud, lowpass(noise(1.5), 90, 4) * np.exp(-t_axis(1.5) * 3), 6.2, 2.5)
    return norm(simple_reverb((groan * 0.7 + scrape * 0.5) * e + thud, 6, 0.75), 0.8)


def step(surface, i):
    sec = 0.5
    tt = t_axis(sec)
    r = np.random.default_rng(100 + i)
    if surface == "marble":
        click = highpass(r.standard_normal(len(tt)), 1800) * np.exp(-tt * 140)
        body = lowpass(r.standard_normal(len(tt)), 900) * np.exp(-tt * 45)
        ping = np.sin(2 * np.pi * r.uniform(2400, 3400) * tt) * np.exp(-tt * 60) * 0.15
        heel = np.zeros_like(tt)
        place(heel, highpass(r.standard_normal(4000), 1500) * np.exp(-t_axis(4000 / SR) * 160) * 0.6, r.uniform(0.045, 0.07))
        x = click * 0.8 + body * 0.5 + ping + heel
    else:  # carpet / velvet
        x = lowpass(r.standard_normal(len(tt)), 700) * np.exp(-tt * 25) * (1 - np.exp(-tt * 200))
    return norm(x, 0.8)


def ui_sound(kind):
    if kind == "hover":
        return norm(bell(1760, 0.4, decay=3.0, bright=0.3), 0.25)
    if kind == "select":
        x = bell(880, 1.5, decay=1.5, bright=0.6) + 0.5 * bell(1318.5, 1.5, decay=1.7, bright=0.4)
        return norm(simple_reverb(x, 1.5, 0.3), 0.5)
    if kind == "back":
        return norm(simple_reverb(bell(587.33, 1.0, decay=2.0, bright=0.4), 1.2, 0.3), 0.4)
    if kind == "open":
        x = np.zeros(int(1.8 * SR))
        place(x, bell(659.25, 1.5, 1.5, 0.5), 0)
        place(x, bell(987.77, 1.4, 1.5, 0.5), 0.09, 0.7)
        return norm(simple_reverb(x, 1.6, 0.35), 0.5)
    raise ValueError(kind)


def placard():  # the Curator's toast: a low brass-gong + glass
    x = np.zeros(int(4 * SR))
    place(x, bell(220, 4, decay=0.8, bright=0.5), 0, 0.8)
    place(x, bell(1318.5, 3, decay=1.2, bright=0.3), 0.15, 0.35)
    return norm(simple_reverb(x, 3, 0.45), 0.6)


def chord_swell(freqs, sec, peak=0.8):
    tt = t_axis(sec)
    x = np.zeros_like(tt)
    for f in freqs:
        x += tone(f, sec, ((1, 1), (2, 0.4), (3, 0.2), (4, 0.1)), vib=0.003)
    e = np.minimum(tt / (sec * 0.35), 1) * np.exp(-np.maximum(tt - sec * 0.35, 0) * 1.6)
    shimmer = np.zeros_like(tt)
    for k in range(10):
        place(shimmer, bell(rng.choice(freqs) * 4, 3, 1.2, 0.4), rng.uniform(0.2, sec * 0.6), 0.2)
    return norm(simple_reverb(lowpass(x, 3000) * e + shimmer, 4, 0.5), peak)


def whoosh():
    sec = 3.2
    tt = t_axis(sec)
    n = noise(sec, "pink")
    out = np.zeros_like(tt)
    for k in range(32):  # sweeping band
        a, b = int(k / 32 * len(tt)), int((k + 1) / 32 * len(tt))
        fc = 200 * (2 ** (k / 32 * 5))
        out[a:b] = bandpass(n, fc * 0.7, min(fc * 1.4, 20000))[a:b]
    e = np.sin(np.pi * tt / sec) ** 1.5
    x = out * e
    place(x, bell(392, 2.0, 1.5, 0.8)[::-1], sec - 2.0, 0.3)
    return norm(simple_reverb(x, 2.5, 0.4), 0.7)


def sketch():  # pencil scratching, loopable
    sec = 6
    x = np.zeros(int(sec * SR))
    t = 0.1
    while t < sec - 0.5:
        d = rng.uniform(0.08, 0.35)
        s = bandpass(noise(d), 2500, 7000) * np.sin(np.pi * t_axis(d) / d)
        place(x, s, t, rng.uniform(0.3, 1))
        t += d + rng.uniform(0.05, 0.5)
    return norm(loopify(x, 0.5), 0.5)


def sphere_hum():
    sec = 20
    tt = t_axis(sec)
    x = tone(55, sec, ((1, 1), (2, 0.5), (3, 0.3), (6, 0.1))) * (0.8 + 0.2 * np.sin(2 * np.pi * tt / 5))
    x += tone(1760, sec, ((1, 0.04), (1.003, 0.04)))
    return norm(loopify(lowpass(x, 2500), 2), 0.6)


def cloth():
    return norm(lowpass(noise(0.8), 3000) * np.sin(np.pi * t_axis(0.8) / 0.8) ** 2, 0.5)


def ending_restore():
    return chord_swell([146.83, 220.0, 293.66, 369.99, 440.0], 14, 0.8)


def ending_break():
    x = chord_swell([138.59, 207.65, 277.18, 329.63], 16, 0.8)
    tt = t_axis(16)
    return x * np.exp(-tt * 0.05)


def template_bed():
    sec = 32
    x = np.zeros(int(sec * SR))
    for f in (130.81, 196.0, 261.63):
        x += tone(f, sec, ((1, 1), (2, 0.3), (3, 0.1)), vib=0.003, vib_rate=0.3)
    return norm(loopify(lowpass(x, 1200)), 0.4)


SOUNDS = {
    "hub_bed_0": (hub_bed_0, 0.6), "hub_bed_1": (hub_bed_1, 0.8), "hub_bed_2": (hub_bed_2, 0.6),
    "amb_hub": (amb_hub, 0.0), "distant_movement": (distant_movement, 0.5),
    "placard": (placard, 0.6), "fragment": (lambda: chord_swell([146.83, 220.0, 277.18, 329.63, 440.0], 9), 0.6),
    "provenance": (lambda: chord_swell([293.66, 440.0, 554.37], 5, 0.6), 0.6),
    "transition": (whoosh, 0.8), "sketch": (sketch, 0.0), "sphere_hum": (sphere_hum, 0.0),
    "cloth": (cloth, 0.0), "ending_restore": (ending_restore, 0.7), "ending_break": (ending_break, 0.7),
    "template_bed": (template_bed, 0.5),
    **{"ui_" + k: ((lambda k=k: ui_sound(k)), 0.0) for k in ("hover", "select", "back", "open")},
    **{"step_marble_%d" % i: ((lambda i=i: step("marble", i)), 0.0) for i in range(1, 7)},
    **{"step_carpet_%d" % i: ((lambda i=i: step("carpet", i)), 0.0) for i in range(1, 5)},
}

if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "assets/audio"
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    os.makedirs(out_dir, exist_ok=True)
    for name, (fn, width) in SOUNDS.items():
        if only and name not in only:
            continue
        write(out_dir, name, fn(), stereo_width=width)

"""Synthesise The Drowned Aria's sound: music stems, sustained instrument notes, the Sirena voice and SFX.

Everything is heard through water: low-passed, slightly swollen, long reverb-like tails.
Loops are made periodic by choosing every frequency as an integer number of cycles per loop length,
so each stem repeats without a click. Run from the repo root:

    tools/.venv/bin/python wings/aria/tools/gen_aria_audio.py

Needs numpy and ffmpeg (libvorbis). Writes wings/aria/audio/*.ogg.
"""
import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio")
rng = np.random.default_rng(3)


def periodic_freq(f, loop_s):
    """Snap a frequency to an integer number of cycles per loop, so the loop is seamless."""
    return round(f * loop_s) / loop_s


def lowpass(x, cutoff):
    """Brick-wall FFT low-pass. Circular, so it preserves loop periodicity."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    rolloff = 1.0 / (1.0 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spec * rolloff, len(x))


def norm(x, peak=0.8):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def write_ogg(name, x):
    path = os.path.join(OUT, name + ".ogg")
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    # oggenc (vorbis-tools): ffmpeg here is built without libvorbis
    subprocess.run(["oggenc", "-q", "4", "-o", path, wav], check=True, stderr=subprocess.DEVNULL)
    os.remove(wav)
    print("wrote", path, "%.2fs" % (len(x) / SR))


def tone(freq, t, harmonics):
    """Additive tone: harmonics is a list of amplitudes for partials 1..n."""
    out = np.zeros_like(t)
    for k, a in enumerate(harmonics, start=1):
        out += a * np.sin(2 * np.pi * freq * k * t)
    return out


def swell(n, attack, release, sr=SR):
    """Envelope: attack and release in seconds, sustained in between."""
    env = np.ones(n)
    a = int(attack * sr)
    r = int(release * sr)
    env[:a] = np.linspace(0, 1, a)
    env[n - r:] *= np.linspace(1, 0, r)
    return env


def loop_t(loop_s):
    n = int(loop_s * SR)
    return n, np.arange(n) / SR


def sustained(freq, loop_s, harmonics, vibrato=0.0, vib_cycles=5, cutoff=1100.0):
    """A sustained, seamlessly looping note with optional vibrato."""
    n, t = loop_t(loop_s)
    f = periodic_freq(freq, loop_s)
    fm = 1.0 + vibrato * np.sin(2 * np.pi * (vib_cycles / loop_s) * t)
    # integrate phase so the frequency modulation stays periodic
    phase = 2 * np.pi * f * np.cumsum(fm) / SR
    out = np.zeros(n)
    for k, a in enumerate(harmonics, start=1):
        out += a * np.sin(k * phase)
    return lowpass(out, cutoff)


def drone_bed():
    L = 16.0
    n, t = loop_t(L)
    x = np.zeros(n)
    # D2 + A2 + D3 pads, soft, slowly breathing
    for f, a in [(73.42, 1.0), (110.0, 0.6), (146.8, 0.35)]:
        x += a * sustained(f, L, [1.0, 0.45, 0.2, 0.08], vibrato=0.002, vib_cycles=2)
    breath = 0.7 + 0.3 * np.sin(2 * np.pi * (1.0 / L) * t)
    return norm(lowpass(x * breath, 700.0), 0.7)


def motif_stem():
    """The leitmotif: a falling D-minor phrase, sung on a muted choir-like tone, repeated."""
    L = 16.0
    n, t = loop_t(L)
    x = np.zeros(n)
    notes = [293.66, 349.23, 440.0, 523.25, 440.0, 392.0, 349.23, 329.63]  # D4 F4 A4 C5 A4 G4 F4 E4
    step = 1.0
    for rep in range(2):
        for i, f in enumerate(notes):
            start = (rep * 8 + i) * step / 1.0
            if start >= L:
                continue
            sl = int(start * SR)
            ln = min(int(1.4 * SR), n - sl)
            if ln <= 0:
                continue
            tt = np.arange(ln) / SR
            ff = periodic_freq(f * (1.0 if rep == 0 else 1.5), L)
            env = np.exp(-tt * 1.4) * np.minimum(1.0, tt / 0.25)
            x[sl:sl + ln] += env * tone(ff, tt, [1.0, 0.3, 0.12, 0.05])
    return norm(lowpass(x, 1300.0), 0.55)


def texture_stem():
    """Water texture: circular noise, bubble ticks and a slow filtered wash."""
    L = 16.0
    n, t = loop_t(L)
    noise = rng.standard_normal(n)
    wash = lowpass(noise, 500.0)
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * (2.0 / L) * t)
    x = wash * mod
    for _ in range(14):
        start = rng.uniform(0, L)
        ln = int(0.09 * SR)
        sl = int(start * SR)
        tt = np.arange(ln) / SR
        f0 = rng.uniform(500, 1400)
        chirp = np.sin(2 * np.pi * (f0 + 1600 * tt) * tt)
        env = np.exp(-tt * 40.0)
        idx = (np.arange(ln) + sl) % n
        x[idx] += 0.25 * env * chirp
    return norm(lowpass(x, 2200.0), 0.5)


def instrument_note(name, freq, harmonics, vib=0.0, cutoff=900.0):
    L = 8.0
    write_ogg(name, norm(sustained(freq, L, harmonics, vibrato=vib, cutoff=cutoff), 0.6))


def harp_loop():
    """Plucked harp currents: pluck every half beat in a loop, pitched C5 down to G4."""
    L = 8.0
    n, t = loop_t(L)
    x = np.zeros(n)
    pitches = [523.25, 587.33, 659.25, 783.99, 659.25, 587.33, 523.25, 392.0] * 2
    for i, f in enumerate(pitches):
        start = i * 0.5
        sl = int(start * SR)
        ln = min(int(1.6 * SR), n - sl)
        tt = np.arange(ln) / SR
        x[sl:sl + ln] += np.exp(-tt * 3.2) * tone(periodic_freq(f, L), tt, [1.0, 0.18, 0.05, 0.02])
    return norm(lowpass(x, 3000.0), 0.6)


def sirena_voice():
    """La Sirena: a vowel-shaped voice (formant bands) with vibrato and breath, 16 s loop."""
    L = 16.0
    n, t = loop_t(L)
    pitch = 311.13  # Eb4-ish, sung over the whole aria
    phase = 2 * np.pi * periodic_freq(pitch, L) * np.cumsum(1.0 + 0.012 * np.sin(2 * np.pi * (6 * 1.0 / L) * t)) / SR
    src = np.zeros(n)
    for k in range(1, 26):
        src += np.sin(k * phase) / k
    # three formant bands ("ah")
    spec = np.fft.rfft(src)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    form = (np.exp(-((freqs - 800) / 220) ** 2) + 0.6 * np.exp(-((freqs - 1200) / 260) ** 2) + 0.35 * np.exp(-((freqs - 2600) / 400) ** 2))
    voice = np.fft.irfft(spec * (form + 0.02), n)
    breath = lowpass(rng.standard_normal(n), 3000.0) * 0.04
    swell_env = 0.75 + 0.25 * np.sin(2 * np.pi * (1.0 / L) * t)
    return norm(lowpass((voice + breath) * swell_env, 2400.0), 0.75)


def sirena_crescendo():
    """A one-shot swell to lean the gravity down (sung through the water), 10 s."""
    n = int(10 * SR)
    t = np.arange(n) / SR
    f = 311.13 * (1 + 0.01 * np.sin(2 * np.pi * 5 * t))
    x = np.zeros(n)
    phase = 2 * np.pi * np.cumsum(f) / SR
    for k in range(1, 14):
        x += np.sin(k * phase) / k
    env = np.minimum(1.0, t / 6.0) * np.exp(-np.maximum(0, t - 8.0) * 2.0)
    return norm(lowpass(x * env, 1800.0), 0.8)


def fork_strike():
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 440.0 * t) + 0.25 * np.sin(2 * np.pi * 880.0 * t) * np.exp(-t * 4)
    x = x * np.exp(-t * 1.6)
    return norm(lowpass(x, 2500.0), 0.7)


def bubble():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    f = 380 + 900 * t / 0.25
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
    return norm(lowpass(x, 3000.0), 0.4)


def tick():
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 90)
    return norm(lowpass(x, 2400.0), 0.5)


def chime():
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    x = tone(659.25, t, [1, 0.2]) * np.exp(-t * 1.4) + tone(987.77, t, [1, 0.1]) * np.exp(-t * 2.0) * 0.6
    return norm(lowpass(x, 2000.0), 0.45)


def groan():
    """Long, slow groan of the chandelier's chains, 12 s, not looped."""
    n = int(12 * SR)
    t = np.arange(n) / SR
    f = 70 + 6 * np.sin(2 * np.pi * 0.2 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * rng.standard_normal(n) * 0.0
    env = np.minimum(1.0, t / 3.0) * (1.0 - t / 12.0)
    return norm(lowpass(x * env, 500.0), 0.7)


def release():
    """Gravity letting go: a falling sweep, 4 s."""
    n = int(4 * SR)
    t = np.arange(n) / SR
    f = 520 * np.exp(-t * 0.9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 0.5)
    return norm(lowpass(x, 1500.0), 0.6)


def crash():
    n = int(4.0 * SR)
    t = np.arange(n) / SR
    x = lowpass(rng.standard_normal(n), 900.0) * np.exp(-t * 2.2)
    x += 0.5 * np.sin(2 * np.pi * 60 * t) * np.exp(-t * 1.5)
    return norm(lowpass(x, 1200.0), 0.85)


def main():
    os.makedirs(OUT, exist_ok=True)
    write_ogg("aria_bed_drone", drone_bed())
    write_ogg("aria_stem_motif", motif_stem())
    write_ogg("aria_stem_texture", texture_stem())
    write_ogg("aria_stem_harp", harp_loop())
    write_ogg("aria_sirena_loop", sirena_voice())
    write_ogg("aria_sirena_swell", sirena_crescendo())
    instrument_note("note_horn", 110.0, [1.0, 0.5, 0.25, 0.12, 0.05], vib=0.004)
    instrument_note("note_organ_c", 130.81, [1.0, 0.0, 0.5, 0.0, 0.3, 0.0, 0.15])
    instrument_note("note_organ_e", 164.81, [1.0, 0.0, 0.5, 0.0, 0.3, 0.0, 0.15])
    instrument_note("note_organ_g", 196.0, [1.0, 0.0, 0.5, 0.0, 0.3, 0.0, 0.15])
    instrument_note("note_cello", 73.42, [1.0, 0.7, 0.4, 0.2], vib=0.003, cutoff=500.0)
    instrument_note("note_glass", 329.63, [1.0, 0.0, 0.3, 0.0, 0.1], vib=0.002, cutoff=2200.0)
    write_ogg("fork_strike", fork_strike())
    write_ogg("bubble", bubble())
    write_ogg("tick", tick())
    write_ogg("chime", chime())
    write_ogg("chandelier_groan", groan())
    write_ogg("gravity_release", release())
    write_ogg("crash", crash())


if __name__ == "__main__":
    main()

"""Cut the Drowned Aria's game audio from the CC recordings in wings/aria/audio/src (see CREDITS.md).
    tools/.venv/bin/python wings/aria/tools/make_audio.py
Needs ffmpeg (decode) and oggenc (encode). Everything is in C: the leitmotif is G, E, C (the cadence).

Instrument notes (one-shots, ~9 s to match Instrument.SUSTAIN):
  note_organ_c/e/g  organ_loud_c4 (373703) at C3, E3, G3
  note_horn         fhorn_18 (682231)                     note_cello  cello_section_fs4 (372840, sounds G4) at C4
  note_glass        wine_glass_fs6 (256251) at C6           note_sirena female_voice_sustained (851043, C +30 cents) on C
  fork_strike       tuning_fork_a4 (361922)                  gravity_release  bubbles (840042) + underwater swell
Music stems (24 s seamless loops, played together; Audio.set_intensity fades the upper ones in):
  aria_bed      organ_quiet_c4 (373735) as a C3+G3 fifth
  aria_strings  cello (372840) swelling C-G, E-G, C-E
  aria_motif    the voice singing G-E-C, answered by the glass C-E-G
  aria_choir    choir_high (679482), down a tone into C
Ambiences (loops): amb_hall (210882, CC-BY), amb_water (504641), amb_drips (162116), amb_rigging (130364),
  amb_crystal (84526 swung in the dome over the hall tone)."""
import os
import subprocess
import tempfile

import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "audio", "src")
OUT = os.path.join(HERE, "..", "audio")
VOICE_TO_C = -0.5  # the voice sits 30-60 cents above C (energy-weighted pitch-class histogram)


def load(name):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", os.path.join(SRC, name), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def shift(x, semitones):
    """Resample: pitch and length move together (fine for sustained notes)."""
    r = 2.0 ** (semitones / 12.0)
    n = int(len(x) / r)
    return np.interp(np.arange(n) * r, np.arange(len(x)), x)


def to_chord(x, pcs=(0, 4, 7), floor_db=-30.0, n=8192):
    """Spectral mask: keep partials within ~35 cents of the chord's pitch classes, duck the rest.
    The choir sample is a moving phrase; this pins it to C-E-G so it can't pass through D/D# against the strings."""
    hop = n // 4
    w = np.hanning(n)
    f = np.fft.rfftfreq(n, 1 / SR)
    c = (1200 * np.log2(np.maximum(f, 1) / 261.63)) % 1200
    d = np.min([np.minimum(np.abs(c - 100 * p), 1200 - np.abs(c - 100 * p)) for p in pcs], axis=0)
    g = np.where(d < 35, 1.0, 10 ** (floor_db / 20))
    g[f < 80] = 1.0
    y = np.zeros(len(x) + n)
    xp = np.concatenate([x, np.zeros(n)])
    for s in range(0, len(x), hop):
        y[s:s + n] += np.fft.irfft(np.fft.rfft(xp[s:s + n] * w) * g, n) * w
    return y[:len(x)] / 1.5  # hann^2 at 75% overlap sums to 1.5


def cut(x, a, b, fin=0.02, fout=0.5):
    y = x[int(a * SR): int(b * SR)].copy()
    i, o = int(fin * SR), int(fout * SR)
    if i:
        y[:i] *= np.sin(np.linspace(0, np.pi / 2, i)) ** 2
    if o:
        y[-o:] *= np.cos(np.linspace(0, np.pi / 2, o)) ** 2
    return y


def place(buf, x, t, gain=1.0):
    """Add x into a loop buffer at t seconds, wrapping round the end so the loop is seamless."""
    s = int(t * SR) % len(buf)
    idx = (s + np.arange(len(x))) % len(buf)
    np.add.at(buf, idx, x * gain)


def norm(x, peak):
    return x * (peak / max(np.abs(x).max(), 1e-9))


def write(name, x):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=pcm.tobytes(), check=True)
    subprocess.run(["oggenc", "-Q", "-q", "5", "-o", os.path.join(OUT, name + ".ogg"), path], check=True)
    os.unlink(path)
    print(f"{name}.ogg  {len(x) / SR:5.1f}s")


def loop_of(x, length, a, seg, fade):
    """Fill `length` seconds by overlapping crossfaded segments of x (from a, seg long)."""
    buf = np.zeros(int(length * SR))
    piece = cut(x, a, a + seg, fade, fade)
    t = 0.0
    while t < length:
        place(buf, piece, t)
        t += seg - fade
    return buf


def notes():
    organ = load("organ_loud_c4.ogg")
    for n, st in (("c", -12), ("e", -8), ("g", -5)):
        write(f"note_organ_{n}", norm(cut(shift(organ, st), 0.0, 9.0, 0.01, 2.5), 0.7))
    horn = load("fhorn_18.ogg")
    sus = np.zeros(int(9.0 * SR))  # the call, then its sustain overlapped out to Instrument.SUSTAIN
    place(sus, cut(horn, 0.0, 2.2, 0.005, 0.5), 0.0)
    for t in (1.7, 3.2, 4.7, 6.2):
        place(sus, cut(horn, 0.6, 2.2, 0.5, 0.5), t, 0.8)
    write("note_horn", norm(cut(sus, 0.0, 9.0, 0.0, 2.5), 0.7))
    write("note_cello", norm(cut(shift(load("cello_section_fs4.ogg"), -7), 0.0, 9.0, 0.05, 2.5), 0.7))
    write("note_glass", norm(cut(shift(load("wine_glass_fs6.ogg"), -6), 0.0, 9.0, 0.01, 2.5), 0.6))
    write("note_sirena", norm(cut(shift(load("female_voice_sustained.ogg"), VOICE_TO_C), 0.0, 8.0, 0.15, 2.0), 0.7))
    fork = load("tuning_fork_a4.ogg")
    write("fork_strike", norm(cut(fork, 0.0, len(fork) / SR, 0.002, 0.8), 0.8))
    rel = np.zeros(int(5.0 * SR))
    place(rel, cut(load("underwater.ogg"), 10.0, 15.0, 1.5, 2.0), 0.0, 0.6)
    bub = load("bubbles.ogg")
    for t, st in ((0.2, 0), (1.0, 3), (1.9, 7)):
        place(rel, shift(bub, st), t, 0.8)
    write("gravity_release", norm(rel, 0.7))


def stems():
    L = 24.0
    oq = load("organ_quiet_c4.ogg")
    bed = loop_of(shift(oq, -12), L, 1.0, 10.0, 2.0) + 0.6 * loop_of(shift(oq, -5), L, 2.0, 9.0, 2.0)
    write("aria_bed", norm(bed, 0.5))

    cello = load("cello_section_fs4.ogg")
    strings = np.zeros(int(L * SR))
    for t, sts in ((0.0, (-7, 0)), (8.0, (-3, 0)), (16.0, (-7, -3))):  # C-G, E-G, C-E
        for st in sts:
            place(strings, cut(shift(cello, st), 1.0, 11.0, 2.5, 2.5), t, 0.5)
    write("aria_strings", norm(strings, 0.5))

    voice = load("female_voice_sustained.ogg")
    glass = load("wine_glass_fs6.ogg")
    motif = np.zeros(int(L * SR))
    for t, st, end in ((1.0, 7, 3.8), (4.0, 4, 3.8), (7.0, 0, 4.5)):  # G, E, C sung
        place(motif, cut(shift(voice, VOICE_TO_C + st), 0.5, end, 0.3, 1.2), t, 0.8)
    for t, st in ((13.0, -6), (15.0, -2), (17.0, 1)):  # C6, E6, G6 on the glass, the answer
        place(motif, cut(shift(glass, st), 0.0, 6.0, 0.05, 2.5), t, 0.45)
    write("aria_motif", norm(motif, 0.5))

    write("aria_choir", norm(loop_of(to_chord(shift(load("choir_high.ogg"), -2)), L, 2.0, 12.0, 3.0), 0.45))


def ambiences():
    write("amb_hall", norm(loop_of(load("theatre_room_tone.ogg"), 40.0, 5.0, 21.0, 2.0), 0.35))
    write("amb_water", norm(loop_of(load("underwater.ogg"), 30.0, 2.0, 16.0, 2.0), 0.4))
    write("amb_drips", norm(loop_of(load("dripping_echo.ogg"), 40.0, 2.0, 21.0, 2.0), 0.45))
    write("amb_rigging", norm(loop_of(load("creaking.ogg"), 24.0, 1.0, 13.0, 2.0), 0.45))
    dome = loop_of(load("theatre_room_tone.ogg"), 30.0, 60.0, 16.0, 2.0) * 0.6 / 0.02
    lamp = load("crystal_lamp.ogg")
    for t, g in ((3.0, 0.5), (14.0, 0.35), (22.0, 0.45)):
        place(dome, lamp, t, g)
    write("amb_crystal", norm(dome, 0.4))


if __name__ == "__main__":
    b = np.zeros(10)
    place(b, np.ones(4), 8 / SR)  # wraps: indices 8, 9, 0, 1
    assert b[0] == b[1] == b[8] == b[9] == 1 and b[2] == 0
    assert abs(len(shift(np.zeros(1200), 12)) - 600) <= 1
    notes()
    stems()
    ambiences()

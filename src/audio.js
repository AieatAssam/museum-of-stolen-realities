// Minimal WebAudio: cathedral drone pad + interaction chimes.
// Started lazily on first pointer lock (user gesture).

let ctx, master;

export function initAudio() {
  if (ctx) return;
  ctx = new (window.AudioContext || window.webkitAudioContext)();
  master = ctx.createGain();
  master.gain.value = 0.16;
  master.connect(ctx.destination);

  // drone: detuned saw pair through lowpass, slow LFO on filter
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass'; lp.frequency.value = 220; lp.Q.value = 2;
  lp.connect(master);
  for (const f of [55, 55.6, 110.4]) {
    const o = ctx.createOscillator();
    o.type = 'sawtooth'; o.frequency.value = f;
    const g = ctx.createGain(); g.gain.value = 0.05;
    o.connect(g); g.connect(lp); o.start();
  }
  const lfo = ctx.createOscillator();
  lfo.frequency.value = 0.06;
  const lfoG = ctx.createGain(); lfoG.gain.value = 120;
  lfo.connect(lfoG); lfoG.connect(lp.frequency); lfo.start();
}

function tone(freq, dur, type = 'sine', gain = 0.25, delay = 0) {
  if (!ctx) return;
  const t0 = ctx.currentTime + delay;
  const o = ctx.createOscillator();
  o.type = type; o.frequency.value = freq;
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(gain, t0 + 0.02);
  g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
  o.connect(g); g.connect(master);
  o.start(t0); o.stop(t0 + dur + 0.1);
}

export const sfx = {
  chime()   { [523, 659, 784, 1047].forEach((f, i) => tone(f, 1.6, 'sine', 0.2, i * 0.09)); },
  bigChime(){ [262, 330, 392, 523, 659, 784].forEach((f, i) => tone(f, 2.8, 'sine', 0.22, i * 0.14)); },
  hit()     { tone(180, 0.12, 'square', 0.18); tone(1200, 0.06, 'triangle', 0.12); },
  hurt()    { tone(110, 0.3, 'sawtooth', 0.22); },
  swing()   { tone(700, 0.08, 'triangle', 0.1); },
  dash()    { tone(300, 0.16, 'sine', 0.14); tone(600, 0.1, 'sine', 0.1, 0.03); },
  shatter() { [1400, 1100, 900, 700, 500].forEach((f, i) => tone(f, 0.5, 'triangle', 0.16, i * 0.05)); },
};

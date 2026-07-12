import * as THREE from 'three';

// Shared procedural texture factory — canvas-authored maps used by every wing.

export function noiseCanvas(fn, size = 512) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  fn(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

// soft vertical light-shaft gradient
export function beamTexture() {
  const c = document.createElement('canvas');
  c.width = 64; c.height = 256;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, 'rgba(255,255,255,.9)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 256);
  const side = g.createLinearGradient(0, 0, 64, 0);
  side.addColorStop(0, 'rgba(0,0,0,1)');
  side.addColorStop(0.5, 'rgba(0,0,0,0)');
  side.addColorStop(1, 'rgba(0,0,0,1)');
  g.globalCompositeOperation = 'destination-out';
  g.fillStyle = side;
  g.fillRect(0, 0, 64, 256);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
}
export const BEAM_TEX = beamTexture();

// radial glow sprite
export const GLOW_TEX = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.4, 'rgba(255,255,255,.35)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();

// weathered masonry: stone courses, per-block tint, cracks, grime
export function stoneMaps(baseR, baseG, baseB) {
  const draw = (g, S, forBump) => {
    g.fillStyle = forBump ? '#808080' : `rgb(${baseR},${baseG},${baseB})`;
    g.fillRect(0, 0, S, S);
    const rows = 8, courseH = S / rows;
    for (let r = 0; r < rows; r++) {
      const off = (r % 2) * courseH;
      for (let x = -1; x < 5; x++) {
        const bw = S / 4, bx = x * bw + off;
        const v = (Math.random() - 0.5) * 26;
        g.fillStyle = forBump
          ? `rgb(${128 + v},${128 + v},${128 + v})`
          : `rgb(${baseR + v},${baseG + v},${baseB + v * 1.4})`;
        g.fillRect(bx + 2, r * courseH + 2, bw - 4, courseH - 4);
        g.fillStyle = forBump ? 'rgba(200,200,200,.35)' : 'rgba(160,170,220,.06)';
        g.fillRect(bx + 2, r * courseH + 2, bw - 4, 3);
      }
      g.fillStyle = forBump ? 'rgb(40,40,40)' : 'rgba(0,0,0,.5)';
      g.fillRect(0, r * courseH, S, 2);
    }
    g.strokeStyle = forBump ? 'rgba(30,30,30,.8)' : 'rgba(0,0,0,.35)';
    g.lineWidth = 1.5;
    for (let i = 0; i < 14; i++) {
      g.beginPath();
      let x = Math.random() * S, y = Math.random() * S;
      g.moveTo(x, y);
      for (let s = 0; s < 6; s++) { x += (Math.random() - 0.5) * 60; y += Math.random() * 40; g.lineTo(x, y); }
      g.stroke();
    }
    for (let i = 0; i < 40; i++) {
      const rr = 10 + Math.random() * 50;
      const gr = g.createRadialGradient(0, 0, 0, 0, 0, rr);
      gr.addColorStop(0, forBump ? 'rgba(90,90,90,.25)' : 'rgba(0,0,0,.16)');
      gr.addColorStop(1, 'rgba(0,0,0,0)');
      g.save();
      g.translate(Math.random() * S, Math.random() * S);
      g.fillStyle = gr;
      g.fillRect(-rr, -rr, rr * 2, rr * 2);
      g.restore();
    }
  };
  return {
    map: noiseCanvas((g, S) => draw(g, S, false)),
    bumpMap: noiseCanvas((g, S) => draw(g, S, true)),
  };
}

// worn plank wood
export function woodMaps() {
  const draw = (g, S, forBump) => {
    g.fillStyle = forBump ? '#808080' : '#241a2e';
    g.fillRect(0, 0, S, S);
    for (let y = 0; y < S; y += 4) {
      const v = (Math.random() - 0.5) * 18 + Math.sin(y * 0.1) * 8;
      g.fillStyle = forBump ? `rgba(${128 + v},${128 + v},${128 + v},.8)` : `rgba(${40 + v},${28 + v * 0.7},${52 + v},.55)`;
      g.fillRect(0, y, S, 3);
    }
    g.strokeStyle = forBump ? 'rgba(60,60,60,.9)' : 'rgba(0,0,0,.4)';
    for (let i = 0; i < 9; i++) {
      const y = Math.random() * S;
      g.beginPath(); g.moveTo(0, y); g.lineTo(S, y + (Math.random() - 0.5) * 20); g.stroke();
    }
  };
  return { map: noiseCanvas((g, S) => draw(g, S, false)), bumpMap: noiseCanvas((g, S) => draw(g, S, true)) };
}

// cloth weave
export function weaveMaps(hexColor) {
  const c = new THREE.Color(hexColor);
  const R = c.r * 255, G = c.g * 255, B = c.b * 255;
  const draw = (g, S, forBump) => {
    g.fillStyle = forBump ? '#808080' : `rgb(${R},${G},${B})`;
    g.fillRect(0, 0, S, S);
    for (let y = 0; y < S; y += 3) {
      g.fillStyle = forBump ? 'rgba(96,96,96,.5)' : 'rgba(0,0,0,.14)';
      g.fillRect(0, y, S, 1);
    }
    for (let x = 0; x < S; x += 3) {
      g.fillStyle = forBump ? 'rgba(160,160,160,.3)' : 'rgba(255,255,255,.05)';
      g.fillRect(x, 0, 1, S);
    }
    const fade = g.createLinearGradient(0, 0, 0, S);
    fade.addColorStop(0.75, 'rgba(0,0,0,0)');
    fade.addColorStop(1, 'rgba(0,0,0,.4)');
    g.fillStyle = fade;
    g.fillRect(0, 0, S, S);
  };
  return { map: noiseCanvas((g, S) => draw(g, S, false), 256), bumpMap: noiseCanvas((g, S) => draw(g, S, true), 256) };
}

// building facade: window grid, some lit, grime streaks (noir wing)
export function facadeMaps(lit = 0.18) {
  const draw = (g, S, forBump) => {
    g.fillStyle = forBump ? '#808080' : '#17171a';
    g.fillRect(0, 0, S, S);
    const cols = 6, rows = 9, cw = S / cols, rh = S / rows;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const x = c * cw + cw * 0.22, y = r * rh + rh * 0.18, w = cw * 0.56, h = rh * 0.6;
      const isLit = Math.random() < lit;
      if (forBump) {
        g.fillStyle = 'rgb(60,60,60)';
        g.fillRect(x - 2, y - 2, w + 4, h + 4);
        g.fillStyle = 'rgb(30,30,30)';
        g.fillRect(x, y, w, h);
      } else {
        g.fillStyle = isLit ? `rgba(${220 + Math.random() * 35},${215 + Math.random() * 30},200,1)` : 'rgb(8,8,10)';
        g.fillRect(x, y, w, h);
        if (isLit) { g.fillStyle = 'rgba(255,255,240,.25)'; g.fillRect(x - 3, y - 3, w + 6, h + 6); }
        g.strokeStyle = 'rgba(0,0,0,.8)';
        g.strokeRect(x, y, w, h);
      }
    }
    // grime streaks
    if (!forBump) for (let i = 0; i < 30; i++) {
      const x = Math.random() * S;
      g.fillStyle = 'rgba(0,0,0,.12)';
      g.fillRect(x, Math.random() * S * 0.3, 2 + Math.random() * 5, S);
    }
  };
  return { map: noiseCanvas((g, S) => draw(g, S, false)), bumpMap: noiseCanvas((g, S) => draw(g, S, true)) };
}

// wet asphalt
export function asphaltMaps() {
  const draw = (g, S, forBump) => {
    g.fillStyle = forBump ? '#808080' : '#141416';
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 2600; i++) {
      const v = Math.random() * 26;
      g.fillStyle = forBump ? `rgba(${110 + v},${110 + v},${110 + v},.5)` : `rgba(${18 + v},${18 + v},${20 + v},.6)`;
      g.fillRect(Math.random() * S, Math.random() * S, 2, 2);
    }
    // cracks + patches
    g.strokeStyle = forBump ? 'rgba(40,40,40,.9)' : 'rgba(0,0,0,.5)';
    for (let i = 0; i < 8; i++) {
      g.beginPath();
      let x = Math.random() * S, y = Math.random() * S;
      g.moveTo(x, y);
      for (let s = 0; s < 7; s++) { x += (Math.random() - 0.5) * 80; y += (Math.random() - 0.5) * 80; g.lineTo(x, y); }
      g.stroke();
    }
  };
  return { map: noiseCanvas((g, S) => draw(g, S, false)), bumpMap: noiseCanvas((g, S) => draw(g, S, true)) };
}

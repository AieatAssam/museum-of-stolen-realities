import * as THREE from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';
import {
  scene, mat, glow, addBoxCollider, addCylCollider, addGround,
} from './core.js';

// ============================================================
// The Stained Glass Kingdom — cathedral environment
// Nave runs along z: entrance z≈+58, altar z≈-38, rose window z≈-55.
// ============================================================

export const PALETTE = [0x2b54c9, 0xb22242, 0xe8b54a, 0x1a7a5e, 0x7a2bc9];
export const world = new THREE.Group();
scene.add(world);

// things main.js animates
export const anim = {
  panes: [],        // emissive stained panes (breathing)
  beams: [],        // god-ray planes
  shards: null,     // instanced floating shards
  shardData: [],
  saints: [],       // suspended silhouette panels
  slabs: [],        // floating glass slabs (traversal)
  resonators: [],   // {group, crystal, ring, light, pos, active}
  altar: {},        // {prism, socket, light, dais}
  windowsGroup: null,
  roseGroup: null,
  caustics: [],     // colored floor pools
};

// ---------- soft beam texture (canvas gradient) ----------
function beamTexture() {
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
const BEAM_TEX = beamTexture();

// radial glow sprite texture
function glowTexture() {
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
}
export const GLOW_TEX = glowTexture();

// ---------- procedural texture factory: color + matching bump ----------
function noiseCanvas(fn, size = 512) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  fn(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

// weathered masonry: courses of stone, per-block tint, cracks, grime
function stoneMaps(baseR, baseG, baseB) {
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
        // edge wear highlight on top edge
        g.fillStyle = forBump ? 'rgba(200,200,200,.35)' : 'rgba(160,170,220,.06)';
        g.fillRect(bx + 2, r * courseH + 2, bw - 4, 3);
      }
      // mortar line
      g.fillStyle = forBump ? 'rgb(40,40,40)' : 'rgba(0,0,0,.5)';
      g.fillRect(0, r * courseH, S, 2);
    }
    // cracks
    g.strokeStyle = forBump ? 'rgba(30,30,30,.8)' : 'rgba(0,0,0,.35)';
    g.lineWidth = 1.5;
    for (let i = 0; i < 14; i++) {
      g.beginPath();
      let x = Math.random() * S, y = Math.random() * S;
      g.moveTo(x, y);
      for (let s = 0; s < 6; s++) { x += (Math.random() - 0.5) * 60; y += Math.random() * 40; g.lineTo(x, y); }
      g.stroke();
    }
    // grime blotches
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

// worn plank wood for pews
function woodMaps() {
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

// cloth weave for banners
function weaveMaps(hexColor) {
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
    // age stains + fraying darkness at bottom
    const fade = g.createLinearGradient(0, 0, 0, S);
    fade.addColorStop(0.75, 'rgba(0,0,0,0)');
    fade.addColorStop(1, 'rgba(0,0,0,.4)');
    g.fillStyle = fade;
    g.fillRect(0, 0, S, S);
  };
  return { map: noiseCanvas((g, S) => draw(g, S, false), 256), bumpMap: noiseCanvas((g, S) => draw(g, S, true), 256) };
}

// ---------- glass material ----------
const paneMat = (color, intensity = 2.2) => new THREE.MeshStandardMaterial({
  color, emissive: color, emissiveIntensity: intensity,
  transparent: true, opacity: 0.92, roughness: 0.15, metalness: 0.1,
  side: THREE.DoubleSide,
});
const leadMat = mat(0x0a0a10, { roughness: 0.5, metalness: 0.7 });
const _stone = stoneMaps(58, 64, 96);
_stone.map.repeat.set(2, 2); _stone.bumpMap.repeat.set(2, 2);
const stoneMat = new THREE.MeshStandardMaterial({
  map: _stone.map, bumpMap: _stone.bumpMap, bumpScale: 2.2,
  roughness: 0.8, metalness: 0.12,
});
const _dark = stoneMaps(34, 40, 66);
_dark.map.repeat.set(3, 3); _dark.bumpMap.repeat.set(3, 3);
const darkStone = new THREE.MeshStandardMaterial({
  map: _dark.map, bumpMap: _dark.bumpMap, bumpScale: 2.0,
  roughness: 0.88, metalness: 0.08,
});
const _wood = woodMaps();
const pewWood = new THREE.MeshStandardMaterial({
  map: _wood.map, bumpMap: _wood.bumpMap, bumpScale: 1.4, roughness: 0.85,
});

// ---------- procedural floor tile texture ----------
function tileTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d');
  g.fillStyle = '#232941';
  g.fillRect(0, 0, 512, 512);
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
    const v = 28 + Math.random() * 14;
    g.fillStyle = `rgb(${v},${v + 5},${v + 22})`;
    g.fillRect(x * 64 + 2, y * 64 + 2, 60, 60);
    // worn highlight
    g.fillStyle = 'rgba(150,160,220,0.05)';
    g.fillRect(x * 64 + 2, y * 64 + 2, 60, 8);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(7, 16);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ============================================================
// FLOOR — polished stone + real mirror strip down the nave
// ============================================================
{
  const tileMap = tileTexture();
  const floor = new THREE.Mesh(
    new THREE.BoxGeometry(56, 1, 130),
    new THREE.MeshStandardMaterial({ map: tileMap, roughness: 0.35, metalness: 0.5 })
  );
  floor.position.set(0, -0.5, 0);
  floor.receiveShadow = true;
  world.add(floor); addGround(floor);

  // uneven worn-stone relief flanking the mirror aisle (real displaced geometry)
  const reliefMaps = stoneMaps(48, 54, 84);
  reliefMaps.map.repeat.set(4, 18); reliefMaps.bumpMap.repeat.set(4, 18);
  for (const sx of [-1, 1]) {
    const relief = new THREE.Mesh(
      new THREE.PlaneGeometry(20.5, 128, 40, 200),
      new THREE.MeshStandardMaterial({
        map: reliefMaps.map, bumpMap: reliefMaps.bumpMap, bumpScale: 1.6,
        displacementMap: reliefMaps.bumpMap, displacementScale: 0.22, displacementBias: -0.11,
        roughness: 0.55, metalness: 0.3,
      })
    );
    relief.rotation.x = -Math.PI / 2;
    relief.position.set(sx * 17.1, 0.04, 0);
    relief.receiveShadow = true;
    world.add(relief); addGround(relief);
  }

  // mirror strip — the processional aisle
  const mirror = new Reflector(new THREE.PlaneGeometry(13, 124), {
    textureWidth: 1024, textureHeight: 1024, color: 0x8890b8, clipBias: 0.003,
  });
  mirror.rotation.x = -Math.PI / 2;
  mirror.position.set(0, 0.02, 0);
  world.add(mirror);

  // inlay border lines
  for (const x of [-6.8, 6.8]) {
    const line = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.06, 124), glow(0xe8b54a, 0.5));
    line.position.set(x, 0.06, 0);
    world.add(line);
  }
  // side chapel floor (east)
  const chapel = new THREE.Mesh(new THREE.BoxGeometry(20, 1, 22), mat(0x0d0f1c, { roughness: 0.3, metalness: 0.5 }));
  chapel.position.set(36, -0.5, 6);
  chapel.receiveShadow = true;
  world.add(chapel); addGround(chapel);
}

// ============================================================
// COLUMNS + VAULT RIBS
// ============================================================
{
  const colGeo = new THREE.CylinderGeometry(1.1, 1.35, 34, 14);
  const capGeo = new THREE.CylinderGeometry(1.7, 1.15, 1.6, 14);
  for (let k = 0; k < 8; k++) {
    for (const x of [-15, 15]) {
      const z = 48 - k * 14;
      const col = new THREE.Mesh(colGeo, stoneMat);
      col.position.set(x, 17, z);
      col.castShadow = true;
      world.add(col);
      const cap = new THREE.Mesh(capGeo, stoneMat);
      cap.position.set(x, 33.5, z);
      world.add(cap);
      addCylCollider(x, z, 1.5);
      // rib arcs to center
      const rib = new THREE.Mesh(new THREE.TorusGeometry(15, 0.35, 8, 24, Math.PI), darkStone);
      rib.position.set(0, 34, z);
      rib.rotation.z = Math.PI;
      rib.rotation.y = 0;
      world.add(rib);
      // side arches along the colonnade
      const arch = new THREE.Mesh(new THREE.TorusGeometry(7, 0.3, 8, 20, Math.PI), darkStone);
      arch.position.set(x, 26, z - 7);
      arch.rotation.y = Math.PI / 2;
      world.add(arch);
    }
  }

  // pews — carved wood with end caps and a gold devotional line
  for (let r = 0; r < 9; r++) {
    for (const side of [-1, 1]) {
      const z = 40 - r * 7;
      const pew = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.9, 1.1), pewWood);
      pew.position.set(side * 11, 0.45, z);
      pew.castShadow = true; pew.receiveShadow = true;
      world.add(pew);
      const back = new THREE.Mesh(new THREE.BoxGeometry(6.5, 1.1, 0.18), pewWood);
      back.position.set(side * 11, 1.4, z + 0.45);
      back.castShadow = true;
      world.add(back);
      for (const ex of [-3.35, 3.35]) {
        const cap = new THREE.Mesh(new THREE.BoxGeometry(0.22, 1.7, 1.2), pewWood);
        cap.position.set(side * 11 + ex, 0.85, z + 0.1);
        world.add(cap);
      }
      const line = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.05, 0.05), glow(0xc8a35a, 0.3));
      line.position.set(side * 11, 1.96, z + 0.45);
      world.add(line);
      addBoxCollider(pew);
    }
  }

  // cornice trims running the length of both walls + pilaster strips
  for (const side of [-1, 1]) {
    for (const [ty, th] of [[12.5, 0.5], [30, 0.7]]) {
      const cornice = new THREE.Mesh(new THREE.BoxGeometry(0.8, th, 118), stoneMat);
      cornice.position.set(side * 21.9, ty, 0);
      world.add(cornice);
      const gold = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 118), glow(0xc8a35a, 0.35));
      gold.position.set(side * 21.4, ty + th / 2, 0);
      world.add(gold);
    }
  }

  // hanging banners — tall jewel-toned cloth with gold hem
  for (let k = 0; k < 6; k++) {
    const side = k % 2 ? -1 : 1;
    const z = 30 - k * 12;
    const banner = new THREE.Group();
    const wm = weaveMaps(PALETTE[k % 5]);
    const cloth = new THREE.Mesh(
      new THREE.PlaneGeometry(2.4, 9, 4, 10),
      new THREE.MeshStandardMaterial({
        map: wm.map, bumpMap: wm.bumpMap, bumpScale: 0.8,
        roughness: 0.92, side: THREE.DoubleSide,
      })
    );
    cloth.position.y = -4.5;
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 3, 8), glow(0xc8a35a, 0.4));
    rod.rotation.z = Math.PI / 2;
    const hem = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.22, 0.06), glow(0xc8a35a, 0.5));
    hem.position.y = -8.9;
    banner.add(cloth, rod, hem);
    banner.position.set(side * 13.5, 28, z);
    banner.userData.sway = Math.random() * 6;
    world.add(banner);
    anim.banners = anim.banners || [];
    anim.banners.push(banner);
  }
}

// ============================================================
// WALLS + LANCET WINDOWS
// ============================================================
function lancetWindow(color) {
  const g = new THREE.Group();
  const paneW = 1.05, paneH = 2.0;
  for (let r = 0; r < 5; r++) for (let q = 0; q < 2; q++) {
    const pane = new THREE.Mesh(new THREE.PlaneGeometry(paneW, paneH), paneMat(color, 0.9 + Math.random() * 0.6));
    pane.position.set((q - 0.5) * (paneW + 0.18), 2 + r * (paneH + 0.18), 0);
    g.add(pane);
    anim.panes.push(pane);
  }
  // pointed top
  const tip = new THREE.Mesh(new THREE.CircleGeometry(1.15, 3), paneMat(color, 1.4));
  tip.rotation.z = Math.PI / 2;
  tip.position.set(0, 13.1, 0);
  g.add(tip);
  anim.panes.push(tip);
  // lead frame + carved stone surround (window recess)
  const frame = new THREE.Mesh(new THREE.BoxGeometry(2.9, 12.4, 0.24), leadMat);
  frame.position.set(0, 7, -0.14);
  g.add(frame);
  const surround = new THREE.Mesh(new THREE.BoxGeometry(3.9, 13.6, 0.5), stoneMat);
  surround.position.set(0, 7, -0.5);
  g.add(surround);
  const sill = new THREE.Mesh(new THREE.BoxGeometry(4.3, 0.4, 0.9), stoneMat);
  sill.position.set(0, 0.4, -0.3);
  g.add(sill);
  return g;
}

{
  anim.windowsGroup = new THREE.Group();
  world.add(anim.windowsGroup);
  for (let k = 0; k < 8; k++) {
    const z = 41 - k * 14;
    for (const side of [-1, 1]) {
      // chapel doorway: leave a real opening in the east wall at z 2..10
      const isDoor = side === 1 && z === -1;
      if (isDoor) {
        const lintel = new THREE.Mesh(new THREE.BoxGeometry(1.4, 28, 14), darkStone);
        lintel.position.set(23, 22, 6);
        world.add(lintel); addBoxCollider(lintel);
        for (const jz of [0.25, 11.75]) {
          const jamb = new THREE.Mesh(new THREE.BoxGeometry(1.4, 8, 3.5), darkStone);
          jamb.position.set(23, 4, jz);
          world.add(jamb); addBoxCollider(jamb);
        }
        const frame = new THREE.Mesh(new THREE.BoxGeometry(0.4, 8.4, 0.4), glow(0x1a7a5e, 0.8));
        frame.position.set(22.6, 4.2, 2.1); world.add(frame);
        const frame2 = frame.clone(); frame2.position.z = 9.9; world.add(frame2);
        continue;
      }
      // contiguous wall segment — no accidental gaps into the void
      const wall = new THREE.Mesh(new THREE.BoxGeometry(1.4, 36, 14), darkStone);
      wall.position.set(side * 23, 18, z + 7);
      world.add(wall);
      addBoxCollider(wall);
      const win = lancetWindow(PALETTE[(k + (side > 0 ? 2 : 0)) % PALETTE.length]);
      win.position.set(side * 22.2, 8, z);
      win.rotation.y = side > 0 ? -Math.PI / 2 : Math.PI / 2;
      anim.windowsGroup.add(win);
    }
  }
  // entrance + far walls
  const back = new THREE.Mesh(new THREE.BoxGeometry(56, 40, 2), darkStone);
  back.position.set(0, 20, 62); world.add(back); addBoxCollider(back);
  // entrance glow: small rose above the door + flanking sconces
  {
    const mini = new THREE.Mesh(new THREE.CircleGeometry(4, 24), paneMat(0xe8b54a, 1.6));
    mini.position.set(0, 24, 60.8);
    mini.rotation.y = Math.PI;
    world.add(mini);
    anim.panes.push(mini);
    const entLight = new THREE.PointLight(0xd8b25c, 14, 30, 1.7);
    entLight.position.set(0, 12, 52);
    world.add(entLight);
    for (const x of [-8, 8]) {
      const sconce = new THREE.Mesh(new THREE.ConeGeometry(0.3, 1, 8), glow(0xe8b54a, 1.6));
      sconce.position.set(x, 6, 60.6);
      world.add(sconce);
    }
  }
  for (const x of [-17, 17]) {
    const fw = new THREE.Mesh(new THREE.BoxGeometry(24, 40, 2), darkStone);
    fw.position.set(x, 20, -56); world.add(fw); addBoxCollider(fw);
  }
  // chapel walls + dressing: a window, sconces, warm ceiling light
  const cw1 = new THREE.Mesh(new THREE.BoxGeometry(2, 26, 24), darkStone);
  cw1.position.set(46, 13, 6); world.add(cw1); addBoxCollider(cw1);
  for (const z of [-6, 18]) {
    const cw = new THREE.Mesh(new THREE.BoxGeometry(24, 26, 2), darkStone);
    cw.position.set(35, 13, z); world.add(cw); addBoxCollider(cw);
  }
  {
    const win = lancetWindow(0x1a7a5e);
    win.position.set(44.8, 4, 6);
    win.rotation.y = -Math.PI / 2;
    anim.windowsGroup.add(win);
    const ceil = new THREE.PointLight(0xd8b25c, 10, 22, 1.7);
    ceil.position.set(36, 12, 6);
    world.add(ceil);
    for (const sz of [-2, 14]) {
      const sconce = new THREE.Mesh(new THREE.ConeGeometry(0.25, 0.8, 8), glow(0xe8b54a, 1.6));
      sconce.position.set(44.6, 5.5, sz);
      world.add(sconce);
    }
  }
}

// ============================================================
// GREAT ROSE WINDOW (procedural, behind altar)
// ============================================================
{
  anim.roseGroup = new THREE.Group();
  const R = 13, rings = 3, center = new THREE.Vector2(0, 0);
  for (let ring = 0; ring < rings; ring++) {
    const r0 = 2.2 + ring * (R - 2.2) / rings;
    const r1 = 2.2 + (ring + 1) * (R - 2.2) / rings - 0.35;
    const sectors = 8 + ring * 4;
    for (let s = 0; s < sectors; s++) {
      const a0 = (s / sectors) * Math.PI * 2, a1 = ((s + 0.92) / sectors) * Math.PI * 2;
      const shape = new THREE.Shape();
      shape.absarc(center.x, center.y, r0, a0, a1, false);
      shape.absarc(center.x, center.y, r1, a1, a0, true);
      const pane = new THREE.Mesh(
        new THREE.ShapeGeometry(shape, 6),
        paneMat(PALETTE[(s + ring * 2) % PALETTE.length], 1.2)
      );
      anim.roseGroup.add(pane);
      anim.panes.push(pane);
    }
  }
  // heart of the rose — dark until climax
  const heart = new THREE.Mesh(new THREE.CircleGeometry(2.0, 24), paneMat(0x1c1230, 0.25));
  anim.roseGroup.add(heart);
  anim.roseHeart = heart;
  // stone ring + lead tracery spokes + trefoil crown
  const rim = new THREE.Mesh(new THREE.TorusGeometry(R + 0.5, 0.8, 10, 48), stoneMat);
  anim.roseGroup.add(rim);
  for (let s = 0; s < 16; s++) {
    const a = (s / 16) * Math.PI * 2;
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.22, R - 2, 0.2), leadMat);
    spoke.position.set(Math.cos(a) * (R / 2 + 1), Math.sin(a) * (R / 2 + 1), 0.05);
    spoke.rotation.z = a + Math.PI / 2;
    anim.roseGroup.add(spoke);
  }
  const ring1 = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.18, 8, 32), leadMat);
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry((2.2 + R) / 2, 0.16, 8, 40), leadMat);
  anim.roseGroup.add(ring1, ring2);
  for (let s = 0; s < 12; s++) {
    const a = (s / 12) * Math.PI * 2;
    const foil = new THREE.Mesh(new THREE.TorusGeometry(0.9, 0.12, 6, 16), leadMat);
    foil.position.set(Math.cos(a) * (R - 1.1), Math.sin(a) * (R - 1.1), 0.1);
    anim.roseGroup.add(foil);
  }
  anim.roseGroup.position.set(0, 20, -55.5);
  world.add(anim.roseGroup);
}

// ============================================================
// GOD RAYS — soft gradient beams from windows to floor
// ============================================================
{
  const mkBeam = (x, y, z, ry, rz, w, h, color, op) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({
        map: BEAM_TEX, color, transparent: true, opacity: op,
        blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide,
      })
    );
    m.position.set(x, y, z);
    m.rotation.set(0, ry, rz);
    m.userData.baseOp = op;
    m.layers.set(1);
    world.add(m);
    anim.beams.push(m);
  };
  for (let k = 0; k < 6; k++) {
    const z = 38 - k * 16;
    // shafts lean from the high windows down toward the nave center
    mkBeam(-13, 15, z, 0.25, 0.55, 10, 32, PALETTE[k % 5], 0.3);
    mkBeam(13, 15, z + 7, -0.25, -0.55, 10, 32, PALETTE[(k + 2) % 5], 0.26);
  }
  // grand beam through the rose window
  mkBeam(0, 16, -40, 0, 0.2, 16, 42, 0xe8b54a, 0.22);
}

// colored light pools on the floor under windows (fake caustics)
{
  for (let k = 0; k < 6; k++) {
    const z = 38 - k * 16;
    for (const side of [-1, 1]) {
      const pool = new THREE.Mesh(
        new THREE.CircleGeometry(3.4, 24),
        new THREE.MeshBasicMaterial({
          map: GLOW_TEX, color: PALETTE[(k + (side > 0 ? 2 : 0)) % 5],
          transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false,
        })
      );
      pool.rotation.x = -Math.PI / 2;
      pool.position.set(side * 11, 0.08, z + (side > 0 ? 7 : 0));
      pool.layers.set(1);
      world.add(pool);
      anim.caustics.push(pool);
    }
  }
}

// ============================================================
// SUSPENDED GLASS — floating shards + saint silhouettes
// ============================================================
{
  // fewer, smaller, colored shards drifting high in the vault — not confetti
  const N = 120;
  const geo = new THREE.TetrahedronGeometry(0.5);
  const m = new THREE.MeshStandardMaterial({
    color: 0xffffff, emissive: 0x000000, emissiveIntensity: 0,
    transparent: true, opacity: 0.6, roughness: 0.05, metalness: 0.3,
  });
  const inst = new THREE.InstancedMesh(geo, m, N);
  inst.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const color = new THREE.Color();
  for (let i = 0; i < N; i++) {
    const d = {
      pos: new THREE.Vector3((Math.random() - 0.5) * 40, 14 + Math.random() * 18, (Math.random() - 0.5) * 110),
      rot: new THREE.Euler(Math.random() * 6, Math.random() * 6, Math.random() * 6),
      spin: (Math.random() - 0.5) * 0.5,
      bob: Math.random() * Math.PI * 2,
      scale: 0.25 + Math.random() * 0.6,
    };
    anim.shardData.push(d);
    inst.setColorAt(i, color.set(PALETTE[i % 5]).multiplyScalar(0.9));
  }
  inst.instanceColor.needsUpdate = true;
  world.add(inst);
  anim.shards = inst;

  // saint panels — tall glass silhouettes rotating slowly in the air
  for (let i = 0; i < 7; i++) {
    const shape = new THREE.Shape();
    shape.moveTo(-1.1, 0); shape.lineTo(-1.4, 3.4); shape.lineTo(-0.6, 4.1);
    shape.lineTo(0, 5.2); shape.lineTo(0.6, 4.1); shape.lineTo(1.4, 3.4); shape.lineTo(1.1, 0);
    shape.closePath();
    const p = new THREE.Mesh(new THREE.ShapeGeometry(shape), paneMat(PALETTE[i % 5], 1.3));
    p.material.side = THREE.DoubleSide;
    p.material.opacity = 0.6;
    p.scale.setScalar(0.8);
    p.position.set((10 + Math.random() * 8) * (i % 2 ? -1 : 1), 15 + Math.random() * 12, 30 - i * 14);
    p.userData = { spin: 0.12 + Math.random() * 0.2, bob: Math.random() * 6 };
    world.add(p);
    anim.saints.push(p);
  }
}

// ============================================================
// HANGING CENSERS — chains from the vault, slow pendulum sway
// ============================================================
{
  anim.censers = [];
  for (let k = 0; k < 5; k++) {
    const g = new THREE.Group();
    const len = 9 + Math.random() * 5;
    const chain = new THREE.Mesh(
      new THREE.CylinderGeometry(0.045, 0.045, len, 6),
      mat(0x3a3428, { metalness: 0.9, roughness: 0.4 })
    );
    chain.position.y = -len / 2;
    const censer = new THREE.Group();
    const bowl = new THREE.Mesh(
      new THREE.SphereGeometry(0.5, 12, 10, 0, Math.PI * 2, 0, Math.PI * 0.6),
      mat(0x8a6a30, { metalness: 0.95, roughness: 0.3 })
    );
    bowl.rotation.x = Math.PI;
    const ember = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 8), glow(0xe8843a, 2.2));
    ember.position.y = 0.1;
    const emberLight = new THREE.PointLight(0xe8843a, 6, 12, 1.8);
    censer.add(bowl, ember, emberLight);
    censer.position.y = -len;
    g.add(chain, censer);
    g.position.set((k % 2 ? -8 : 8) + (Math.random() - 0.5) * 3, 33, 34 - k * 15);
    g.userData = { phase: Math.random() * 6, amp: 0.06 + Math.random() * 0.05 };
    world.add(g);
    anim.censers.push(g);
  }
}

// ============================================================
// TRAVERSAL — floating glass slabs up to the west gallery
// ============================================================
export function makeSlab(x, y, z, w = 3.4, d = 3.4, visible = true) {
  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(w, 0.35, d),
    new THREE.MeshStandardMaterial({
      color: 0x9db8ff, emissive: 0x4a6ae8, emissiveIntensity: 0.5,
      transparent: true, opacity: visible ? 0.55 : 0.0, roughness: 0.05, metalness: 0.2,
    })
  );
  slab.position.set(x, y, z);
  slab.userData = { baseY: y, bob: Math.random() * Math.PI * 2, on: visible };
  world.add(slab);
  anim.slabs.push(slab);
  if (visible) addGround(slab);
  return slab;
}

// west gallery ledge (resonator B lives up here)
{
  const ledge = new THREE.Mesh(new THREE.BoxGeometry(10, 1, 16), stoneMat);
  ledge.position.set(-18, 10, -6);
  world.add(ledge); addGround(ledge); addBoxCollider(ledge);
  // stairs of glass slabs — LOCKED until resonator A (spawned hidden).
  // The flight climbs OUTSIDE the ledge footprint (x > -13) and tops out
  // level with the ledge so the last hop lands cleanly on it.
  const steps = [
    [-4, 1.8, 10], [-7.5, 3.6, 7], [-10.5, 5.4, 3.5],
    [-12.4, 7.2, 0], [-12.4, 9.0, -3.5], [-12.2, 10.4, -6.5],
  ];
  anim.stairSlabs = steps.map(([x, y, z]) => makeSlab(x, y, z, 3.4, 3.4, false));
}

// ============================================================
// RESONATORS — three crystal pylons
// ============================================================
function makeResonator(x, y, z, color) {
  const g = new THREE.Group();
  const base = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.9, 1.2, 8), stoneMat);
  base.position.y = 0.6;
  const crystal = new THREE.Mesh(
    new THREE.OctahedronGeometry(1.1),
    new THREE.MeshStandardMaterial({
      color, emissive: color, emissiveIntensity: 0.35,
      transparent: true, opacity: 0.9, roughness: 0.05,
    })
  );
  crystal.material.emissiveIntensity = 1.4;
  crystal.position.y = 2.8;
  crystal.scale.set(0.7, 1.15, 0.7);
  // inner heart glow + orbiting motes
  const heart = new THREE.Sprite(new THREE.SpriteMaterial({
    map: GLOW_TEX, color, transparent: true, opacity: 0.85,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  heart.scale.setScalar(2.6);
  heart.position.y = 2.8;
  const motes = new THREE.Group();
  for (let i = 0; i < 5; i++) {
    const mote = new THREE.Mesh(new THREE.OctahedronGeometry(0.09), glow(color, 1.8));
    mote.userData = { a: (i / 5) * Math.PI * 2, r: 1.15 + (i % 2) * 0.3, h: 2.2 + i * 0.3 };
    motes.add(mote);
  }
  motes.position.y = 0;
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(1.8, 0.06, 8, 40),
    glow(color, 0.4)
  );
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 1.4;
  const light = new THREE.PointLight(color, 20, 20);
  light.position.y = 3;
  g.add(base, crystal, ring, light, heart, motes);
  g.position.set(x, y, z);
  world.add(g);
  addCylCollider(x, z, 1.6);
  const r = { group: g, crystal, ring, light, motes, pos: new THREE.Vector3(x, y, z), active: false, color };
  anim.resonators.push(r);
  return r;
}
makeResonator(36, 0, 6, 0x1a7a5e);       // A — side chapel
makeResonator(-18, 10.5, -10, 0x7a2bc9); // B — west gallery ledge
makeResonator(14, 0, -46, 0xb22242);     // C — far transept, warden territory

// ============================================================
// ALTAR OF THE HEART PRISM
// ============================================================
{
  const dais = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 6.5, 1.4, 24), stoneMat);
  dais.position.set(0, 0.7, -38);
  world.add(dais); addGround(dais);
  const steps = new THREE.Mesh(new THREE.CylinderGeometry(7.5, 8.5, 0.6, 24), darkStone);
  steps.position.set(0, 0.3, -38);
  world.add(steps); addGround(steps);
  const daisTrim = new THREE.Mesh(new THREE.TorusGeometry(5.6, 0.08, 8, 48), glow(0xc8a35a, 0.5));
  daisTrim.rotation.x = Math.PI / 2;
  daisTrim.position.set(0, 1.42, -38);
  world.add(daisTrim);

  const socket = new THREE.Mesh(new THREE.TorusGeometry(1.3, 0.14, 10, 40), glow(0xe8b54a, 0.6));
  socket.position.set(0, 3.4, -38);
  world.add(socket);

  // the Heart Prism — hovers dim and cracked until restored
  const prism = new THREE.Mesh(
    new THREE.OctahedronGeometry(0.95),
    new THREE.MeshStandardMaterial({
      color: 0x3a2a4a, emissive: 0x8a2be2, emissiveIntensity: 0.15,
      transparent: true, opacity: 0.85, roughness: 0.1,
    })
  );
  prism.scale.y = 1.5;
  prism.position.set(0, 3.4, -38);
  world.add(prism);

  const light = new THREE.PointLight(0xe8b54a, 18, 28);
  light.position.set(0, 5, -38);
  world.add(light);

  anim.altar = { prism, socket, light, pos: new THREE.Vector3(0, 0, -38) };
}

// ============================================================
// LIGHTS + DUST
// ============================================================
export const hemi = new THREE.HemisphereLight(0x6a7ade, 0x141830, 1.7);
scene.add(hemi);
export const moon = new THREE.DirectionalLight(0x9eb0f4, 1.6);
moon.position.set(20, 50, 30);
moon.castShadow = true;
moon.shadow.mapSize.set(2048, 2048);
moon.shadow.camera.left = -60; moon.shadow.camera.right = 60;
moon.shadow.camera.top = 70; moon.shadow.camera.bottom = -70;
scene.add(moon);
scene.add(new THREE.AmbientLight(0x3a4470, 1.2));

// one coherent scheme: cool cobalt nave, warm gold processional axis
for (let k = 0; k < 4; k++) {
  const axis = new THREE.PointLight(0xd8b25c, 9, 24, 1.7);
  axis.position.set(0, 6, 40 - k * 26);
  scene.add(axis);
}
// two jewel accents only — cobalt near entrance, violet mid-nave
const jewelA = new THREE.PointLight(0x2b54c9, 12, 30, 1.7);
jewelA.position.set(-12, 10, 30); scene.add(jewelA);
const jewelB = new THREE.PointLight(0x7a2bc9, 12, 30, 1.7);
jewelB.position.set(12, 10, -10); scene.add(jewelB);

export let dust;
{
  const n = 900, pos = new Float32Array(n * 3);
  for (let k = 0; k < n; k++) {
    pos[k * 3] = (Math.random() - 0.5) * 50;
    pos[k * 3 + 1] = Math.random() * 32;
    pos[k * 3 + 2] = (Math.random() - 0.5) * 120;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  dust = new THREE.Points(g, new THREE.PointsMaterial({
    map: GLOW_TEX, color: 0xc8b28a, size: 0.22, transparent: true, opacity: 0.18,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  dust.layers.set(1);
  scene.add(dust);
}

// ============================================================
// per-frame environment animation
// ============================================================
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
export function updateWorld(t, dt) {
  // breathing panes
  for (let i = 0; i < anim.panes.length; i++) {
    const p = anim.panes[i];
    p.material.emissiveIntensity = (p.userData.boost || 1) * (1.0 + Math.sin(t * 0.7 + i * 1.7) * 0.25);
  }
  // beams sway
  for (let i = 0; i < anim.beams.length; i++) {
    const b = anim.beams[i];
    b.material.opacity = b.userData.baseOp * (1 + Math.sin(t * 0.5 + i) * 0.35);
    b.rotation.z += Math.sin(t * 0.11 + i) * 0.00035;
  }
  // caustic pools pulse
  for (let i = 0; i < anim.caustics.length; i++) {
    const c = anim.caustics[i];
    c.material.opacity = 0.28 + Math.sin(t * 0.6 + i * 2.1) * 0.1;
    c.scale.setScalar(1 + Math.sin(t * 0.4 + i) * 0.08);
  }
  // floating shards
  const inst = anim.shards;
  for (let i = 0; i < anim.shardData.length; i++) {
    const d = anim.shardData[i];
    d.rot.y += d.spin * dt;
    d.rot.x += d.spin * 0.6 * dt;
    _p.copy(d.pos);
    _p.y += Math.sin(t * 0.5 + d.bob) * 0.6;
    _q.setFromEuler(d.rot);
    _s.setScalar(d.scale);
    _m.compose(_p, _q, _s);
    inst.setMatrixAt(i, _m);
  }
  inst.instanceMatrix.needsUpdate = true;
  // saints rotate
  for (const s of anim.saints) {
    s.rotation.y += s.userData.spin * dt;
    s.position.y += Math.sin(t * 0.4 + s.userData.bob) * 0.004;
  }
  // slabs bob
  for (const s of anim.slabs) {
    s.position.y = s.userData.baseY + Math.sin(t * 0.8 + s.userData.bob) * 0.18;
  }
  // resonators idle
  for (const r of anim.resonators) {
    r.crystal.rotation.y += dt * (r.active ? 2.2 : 0.4);
    r.ring.rotation.z += dt * 0.6;
    for (const m of r.motes.children) {
      const d = m.userData;
      d.a += dt * (r.active ? 1.8 : 0.5);
      m.position.set(Math.cos(d.a) * d.r, d.h + Math.sin(t * 1.4 + d.a) * 0.2, Math.sin(d.a) * d.r);
      m.rotation.y += dt * 2;
    }
    if (r.active) {
      r.light.intensity = 26 + Math.sin(t * 5) * 6;
      r.crystal.material.emissiveIntensity = 1.8 + Math.sin(t * 5) * 0.5;
    }
  }
  // altar prism
  const a = anim.altar;
  a.prism.rotation.y += dt * 0.5;
  a.prism.position.y = 3.4 + Math.sin(t * 1.2) * 0.15;
  a.socket.rotation.z += dt * 0.3;
  // dust drift
  dust.rotation.y = t * 0.006;
  // banners sway
  if (anim.banners) for (const b of anim.banners) {
    b.rotation.x = Math.sin(t * 0.5 + b.userData.sway) * 0.06;
    b.rotation.z = Math.cos(t * 0.35 + b.userData.sway) * 0.04;
  }
  // censers swing as slow pendulums
  if (anim.censers) for (const c of anim.censers) {
    c.rotation.x = Math.sin(t * 0.7 + c.userData.phase) * c.userData.amp;
    c.rotation.z = Math.cos(t * 0.55 + c.userData.phase) * c.userData.amp * 0.7;
  }
  // colored floor pools slowly wander, like light through moving glass
  for (let i = 0; i < anim.caustics.length; i++) {
    anim.caustics[i].rotation.z = t * 0.05 * (i % 2 ? 1 : -1);
    anim.caustics[i].position.x += Math.sin(t * 0.13 + i * 2.6) * 0.002;
  }
}

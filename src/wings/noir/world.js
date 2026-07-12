import * as THREE from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';
import {
  scene, mat, glow, addBoxCollider, addGround,
} from '../../engine/core.js';
import { BEAM_TEX, GLOW_TEX, facadeMaps, asphaltMaps, reliefPlane } from '../../engine/textures.js';

// ============================================================
// Wing III — The Long Shadow. A monochrome noir city at 3:11 a.m.
// Rain, wet asphalt, lit windows, sweeping searchlights.
// The only true color in the wing is the Curator's red.
// ============================================================

export const world = new THREE.Group();
scene.add(world);

// wing atmosphere: dense grey rain-fog, black sky
scene.fog.color.set(0x0b0b0e);
scene.fog.density = 0.016;
scene.background.set(0x08080b);

export const anim = {
  neon: [],        // flickering signs
  lampPools: [],
  beams: [],
  searchlights: [],
  steam: [],
  projectors: [],  // activation nodes {group, head, light, pos, active, color}
  escapes: [],     // fire-escape platforms
  marquee: {},     // relic site
  rain: null,
  colorables: [],  // {mat, grey, color} — for the 11-second color flood
};

// grayscale palette helpers
const g05 = 0x0d0d10, g2 = 0x1c1c20, g4 = 0x3a3a40, g7 = 0x77777d, gW = 0xf2f2ee;

function colorable(material, floodColor) {
  anim.colorables.push({ mat: material, grey: material.color.clone(), color: new THREE.Color(floodColor) });
  return material;
}

// ---------- street ----------
{
  const am = asphaltMaps();
  am.map.repeat.set(4, 14); am.bumpMap.repeat.set(4, 14);
  const street = new THREE.Mesh(
    new THREE.BoxGeometry(30, 1, 130),
    new THREE.MeshStandardMaterial({ map: am.map, bumpMap: am.bumpMap, bumpScale: 1.6, roughness: 0.5, metalness: 0.25 })
  );
  street.position.set(0, -0.5, 0);
  street.receiveShadow = true;
  world.add(street); addGround(street);

  // displaced worn asphalt flanking the mirror lane — real relief geometry
  for (const sx of [-1, 1]) {
    const rm = asphaltMaps();
    rm.map.repeat.set(2, 16); rm.bumpMap.repeat.set(2, 16);
    const lane = reliefPlane({
      width: 9, height: 126, wSegs: 24, hSegs: 200, maps: rm,
      dispScale: 0.16, matOpts: { roughness: 0.45, metalness: 0.3 },
    });
    lane.position.set(sx * 9.6, 0.05, 0);
    world.add(lane); addGround(lane);
  }

  // rain-wet mirror down the middle of the road
  const mirror = new Reflector(new THREE.PlaneGeometry(10, 124), {
    textureWidth: 1024, textureHeight: 1024, color: 0x556, clipBias: 0.003,
  });
  mirror.rotation.x = -Math.PI / 2;
  mirror.position.set(0, 0.02, 0);
  world.add(mirror);

  // lane line, worn
  for (let z = -55; z < 60; z += 8) {
    const dash = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.03, 4), mat(0x8a8a80, { roughness: 0.9 }));
    dash.position.set(0, 0.06, z);
    world.add(dash);
  }

  // sidewalks + curbs
  for (const side of [-1, 1]) {
    const walk = new THREE.Mesh(new THREE.BoxGeometry(6, 1.3, 130), mat(0x26262b, { roughness: 0.85 }));
    walk.position.set(side * 12, -0.35, 0);
    walk.receiveShadow = true;
    world.add(walk); addGround(walk); addBoxCollider(walk);
    const curb = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.35, 130), mat(0x3d3d44, { roughness: 0.7 }));
    curb.position.set(side * 9.1, 0.12, 0);
    world.add(curb);
  }
}

// ---------- buildings ----------
function building(x, z, w, d, h, lit = 0.3) {
  const fm = facadeMaps(lit);
  fm.map.repeat.set(Math.max(1, Math.round(w / 8)), Math.max(1, Math.round(h / 10)));
  fm.bumpMap.repeat.copy(fm.map.repeat);
  const b = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    new THREE.MeshStandardMaterial({ map: fm.map, bumpMap: fm.bumpMap, bumpScale: 3.2, roughness: 0.75 })
  );
  b.position.set(x, h / 2, z);
  b.castShadow = true; b.receiveShadow = true;
  world.add(b);
  addBoxCollider(b);
  // parapet
  const cap = new THREE.Mesh(new THREE.BoxGeometry(w + 0.5, 0.5, d + 0.5), mat(g2, { roughness: 0.9 }));
  cap.position.set(x, h + 0.25, z);
  world.add(cap);
  return b;
}

{
  // front row — canyon walls
  const rows = [
    [-18, 46, 9, 10, 24], [-19, 30, 10, 12, 34], [-17, 12, 8, 12, 20],
    [-19, -6, 11, 13, 38], [-18, -24, 9, 11, 26], [-19, -44, 11, 14, 30],
    [18, 46, 9, 11, 28], [18, 28, 8, 12, 22],
    [18, 8, 8, 12, 12],            // low rooftop — node B lives up here
    [19, -10, 10, 12, 36], [18, -26, 8, 10, 18], [19, -46, 11, 13, 32],
  ];
  for (const [x, z, w, d, h] of rows) building(x, z, w, d, h);

  // the low rooftop is playable
  const roof = new THREE.Mesh(new THREE.BoxGeometry(8, 0.4, 12), mat(0x2a2a30, { roughness: 0.9 }));
  roof.position.set(18, 12.2, 8);
  world.add(roof); addGround(roof);

  // background row — taller silhouettes for depth
  for (let i = 0; i < 10; i++) {
    const x = (i % 2 ? -1 : 1) * (30 + Math.random() * 8);
    const h = 34 + Math.random() * 22;
    const b = new THREE.Mesh(new THREE.BoxGeometry(10 + Math.random() * 6, h, 12), mat(0x0f0f13, { roughness: 1 }));
    b.position.set(x, h / 2, 50 - i * 12);
    world.add(b);
  }
  // street ends
  for (const z of [63, -63]) {
    const wall = new THREE.Mesh(new THREE.BoxGeometry(70, 44, 2), mat(g05, { roughness: 1 }));
    wall.position.set(0, 22, z);
    world.add(wall); addBoxCollider(wall);
  }
}

// ---------- fire escape up to the rooftop (node B) ----------
{
  const railMat = mat(0x6a6a76, { metalness: 0.9, roughness: 0.35 });
  const steps = [
    [10, 1.6, 15], [12.5, 3.4, 13], [14.5, 5.2, 15], [14.5, 7.0, 17.5],
    [14.5, 8.8, 15], [14.7, 10.6, 12.4], [15.5, 11.9, 14.3],
  ];
  let prev = null;
  for (const [x, y, z] of steps) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.22, 2.6), railMat);
    p.position.set(x, y, z);
    p.castShadow = true;
    world.add(p); addGround(p);
    // glowing rails on both open sides so the route reads at a glance
    for (const dz of [-1.25, 1.25]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.06, 0.06), glow(0xfff4d8, 0.9));
      rail.position.set(x, y + 0.6, z + dz);
      world.add(rail);
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.6, 0.06), railMat);
      post.position.set(x - 1.2, y + 0.3, z + dz);
      world.add(post);
    }
    // small landing lamp
    const lampGlow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: GLOW_TEX, color: 0xfff0d0, transparent: true, opacity: 0.5,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    lampGlow.scale.setScalar(1.6);
    lampGlow.position.set(x, y + 1.1, z);
    world.add(lampGlow);
    const pl = new THREE.PointLight(0xfff0d0, 4, 7, 1.8);
    pl.position.set(x, y + 1, z);
    world.add(pl);
    // diagonal stringer connecting to the previous landing
    if (prev) {
      const dir = new THREE.Vector3(x - prev[0], y - prev[1], z - prev[2]);
      const len = dir.length();
      const beam = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, len), railMat);
      beam.position.set((x + prev[0]) / 2, (y + prev[1]) / 2, (z + prev[2]) / 2);
      beam.lookAt(new THREE.Vector3(x, y, z));
      world.add(beam);
    }
    prev = [x, y, z];
    anim.escapes.push(p);
  }
}

// ---------- streetlamps ----------
function lamp(x, z) {
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 6.5, 8), mat(0x222228, { metalness: 0.8, roughness: 0.5 }));
  pole.position.set(x, 3.25, z);
  world.add(pole);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.28, 10, 8), glow(0xfff4d8, 2.4));
  head.position.set(x, 6.6, z);
  world.add(head);
  const light = new THREE.PointLight(0xfff0d0, 20, 26, 1.7);
  light.position.set(x, 6.3, z);
  world.add(light);
  // volumetric cone
  const cone = new THREE.Mesh(
    new THREE.PlaneGeometry(4.5, 7),
    new THREE.MeshBasicMaterial({ map: BEAM_TEX, color: 0xfff0d0, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })
  );
  cone.position.set(x, 3.4, z);
  cone.layers.set(1);
  world.add(cone);
  anim.beams.push(cone);
  // light pool
  const pool = new THREE.Mesh(
    new THREE.CircleGeometry(3, 20),
    new THREE.MeshBasicMaterial({ map: GLOW_TEX, color: 0xfff0d0, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  pool.rotation.x = -Math.PI / 2;
  pool.position.set(x, 0.09, z);
  pool.layers.set(1);
  world.add(pool);
  anim.lampPools.push(pool);
}
for (let k = 0; k < 8; k++) lamp(k % 2 ? -10.4 : 10.4, 48 - k * 14);

// ---------- neon signage (abstract bars + one red intrusion) ----------
function neonBar(x, y, z, w, h, color, ry = 0) {
  const bar = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.12), glow(color, 1.8));
  bar.position.set(x, y, z);
  bar.rotation.y = ry;
  bar.userData.flicker = Math.random() * 10;
  world.add(bar);
  anim.neon.push(bar);
  return bar;
}
{
  neonBar(13.6, 9, 30, 0.3, 5, gW, Math.PI / 2);
  neonBar(-13.4, 12, 18, 0.3, 7, gW, Math.PI / 2);
  neonBar(13.6, 14, -12, 4, 0.35, gW, Math.PI / 2);
  neonBar(-13.4, 8, -30, 0.3, 4, gW, Math.PI / 2);
  neonBar(-13.4, 16, 40, 3, 0.3, gW, Math.PI / 2);
}

// ---------- searchlights sweeping the sky ----------
for (const side of [-1, 1]) {
  const beam = new THREE.Mesh(
    new THREE.PlaneGeometry(3, 46),
    new THREE.MeshBasicMaterial({ map: BEAM_TEX, color: 0xdfe6ff, transparent: true, opacity: 0.13, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })
  );
  beam.geometry.translate(0, 23, 0);
  beam.position.set(side * 24, 26, side > 0 ? -20 : 24);
  beam.layers.set(1);
  world.add(beam);
  anim.searchlights.push(beam);
}

// ---------- rain ----------
{
  const n = 1600, pos = new Float32Array(n * 3);
  for (let k = 0; k < n; k++) {
    pos[k * 3] = (Math.random() - 0.5) * 60;
    pos[k * 3 + 1] = Math.random() * 34;
    pos[k * 3 + 2] = (Math.random() - 0.5) * 124;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  anim.rain = new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0x9aa0b8, size: 0.08, transparent: true, opacity: 0.55,
  }));
  scene.add(anim.rain);
}

// ---------- steam from grates ----------
for (let k = 0; k < 4; k++) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({
    map: GLOW_TEX, color: 0x555560, transparent: true, opacity: 0.16,
    blending: THREE.NormalBlending, depthWrite: false,
  }));
  s.position.set(k % 2 ? -7 : 7, 1, 26 - k * 20);
  s.userData.phase = Math.random() * 5;
  scene.add(s);
  anim.steam.push(s);
}

// footage texture: flickering abstract frames, redrawn each activation pulse
function footageCanvas() {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 160;
  return { canvas: c, tex: new THREE.CanvasTexture(c) };
}
export function drawFootage(f, t, colorful = 0) {
  const g = f.canvas.getContext('2d');
  const W = 256, H = 160;
  g.fillStyle = '#0a0a0c';
  g.fillRect(0, 0, W, H);
  // sweeping silhouette skyline + circling searchlight, like an old newsreel
  g.fillStyle = colorful ? `hsl(${(t * 40) % 360},70%,60%)` : '#e8e8e0';
  const n = 7;
  for (let i = 0; i < n; i++) {
    const h = 40 + 50 * Math.abs(Math.sin(i * 2.4 + t * 0.7));
    g.fillRect(i * (W / n) + 4, H - h, W / n - 8, h);
  }
  g.strokeStyle = colorful ? '#fff' : '#f2f2ee';
  g.lineWidth = 5;
  g.beginPath();
  const a = t * 1.6;
  g.moveTo(W / 2, H);
  g.lineTo(W / 2 + Math.cos(a) * 130, H - Math.abs(Math.sin(a)) * 150);
  g.stroke();
  // grain
  for (let i = 0; i < 220; i++) {
    g.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,.12)' : 'rgba(0,0,0,.2)';
    g.fillRect(Math.random() * W, Math.random() * H, 2, 2);
  }
  if (Math.random() < 0.06) { g.fillStyle = 'rgba(255,255,255,.1)'; g.fillRect(0, 0, W, H); }
  f.tex.needsUpdate = true;
}

// ---------- activation nodes: three film projectors ----------
function projector(x, y, z) {
  const g = new THREE.Group();
  const legMat = mat(0x2c2c33, { metalness: 0.85, roughness: 0.4 });
  for (let i = 0; i < 3; i++) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 2, 6), legMat);
    const a = (i / 3) * Math.PI * 2;
    leg.position.set(Math.sin(a) * 0.5, 1, Math.cos(a) * 0.5);
    leg.rotation.z = Math.sin(a) * 0.3;
    leg.rotation.x = -Math.cos(a) * 0.3;
    g.add(leg);
  }
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.7, 1.3), mat(0x3a3a42, { metalness: 0.9, roughness: 0.35 }));
  body.position.y = 2.3;
  const reel = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.08, 8, 20), legMat);
  reel.position.set(0, 3.0, -0.3);
  const lens = new THREE.Mesh(new THREE.SphereGeometry(0.18, 10, 8), glow(gW, 0.4));
  lens.position.set(0, 2.3, 0.75);
  const light = new THREE.PointLight(0xffffff, 0.0, 16);
  light.position.y = 2.4;
  g.add(body, reel, lens, light);
  g.position.set(x, y, z);
  world.add(g);
  const node = { group: g, reel, lens, light, pos: new THREE.Vector3(x, y, z), active: false, color: 0xf2f2ee };
  anim.projectors.push(node);
  return node;
}
// each projector throws a cone of light and a flickering picture onto the facing wall
function aimProjector(node, wallX, wallZ, ry, w = 7, h = 4.4) {
  const from = node.pos.clone().add(new THREE.Vector3(0, 2.3, 0));
  const to = new THREE.Vector3(wallX, from.y + 1.2, wallZ);
  const dir = to.clone().sub(from);
  const len = dir.length();
  const beam = new THREE.Mesh(
    new THREE.PlaneGeometry(2.2, len),
    new THREE.MeshBasicMaterial({ map: BEAM_TEX, color: 0xfff8e0, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })
  );
  beam.position.copy(from).addScaledVector(dir, 0.5);
  beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  beam.layers.set(1);
  world.add(beam);
  const f = footageCanvas();
  const img = new THREE.Mesh(
    new THREE.PlaneGeometry(w, h),
    new THREE.MeshBasicMaterial({ map: f.tex, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  img.position.set(wallX, from.y + 1.2, wallZ);
  img.rotation.y = ry;
  world.add(img);
  node.beam = beam; node.img = img; node.footage = f;
}
projector(8, 0, 20);        // A — street plaza
projector(18, 12.4, 8);     // B — the low rooftop
projector(-10, 0, -28);     // C — guardian's plaza
aimProjector(anim.projectors[0], -13.3, 18, Math.PI / 2);
aimProjector(anim.projectors[1], 13.4, -6, -Math.PI / 2, 8, 5);
aimProjector(anim.projectors[2], 13.9, -26, -Math.PI / 2);

// ---------- the cinema + marquee altar (relic site) ----------
{
  const cin = new THREE.Group();
  // marquee slab over the entrance
  const marq = new THREE.Mesh(new THREE.BoxGeometry(12, 2.4, 3), mat(0x222228, { roughness: 0.6, metalness: 0.4 }));
  marq.position.set(0, 6, -56);
  world.add(marq);
  // the one color in the city: the Curator's red sign
  const redSign = new THREE.Mesh(new THREE.BoxGeometry(10, 1.1, 0.2), glow(0xb22242, 1.6));
  redSign.position.set(0, 6, -54.4);
  world.add(redSign);
  anim.neon.push(redSign);
  // ticket-booth dais + hovering film frame (the Undeveloped Negative)
  const dais = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 3.2, 0.8, 18), mat(0x2c2c33, { roughness: 0.6 }));
  dais.position.set(0, 0.4, -50);
  world.add(dais); addGround(dais);
  const frame = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.0, 0.06), mat(0x111114, { roughness: 0.3 }));
  frame.position.set(0, 2.6, -50);
  world.add(frame);
  const negative = new THREE.Mesh(new THREE.PlaneGeometry(1.15, 0.78), glow(0x9aa0b8, 0.5, { side: THREE.DoubleSide }));
  negative.position.set(0, 2.6, -50.04);
  world.add(negative);
  const light = new THREE.PointLight(0xdfe6ff, 6, 16);
  light.position.set(0, 4, -50);
  world.add(light);
  // the picture house screen: framed white sheet high on the end wall
  const screenFrame = new THREE.Mesh(new THREE.BoxGeometry(21, 12.4, 0.5), mat(0x0c0c0f, { roughness: 0.6 }));
  screenFrame.position.set(0, 14, -61.6);
  world.add(screenFrame);
  const screenF = footageCanvas();
  const screen = new THREE.Mesh(
    new THREE.PlaneGeometry(20, 11.4),
    new THREE.MeshStandardMaterial({ color: 0x3c3c42, emissive: 0xffffff, emissiveIntensity: 0.25, emissiveMap: screenF.tex, map: screenF.tex, roughness: 0.9 })
  );
  screen.position.set(0, 14, -61.2);
  world.add(screen);
  anim.screen = { mesh: screen, footage: screenF, playing: false, colorful: 0 };

  anim.marquee = { frame, negative, light, redSign, pos: new THREE.Vector3(0, 0.8, -50) };
  world.add(cin);
}

// ---------- lighting: cold moon + sodium accents ----------
export const hemi = new THREE.HemisphereLight(0x6a7088, 0x14141c, 1.65);
scene.add(hemi);
export const moon = new THREE.DirectionalLight(0xc8d2f0, 1.5);
moon.position.set(-30, 60, 20);
moon.castShadow = true;
moon.shadow.mapSize.set(2048, 2048);
moon.shadow.camera.left = -60; moon.shadow.camera.right = 60;
moon.shadow.camera.top = 70; moon.shadow.camera.bottom = -70;
scene.add(moon);
scene.add(new THREE.AmbientLight(0x363a4c, 1.5));

// ---------- dawn sun + rainbow (revealed by the climax) ----------
export const dawn = { sun: null, sunLight: null, rainbow: null };
{
  dawn.sun = new THREE.Sprite(new THREE.SpriteMaterial({
    map: GLOW_TEX, color: 0xffd9a0, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  dawn.sun.scale.setScalar(46);
  dawn.sun.position.set(-16, 20, -110);
  scene.add(dawn.sun);
  dawn.sunLight = new THREE.DirectionalLight(0xffc878, 0);
  dawn.sunLight.position.set(-18, 26, -110);
  scene.add(dawn.sunLight);
  // rainbow: seven nested translucent arcs over the skyline
  dawn.rainbow = new THREE.Group();
  const RB = [0xff4444, 0xff9a3c, 0xffe14a, 0x4ade6a, 0x3ca8ff, 0x5a6cff, 0xa05aff];
  RB.forEach((c, i) => {
    const arc = new THREE.Mesh(
      new THREE.TorusGeometry(46 - i * 1.6, 0.7, 8, 64, Math.PI),
      new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })
    );
    dawn.rainbow.add(arc);
  });
  dawn.rainbow.position.set(6, 8, -100);
  scene.add(dawn.rainbow);
}

// ---------- the color flood (climax) ----------
export const flood = { k: 0, target: 0 };
const FLOOD_NEON = [0x2b54c9, 0xb22242, 0xe8b54a, 0x1a7a5e, 0x7a2bc9];

// ---------- per-frame ----------
export function updateWorld(t, dt) {
  // rain falls
  {
    const p = anim.rain.geometry.attributes.position;
    for (let k = 0; k < p.count; k++) {
      let y = p.getY(k) - dt * (18 + (k % 7));
      if (y < 0) y = 34;
      p.setY(k, y);
    }
    p.needsUpdate = true;
  }
  // neon flicker
  for (const n of anim.neon) {
    const f = Math.sin(t * 17 + n.userData.flicker * 13) > -0.92 ? 1 : 0.25;
    n.material.emissiveIntensity = (n === anim.marquee.redSign ? 1.6 : 1.8) * f;
  }
  // searchlights sweep
  anim.searchlights.forEach((b, i) => {
    b.rotation.z = Math.sin(t * 0.17 + i * 2.4) * 0.5 * (i ? 1 : -1);
  });
  // steam rises and loops
  for (const s of anim.steam) {
    const k = ((t * 0.25 + s.userData.phase) % 1);
    s.position.y = 0.5 + k * 5;
    s.scale.setScalar(1.5 + k * 4);
    s.material.opacity = 0.18 * (1 - k);
  }
  // lamp pools shimmer in the rain
  anim.lampPools.forEach((p, i) => {
    p.material.opacity = 0.18 + Math.sin(t * 2.2 + i * 1.7) * 0.05;
  });
  // projectors: spin, glow, and actually PROJECT
  for (const n of anim.projectors) {
    n.reel.rotation.z += dt * (n.active ? 4 : 0.3);
    if (n.active) {
      n.light.intensity = 18 + Math.sin(t * 7) * 4;
      n.lens.material.emissiveIntensity = 2.2 + Math.sin(t * 7) * 0.6;
      if (n.beam) {
        const flick = 0.9 + Math.sin(t * 23 + n.pos.x) * 0.1;
        n.beam.material.opacity = Math.min(0.22, n.beam.material.opacity + dt * 0.2) * flick;
        n.img.material.opacity = Math.min(0.75, n.img.material.opacity + dt * 0.5) * flick;
        if ((t * 12 | 0) % 2 === 0) drawFootage(n.footage, t + n.pos.z, flood.k > 0.05 ? 1 : 0);
      }
    }
  }
  // the picture house screen
  if (anim.screen.playing && (t * 12 | 0) % 2 === 0) {
    drawFootage(anim.screen.footage, t, anim.screen.colorful);
    anim.screen.mesh.material.emissiveIntensity = 2.4 + Math.sin(t * 19) * 0.5;
  }
  // dawn + rainbow rise with the flood
  if (flood.k > 0.01) {
    dawn.sun.material.opacity = flood.k * 0.95;
    dawn.sun.position.y = 24 + flood.k * 32;
    dawn.sunLight.intensity = flood.k * 2.6;
    dawn.rainbow.children.forEach((arc, i) => {
      arc.material.opacity = Math.max(0, flood.k - i * 0.04) * 0.5;
    });
  } else {
    dawn.sun.material.opacity *= 0.98;
    dawn.rainbow.children.forEach(a => a.material.opacity *= 0.98);
    dawn.sunLight.intensity *= 0.98;
  }
  // negative hovers
  anim.marquee.negative.position.y = 2.6 + Math.sin(t * 1.3) * 0.1;

  // color flood lerp — eleven seconds of technicolor
  flood.k += (flood.target - flood.k) * dt * 1.2;
  if (flood.k > 0.01) {
    const k = flood.k;
    anim.neon.forEach((n, i) => {
      if (n === anim.marquee.redSign) return;
      n.material.emissive.lerpColors(new THREE.Color(gW), new THREE.Color(FLOOD_NEON[i % 5]), k);
      n.material.color.copy(n.material.emissive);
      n.material.emissiveIntensity = 1.8 + k * 1.2;
    });
    anim.lampPools.forEach((p, i) => {
      p.material.color.lerpColors(new THREE.Color(0xfff0d0), new THREE.Color(FLOOD_NEON[(i + 1) % 5]), k);
      p.material.opacity = 0.2 + k * 0.25;
    });
    anim.beams.forEach((b, i) => {
      b.material.color.lerpColors(new THREE.Color(0xfff0d0), new THREE.Color(FLOOD_NEON[(i + 2) % 5]), k);
      b.material.opacity = 0.1 + k * 0.14;
    });
    anim.searchlights.forEach((b, i) => {
      b.material.color.lerpColors(new THREE.Color(0xdfe6ff), new THREE.Color(i ? 0xe8b54a : 0x2b54c9), k);
      b.material.opacity = 0.13 + k * 0.12;
    });
    anim.rain.material.color.lerpColors(new THREE.Color(0x9aa0b8), new THREE.Color(0x9ad4ff), k);
    hemi.color.lerpColors(new THREE.Color(0x555a70), new THREE.Color(0xb09ae8), k);
    hemi.intensity = 1.65 + k * 1.3;
    scene.fog.color.lerpColors(new THREE.Color(0x0b0b0e), new THREE.Color(0x35406e), k);
    scene.background.copy(scene.fog.color);
  }
}

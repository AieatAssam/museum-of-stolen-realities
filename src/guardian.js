import * as THREE from 'three';
import { scene, mat, glow, ui, shake, addBoxCollider, addGround } from './core.js';
import { PALETTE, GLOW_TEX } from './world.js';
import { player, damagePlayer, attackHits, burstSparks } from './player.js';

// ============================================================
// The Rose Warden — a crowned angel of stained glass.
// Dormant: a grey statue exhibit kneeling before the rose window.
// Awake: colors ignite, a rose-wheel halo spins behind it, four
// glass wings flare, and a storm of shards orbits — the shards
// are harmless glass; only its attacks hurt. After each attack
// it is EXPOSED: shards retract, core burns gold, double damage.
// ============================================================

export const warden = {
  group: new THREE.Group(),
  pos: new THREE.Vector3(0, 2.9, -46),
  home: new THREE.Vector3(0, 2.9, -46),
  hp: 10, maxHp: 10,
  state: 'dormant',   // dormant | waking | patrol | volley | sweep | exposed | stagger | dead
  stateT: 0,
  aggro: false,
  dead: false,
  flash: 0,
  ignite: 0,          // 0 = grey statue, 1 = full stained glass
  nearDormant: false,
};

// ---------- glass-figure parts (grey until ignited) ----------
const parts = []; // {mesh, color, ei}
const GREY = new THREE.Color(0x5a5a68);
function glassPart(geo, color, ei = 1.0) {
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
    color: GREY.clone(), transparent: true, opacity: 0.96,
    roughness: 0.12, metalness: 0.15,
  }));
  m.castShadow = true;
  parts.push({ mesh: m, color: new THREE.Color(color), ei });
  return m;
}

let torso, head, eye, wheel, wings = [], arms = [], shardCloud;
const shardData = [];
{
  const g = warden.group;

  torso = glassPart(new THREE.OctahedronGeometry(0.95, 0), 0xb22242, 0.7);
  torso.scale.set(1, 1.6, 0.65);

  const chest = glassPart(new THREE.OctahedronGeometry(0.5, 0), 0x7a2bc9, 0.9);
  chest.scale.set(1, 1.1, 0.7);
  chest.position.set(0, 0.55, 0.25);

  head = glassPart(new THREE.OctahedronGeometry(0.34, 0), 0x2b54c9, 0.9);
  head.scale.set(1, 1.25, 0.9);
  head.position.y = 1.95;

  eye = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 10), glow(0xffffff, 2.6));
  eye.position.set(0, 1.98, 0.3);

  // crown of five glass thorns
  for (let i = 0; i < 5; i++) {
    const thorn = glassPart(new THREE.ConeGeometry(0.07, 0.5, 5), 0xe8b54a, 1.2);
    const a = ((i - 2) / 5) * Math.PI * 1.1;
    thorn.position.set(Math.sin(a) * 0.32, 2.35 + Math.cos(a) * 0.1, 0);
    thorn.rotation.z = -a * 0.8;
    g.add(thorn);
  }

  // rose-wheel halo: ring, spokes, colored roundels — the boss IS a rose window
  wheel = new THREE.Group();
  const rim = glassPart(new THREE.TorusGeometry(2.1, 0.09, 8, 48), 0xe8b54a, 0.9);
  wheel.add(rim);
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    const spoke = glassPart(new THREE.BoxGeometry(0.07, 1.9, 0.07), 0xe8b54a, 0.7);
    spoke.position.set(Math.cos(a) * 1.05, Math.sin(a) * 1.05, 0);
    spoke.rotation.z = a + Math.PI / 2;
    wheel.add(spoke);
    const pane = glassPart(new THREE.CircleGeometry(0.34, 12), PALETTE[i % 5], 1.5);
    pane.position.set(Math.cos(a + 0.39) * 1.45, Math.sin(a + 0.39) * 1.45, 0.02);
    pane.material.side = THREE.DoubleSide;
    wheel.add(pane);
  }
  wheel.position.set(0, 1.2, -0.55);
  g.add(wheel);

  // four glass wings
  const wingShape = new THREE.Shape();
  wingShape.moveTo(0, 0); wingShape.quadraticCurveTo(0.9, 0.5, 1.5, 2.1);
  wingShape.quadraticCurveTo(0.7, 1.7, 0, 1.1); wingShape.closePath();
  for (let i = 0; i < 4; i++) {
    const wing = glassPart(new THREE.ShapeGeometry(wingShape, 8), PALETTE[(i * 2 + 1) % 5], 1.1);
    wing.material.side = THREE.DoubleSide;
    const side = i % 2 ? -1 : 1;
    const up = i < 2 ? 1 : 0.45;
    wing.position.set(side * 0.5, 0.6 + up * 0.5, -0.35);
    wing.scale.set(side * (0.8 + up * 0.5), 0.8 + up * 0.5, 1);
    wing.userData = { side, up, i };
    wings.push(wing);
    g.add(wing);
  }

  // two shard arms
  for (const side of [-1, 1]) {
    const arm = glassPart(new THREE.TetrahedronGeometry(0.45), 0x1a7a5e, 0.8);
    arm.scale.set(0.7, 1.9, 0.7);
    arm.position.set(side * 1.15, 0.4, 0.15);
    arm.rotation.z = side * 0.5;
    arms.push(arm);
    g.add(arm);
  }

  g.add(torso, chest, head, eye);

  // orbiting shard storm (visual only — never damages)
  const N = 90;
  shardCloud = new THREE.InstancedMesh(
    new THREE.TetrahedronGeometry(0.3),
    new THREE.MeshStandardMaterial({
      color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.2,
      transparent: true, opacity: 0.88, roughness: 0.12, metalness: 0.25,
    }),
    N
  );
  shardCloud.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const col = new THREE.Color();
  for (let i = 0; i < N; i++) {
    shardData.push({
      r: 2.0 + Math.random() * 1.6,
      a: Math.random() * Math.PI * 2,
      y: (Math.random() - 0.5) * 2.6,
      sp: 0.8 + Math.random() * 1.6,
      sc: 0.5 + Math.random() * 0.9,
      scatter: 0,
    });
    shardCloud.setColorAt(i, col.set(PALETTE[i % 5]));
  }
  shardCloud.instanceColor.needsUpdate = true;
  shardCloud.visible = false; // hidden while it is a statue
  g.add(shardCloud);

  g.position.copy(warden.pos);
  scene.add(g);

  // museum plinth under the "exhibit" + collider so the statue is solid
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.4, 0.9, 20), mat(0x232941, { roughness: 0.6 }));
  plinth.position.set(warden.home.x, 0.45, warden.home.z);
  plinth.receiveShadow = true;
  scene.add(plinth);
  addBoxCollider(plinth); // low box: blocks walking through, steppable on top
  addGround(plinth);
  warden._plinth = plinth;
}

const underGlow = new THREE.Sprite(new THREE.SpriteMaterial({
  map: GLOW_TEX, color: 0xb22242, transparent: true, opacity: 0,
  blending: THREE.AdditiveBlending, depthWrite: false,
}));
underGlow.scale.setScalar(7);
scene.add(underGlow);

// ---------- projectiles ----------
const bolts = [];
for (let i = 0; i < 12; i++) {
  const b = new THREE.Mesh(new THREE.ConeGeometry(0.18, 0.9, 6), glow(0xb22242, 2.5));
  b.visible = false;
  scene.add(b);
  bolts.push({ mesh: b, vel: new THREE.Vector3(), life: 0 });
}
function fireBolt(from, to, speed = 16) {
  for (const b of bolts) {
    if (b.life > 0) continue;
    b.life = 4;
    b.mesh.visible = true;
    b.mesh.position.copy(from);
    b.vel.copy(to).sub(from).normalize().multiplyScalar(speed);
    b.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.vel.clone().normalize());
    return;
  }
}

function setState(s, t = 0) { warden.state = s; warden.stateT = t; }

// statue stirs: called at Resonance II — main.js stages the cinematic around it
export function wakeWarden() {
  if (warden.state !== 'dormant') return;
  setState('waking');
  warden.aggro = true;
  shardCloud.visible = true;
  ui.bossname.textContent = 'The Rose Warden';
  ui.bossbar.classList.add('show');
}

export function wardenTakeHit() {
  const dmg = warden.state === 'exposed' ? 2 : 1;
  warden.hp -= dmg;
  warden.flash = 0.25;
  ui.bossfill.style.width = `${Math.max(0, warden.hp / warden.maxHp) * 100}%`;
  burstSparks(warden.pos, 0xf4dfa0, 10);
  shake(0.3);
  for (const d of shardData) d.scatter = 1;
  if (warden.hp <= 0 && !warden.dead) {
    warden.dead = true;
    setState('dead');
    ui.bossbar.classList.remove('show');
    return 'killed';
  }
  if (warden.state !== 'exposed') setState('stagger', 0);
  return 'hit';
}

// ---------- per-frame ----------
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
const _e = new THREE.Euler();
const GOLD = new THREE.Color(0xe8b54a);

export function updateWarden(dt, t) {
  const w = warden;
  w.stateT += dt;
  w.flash = Math.max(0, w.flash - dt);

  const toPlayer = player.pos.clone().add(new THREE.Vector3(0, 1.4, 0)).sub(w.pos);
  const dist = toPlayer.length();

  // --- state machine ---
  if (w.state === 'dormant') {
    // kneeling grey statue on its plinth
    w.pos.set(w.home.x, 2.0, w.home.z);
    w.nearDormant = dist < 8;
  } else if (w.state === 'waking') {
    // 2.6 s ignition: rise off the plinth, colors flood in, shards spin out
    w.ignite = Math.min(1, w.stateT / 2.2);
    w.pos.y = 2.0 + w.ignite * 0.9;
    if (w.stateT > 2.6) setState('patrol');
  } else if (w.state === 'patrol') {
    const desired = player.pos.clone().add(new THREE.Vector3(0, 2.6, 0));
    const dir = desired.sub(w.pos);
    const d = dir.length();
    if (d > 6) w.pos.addScaledVector(dir.normalize(), dt * 5);
    else if (d < 3) w.pos.addScaledVector(dir.normalize(), -dt * 4);
    w.pos.y = 2.6 + Math.sin(t * 1.1) * 0.5;
    if (w.stateT > 2.4 && dist < 26) {
      setState(Math.random() < 0.6 ? 'volley' : 'sweep');
    }
  } else if (w.state === 'volley') {
    if (w.stateT < 0.7) {
      wheel.scale.setScalar(1 + w.stateT * 0.6);
    } else if (!w._fired) {
      w._fired = true;
      fireBolt(w.pos, player.pos.clone().add(new THREE.Vector3(0, 1.2, 0)));
      setTimeout(() => fireBolt(w.pos.clone(), player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))), 220);
      setTimeout(() => fireBolt(w.pos.clone(), player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))), 440);
    }
    if (w.stateT > 1.5) { w._fired = false; wheel.scale.setScalar(1); setState('exposed'); }
  } else if (w.state === 'sweep') {
    if (w.stateT < 0.6) {
      if (!w._target) w._target = player.pos.clone().add(new THREE.Vector3(0, 1.6, 0));
    } else if (w.stateT < 1.2) {
      const dir = w._target.clone().sub(w.pos);
      if (dir.length() > 0.5) w.pos.addScaledVector(dir.normalize(), dt * 34);
      if (w.pos.distanceTo(player.pos.clone().add(new THREE.Vector3(0, 1.6, 0))) < 2.2) {
        damagePlayer(1, w.pos);
      }
    } else { w._target = null; setState('exposed'); }
  } else if (w.state === 'exposed') {
    // vulnerable window: shards retract, core burns gold — STRIKE NOW
    if (w.stateT > 2.2) setState('patrol');
  } else if (w.state === 'stagger') {
    if (w.stateT > 0.9) setState('patrol');
  } else if (w.state === 'dead') {
    for (const d of shardData) { d.scatter = Math.min(3.5, d.scatter + dt * 2.4); d.sp *= 0.99; }
    w.pos.y = Math.max(0.8, w.pos.y - dt * 0.8);
    w.group.scale.multiplyScalar(Math.max(0.0, 1 - dt * 0.35));
  }

  // --- player hits (any awake state except death) ---
  if (!w.dead && w.state !== 'dormant' && w.state !== 'waking' && attackHits(w.pos, 3.4)) {
    if (!w._hitThisSwing) {
      w._hitThisSwing = true;
      const r = wardenTakeHit();
      if (r === 'killed') return 'killed';
    }
  }
  if (player.attackAnim <= 0) w._hitThisSwing = false;

  // --- visuals ---
  w.group.position.copy(w.pos);
  if (w.state !== 'dormant') {
    w.group.lookAt(player.pos.x, w.pos.y, player.pos.z);
  } else {
    w.group.rotation.set(0.35, Math.PI, 0); // statue bows toward the nave
  }

  // ignition: grey statue -> stained glass
  const exposedGlow = w.state === 'exposed' ? (0.5 + Math.sin(t * 9) * 0.5) : 0;
  for (const p of parts) {
    const m = p.mesh.material;
    m.color.lerpColors(GREY, p.color, w.ignite);
    if (w.flash > 0) {
      m.emissive.setRGB(1, 1, 1); m.emissiveIntensity = 1.6;
    } else if (exposedGlow > 0) {
      m.emissive.lerpColors(p.color, GOLD, exposedGlow); m.emissiveIntensity = p.ei * (0.6 + exposedGlow);
    } else {
      m.emissive.copy(p.color); m.emissiveIntensity = p.ei * w.ignite * (0.55 + Math.sin(t * 1.3) * 0.1);
    }
  }
  eye.material.emissiveIntensity = 0.4 + w.ignite * 2.2;
  eye.material.color.set(w.ignite > 0.5 ? 0xb22242 : 0x777788);
  eye.material.emissive.copy(eye.material.color);

  // wheel spins when awake, wings breathe / flare
  wheel.rotation.z += dt * (0.15 + w.ignite * (w.state === 'volley' ? 2.4 : 0.5));
  const attacking = w.state === 'volley' || w.state === 'sweep';
  for (const wing of wings) {
    const { side, up, i } = wing.userData;
    const spread = w.ignite * (attacking ? 1.2 : 0.75 + Math.sin(t * 1.6 + i) * 0.1);
    wing.rotation.z = side * (0.35 + up * 0.4) * spread;
    wing.rotation.y = side * 0.35 * spread;
  }
  for (const arm of arms) arm.rotation.x = w.ignite * Math.sin(t * 1.8) * 0.15 - (attacking ? 0.7 : 0);

  underGlow.position.set(w.pos.x, 0.15, w.pos.z);
  underGlow.material.color.set(w.state === 'exposed' ? 0xe8b54a : 0xb22242);
  underGlow.material.opacity = w.dead
    ? Math.max(0, underGlow.material.opacity - dt * 0.3)
    : w.ignite * (0.3 + Math.sin(t * 2) * 0.08);

  // shard storm — tight orbit; flares out when attacking; retracts when exposed
  const radiusK = w.state === 'exposed' ? 0.45 : attacking ? 1.6 : 1;
  for (let i = 0; i < shardData.length; i++) {
    const d = shardData[i];
    d.a += d.sp * dt * (attacking ? 2.2 : 1);
    d.scatter = Math.max(0, d.scatter - dt * 1.4);
    const r = (d.r * radiusK + d.scatter * 3) * Math.max(w.ignite, w.dead ? 1 : 0);
    _p.set(Math.cos(d.a) * r, d.y + (attacking ? Math.sin(d.a * 2) * 1.2 : 0), Math.sin(d.a) * r * 0.7);
    _e.set(d.a, d.a * 1.3, 0);
    _q.setFromEuler(_e);
    _s.setScalar(d.sc);
    _m.compose(_p, _q, _s);
    shardCloud.setMatrixAt(i, _m);
  }
  shardCloud.instanceMatrix.needsUpdate = true;

  // --- bolts ---
  for (const b of bolts) {
    if (b.life <= 0) continue;
    b.life -= dt;
    b.mesh.position.addScaledVector(b.vel, dt);
    b.mesh.rotation.z += dt * 8;
    if (b.mesh.position.distanceTo(player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))) < 1.1) {
      damagePlayer(1, b.mesh.position);
      b.life = 0;
    }
    if (b.life <= 0) b.mesh.visible = false;
  }
  return null;
}

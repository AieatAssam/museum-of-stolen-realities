import * as THREE from 'three';
import { scene, mat, glow, ui, shake } from './core.js';
import { PALETTE, GLOW_TEX } from './world.js';
import { player, damagePlayer, attackHits, burstSparks } from './player.js';

// ============================================================
// The Rose Warden — a guardian of fractured stained glass.
// Core of dark lead, orbited by a storm of colored shards that
// form wings when it attacks. States: dormant → patrol →
// volley → sweep → stagger → shatter (death).
// ============================================================

export const warden = {
  group: new THREE.Group(),
  pos: new THREE.Vector3(0, 3.2, -46),
  home: new THREE.Vector3(0, 3.2, -46),
  hp: 10, maxHp: 10,
  state: 'dormant',      // dormant | patrol | volley | sweep | stagger | dead
  stateT: 0,
  aggro: false,
  dead: false,
  flash: 0,
};

// ---------- body ----------
let core, halo, shardCloud;
const shardData = [];
{
  const g = warden.group;
  core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1.1, 1),
    mat(0x0c0a14, { roughness: 0.3, metalness: 0.9 })
  );
  core.castShadow = true;
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.34, 14, 14), glow(0xb22242, 2.2));
  eye.position.set(0, 0, 0.95);
  halo = new THREE.Mesh(new THREE.TorusGeometry(2.6, 0.07, 8, 48), glow(0xb22242, 0.8));
  g.add(core, eye, halo);

  const N = 90;
  shardCloud = new THREE.InstancedMesh(
    new THREE.TetrahedronGeometry(0.34),
    new THREE.MeshStandardMaterial({
      color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.22,
      transparent: true, opacity: 0.9, roughness: 0.12, metalness: 0.25,
    }),
    N
  );
  shardCloud.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const col = new THREE.Color();
  for (let i = 0; i < N; i++) {
    shardData.push({
      r: 1.8 + Math.random() * 1.6,
      a: Math.random() * Math.PI * 2,
      y: (Math.random() - 0.5) * 2.4,
      sp: 0.8 + Math.random() * 1.6,
      sc: 0.5 + Math.random() * 0.9,
      scatter: 0,
    });
    shardCloud.setColorAt(i, col.set(PALETTE[i % 5]));
  }
  shardCloud.instanceColor.needsUpdate = true;
  g.add(shardCloud);
  g.position.copy(warden.pos);
  scene.add(g);
}

// glow sprite under it
const underGlow = new THREE.Sprite(new THREE.SpriteMaterial({
  map: GLOW_TEX, color: 0xb22242, transparent: true, opacity: 0.4,
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

export function wakeWarden() {
  if (warden.state === 'dormant') {
    setState('patrol');
    warden.aggro = true;
    ui.bossname.textContent = 'The Rose Warden';
    ui.bossbar.classList.add('show');
  }
}

export function wardenTakeHit() {
  warden.hp -= 1;
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
  setState('stagger', 0);
  return 'hit';
}

// ---------- per-frame ----------
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
const _e = new THREE.Euler();

export function updateWarden(dt, t) {
  const w = warden;
  w.stateT += dt;
  w.flash = Math.max(0, w.flash - dt);

  const toPlayer = player.pos.clone().add(new THREE.Vector3(0, 1.4, 0)).sub(w.pos);
  const dist = toPlayer.length();

  // --- state machine ---
  if (w.state === 'dormant') {
    w.pos.y = w.home.y + Math.sin(t * 0.5) * 0.3;
  } else if (w.state === 'patrol') {
    // drift toward player, keep midrange
    const desired = player.pos.clone().add(new THREE.Vector3(0, 3.2, 0));
    const dir = desired.sub(w.pos);
    const d = dir.length();
    if (d > 7) w.pos.addScaledVector(dir.normalize(), dt * 5);
    else if (d < 4.5) w.pos.addScaledVector(dir.normalize(), -dt * 4);
    w.pos.y = 3.2 + Math.sin(t * 1.1) * 0.5;
    if (w.stateT > 2.6 && dist < 26) {
      setState(Math.random() < 0.6 ? 'volley' : 'sweep');
    }
  } else if (w.state === 'volley') {
    // telegraph 0.7s (halo swells), then 3 bolts
    if (w.stateT < 0.7) {
      halo.scale.setScalar(1 + w.stateT * 1.2);
    } else if (!w._fired) {
      w._fired = true;
      const target = player.pos.clone().add(new THREE.Vector3(0, 1.2, 0));
      fireBolt(w.pos, target);
      setTimeout(() => fireBolt(w.pos.clone(), player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))), 220);
      setTimeout(() => fireBolt(w.pos.clone(), player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))), 440);
    }
    if (w.stateT > 1.6) { w._fired = false; halo.scale.setScalar(1); setState('patrol'); }
  } else if (w.state === 'sweep') {
    // wind up then dash through the player's position
    if (w.stateT < 0.6) {
      if (!w._target) w._target = player.pos.clone().add(new THREE.Vector3(0, 1.6, 0));
      core.rotation.y += dt * 12;
    } else if (w.stateT < 1.2) {
      const dir = w._target.clone().sub(w.pos);
      if (dir.length() > 0.5) w.pos.addScaledVector(dir.normalize(), dt * 34);
      if (w.pos.distanceTo(player.pos.clone().add(new THREE.Vector3(0, 1.6, 0))) < 2.2) {
        damagePlayer(1, w.pos);
      }
    } else { w._target = null; setState('patrol'); }
  } else if (w.state === 'stagger') {
    // vulnerable pause; shards scattered
    if (w.stateT > 0.9) setState('patrol');
  } else if (w.state === 'dead') {
    // shatter outward, sink, fade
    for (const d of shardData) { d.scatter = Math.min(3.5, d.scatter + dt * 2.4); d.sp *= 0.99; }
    w.pos.y = Math.max(0.8, w.pos.y - dt * 0.8);
    core.scale.multiplyScalar(1 - dt * 0.4);
    halo.material.opacity = Math.max(0, (halo.material.opacity ?? 1) - dt);
    halo.material.transparent = true;
  }

  // --- contact damage (body) ---
  if (!w.dead && w.state !== 'dormant' && dist < 2.4) damagePlayer(1, w.pos);

  // --- player hits ---
  if (!w.dead && w.state !== 'dormant' && attackHits(w.pos, 3.2)) {
    if (!w._hitThisSwing) {
      w._hitThisSwing = true;
      const r = wardenTakeHit();
      if (r === 'killed') return 'killed';
    }
  }
  if (player.attackAnim <= 0) w._hitThisSwing = false;

  // --- visuals ---
  w.group.position.copy(w.pos);
  w.group.lookAt(player.pos.x, w.pos.y, player.pos.z);
  core.rotation.x += dt * 0.7;
  core.material.emissive = new THREE.Color(w.flash > 0 ? 0xffffff : 0x000000);
  core.material.emissiveIntensity = w.flash > 0 ? 2 : 0;
  halo.rotation.x = Math.PI / 2 + Math.sin(t * 0.8) * 0.2;
  halo.rotation.z += dt * 0.5;
  underGlow.position.set(w.pos.x, 0.15, w.pos.z);
  underGlow.material.opacity = w.dead ? Math.max(0, underGlow.material.opacity - dt * 0.3) : 0.35 + Math.sin(t * 2) * 0.1;

  // shard cloud — orbit tight, flare into "wings" when attacking, scatter on hit
  const attacking = w.state === 'volley' || w.state === 'sweep';
  for (let i = 0; i < shardData.length; i++) {
    const d = shardData[i];
    d.a += d.sp * dt * (attacking ? 2.2 : 1);
    d.scatter = Math.max(0, d.scatter - dt * 1.4);
    const wing = attacking ? Math.abs(Math.sin(d.a)) * 2.2 : 0;
    const r = d.r + wing + d.scatter * 3;
    _p.set(Math.cos(d.a) * r, d.y + (attacking ? Math.sin(d.a * 2) * 1.4 : 0), Math.sin(d.a) * r * 0.7);
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

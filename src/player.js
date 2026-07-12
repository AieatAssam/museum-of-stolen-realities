import * as THREE from 'three';
import {
  scene, camera, input, mat, glow, resolveCollisions, groundHeightAt,
  shake, ui,
} from './core.js';
import { GLOW_TEX } from './world.js';

// ============================================================
// Vesper — the Reality Thief. Procedural animation:
// idle breathing, run lean+bob, cloak sway, landing squash,
// attack swing with additive trail, dash with FOV kick + ghosts.
// ============================================================

export const player = {
  group: new THREE.Group(),
  pos: new THREE.Vector3(0, 0, 52),
  vel: new THREE.Vector3(),
  yaw: Math.PI,             // facing -z (toward altar)
  onGround: true,
  hp: 5, maxHp: 5,
  iframes: 0,
  attackCd: 0, attackAnim: 0,
  dashCd: 0, dashTime: 0,
  jumps: 0,
  speed: 11,
  spawn: new THREE.Vector3(0, 0, 52),
  dead: false,
  moveLocked: false,
};

// ---------- build the character ----------
// Vesper floats a hand-span above the floor: layered robes, gold circlet,
// long ribbon scarf, slim crescent blade. Dreamy, weightless, readable.
let cloak, innerSkirt, hood, scarf, blade, bladePivot, body, circlet, hem;
{
  const g = player.group;
  const robeMat = mat(0x453f7d, { roughness: 0.7 });
  const robeDark = mat(0x2c2758, { roughness: 0.8 });

  const skirtProfile = (flare, h) => {
    const pts = [];
    for (let i = 0; i <= 14; i++) {
      const v = i / 14;
      // gentle S-curve: narrow waist, soft bell hem
      const r = 0.13 + Math.pow(v, 1.6) * flare + Math.sin(v * Math.PI) * 0.05;
      pts.push(new THREE.Vector2(r, h - v * h));
    }
    return pts;
  };
  cloak = new THREE.Mesh(new THREE.LatheGeometry(skirtProfile(0.52, 1.5), 24), robeMat);
  cloak.position.y = 0.42;
  cloak.castShadow = true;

  innerSkirt = new THREE.Mesh(new THREE.LatheGeometry(skirtProfile(0.42, 1.42), 24), robeDark);
  innerSkirt.position.y = 0.36;

  // luminous hem — a floating ring of gold light at the robe's edge
  hem = new THREE.Mesh(new THREE.TorusGeometry(0.58, 0.016, 8, 40), glow(0xe8c46a, 0.4));
  hem.rotation.x = Math.PI / 2;
  hem.position.y = 0.38;

  body = new THREE.Mesh(new THREE.CapsuleGeometry(0.13, 0.42, 4, 12), robeDark);
  body.position.y = 1.52;

  // shoulder mantle
  const mantle = new THREE.Mesh(new THREE.ConeGeometry(0.4, 0.55, 18, 1, true), robeDark);
  mantle.position.y = 1.78;

  hood = new THREE.Group();
  const hoodM = new THREE.Mesh(new THREE.SphereGeometry(0.3, 18, 14), robeMat);
  hoodM.scale.set(1, 1.15, 1.08);
  const face = new THREE.Mesh(new THREE.SphereGeometry(0.21, 14, 12), mat(0x0a0912, { roughness: 0.4 }));
  face.position.set(0, -0.02, 0.13);
  const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.028, 8, 8), glow(0xf4dfa0, 2.4));
  const eyeR = eyeL.clone();
  eyeL.position.set(-0.075, 0.02, 0.27); eyeR.position.set(0.075, 0.02, 0.27);
  circlet = new THREE.Mesh(new THREE.TorusGeometry(0.31, 0.018, 8, 28), glow(0xe8c46a, 0.55));
  circlet.rotation.x = 0.35;
  circlet.position.y = 0.12;
  hood.add(hoodM, face, eyeL, eyeR, circlet);
  hood.position.y = 2.16;

  // one continuous ribbon scarf — vertex-waved each frame for a dreamy trail
  const ribbonGeo = new THREE.PlaneGeometry(0.1, 1.7, 1, 16);
  ribbonGeo.translate(0, -0.85, 0);
  scarf = new THREE.Mesh(
    ribbonGeo,
    glow(0xc8a35a, 0.5, { side: THREE.DoubleSide, transparent: true, opacity: 0.7 })
  );
  scarf.position.set(0.05, 2.12, -0.26);
  scarf.rotation.x = -0.55; // trails behind her
  scarf.userData.basePos = ribbonGeo.attributes.position.array.slice();

  const sash = new THREE.Mesh(new THREE.TorusGeometry(0.19, 0.028, 8, 24), glow(0xe8c46a, 0.45));
  sash.rotation.x = Math.PI / 2;
  sash.position.y = 1.32;

  // slim crescent blade
  bladePivot = new THREE.Group();
  bladePivot.position.set(0.44, 1.4, -0.08);
  blade = new THREE.Group();
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.035, 0.42, 10), mat(0x2c2a3a, { metalness: 0.85, roughness: 0.25 }));
  const crescent = new THREE.Mesh(
    new THREE.TorusGeometry(0.3, 0.028, 8, 28, Math.PI * 1.15),
    mat(0xe8dcc0, { metalness: 0.95, roughness: 0.08, emissive: 0xc8a35a, emissiveIntensity: 0.25 })
  );
  crescent.position.y = 0.38;
  crescent.rotation.z = -0.4;
  blade.add(handle, crescent);
  blade.rotation.z = -0.45;
  bladePivot.add(blade);

  // soft personal light so she reads in every corner of the museum
  const aura = new THREE.PointLight(0x9a8cf4, 1.2, 6, 1.6);
  aura.position.set(0.4, 2.6, 0.6);

  g.add(cloak, innerSkirt, hem, body, mantle, hood, scarf, sash, bladePivot, aura);
  scene.add(g);
}

// attack trail — additive arc flashed on swing
const trail = new THREE.Mesh(
  new THREE.RingGeometry(1.1, 2.3, 24, 1, 0, Math.PI * 1.2),
  new THREE.MeshBasicMaterial({
    color: 0xf4dfa0, transparent: true, opacity: 0, side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending, depthWrite: false,
  })
);
trail.rotation.x = -Math.PI / 2;
scene.add(trail);

// dash ghosts
const ghosts = [];
for (let i = 0; i < 4; i++) {
  const gh = new THREE.Mesh(
    new THREE.ConeGeometry(0.55, 1.8, 10),
    new THREE.MeshBasicMaterial({ color: 0x8ea0e8, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  scene.add(gh);
  ghosts.push(gh);
}

// hit sparkle sprites (reused pool)
const sparks = [];
for (let i = 0; i < 10; i++) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({
    map: GLOW_TEX, color: 0xf4dfa0, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  s.scale.setScalar(0.001);
  scene.add(s);
  sparks.push({ s, life: 0, vel: new THREE.Vector3() });
}
export function burstSparks(pos, color = 0xf4dfa0, n = 8) {
  let used = 0;
  for (const sp of sparks) {
    if (used >= n) break;
    if (sp.life > 0) continue;
    sp.life = 0.5 + Math.random() * 0.3;
    sp.s.material.color.set(color);
    sp.s.position.copy(pos);
    sp.vel.set((Math.random() - 0.5) * 8, Math.random() * 7, (Math.random() - 0.5) * 8);
    used++;
  }
}

// hearts HUD
export function drawHearts() {
  ui.hearts.innerHTML = '';
  for (let i = 0; i < player.maxHp; i++) {
    const h = document.createElement('i');
    if (i >= player.hp) h.className = 'off';
    ui.hearts.appendChild(h);
  }
}
drawHearts();

export function damagePlayer(n, fromPos) {
  if (player.iframes > 0 || player.dead) return;
  player.hp -= n;
  player.iframes = 1.1;
  drawHearts();
  shake(0.5);
  document.body.classList.add('hurt');
  setTimeout(() => document.body.classList.remove('hurt'), 350);
  if (fromPos) {
    const away = player.pos.clone().sub(fromPos).setY(0).normalize().multiplyScalar(14);
    player.vel.x = away.x; player.vel.z = away.z; player.vel.y = 6;
  }
  if (player.hp <= 0) {
    player.dead = true;
    setTimeout(() => {
      player.pos.copy(player.spawn);
      player.vel.set(0, 0, 0);
      player.hp = player.maxHp;
      player.dead = false;
      drawHearts();
    }, 1200);
  }
}

// attack query — main.js asks "did this swing hit X?"
// The swing aims where the CAMERA looks, not where the run animation faces.
export function attackHits(targetPos, range = 3.4) {
  if (player.attackAnim <= 0.12 || player.attackAnim > 0.3) return false;
  const d = targetPos.clone().sub(player.pos);
  if (d.length() > range + 1.2) return false;
  d.setY(0).normalize();
  const f = new THREE.Vector3(-Math.sin(input.lookX), 0, -Math.cos(input.lookX));
  return f.dot(d) > 0.2;
}

// ---------- per-frame ----------
const scarfHistory = [];
let baseFov = 55, wasAirborne = false, squash = 0;

export function updatePlayer(dt, t, zone) {
  const p = player;
  p.iframes = Math.max(0, p.iframes - dt);
  p.attackCd = Math.max(0, p.attackCd - dt);
  p.dashCd = Math.max(0, p.dashCd - dt);
  p.attackAnim = Math.max(0, p.attackAnim - dt);

  // ----- camera-relative movement -----
  const yawCam = input.lookX;
  const fwd = new THREE.Vector3(-Math.sin(yawCam), 0, -Math.cos(yawCam));
  const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
  const wish = new THREE.Vector3();
  if (!p.moveLocked && !p.dead) {
    if (input.keys.KeyW) wish.add(fwd);
    if (input.keys.KeyS) wish.sub(fwd);
    if (input.keys.KeyD) wish.add(right);
    if (input.keys.KeyA) wish.sub(right);
  }
  const moving = wish.lengthSq() > 0;
  if (moving) wish.normalize();

  // dash
  if (input.keys.ShiftLeft && p.dashCd <= 0 && moving && !p.moveLocked) {
    p.dashCd = 1.1; p.dashTime = 0.18;
    p.vel.x = wish.x * 38; p.vel.z = wish.z * 38;
    for (const gh of ghosts) gh.material.opacity = 0.5;
  }
  p.dashTime = Math.max(0, p.dashTime - dt);

  // horizontal velocity: accelerate toward wish
  const accel = p.onGround ? 60 : 30;
  const target = wish.multiplyScalar(p.dashTime > 0 ? 38 : p.speed);
  p.vel.x += (target.x - p.vel.x) * Math.min(1, accel * dt / p.speed);
  p.vel.z += (target.z - p.vel.z) * Math.min(1, accel * dt / p.speed);

  // jump / double jump
  if (input.keys.Space && !p._spaceHeld && !p.moveLocked && !p.dead) {
    if (p.onGround) { p.vel.y = 13; p.onGround = false; p.jumps = 1; }
    else if (p.jumps < 2) { p.vel.y = 12; p.jumps = 2; burstSparks(p.pos.clone().add(new THREE.Vector3(0, 0.4, 0)), 0x8ea0e8, 6); }
  }
  p._spaceHeld = input.keys.Space;

  p.vel.y -= 34 * dt;

  // integrate + collide — substep so a dash can never tunnel through a wall
  {
    const move = Math.hypot(p.vel.x * dt, p.vel.z * dt);
    const steps = Math.max(1, Math.ceil(move / 0.25));
    for (let i = 0; i < steps; i++) {
      p.pos.x += (p.vel.x * dt) / steps;
      p.pos.z += (p.vel.z * dt) / steps;
      resolveCollisions(p.pos, 0.55, p.pos.y + 0.2, p.pos.y + 1.9);
    }
    resolveCollisions(p.pos, 0.55, p.pos.y + 0.2, p.pos.y + 1.9); // settle
  }
  p.pos.y += p.vel.y * dt;

  const gy = groundHeightAt(p.pos.x, p.pos.y + 0.5, p.pos.z);
  if (p.vel.y <= 0 && p.pos.y <= gy + 0.05 && gy > -100) {
    if (!p.onGround && wasAirborne && p.vel.y < -12) { squash = 0.35; shake(0.15); }
    p.pos.y = gy; p.vel.y = 0; p.onGround = true; p.jumps = 0;
  } else if (p.pos.y > gy + 0.1) {
    p.onGround = false;
  }
  wasAirborne = !p.onGround;

  // fell into the void
  if (p.pos.y < -30) {
    damagePlayer(1, null);
    p.pos.copy(p.spawn); p.vel.set(0, 0, 0);
  }

  // ----- attack -----
  if (input.attack && p.attackCd <= 0 && !p.moveLocked && !p.dead) {
    p.attackCd = 0.45; p.attackAnim = 0.3;
    // snap facing to the camera's aim so the swing goes where you look
    p.yaw = Math.atan2(-Math.sin(input.lookX), -Math.cos(input.lookX));
    trail.material.opacity = 0.85;
    trail.position.copy(p.pos).y += 1.3;
    trail.rotation.z = -input.lookX + Math.PI / 2;
    shake(0.06);
  }
  input.attack = false;

  // ----- facing -----
  if (moving) {
    const desired = Math.atan2(p.vel.x, p.vel.z);
    let d = desired - p.yaw;
    while (d > Math.PI) d -= Math.PI * 2;
    while (d < -Math.PI) d += Math.PI * 2;
    p.yaw += d * Math.min(1, 14 * dt);
  }

  // ----- procedural animation: dreamy float -----
  const g = p.group;
  g.position.copy(p.pos);
  g.rotation.y = p.yaw;
  const speed2d = Math.hypot(p.vel.x, p.vel.z);
  // she hovers: slow breathing rise and fall, no footstep bob
  const hover = 0.14 + Math.sin(t * 1.6) * 0.05 + (p.onGround ? 0 : -0.1);
  g.position.y += hover;
  // gentle lean into motion, eased
  g.rotation.x = THREE.MathUtils.lerp(g.rotation.x, speed2d * 0.014, 5 * dt);
  g.rotation.z = THREE.MathUtils.lerp(g.rotation.z, -p.vel.x * 0.004 * Math.cos(p.yaw), 5 * dt);
  // landing squash — soft, cushioned
  squash = Math.max(0, squash - dt * 1.8);
  const sy = 1 - squash * 0.25 + (p.onGround ? 0 : 0.05);
  g.scale.set(1 + squash * 0.18, sy, 1 + squash * 0.18);
  // robes breathe and flare with speed; hem ring drifts behind
  const flare = 1 + Math.sin(t * 1.6) * 0.03 + speed2d * 0.02 + (p.dashTime > 0 ? 0.3 : 0);
  cloak.scale.x = cloak.scale.z = flare;
  innerSkirt.scale.x = innerSkirt.scale.z = flare * 0.97;
  cloak.rotation.y = Math.sin(t * 0.9) * 0.06;
  hem.scale.setScalar(1 + Math.sin(t * 1.6 + 0.8) * 0.05 + speed2d * 0.015);
  hem.position.y = 0.38 + Math.sin(t * 1.6 + 1.2) * 0.03;
  // hood: slow dreamlike glance
  hood.rotation.y = Math.sin(t * 0.3) * 0.12;
  hood.rotation.z = Math.sin(t * 0.45) * 0.03;
  // blade swing — anticipation then sweep
  if (p.attackAnim > 0) {
    const k = 1 - p.attackAnim / 0.3;
    const swing = k < 0.25 ? -k * 2 : (k - 0.25) / 0.75 * Math.PI * 1.7 - 0.5;
    bladePivot.rotation.y = -swing;
    bladePivot.rotation.x = -0.35;
  } else {
    bladePivot.rotation.y = THREE.MathUtils.lerp(bladePivot.rotation.y, Math.sin(t * 1.2) * 0.08, 6 * dt);
    bladePivot.rotation.x = THREE.MathUtils.lerp(bladePivot.rotation.x, 0, 6 * dt);
  }
  // ribbon scarf — travelling wave along the strip; lifts and streams with speed
  {
    const posA = scarf.geometry.attributes.position;
    const base = scarf.userData.basePos;
    const drift = Math.min(1.2, speed2d * 0.08);
    for (let i = 0; i < posA.count; i++) {
      const by = base[i * 3 + 1];          // 0 .. -1.7 down the ribbon
      const k = -by / 1.7;                 // 0 at hood, 1 at tip
      posA.setX(i, base[i * 3] + Math.sin(t * 2.4 - k * 4.5) * 0.14 * k);
      posA.setZ(i, base[i * 3 + 2] + Math.sin(t * 1.7 - k * 3.2) * 0.08 * k - k * k * drift * 0.45);
    }
    posA.needsUpdate = true;
    scarf.rotation.x = -0.55 - drift * 0.5;
  }
  // i-frame flicker
  g.visible = p.iframes > 0 ? Math.floor(t * 18) % 2 === 0 : true;
  if (p.dead) g.visible = false;

  // trail fade
  trail.material.opacity = Math.max(0, trail.material.opacity - dt * 4);
  // ghosts fade + trail behind
  ghosts.forEach((gh, i) => {
    gh.material.opacity = Math.max(0, gh.material.opacity - dt * 2.2);
    if (gh.material.opacity > 0) {
      gh.position.copy(p.pos).addScaledVector(new THREE.Vector3(p.vel.x, 0, p.vel.z).normalize(), -(i + 1) * 0.7);
      gh.position.y += 0.9;
    }
  });
  // sparks
  for (const sp of sparks) {
    if (sp.life <= 0) continue;
    sp.life -= dt;
    sp.vel.y -= 20 * dt;
    sp.s.position.addScaledVector(sp.vel, dt);
    sp.s.scale.setScalar(Math.max(0.001, sp.life * 0.9));
    sp.s.material.opacity = Math.min(1, sp.life * 2);
    if (sp.life <= 0) sp.s.material.opacity = 0;
  }

  // ----- camera: cinematic follow with FOV kicks -----
  const dist = 8.5, height = 2.6;
  const cx = p.pos.x + Math.sin(input.lookX) * Math.cos(input.lookY) * dist;
  const cz = p.pos.z + Math.cos(input.lookX) * Math.cos(input.lookY) * dist;
  const cy = p.pos.y + height + Math.sin(input.lookY) * dist;
  return new THREE.Vector3(cx, cy, cz);
}

export function cameraFovKick(dt) {
  const targetFov = baseFov + (player.dashTime > 0 ? 9 : 0) + Math.hypot(player.vel.x, player.vel.z) * 0.12;
  camera.fov += (targetFov - camera.fov) * Math.min(1, 6 * dt);
  camera.updateProjectionMatrix();
}

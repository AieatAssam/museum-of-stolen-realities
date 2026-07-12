import * as THREE from 'three';
import { scene, mat, glow, ui, shake } from '../../engine/core.js';
import { BEAM_TEX, GLOW_TEX } from '../../engine/textures.js';
import { player, damagePlayer, attackHits, burstSparks } from '../../engine/player.js';

// ============================================================
// The Better Half — a detective's shadow that left him.
// Dormant: a flat silhouette pinned to the street under a lamp.
// Awake: glides upright, throws shadow-knives, dashes low along
// the ground. After each attack a spotlight PINS it: it turns
// pale grey and takes double damage.
// ============================================================

export const shade = {
  group: new THREE.Group(),
  pos: new THREE.Vector3(-6, 1.6, -34),
  home: new THREE.Vector3(-6, 1.6, -34),
  hp: 10, maxHp: 10,
  state: 'dormant',   // dormant | waking | patrol | volley | sweep | exposed | stagger | dead
  stateT: 0,
  aggro: false,
  dead: false,
  flash: 0,
  ignite: 0,
  nearDormant: false,
};

// silhouette: man in a long coat and hat, built from one shape
let body, hatBrim;
const silMat = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide, transparent: true, opacity: 0.98 });
{
  const s = new THREE.Shape();
  s.moveTo(-0.55, 0); s.lineTo(-0.7, 1.4); s.quadraticCurveTo(-0.75, 2.1, -0.45, 2.5); // coat left
  s.lineTo(-0.3, 2.55); s.lineTo(-0.32, 2.8); s.quadraticCurveTo(0, 3.05, 0.32, 2.8);  // head
  s.lineTo(0.3, 2.55); s.lineTo(0.45, 2.5); s.quadraticCurveTo(0.75, 2.1, 0.7, 1.4);   // coat right
  s.lineTo(0.55, 0); s.closePath();
  body = new THREE.Mesh(new THREE.ShapeGeometry(s, 10), silMat);
  hatBrim = new THREE.Mesh(new THREE.PlaneGeometry(1.15, 0.16), silMat);
  hatBrim.position.set(0, 2.78, 0.01);
  shade.group.add(body, hatBrim);
  shade.group.position.copy(shade.pos);
  scene.add(shade.group);
}

// dormant decal: the shadow lying flat on the asphalt under a lamp
const decal = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 5.2), new THREE.MeshBasicMaterial({
  color: 0x000000, transparent: true, opacity: 0.85, depthWrite: false,
}));
decal.rotation.x = -Math.PI / 2;
decal.position.set(shade.home.x, 0.07, shade.home.z);
scene.add(decal);

// the pinning spotlight cone (appears when exposed)
const pin = new THREE.Mesh(
  new THREE.PlaneGeometry(5, 12),
  new THREE.MeshBasicMaterial({ map: BEAM_TEX, color: 0xffffff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })
);
pin.layers.set(1);
scene.add(pin);

const underGlow = new THREE.Sprite(new THREE.SpriteMaterial({
  map: GLOW_TEX, color: 0xdfe6ff, transparent: true, opacity: 0,
  blending: THREE.AdditiveBlending, depthWrite: false,
}));
underGlow.scale.setScalar(6);
scene.add(underGlow);

// shadow knives
const knives = [];
for (let i = 0; i < 10; i++) {
  const k = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.9, 4), new THREE.MeshBasicMaterial({ color: 0x05050a }));
  const rim = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.98, 4), glow(0xdfe6ff, 0.8, { transparent: true, opacity: 0.4 }));
  k.add(rim);
  k.visible = false;
  scene.add(k);
  knives.push({ mesh: k, vel: new THREE.Vector3(), life: 0 });
}
function throwKnife(from, to, speed = 18) {
  for (const k of knives) {
    if (k.life > 0) continue;
    k.life = 4;
    k.mesh.visible = true;
    k.mesh.position.copy(from);
    k.vel.copy(to).sub(from).normalize().multiplyScalar(speed);
    k.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), k.vel.clone().normalize());
    return;
  }
}

function setState(s, t = 0) { shade.state = s; shade.stateT = t; }

export function wakeShade() {
  if (shade.state !== 'dormant') return;
  setState('waking');
  shade.aggro = true;
  ui.bossname.textContent = 'The Better Half';
  ui.bossbar.classList.add('show');
}

export function shadeTakeHit() {
  const dmg = shade.state === 'exposed' ? 2 : 1;
  shade.hp -= dmg;
  shade.flash = 0.25;
  ui.bossfill.style.width = `${Math.max(0, shade.hp / shade.maxHp) * 100}%`;
  burstSparks(shade.pos, 0xdfe6ff, 8);
  shake(0.3);
  if (shade.hp <= 0 && !shade.dead) {
    shade.dead = true;
    setState('dead');
    ui.bossbar.classList.remove('show');
    return 'killed';
  }
  if (shade.state !== 'exposed') setState('stagger', 0);
  return 'hit';
}

shade.wake = wakeShade;
shade.takeHit = shadeTakeHit;

shade.update = function updateShade(dt, t) {
  const w = shade;
  w.stateT += dt;
  w.flash = Math.max(0, w.flash - dt);

  const dist = player.pos.distanceTo(w.pos);

  if (w.state === 'dormant') {
    w.nearDormant = player.pos.distanceTo(w.home) < 8;
    w.group.visible = false;
    decal.material.opacity = 0.85 + Math.sin(t * 0.8) * 0.1;
  } else if (w.state === 'waking') {
    // the shadow peels up off the street
    w.group.visible = true;
    w.ignite = Math.min(1, w.stateT / 2.0);
    w.group.rotation.x = -Math.PI / 2 * (1 - w.ignite);
    w.pos.set(w.home.x, 0.1 + w.ignite * 1.5, w.home.z);
    decal.material.opacity = 0.85 * (1 - w.ignite);
    if (w.stateT > 2.4) { setState('patrol'); decal.visible = false; }
  } else if (w.state === 'patrol') {
    const desired = player.pos.clone().add(new THREE.Vector3(0, 1.6, 0));
    const dir = desired.sub(w.pos);
    const d = dir.length();
    if (d > 6) w.pos.addScaledVector(dir.normalize(), dt * 6);
    else if (d < 3) w.pos.addScaledVector(dir.normalize(), -dt * 4.5);
    w.pos.y = 1.6 + Math.sin(t * 1.4) * 0.25;
    if (w.stateT > 2.2 && dist < 26) setState(Math.random() < 0.55 ? 'volley' : 'sweep');
  } else if (w.state === 'volley') {
    if (w.stateT > 0.6 && !w._fired) {
      w._fired = true;
      throwKnife(w.pos, player.pos.clone().add(new THREE.Vector3(0, 1.2, 0)));
      setTimeout(() => throwKnife(w.pos.clone(), player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))), 200);
      setTimeout(() => throwKnife(w.pos.clone(), player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))), 400);
    }
    if (w.stateT > 1.4) { w._fired = false; setState('exposed'); }
  } else if (w.state === 'sweep') {
    // drops flat and slides along the ground through the player
    if (w.stateT < 0.5) {
      if (!w._target) w._target = player.pos.clone().setY(0.15);
      w.group.rotation.x = -Math.PI / 2 * (w.stateT / 0.5);
      w.pos.y = Math.max(0.15, 1.6 - w.stateT * 3);
    } else if (w.stateT < 1.15) {
      const dir = w._target.clone().sub(w.pos).setY(0);
      if (dir.length() > 0.5) w.pos.addScaledVector(dir.normalize(), dt * 36);
      if (w.pos.distanceTo(player.pos.clone().setY(w.pos.y)) < 1.8 && player.pos.y < 1.2) {
        damagePlayer(1, w.pos);
      }
    } else { w._target = null; w.group.rotation.x = 0; w.pos.y = 1.6; setState('exposed'); }
  } else if (w.state === 'exposed') {
    if (w.stateT > 2.2) setState('patrol');
  } else if (w.state === 'stagger') {
    if (w.stateT > 0.8) setState('patrol');
  } else if (w.state === 'dead') {
    // dissolves into the wet street
    w.group.scale.y = Math.max(0.01, w.group.scale.y - dt * 0.7);
    w.pos.y = Math.max(0.1, w.pos.y - dt * 1.4);
    silMat.opacity = Math.max(0, silMat.opacity - dt * 0.5);
  }

  // player hits
  if (!w.dead && w.state !== 'dormant' && w.state !== 'waking' && attackHits(w.pos, 3.4)) {
    if (!w._hitThisSwing) {
      w._hitThisSwing = true;
      const r = shadeTakeHit();
      if (r === 'killed') return 'killed';
    }
  }
  if (player.attackAnim <= 0) w._hitThisSwing = false;

  // visuals
  w.group.position.copy(w.pos);
  if (w.state !== 'dormant' && w.state !== 'sweep') {
    w.group.lookAt(player.pos.x, w.pos.y, player.pos.z);
  }
  // exposed: pinned by a spotlight, silhouette goes pale
  const exposed = w.state === 'exposed';
  pin.material.opacity += ((exposed ? 0.3 : 0) - pin.material.opacity) * dt * 6;
  if (exposed || pin.material.opacity > 0.02) {
    pin.position.set(w.pos.x, w.pos.y + 4.5, w.pos.z);
    pin.lookAt(player.pos.x, w.pos.y + 4.5, player.pos.z);
  }
  const pale = exposed ? 0.75 + Math.sin(t * 9) * 0.2 : (w.flash > 0 ? 1 : 0);
  silMat.color.setScalar(pale * 0.85);
  underGlow.position.set(w.pos.x, 0.12, w.pos.z);
  underGlow.material.color.set(exposed ? 0xffffff : 0x8890b8);
  underGlow.material.opacity = w.dead ? Math.max(0, underGlow.material.opacity - dt * 0.4) : w.ignite * 0.3;

  // knives
  for (const k of knives) {
    if (k.life <= 0) continue;
    k.life -= dt;
    k.mesh.position.addScaledVector(k.vel, dt);
    k.mesh.rotation.z += dt * 10;
    if (k.mesh.position.distanceTo(player.pos.clone().add(new THREE.Vector3(0, 1.2, 0))) < 1.1) {
      damagePlayer(1, k.mesh.position);
      k.life = 0;
    }
    if (k.life <= 0) k.mesh.visible = false;
  }
  return null;
};

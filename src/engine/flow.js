import * as THREE from 'three';
import {
  scene, camera, composer, bloom, input, ui, toast, letterbox,
  shake, shakeOffset, cine, after, updateTimers,
  clampSegment, groundHeightAt,
} from './core.js';
import {
  player, updatePlayer, cameraFovKick, drawHearts, burstSparks,
} from './player.js';
import { initAudio, sfx } from './audio.js';

// ============================================================
// Generic wing runner: intro cinematic → activation nodes →
// guardian → relic climax. All environment-specific content,
// transformations and story beats live in the wing module;
// this file owns the loop, interaction, UI and progression.
//
// wing = {
//   meta: { kicker, title, sub, hint, endKicker, endTitle, endBody,
//           startToastA, startToastB, firstObjective, nodeVerb },
//   spawn: Vector3, lookX0,
//   intro: { len, cam(e) -> { pos:Vector3, look:Vector3 } },
//   nodes: [{ pos, color, radius? }],
//   onNode(i, api),
//   guardian: { update(dt,t)->'killed'|null, dead } | null,
//   onGuardianKilled(api),
//   relic: { pos, radius?, prompt, locked(api)->string|null, restore(api) },
//   update(t, dt, api),
// }
// ============================================================

const objEl = document.getElementById('objtext');
const pips = [...document.querySelectorAll('#pips i')];
const promptEl = document.getElementById('prompt');
const promptAct = document.getElementById('prompt-act');
const titleEl = document.getElementById('title');
const objectiveEl = document.getElementById('objective');
const hintEl = document.getElementById('hint');

export const flow = { stage: 0, activated: 0 };

export function setObjective(text) {
  objEl.style.transition = 'opacity .45s';
  objEl.style.opacity = 0;
  setTimeout(() => { objEl.textContent = text; objEl.style.opacity = 1; }, 450);
}

const waves = [];
export function spawnWave(pos, color) {
  const wave = new THREE.Mesh(
    new THREE.RingGeometry(0.5, 1.2, 48),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  wave.rotation.x = -Math.PI / 2;
  wave.position.copy(pos).y += 0.3;
  scene.add(wave);
  waves.push(wave);
}

const drops = [];
export function spawnDrop({ pos, color, prompt, onTake, mesh }) {
  const m = mesh || new THREE.Mesh(
    new THREE.OctahedronGeometry(0.5),
    new THREE.MeshStandardMaterial({ color: 0x2a2a35, emissive: color, emissiveIntensity: 1.2, roughness: 0.3, metalness: 0.8 })
  );
  m.position.copy(pos);
  m.add(new THREE.PointLight(color, 12, 10));
  scene.add(m);
  const d = { mesh: m, prompt, onTake, taken: false };
  drops.push(d);
  return d;
}

// api handed to wing callbacks
export const api = {
  THREE, scene, camera, bloom, toast, letterbox, shake, cine, after, sfx,
  burstSparks, spawnWave, spawnDrop, setObjective, drawHearts, player, flow,
  lockPlayer(v) { player.moveLocked = v; },
  endGame() {
    flow.stage = 6;
    document.getElementById('ending').classList.add('show');
  },
};

let wing = null;

function nearestInteractable() {
  if (player.moveLocked) return null; // no prompts inside cinematics
  for (let i = 0; i < wing.nodes.length; i++) {
    const n = wing.nodes[i];
    if (!n.active && player.pos.distanceTo(n.pos) < (n.radius || 3.6)) return { type: 'node', i, n };
  }
  for (const d of drops) {
    if (!d.taken && player.pos.distanceTo(d.mesh.position) < 3) return { type: 'drop', d };
  }
  const r = wing.relic;
  if (r && flow.stage < 6 && player.pos.distanceTo(r.pos) < (r.radius || 5)) {
    const lockedMsg = r.locked(api);
    return lockedMsg ? { type: 'relic-locked', msg: lockedMsg } : { type: 'relic' };
  }
  return null;
}

function activateNode(i) {
  const n = wing.nodes[i];
  n.active = true;
  flow.activated++;
  pips[flow.activated - 1].classList.add('on');
  sfx.chime();
  shake(0.35);
  burstSparks(n.pos.clone().add(new THREE.Vector3(0, 3, 0)), n.color, 10);
  spawnWave(n.pos, n.color);
  wing.onNode(i, api);
}

export function runWing(w) {
  wing = w;
  flow.stage = 0; flow.activated = 0;
  api.activateNode = activateNode;

  // meta → DOM
  const m = wing.meta;
  document.querySelector('#title .no').textContent = m.kicker;
  document.querySelector('#title h1').textContent = m.title;
  document.querySelector('#title .sub').textContent = m.sub;
  document.querySelector('#ending .no').textContent = m.endKicker;
  document.querySelector('#ending h1').innerHTML = m.endTitle;
  document.querySelector('#ending p').textContent = m.endBody;
  document.title = `Museum of Stolen Realities — ${m.title}`;

  player.pos.copy(wing.spawn);
  player.spawn.copy(wing.spawn);
  input.lookX = wing.lookX0 ?? 0;

  letterbox(true);
  document.addEventListener('pointerlockchange', () => { initAudio(); }, { once: true });

  // debug hooks for automated tests
  window.__game = {
    player, bloom, scene, camera, input, wing,
    guardian: wing.guardian,
    get warden() { return wing.guardian; },
    teleport(x, y, z) { player.pos.set(x, y, z); player.vel.set(0, 0, 0); },
    activateAll() { wing.nodes.forEach((n, i) => { if (!n.active) activateNode(i); }); },
    activateOne(i) { if (!wing.nodes[i].active) activateNode(i); },
    killWarden() { wing.debugKillGuardian?.(); },
    get anim() { return wing.debugAnim; },
    get stage() { return { activated: flow.activated, wardenDead: !!wing.guardian?.dead, stage: flow.stage }; },
  };

  let introT = 0;
  const clock = new THREE.Clock();
  const shakeVec = new THREE.Vector3();

  function tick() {
    requestAnimationFrame(tick);
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;

    updateTimers(dt);
    wing.update(t, dt, api);

    // ----- intro -----
    if (flow.stage === 0) {
      introT += dt;
      const k = Math.min(1, introT / wing.intro.len);
      const e = k * k * (3 - 2 * k);
      const shot = wing.intro.cam(e);
      camera.position.copy(shot.pos);
      camera.lookAt(shot.look);
      if (introT > wing.intro.len - 2.2) titleEl.classList.add('hide');
      if (introT >= wing.intro.len) {
        flow.stage = 1;
        letterbox(false);
        titleEl.style.display = 'none';
        objectiveEl.classList.add('show');
        setObjective(m.firstObjective);
        toast(m.startToastA, m.startToastB);
      }
      composer.render();
      return;
    }

    // ----- gameplay -----
    const camTarget = updatePlayer(dt, t);
    cameraFovKick(dt);

    if (wing.guardian) {
      const res = wing.guardian.update(dt, t);
      if (res === 'killed') wing.onGuardianKilled(api);
    }

    // drops idle
    for (const d of drops) {
      if (d.taken) continue;
      d.mesh.rotation.y = t * 1.2;
      d.mesh.position.y += Math.sin(t * 2) * 0.003;
    }

    // interact
    const inter = nearestInteractable();
    if (inter) {
      promptAct.textContent =
        inter.type === 'relic' ? wing.relic.prompt
        : inter.type === 'relic-locked' ? inter.msg
        : inter.type === 'drop' ? inter.d.prompt
        : wing.meta.nodeVerb;
      promptEl.classList.add('show');
      if (input.keys.KeyE && !input._eHeld) {
        if (inter.type === 'node') activateNode(inter.i);
        else if (inter.type === 'relic') wing.relic.restore(api);
        else if (inter.type === 'drop') { inter.d.taken = true; inter.d.mesh.visible = false; inter.d.onTake(api); }
        else if (inter.type === 'relic-locked') toast('Sealed', inter.msg);
      }
    } else promptEl.classList.remove('show');
    input._eHeld = input.keys.KeyE;

    // waves expand
    for (let i = waves.length - 1; i >= 0; i--) {
      const w2 = waves[i];
      w2.scale.addScalar(dt * 14);
      w2.material.opacity -= dt * 0.9;
      if (w2.material.opacity <= 0) { scene.remove(w2); waves.splice(i, 1); }
    }

    if (input.locked) hintEl.style.opacity = 0;

    // ----- camera -----
    if (cine.active) {
      cine.t -= dt;
      camera.position.lerp(cine.pos, dt * 1.6);
      camera.lookAt(cine.look);
      if (cine.t <= 0 && flow.stage < 6) { cine.active = false; letterbox(false); }
    } else {
      const head = new THREE.Vector3(player.pos.x, player.pos.y + 2.1, player.pos.z);
      const tC = clampSegment(head, camTarget, 0.55);
      const clamped = head.clone().lerp(camTarget, tC);
      const gy = groundHeightAt(clamped.x, clamped.y + 1, clamped.z);
      if (gy > -100) clamped.y = Math.max(clamped.y, gy + 0.5);
      camera.position.lerp(clamped, 1 - Math.pow(0.0005, dt));
      camera.lookAt(head);
    }
    camera.position.add(shakeOffset(dt, shakeVec));

    composer.render();
  }
  tick();
}

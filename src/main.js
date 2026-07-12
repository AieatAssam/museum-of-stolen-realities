import * as THREE from 'three';
import {
  scene, camera, composer, bloom, input, ui, toast, letterbox,
  shake, shakeOffset, cine, after, updateTimers, addGround,
  clampSegment, groundHeightAt,
} from './core.js';
import {
  world, anim, hemi, moon, updateWorld, PALETTE, makeSlab,
} from './world.js';
import {
  player, updatePlayer, cameraFovKick, drawHearts, burstSparks, attackHits,
} from './player.js';
import { warden, updateWarden, wakeWarden, wardenTakeHit } from './guardian.js';
import { initAudio, sfx } from './audio.js';

// ============================================================
// Orchestration: intro cinematic → three resonators (each a
// transformation) → wake & defeat the Rose Warden → restore
// the Heart Prism → climax.
// ============================================================

let stage = 0; // 0 intro, 1 explore, 2..4 = resonators done, 5 warden dead, 6 prism restored
let activated = 0;

const objEl = document.getElementById('objtext');
const pips = [...document.querySelectorAll('#pips i')];
const promptEl = document.getElementById('prompt');
const promptAct = document.getElementById('prompt-act');
const titleEl = document.getElementById('title');
const objectiveEl = document.getElementById('objective');
const hintEl = document.getElementById('hint');

function setObjective(text) {
  objEl.style.opacity = 0;
  setTimeout(() => { objEl.textContent = text; objEl.style.opacity = 1; }, 450);
  objEl.style.transition = 'opacity .45s';
}

// ---------- intro cinematic ----------
let introT = 0;
const INTRO_LEN = 7.5;
letterbox(true);
document.addEventListener('pointerlockchange', () => { initAudio(); }, { once: true });

// ---------- interactions ----------
function nearestInteractable() {
  // resonators
  for (const r of anim.resonators) {
    if (!r.active && player.pos.distanceTo(r.pos) < 3.6) return { type: 'resonator', r };
  }
  if (activated === 3 && warden.dead && player.pos.distanceTo(anim.altar.pos) < 5) {
    return { type: 'altar' };
  }
  return null;
}

function activateResonator(r) {
  r.active = true;
  activated++;
  pips[activated - 1].classList.add('on');
  sfx.chime();
  shake(0.35);
  burstSparks(r.pos.clone().add(new THREE.Vector3(0, 3, 0)), r.color, 10);

  // shockwave ring
  const wave = new THREE.Mesh(
    new THREE.RingGeometry(0.5, 1.2, 48),
    new THREE.MeshBasicMaterial({ color: r.color, transparent: true, opacity: 0.9, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  wave.rotation.x = -Math.PI / 2;
  wave.position.copy(r.pos).y += 0.3;
  scene.add(wave);
  waves.push(wave);

  // per-resonator transformation
  if (activated === 1) {
    // glass stairs to the west gallery materialize, windows warm
    toast('Resonance I', 'The kingdom exhales. Glass remembers how to hold you.');
    anim.stairSlabs.forEach((s, i) => {
      setTimeout(() => {
        s.userData.on = true;
        addGround(s);
        s.material.opacity = 0.55;
        burstSparks(s.position, 0x4a6ae8, 6);
      }, 300 + i * 260);
    });
    for (const p of anim.panes) p.userData.boost = 1.35;
    setObjective('Climb the risen glass to the second resonator.');
  } else if (activated === 2) {
    // god rays double, warden stirs
    toast('Resonance II', 'Something in the transept unfolds its wings.');
    for (const b of anim.beams) b.userData.baseOp *= 1.8;
    hemi.intensity = 0.8;
    moon.intensity = 1.0;
    wakeWarden();
    setObjective('The third resonator lies in the Warden’s transept.');
  } else if (activated === 3) {
    toast('Resonance III', 'The Heart Prism stirs. The Warden objects.');
    bloom.strength = 0.7;
    setObjective('Defeat the Rose Warden.');
  }
}

function restorePrism() {
  stage = 6;
  player.moveLocked = true;
  sfx.bigChime();
  letterbox(true);

  const a = anim.altar;
  // climax: prism ignites, rises to the rose window heart, everything blazes
  cine.active = true;
  cine.t = 11;
  cine.pos.set(0, 4, -22);
  cine.look.copy(a.prism.position);

  after(0.5, () => {
    a.prism.material.color.set(0xe8b54a);
    a.prism.material.emissive.set(0xe8b54a);
    a.prism.material.emissiveIntensity = 3;
    a.light.intensity = 60;
    burstSparks(a.prism.position, 0xe8b54a, 10);
    shake(0.4);
  });
  after(2.0, () => {
    climax.rising = true;
    cine.pos.set(0, 10, -14);
  });
  after(5.5, () => {
    // prism reaches the rose heart — full blaze
    anim.roseHeart.material.color.set(0xe8b54a);
    anim.roseHeart.material.emissive.set(0xe8b54a);
    anim.roseHeart.material.emissiveIntensity = 4;
    for (const p of anim.panes) p.userData.boost = 2.2;
    bloom.strength = 1.15;
    sfx.shatter();
    shake(0.6);
    cine.pos.set(0, 18, -30);
    cine.look.set(0, 20, -55);
  });
  after(9.0, () => {
    document.getElementById('ending').classList.add('show');
  });
}

const climax = { rising: false };
const waves = [];

// ---------- debug hooks (smoke test) ----------
window.__game = {
  player, warden, bloom, anim, scene, camera, input,
  teleport(x, y, z) { player.pos.set(x, y, z); player.vel.set(0, 0, 0); },
  activateAll() { for (const r of anim.resonators) if (!r.active) activateResonator(r); },
  killWarden() { wakeWarden(); while (!warden.dead) wardenTakeHit(); },
  get stage() { return { activated, wardenDead: warden.dead, stage }; },
};

// ---------- main loop ----------
const clock = new THREE.Clock();
const shakeVec = new THREE.Vector3();

function tick() {
  requestAnimationFrame(tick);
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;

  updateTimers(dt);
  updateWorld(t, dt);

  // ----- intro -----
  if (stage === 0) {
    introT += dt;
    const k = Math.min(1, introT / INTRO_LEN);
    const e = k * k * (3 - 2 * k); // smoothstep
    // crane: from the rose window down the nave to the player
    camera.position.set(
      Math.sin(e * 1.2) * 6,
      26 - e * 22,
      -48 + e * 96
    );
    camera.lookAt(0, 20 - e * 18, -55 + e * 30);
    if (introT > INTRO_LEN - 2.2) titleEl.classList.add('hide');
    if (introT >= INTRO_LEN) {
      stage = 1;
      letterbox(false);
      titleEl.style.display = 'none';
      objectiveEl.classList.add('show');
      setObjective('Wake the first resonator, in the eastern chapel.');
      toast('Wing I · Acquisition № 214', 'The Stained Glass Kingdom');
    }
    composer.render();
    return;
  }

  // ----- gameplay -----
  const camTarget = updatePlayer(dt, t);
  cameraFovKick(dt);

  const res = updateWarden(dt, t);
  if (res === 'killed') {
    sfx.shatter();
    toast('The Rose Warden', 'shatters into four hundred grieving colors.');
    setObjective('Restore the Heart Prism at the altar.');
    bloom.strength = 0.8;
  }

  // interact
  const inter = nearestInteractable();
  if (inter) {
    promptAct.textContent = inter.type === 'altar' ? 'Restore the Heart Prism' : 'Resonate';
    promptEl.classList.add('show');
    if (input.keys.KeyE && !input._eHeld) {
      if (inter.type === 'resonator') activateResonator(inter.r);
      else if (inter.type === 'altar' && stage < 6) restorePrism();
    }
  } else promptEl.classList.remove('show');
  input._eHeld = input.keys.KeyE;

  // shockwave rings expand
  for (let i = waves.length - 1; i >= 0; i--) {
    const w = waves[i];
    w.scale.addScalar(dt * 14);
    w.material.opacity -= dt * 0.9;
    if (w.material.opacity <= 0) { scene.remove(w); waves.splice(i, 1); }
  }

  // climax prism rise
  if (climax.rising) {
    const a = anim.altar;
    const target = new THREE.Vector3(0, 20, -54.2);
    a.prism.position.lerp(target, dt * 0.55);
    a.prism.rotation.y += dt * 4;
    cine.look.copy(a.prism.position);
  }

  // hide hint once playing
  if (input.locked) hintEl.style.opacity = 0;

  // ----- camera -----
  if (cine.active) {
    cine.t -= dt;
    camera.position.lerp(cine.pos, dt * 1.6);
    camera.lookAt(cine.look);
    if (cine.t <= 0 && stage < 6) { cine.active = false; letterbox(false); }
  } else {
    // occlusion: pull the camera in so walls and columns never cut the frame
    const head = new THREE.Vector3(player.pos.x, player.pos.y + 2.1, player.pos.z);
    const tClamp = clampSegment(head, camTarget, 0.55);
    const clamped = head.clone().lerp(camTarget, tClamp);
    // never sink below the floor under the camera
    const gy = groundHeightAt(clamped.x, clamped.y + 1, clamped.z);
    if (gy > -100) clamped.y = Math.max(clamped.y, gy + 0.5);
    camera.position.lerp(clamped, 1 - Math.pow(0.0005, dt));
    camera.lookAt(head);
  }
  camera.position.add(shakeOffset(dt, shakeVec));

  composer.render();
}
tick();

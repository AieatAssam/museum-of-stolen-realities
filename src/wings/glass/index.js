import * as THREE from 'three';
import { anim, hemi, moon, updateWorld } from './world.js';
import { warden, updateWarden, wakeWarden, wardenTakeHit } from './guardian.js';
import { addGround } from '../../engine/core.js';
import { flow } from '../../engine/flow.js';

// ============================================================
// Wing I — The Stained Glass Kingdom. Content + story beats;
// the loop, UI and interaction live in engine/flow.js.
// ============================================================

const climax = { rising: false };
let leadHeart = null;

function dropLeadHeart(api) {
  leadHeart = api.spawnDrop({
    pos: new THREE.Vector3(warden.pos.x, 1.2, warden.pos.z),
    color: 0xb22242,
    prompt: 'Take the Lead Heart',
    onTake(api2) {
      api2.player.maxHp += 2;
      api2.player.hp = api2.player.maxHp;
      api2.drawHearts();
      api2.sfx.chime();
      api2.toast('The Lead Heart', 'What it guarded, it gives. +2 hearts.');
      if (flow.activated === 3) api2.setObjective('Restore the Heart Prism at the altar.');
    },
  });
}

export default {
  meta: {
    kicker: 'Museum of Stolen Realities · Wing I · Acquisition № 214',
    title: 'The Stained Glass Kingdom',
    sub: 'Restore the Heart Prism. Wake the three resonators. Do not trust the light.',
    startToastA: 'Wing I · Acquisition № 214',
    startToastB: 'The Stained Glass Kingdom',
    firstObjective: 'Wake the first resonator, in the eastern chapel.',
    nodeVerb: 'Resonate',
    endKicker: 'Fragment I of VI · Recovered',
    endTitle: '"The kingdom remembers its light.<br>Somewhere, the Curator updates your placard."',
    endBody: 'The Heart Prism is restored — and stolen, again, properly this time. Five wings remain.',
  },

  spawn: new THREE.Vector3(0, 0, 52),
  lookX0: 0,

  intro: {
    len: 7.5,
    cam(e) {
      return {
        pos: new THREE.Vector3(Math.sin(e * 1.2) * 6, 26 - e * 22, -48 + e * 96),
        look: new THREE.Vector3(0, 20 - e * 18, -55 + e * 30),
      };
    },
  },

  nodes: anim.resonators.map(r => ({ pos: r.pos, color: r.color, r })),

  onNode(i, api) {
    const n = this.nodes[i];
    n.r.active = true;
    if (flow.activated === 1) {
      api.toast('Resonance I', 'The kingdom exhales. Glass remembers how to hold you.');
      anim.stairSlabs.forEach((s, k) => {
        setTimeout(() => {
          s.userData.on = true;
          addGround(s);
          s.material.opacity = 0.55;
          api.burstSparks(s.position, 0x4a6ae8, 6);
        }, 300 + k * 260);
      });
      for (const p of anim.panes) p.userData.boost = 1.35;
      api.setObjective('Climb the risen glass to the second resonator.');
    } else if (flow.activated === 2) {
      for (const b of anim.beams) b.userData.baseOp *= 1.8;
      hemi.intensity = 1.9;
      moon.intensity = 1.8;
      api.lockPlayer(true);
      api.cine.active = true; api.cine.t = 4.2;
      api.cine.pos.set(warden.home.x + 6, 4.5, warden.home.z + 9);
      api.cine.look.copy(warden.home).add(new THREE.Vector3(0, 1.5, 0));
      api.letterbox(true);
      api.after(0.8, () => {
        wakeWarden();
        api.sfx.shatter();
        api.shake(0.5);
        api.toast('Acquisition № 214(b)', 'The exhibit is awake. The exhibit remembers its post.');
      });
      api.after(4.0, () => {
        api.lockPlayer(false);
        api.setObjective('The third resonator lies in the Warden’s transept.');
      });
    } else if (flow.activated === 3) {
      api.bloom.strength = 0.7;
      if (warden.dead) {
        api.toast('Resonance III', 'The Heart Prism stirs. Nothing is left to object.');
        api.setObjective(leadHeart && !leadHeart.taken
          ? 'Take what the Warden guarded. Then the altar.'
          : 'Restore the Heart Prism at the altar.');
      } else {
        api.toast('Resonance III', 'The Heart Prism stirs. The Warden objects.');
        api.setObjective('Defeat the Rose Warden.');
      }
    }
  },

  guardian: warden,

  onGuardianKilled(api) {
    api.sfx.shatter();
    api.toast('The Rose Warden', 'shatters into four hundred grieving colors.');
    api.setObjective(flow.activated === 3
      ? 'Take what the Warden guarded. Then the altar.'
      : 'Wake the remaining resonators.');
    api.bloom.strength = 0.8;
    dropLeadHeart(api);
  },

  debugKillGuardian() { wakeWarden(); while (!warden.dead) wardenTakeHit(); },
  debugAnim: anim,

  relic: {
    pos: anim.altar.pos,
    prompt: 'Restore the Heart Prism',
    locked() {
      if (flow.activated < 3) return `Sealed — ${3 - flow.activated} resonator${flow.activated === 2 ? '' : 's'} still sleep`;
      if (!warden.dead) return 'Sealed — the Warden objects';
      return null;
    },
    restore(api) {
      api.lockPlayer(true);
      api.sfx.bigChime();
      api.letterbox(true);
      const a = anim.altar;
      api.cine.active = true;
      api.cine.t = 11;
      api.cine.pos.set(0, 4, -22);
      api.cine.look.copy(a.prism.position);
      api.after(0.5, () => {
        a.prism.material.color.set(0xe8b54a);
        a.prism.material.emissive.set(0xe8b54a);
        a.prism.material.emissiveIntensity = 3;
        a.light.intensity = 60;
        api.burstSparks(a.prism.position, 0xe8b54a, 10);
        api.shake(0.4);
      });
      api.after(2.0, () => {
        climax.rising = true;
        api.cine.pos.set(0, 10, -14);
      });
      api.after(5.5, () => {
        anim.roseHeart.material.color.set(0xe8b54a);
        anim.roseHeart.material.emissive.set(0xe8b54a);
        anim.roseHeart.material.emissiveIntensity = 4;
        for (const p of anim.panes) p.userData.boost = 2.2;
        api.bloom.strength = 1.15;
        api.sfx.shatter();
        api.shake(0.6);
        api.cine.pos.set(0, 18, -30);
        api.cine.look.set(0, 20, -55);
      });
      api.after(9.0, () => api.endGame());
    },
  },

  update(t, dt, api) {
    updateWorld(t, dt);

    if (climax.rising) {
      const a = anim.altar;
      a.prism.position.lerp(new THREE.Vector3(0, 20, -54.2), dt * 0.55);
      a.prism.rotation.y += dt * 4;
      api.cine.look.copy(a.prism.position);
    }

    if (flow.stage < 1) return;

    // guardian is updated by flow; here: story beats around it
    if (warden.state === 'exposed' && !warden._hinted) {
      warden._hinted = true;
      api.toast('The shards are only glass', 'Strike while the core burns gold.', 3800);
    }
    if (warden.nearDormant && !warden._placarded) {
      warden._placarded = true;
      api.toast('Acquisition № 214(b) · "Warden of the Rose"', 'Patrons are asked not to tap the glass.', 4200);
    }
  },
};

// guardian adapter: flow calls wing.guardian.update — bind module funcs
warden.update = (dt, t) => updateWarden(dt, t);

import * as THREE from 'three';
import { anim, hemi, updateWorld, flood } from './world.js';
import { shade } from './guardian.js';
import { scene } from '../../engine/core.js';
import { flow } from '../../engine/flow.js';

// ============================================================
// Wing III — The Long Shadow. Monochrome noir city, 3:11 a.m.
// Wake three projectors, defeat the Better Half, develop the
// Negative — and the city gets eleven seconds of color.
// ============================================================

let hatDrop = null;

export default {
  meta: {
    kicker: 'Museum of Stolen Realities · Wing III · Acquisition № 501',
    title: 'The Long Shadow',
    sub: 'Develop the Negative. Wake the three projectors. It is always 3:11 a.m.',
    startToastA: 'Wing III · Acquisition № 501',
    startToastB: 'The Long Shadow',
    firstObjective: 'Wake the first projector, in the lamplit plaza.',
    nodeVerb: 'Roll film',
    endKicker: 'Fragment II of VI · Recovered',
    endTitle: '"For eleven seconds, the city remembered color.<br>The rain has not stopped talking about it."',
    endBody: 'The Negative is developed and stolen back. Somewhere a detective tips his hat to nothing. Four wings remain.',
  },

  spawn: new THREE.Vector3(0, 0, 52),
  lookX0: 0,

  intro: {
    len: 7.5,
    cam(e) {
      // fall from the rooftops down into the rain-lit canyon
      return {
        pos: new THREE.Vector3(-14 + e * 12, 30 - e * 26, -30 + e * 76),
        look: new THREE.Vector3(0, 24 - e * 22, -50 + e * 40),
      };
    },
  },

  nodes: anim.projectors.map(p => ({ pos: p.pos, color: 0xf2f2ee, p })),

  onNode(i, api) {
    this.nodes[i].p.active = true;
    if (flow.activated === 1) {
      api.toast('Reel I', 'Somewhere a projector hums. The lamps lean in to watch.');
      hemi.intensity = 1.35;
      api.setObjective('The second projector runs on the low rooftop — take the fire escape.');
    } else if (flow.activated === 2) {
      // the shadow peels off the street
      api.lockPlayer(true);
      api.cine.active = true; api.cine.t = 4.0;
      api.cine.pos.set(shade.home.x + 7, 3.5, shade.home.z + 8);
      api.cine.look.copy(shade.home).setY(1.5);
      api.letterbox(true);
      api.after(0.7, () => {
        shade.wake();
        api.sfx.hurt();
        api.shake(0.4);
        api.toast('Acquisition № 501(a)', 'The shadow no longer matches anything. It stands up anyway.');
      });
      api.after(3.8, () => {
        api.lockPlayer(false);
        api.setObjective('The third projector waits in the Shadow’s plaza.');
      });
    } else if (flow.activated === 3) {
      api.bloom.strength = 0.6;
      if (shade.dead) {
        api.toast('Reel III', 'Every lamp on the street turns toward the cinema.');
        api.setObjective(hatDrop && !hatDrop.taken
          ? 'Take what the Shadow left behind. Then the marquee.'
          : 'Develop the Negative at the cinema marquee.');
      } else {
        api.toast('Reel III', 'The projectors are ready. The Shadow is not amused.');
        api.setObjective('Defeat the Better Half.');
      }
    }
  },

  guardian: shade,

  onGuardianKilled(api) {
    api.sfx.shatter();
    api.toast('The Better Half', 'folds back into the wet asphalt, almost gratefully.');
    api.setObjective(flow.activated === 3
      ? 'Take what the Shadow left behind. Then the marquee.'
      : 'Wake the remaining projectors.');
    hatDrop = api.spawnDrop({
      pos: new THREE.Vector3(shade.pos.x, 1.1, shade.pos.z),
      color: 0xdfe6ff,
      prompt: 'Take the Detective’s Hat',
      onTake(api2) {
        api2.player.maxHp += 2;
        api2.player.hp = api2.player.maxHp;
        api2.drawHearts();
        api2.sfx.chime();
        api2.toast('The Detective’s Hat', 'Someone kept it brushed all these years. +2 hearts.');
        if (flow.activated === 3) api2.setObjective('Develop the Negative at the cinema marquee.');
      },
    });
  },

  debugKillGuardian() { shade.wake(); while (!shade.dead) shade.takeHit(); },
  debugAnim: anim,

  relic: {
    pos: anim.marquee.pos,
    prompt: 'Develop the Negative',
    locked() {
      if (flow.activated < 3) return `Dark — ${3 - flow.activated} projector${flow.activated === 2 ? '' : 's'} still cold`;
      if (!shade.dead) return 'Dark — the Shadow stands in the light';
      return null;
    },
    restore(api) {
      api.lockPlayer(true);
      api.sfx.bigChime();
      api.letterbox(true);
      api.cine.active = true;
      api.cine.t = 11.5;
      api.cine.pos.set(8, 3.5, -38);
      api.cine.look.copy(anim.marquee.negative.position);
      api.after(0.6, () => {
        anim.marquee.negative.material.emissiveIntensity = 3;
        anim.marquee.light.intensity = 40;
        api.burstSparks(anim.marquee.negative.position, 0xffffff, 10);
        api.shake(0.35);
      });
      api.after(2.0, () => {
        // ELEVEN SECONDS OF COLOR
        flood.target = 1;
        api.bloom.strength = 0.85;
        api.sfx.shatter();
        api.toast('3:11 a.m.', 'For eleven seconds, the city remembers.', 5000);
        // turn to face the whole boulevard as it floods with color
        api.cine.pos.set(0, 13, -46);
        api.cine.look.set(0, 3, 30);
      });
      api.after(8.5, () => {
        flood.target = 0;             // the monochrome lid comes back down
        api.bloom.strength = 0.5;
      });
      api.after(10.5, () => api.endGame());
    },
  },

  update(t, dt, api) {
    updateWorld(t, dt);
    if (flow.stage < 1) return;
    if (shade.state === 'exposed' && !shade._hinted) {
      shade._hinted = true;
      api.toast('The light pins it', 'Strike while the silhouette turns pale.', 3800);
    }
    if (shade.nearDormant && !shade._placarded) {
      shade._placarded = true;
      api.toast('Acquisition № 501(a) · "Shadow, Unaccompanied"', 'Found eleven seconds ahead of its owner. Do not stand on it.', 4200);
    }
  },
};

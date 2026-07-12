import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// ---------- renderer / scene / camera / post ----------
export const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.25;
document.body.prepend(renderer.domElement);

export const scene = new THREE.Scene();
scene.background = new THREE.Color(0x060503);
scene.fog = new THREE.FogExp2(0x0a0e20, 0.014);

export const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 500);
camera.layers.enable(1); // layer 1 = additive atmosphere, excluded from mirror reflections

export const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
// clamp HDR before bloom: specular peaks on polished surfaces can hit Inf in the
// half-float buffer, and Inf passes any bloom threshold and smears the whole frame
composer.addPass(new ShaderPass({
  uniforms: { tDiffuse: { value: null } },
  vertexShader: `varying vec2 vUv;
    void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `uniform sampler2D tDiffuse; varying vec2 vUv;
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      gl_FragColor = vec4(clamp(c.rgb, vec3(0.0), vec3(8.0)), c.a);
    }`,
}));
export const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.35, 0.4, 1.0);
composer.addPass(bloom);
composer.addPass(new OutputPass());

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});

// ---------- material helpers ----------
export const mat = (color, opts = {}) => new THREE.MeshStandardMaterial({ color, ...opts });
export const glow = (color, intensity = 2, opts = {}) =>
  new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: intensity, ...opts });

// ---------- physics: colliders + walkable ground ----------
export const colliders = [];      // {min:Vector3,max:Vector3} AABBs
export const cylinders = [];      // {x,z,r} infinite vertical cylinders
export const groundMeshes = [];   // meshes the down-ray can stand on

const _box = new THREE.Box3();
export function addBoxCollider(objOrBox) {
  const b = objOrBox.isBox3 ? objOrBox.clone() : _box.setFromObject(objOrBox).clone();
  colliders.push({ min: b.min.clone(), max: b.max.clone() });
}
export function addCylCollider(x, z, r) { cylinders.push({ x, z, r }); }
export function addGround(mesh) { groundMeshes.push(mesh); }

// clamp a camera segment so it never enters a collider AABB (with padding)
const _pt = new THREE.Vector3();
export function clampSegment(from, to, pad = 0.5) {
  const steps = 24;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    _pt.lerpVectors(from, to, t);
    for (const c of colliders) {
      if (
        _pt.x > c.min.x - pad && _pt.x < c.max.x + pad &&
        _pt.y > c.min.y - pad && _pt.y < c.max.y + pad &&
        _pt.z > c.min.z - pad && _pt.z < c.max.z + pad
      ) {
        return Math.max(0.12, (i - 1) / steps);
      }
    }
    for (const c of cylinders) {
      const dx = _pt.x - c.x, dz = _pt.z - c.z, rr = c.r + pad * 0.6;
      if (dx * dx + dz * dz < rr * rr) return Math.max(0.12, (i - 1) / steps);
    }
  }
  return 1;
}

// push a horizontal position (sphere radius r at any height range [y0,y1]) out of colliders
export function resolveCollisions(pos, r, y0, y1) {
  for (const c of colliders) {
    if (y1 < c.min.y || y0 > c.max.y) continue;
    const cx = Math.max(c.min.x, Math.min(pos.x, c.max.x));
    const cz = Math.max(c.min.z, Math.min(pos.z, c.max.z));
    const dx = pos.x - cx, dz = pos.z - cz;
    const d2 = dx * dx + dz * dz;
    if (d2 < r * r) {
      if (d2 > 1e-8) {
        const d = Math.sqrt(d2), push = (r - d) / d;
        pos.x += dx * push; pos.z += dz * push;
      } else {
        // inside the box: push out the nearest face on x/z
        const px = Math.min(pos.x - c.min.x + r, c.max.x - pos.x + r);
        const pz = Math.min(pos.z - c.min.z + r, c.max.z - pos.z + r);
        if (px < pz) pos.x += (pos.x - c.min.x < c.max.x - pos.x) ? -(px) : px;
        else pos.z += (pos.z - c.min.z < c.max.z - pos.z) ? -(pz) : pz;
      }
    }
  }
  for (const c of cylinders) {
    const dx = pos.x - c.x, dz = pos.z - c.z;
    const rr = r + c.r, d2 = dx * dx + dz * dz;
    if (d2 < rr * rr && d2 > 1e-8) {
      const d = Math.sqrt(d2), push = (rr - d) / d;
      pos.x += dx * push; pos.z += dz * push;
    }
  }
}

const _ray = new THREE.Raycaster();
const _down = new THREE.Vector3(0, -1, 0);
const _origin = new THREE.Vector3();
export function groundHeightAt(x, y, z) {
  _origin.set(x, y + 2.5, z);
  _ray.set(_origin, _down);
  _ray.far = 60;
  const hits = _ray.intersectObjects(groundMeshes, false);
  return hits.length ? hits[0].point.y : -Infinity;
}

// ---------- input ----------
export const input = { keys: {}, attack: false, lookX: 0, lookY: 0, locked: false };
addEventListener('keydown', e => input.keys[e.code] = true);
addEventListener('keyup', e => input.keys[e.code] = false);

renderer.domElement.addEventListener('click', () => {
  if (!input.locked) renderer.domElement.requestPointerLock();
  else input.attack = true;
});
document.addEventListener('pointerlockchange', () => {
  input.locked = document.pointerLockElement === renderer.domElement;
});
addEventListener('mousemove', e => {
  if (!input.locked) return;
  input.lookX -= e.movementX * 0.0026;
  input.lookY = Math.max(-0.5, Math.min(1.15, input.lookY + e.movementY * 0.002));
});

// ---------- HUD ----------
export const ui = {
  frag: document.getElementById('fragcount'),
  prov: document.getElementById('provcount'),
  hearts: document.getElementById('hearts'),
  bossbar: document.getElementById('bossbar'),
  bossname: document.getElementById('bossname'),
  bossfill: document.getElementById('bossfill'),
  plaque: document.getElementById('plaque'),
  plaqueNo: document.getElementById('plaque-no'),
  plaqueTitle: document.getElementById('plaque-title'),
  plaqueSub: document.getElementById('plaque-sub'),
  toastBox: document.getElementById('toast'),
  toast1: document.getElementById('toast1'),
  toast2: document.getElementById('toast2'),
  ending: document.getElementById('ending'),
};

export function toast(kicker, line, ms = 3400) {
  ui.toast1.textContent = kicker;
  ui.toast2.textContent = line;
  ui.toastBox.classList.add('show');
  clearTimeout(ui.toastBox._t);
  ui.toastBox._t = setTimeout(() => ui.toastBox.classList.remove('show'), ms);
}

export function letterbox(on) { document.body.classList.toggle('cine', on); }

// ---------- camera shake ----------
let shakeAmp = 0;
export function shake(a) { shakeAmp = Math.max(shakeAmp, a); }
export function shakeOffset(dt, out) {
  shakeAmp = Math.max(0, shakeAmp - dt * 2.2);
  out.set((Math.random() - 0.5) * shakeAmp, (Math.random() - 0.5) * shakeAmp, 0);
  return out;
}

// ---------- cinematic camera override ----------
export const cine = { active: false, pos: new THREE.Vector3(), look: new THREE.Vector3(), t: 0 };
export function cineShot(pos, look, seconds) {
  cine.active = true; cine.pos.copy(pos); cine.look.copy(look); cine.t = seconds;
  letterbox(true);
}

// ---------- timers (scripted moments) ----------
const timers = [];
export function after(sec, fn) { timers.push({ t: sec, fn }); }
export function updateTimers(dt) {
  for (let i = timers.length - 1; i >= 0; i--) {
    timers[i].t -= dt;
    if (timers[i].t <= 0) { const f = timers[i].fn; timers.splice(i, 1); f(); }
  }
}

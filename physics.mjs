import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--use-gl=angle', '--enable-unsafe-swiftshader', '--window-size=1280,720'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720 });
const errors = [];
page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
await page.goto('http://localhost:8642/', { waitUntil: 'load', timeout: 60000 });
await page.waitForFunction('window.__game !== undefined', { timeout: 30000 });
await new Promise(r => setTimeout(r, 10500)); // intro

const results = [];
const check = (name, ok, detail) => results.push(`${ok ? 'PASS' : 'FAIL'} ${name} ${detail}`);

// focus canvas for keys
await page.click('canvas');
await new Promise(r => setTimeout(r, 300));

// 1. walk into east wall — must not clip through (inner face ~22.3)
await page.evaluate(() => { window.__game.input.lookX = -Math.PI / 2; window.__game.teleport(19, 0, 24); });
await page.keyboard.down('KeyW');
await new Promise(r => setTimeout(r, 2000));
await page.keyboard.up('KeyW');
let pos = await page.evaluate(() => ({ ...window.__game.player.pos }));
check('wall-walk', pos.x < 22.5 && pos.x > 20, `x=${pos.x.toFixed(2)}`);

// 2. dash into wall repeatedly — no tunneling
for (let i = 0; i < 3; i++) {
  await page.evaluate(() => window.__game.teleport(20, 0, 24));
  await page.keyboard.down('KeyW');
  await page.keyboard.down('ShiftLeft');
  await new Promise(r => setTimeout(r, 500));
  await page.keyboard.up('ShiftLeft');
  await page.keyboard.up('KeyW');
}
pos = await page.evaluate(() => ({ ...window.__game.player.pos }));
check('wall-dash', pos.x < 22.5, `x=${pos.x.toFixed(2)}`);

// 3. glass stair slab holds the player after resonator A
await page.evaluate(() => { window.__game.activateAll(); });
await new Promise(r => setTimeout(r, 2500)); // stairs materialize
await page.evaluate(() => window.__game.teleport(-4, 4, 10));
await new Promise(r => setTimeout(r, 1500));
pos = await page.evaluate(() => ({ ...window.__game.player.pos }));
check('slab-stand', pos.y > 1.2 && pos.y < 2.3, `y=${pos.y.toFixed(2)}`);

// 4. camera occlusion — back to a wall, camera must stay inside the nave
await page.evaluate(() => { window.__game.input.lookX = Math.PI / 2; window.__game.teleport(20.5, 0, 24); });
await new Promise(r => setTimeout(r, 1500));
const cam = await page.evaluate(() => ({ ...window.__game.camera.position }));
check('camera-occlusion', cam.x < 22.4, `camX=${cam.x.toFixed(2)}`);

// 5. pew collider — walking into a pew stops you
await page.evaluate(() => { window.__game.input.lookX = 0; window.__game.teleport(-11, 0, 44); });
await page.keyboard.down('KeyW');
await new Promise(r => setTimeout(r, 1200));
await page.keyboard.up('KeyW');
pos = await page.evaluate(() => ({ ...window.__game.player.pos }));
check('pew-collider', pos.z > 40.4, `z=${pos.z.toFixed(2)}`);

// 6. stair flight: every slab supports the player
const slabTops = await page.evaluate(() => window.__game.anim.stairSlabs.map(s => ({ x: s.position.x, y: s.userData.baseY, z: s.position.z })));
let allStand = true, slabDetail = '';
for (const s of slabTops) {
  await page.evaluate((s) => window.__game.teleport(s.x, s.y + 1.5, s.z), s);
  await new Promise(r => setTimeout(r, 900));
  const y = await page.evaluate(() => window.__game.player.pos.y);
  if (Math.abs(y - s.y) > 0.8) { allStand = false; slabDetail = `slab@${s.x},${s.z} y=${y.toFixed(2)} want~${s.y}`; break; }
}
check('slab-flight', allStand, slabDetail || `${slabTops.length} slabs OK`);

// 7. final hop from top slab onto the west ledge
{
  const top = slabTops[slabTops.length - 1];
  await page.evaluate((top) => {
    const dirx = -16 - top.x, dirz = -9 - top.z;
    window.__game.input.lookX = Math.atan2(-dirx, -dirz);
    window.__game.teleport(top.x, top.y + 0.4, top.z);
  }, top);
  await new Promise(r => setTimeout(r, 400));
  await page.keyboard.down('KeyW');
  await new Promise(r => setTimeout(r, 150));
  await page.keyboard.down('Space');
  await new Promise(r => setTimeout(r, 150));
  await page.keyboard.up('Space');
  await new Promise(r => setTimeout(r, 900));
  await page.keyboard.up('KeyW');
  await new Promise(r => setTimeout(r, 800));
  pos = await page.evaluate(() => ({ ...window.__game.player.pos }));
  check('ledge-hop', pos.y > 10.2 && pos.x < -13, `x=${pos.x.toFixed(2)} y=${pos.y.toFixed(2)}`);
}

// 8. attack aims where the camera looks
{
  await page.evaluate(() => { window.__game.input.lookX = 0; window.__game.teleport(0, 0, -43.5); });
  await new Promise(r => setTimeout(r, 3500)); // clear the wake cinematic
  await page.evaluate(() => { const w = window.__game.warden; w.state = 'patrol'; w.stateT = 0; w.pos.set(0, 2.6, -46.5); });
  await new Promise(r => setTimeout(r, 120));
  const hp0 = await page.evaluate(() => window.__game.warden.hp);
  await page.evaluate(() => { window.__game.input.attack = true; window.__game.input.locked = true; });
  await new Promise(r => setTimeout(r, 600));
  const hp1 = await page.evaluate(() => window.__game.warden.hp);
  check('attack-aim-hit', hp1 < hp0, `hp ${hp0}->${hp1}`);
  await page.evaluate(() => { window.__game.input.lookX = Math.PI; });
  await new Promise(r => setTimeout(r, 300));
  const hp2 = await page.evaluate(() => window.__game.warden.hp);
  await page.evaluate(() => { window.__game.input.attack = true; });
  await new Promise(r => setTimeout(r, 600));
  const hp3 = await page.evaluate(() => window.__game.warden.hp);
  check('attack-aim-miss', hp3 === hp2, `hp ${hp2}->${hp3}`);
}

console.log(results.join('\n'));
console.log(errors.length ? errors.join('\n') : 'NO ERRORS');
await browser.close();
process.exit(results.some(r => r.startsWith('FAIL')) || errors.length ? 1 : 0);

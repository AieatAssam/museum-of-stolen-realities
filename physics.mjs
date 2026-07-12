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

console.log(results.join('\n'));
console.log(errors.length ? errors.join('\n') : 'NO ERRORS');
await browser.close();
process.exit(results.some(r => r.startsWith('FAIL')) || errors.length ? 1 : 0);

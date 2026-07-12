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
await page.waitForFunction('window.__game !== undefined');
await new Promise(r => setTimeout(r, 11000));

// OUT-OF-ORDER path: only two resonators, then kill the warden, then the third
await page.evaluate(() => { window.__game.activateOne(0); window.__game.activateOne(1); });
await new Promise(r => setTimeout(r, 5500)); // wake cinematic

// kill via REAL attacks: chase warden, aim camera at it, swing until dead
for (let i = 0; i < 60; i++) {
  const dead = await page.evaluate(() => {
    const g = window.__game, w = g.warden, p = g.player;
    if (w.dead) return true;
    // stand 3 units from warden, aim at it
    const dx = w.pos.x - p.pos.x, dz = w.pos.z - p.pos.z;
    const d = Math.hypot(dx, dz) || 1;
    g.teleport(w.pos.x - (dx / d) * 3, 0, w.pos.z - (dz / d) * 3);
    g.input.lookX = Math.atan2(-dx / d, -dz / d);
    g.input.attack = true;
    return false;
  });
  if (dead) break;
  await new Promise(r => setTimeout(r, 500));
}

const s1 = await page.evaluate(() => {
  const g = window.__game;
  return { dead: g.warden.dead, hp: g.warden.hp, stage: g.stage };
});
console.log('after fight:', JSON.stringify(s1));

// now the third resonator, post-mortem
await page.evaluate(() => window.__game.activateOne(2));
await new Promise(r => setTimeout(r, 1200));
const obj = await page.evaluate(() => document.getElementById('objtext').textContent);
console.log('objective after late resonance III:', JSON.stringify(obj));

// walk to warden corpse position — heart prompt?
const heartInfo = await page.evaluate(() => {
  const g = window.__game;
  g.teleport(g.warden.pos.x, 0, g.warden.pos.z + 1);
  return { wardenPos: { x: g.warden.pos.x.toFixed(1), y: g.warden.pos.y.toFixed(1), z: g.warden.pos.z.toFixed(1) } };
});
await new Promise(r => setTimeout(r, 800));
const prompt1 = await page.evaluate(() => ({ shown: document.getElementById('prompt').classList.contains('show'), text: document.getElementById('prompt-act').textContent }));
console.log('at corpse:', JSON.stringify(heartInfo), JSON.stringify(prompt1));

// take heart
await page.click('canvas');
await page.keyboard.down('KeyE'); await new Promise(r => setTimeout(r, 250)); await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 600));

// altar
await page.evaluate(() => window.__game.teleport(0, 1.5, -34));
await new Promise(r => setTimeout(r, 800));
const prompt2 = await page.evaluate(() => ({ shown: document.getElementById('prompt').classList.contains('show'), text: document.getElementById('prompt-act').textContent }));
console.log('at altar:', JSON.stringify(prompt2));
await page.keyboard.down('KeyE'); await new Promise(r => setTimeout(r, 250)); await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 3000));
const s2 = await page.evaluate(() => window.__game.stage);
console.log('final:', JSON.stringify(s2));
console.log(errors.length ? errors.join('\n') : 'NO ERRORS');
await browser.close();

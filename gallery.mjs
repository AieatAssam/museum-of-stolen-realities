import puppeteer from 'puppeteer-core';
const SHOT = process.env.SHOT_DIR || '/tmp';
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--use-gl=angle', '--enable-unsafe-swiftshader', '--window-size=1600,900'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 900 });
const errors = [];
page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
await page.goto('http://localhost:8642/', { waitUntil: 'load', timeout: 60000 });
await page.waitForFunction('window.__game !== undefined', { timeout: 30000 });

// mid-intro crane shot
await new Promise(r => setTimeout(r, 4000));
await page.screenshot({ path: SHOT + '/g1-intro.png' });
await new Promise(r => setTimeout(r, 6500));

// nave from entrance, looking down toward the rose window
await page.evaluate(() => { window.__game.input.lookX = 0; window.__game.input.lookY = 0.15; window.__game.teleport(0, 0, 44); });
await new Promise(r => setTimeout(r, 1500));
await page.screenshot({ path: SHOT + '/g2-nave.png' });

// chapel resonator
await page.evaluate(() => { window.__game.input.lookX = Math.PI * 0.65; window.__game.teleport(31, 0, 6); });
await new Promise(r => setTimeout(r, 1500));
await page.screenshot({ path: SHOT + '/g3-chapel.png' });

// activate A, glass stairs rising
await page.evaluate(() => window.__game.teleport(35, 0, 6));
await page.click('canvas');
await page.keyboard.down('KeyE');
await new Promise(r => setTimeout(r, 250));
await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 2500));
await page.evaluate(() => { window.__game.input.lookX = -Math.PI * 0.4; window.__game.teleport(0, 0, 12); });
await new Promise(r => setTimeout(r, 1200));
await page.screenshot({ path: SHOT + '/g4-stairs.png' });

// warden mid-fight
await page.evaluate(() => { window.__game.activateAll(); });
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { window.__game.input.lookX = Math.PI; window.__game.teleport(4, 0, -34); });
await new Promise(r => setTimeout(r, 3500));
await page.screenshot({ path: SHOT + '/g5-warden.png' });

// climax
await page.evaluate(() => window.__game.killWarden());
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => window.__game.teleport(0, 1.5, -34));
await new Promise(r => setTimeout(r, 700));
await page.keyboard.down('KeyE');
await new Promise(r => setTimeout(r, 250));
await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 6800));
await page.screenshot({ path: SHOT + '/g6-climax.png' });
await new Promise(r => setTimeout(r, 4500));
await page.screenshot({ path: SHOT + '/g7-ending.png' });

const state = await page.evaluate(() => window.__game.stage);
console.log('state:', JSON.stringify(state));
console.log(errors.length ? errors.join('\n') : 'NO ERRORS');
await browser.close();

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
page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()); });

await page.goto('http://localhost:8642/', { waitUntil: 'networkidle0', timeout: 30000 });
await new Promise(r => setTimeout(r, 2500));
await page.screenshot({ path: SHOT + '/s1-intro.png' });

// wait for intro to finish
await new Promise(r => setTimeout(r, 6500));
await page.screenshot({ path: SHOT + '/s2-play.png' });

// teleport to resonator A (chapel), activate with E
await page.evaluate(() => window.__game.teleport(33, 0, 6));
await new Promise(r => setTimeout(r, 800));
await page.keyboard.down('KeyE');
await new Promise(r => setTimeout(r, 200));
await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 1500));
await page.screenshot({ path: SHOT + '/s3-resonatorA.png' });

// activate all, teleport to warden fight
await page.evaluate(() => window.__game.activateAll());
await new Promise(r => setTimeout(r, 1200));
await page.evaluate(() => window.__game.teleport(6, 0, -40));
await new Promise(r => setTimeout(r, 2200));
await page.screenshot({ path: SHOT + '/s4-warden.png' });

// kill warden, go to altar, restore
await page.evaluate(() => window.__game.killWarden());
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => window.__game.teleport(0, 1.5, -34));
await new Promise(r => setTimeout(r, 800));
await page.keyboard.down('KeyE');
await new Promise(r => setTimeout(r, 200));
await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 6500));
await page.screenshot({ path: SHOT + '/s5-climax.png' });
await new Promise(r => setTimeout(r, 4500));
await page.screenshot({ path: SHOT + '/s6-ending.png' });

const state = await page.evaluate(() => window.__game.stage);
console.log('state:', JSON.stringify(state));
console.log(errors.length ? errors.join('\n') : 'NO ERRORS');
await browser.close();
process.exit(errors.length ? 1 : 0);

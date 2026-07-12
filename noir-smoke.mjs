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
await page.goto('http://localhost:8642/?wing=noir', { waitUntil: 'load', timeout: 60000 });
await page.waitForFunction('window.__game !== undefined', { timeout: 30000 });
await new Promise(r => setTimeout(r, 4000));
await page.screenshot({ path: SHOT + '/n1-intro.png' });
await new Promise(r => setTimeout(r, 7000));

// street view
await page.evaluate(() => { window.__game.input.lookX = 0; window.__game.input.lookY = 0.12; window.__game.teleport(0, 0, 42); });
await new Promise(r => setTimeout(r, 1500));
await page.screenshot({ path: SHOT + '/n2-street.png' });

// activate 2 nodes -> wake cinematic
await page.evaluate(() => { window.__game.activateOne(0); window.__game.activateOne(1); });
await new Promise(r => setTimeout(r, 3000));
await page.screenshot({ path: SHOT + '/n3-wake.png' });
await new Promise(r => setTimeout(r, 3000));

// fight view
await page.evaluate(() => { window.__game.input.lookX = Math.PI * 0.9; window.__game.teleport(-2, 0, -26); });
await new Promise(r => setTimeout(r, 2500));
await page.screenshot({ path: SHOT + '/n4-shade.png' });

// kill, third node, drop, marquee climax
await page.evaluate(() => { window.__game.killWarden(); window.__game.activateOne(2); });
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => window.__game.teleport(window.__game.guardian.pos.x, 0, window.__game.guardian.pos.z + 1));
await new Promise(r => setTimeout(r, 700));
await page.click('canvas');
await page.keyboard.down('KeyE'); await new Promise(r => setTimeout(r, 250)); await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 600));
await page.evaluate(() => window.__game.teleport(0, 1, -48));
await new Promise(r => setTimeout(r, 700));
await page.keyboard.down('KeyE'); await new Promise(r => setTimeout(r, 250)); await page.keyboard.up('KeyE');
await new Promise(r => setTimeout(r, 5000));
await page.screenshot({ path: SHOT + '/n5-colorflood.png' });
await new Promise(r => setTimeout(r, 7000));
await page.screenshot({ path: SHOT + '/n6-ending.png' });

const state = await page.evaluate(() => window.__game.stage);
console.log('state:', JSON.stringify(state));
console.log(errors.length ? errors.join('\n') : 'NO ERRORS');
await browser.close();
process.exit(errors.length ? 1 : 0);

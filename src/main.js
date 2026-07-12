import { runWing } from './engine/flow.js';

// Wing loader — ?wing=glass (default) | noir
const id = new URLSearchParams(location.search).get('wing') || 'glass';
const known = ['glass', 'noir'];
const pick = known.includes(id) ? id : 'glass';

import(`./wings/${pick}/index.js`).then(mod => runWing(mod.default));

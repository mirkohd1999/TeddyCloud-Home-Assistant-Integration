/* Simple card/editor regression checks without a browser or Home Assistant. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const paths = require('node:path');

class FakeElement {
  attachShadow() {
    const root = {
      innerHTML: '',
      addEventListener() {},
      getElementById() { return {addEventListener() {}}; },
      querySelectorAll() { return []; }
    };
    this.shadowRoot = root;
    return root;
  }
  dispatchEvent(event) { this._lastEvent = event; }
}
const components = new Map();
const context = {
  HTMLElement: FakeElement,
  customElements: {
    get(name) { return components.get(name); },
    define(name, value) { components.set(name, value); }
  },
  window: {customCards: []},
  setInterval: () => 1,
  clearInterval() {},
  console,
  Date,
  Event: class {},
  CustomEvent: class { constructor(name, options) {this.type=name;this.detail=options.detail;} }
};
vm.runInNewContext(
  fs.readFileSync(paths.join(__dirname, '../www/teddycloud-homeassistant-card.js'), 'utf8'),
  context
);
const Card = components.get('teddycloud-homeassistant-card');
const Editor = components.get('teddycloud-homeassistant-card-editor');
assert.ok(Card);
assert.ok(Editor);
const hass = {states: {
  'media_player.test': {
    state: 'playing',
    attributes: {
      friendly_name: 'Kinderzimmer',
      media_title: 'Mein Tonie',
      media_duration: 600,
      estimated_playback_started: new Date().toISOString(),
      box_color: '#aabbcc', volume_level_raw: 8,
      charger: 'ON', figure_present: true, entity_picture: '/local/tonie.png'
    }
  },
  'sensor.gross': {state:'pressed', attributes:{friendly_name:'Kinderzimmer Großes Ohr (lauter)', press_count:2}},
  'sensor.klein': {state:'double-pressed', attributes:{friendly_name:'Kinderzimmer Kleines Ohr (leiser)', press_count:1}}
}};
for (const mode of ['compact','artwork','status','tiles','custom','player','settings','all']) {
  const card = new Card();
  card.setConfig({entity:'media_player.test', mode});
  card.hass = hass;
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes('ha-card'), 'missing HA card in ' + mode);
  assert.ok(html.includes('Mein Tonie') || mode === 'settings', 'missing title in ' + mode);
  if (mode === 'compact') assert.ok(html.includes('small-art'));
  if (mode === 'status') assert.ok(html.includes('Großes Ohr'));
  if (mode === 'tiles') assert.ok(html.includes('grid'));
  if (mode === 'all') assert.ok(html.includes('Toniebox-Einstellungen'));
}
const custom = new Card();
custom.setConfig({entity:'media_player.test', mode:'custom',
  layout:'grid', columns:3, sections:['title','ears','volume','progress']});
custom.hass = hass;
const html = custom.shadowRoot.innerHTML;
assert.ok(html.includes('--board-cols:3'));
assert.ok(html.indexOf('Mein Tonie') < html.indexOf('Großes Ohr'));
assert.ok(html.includes('Doppelt') && html.includes('Einfach'));
assert.ok(!html.includes('Toniebox-Einstellungen'));
const empty = new Card();
empty.setConfig({entity:'media_player.test',mode:'custom',sections:[]});
empty.hass = hass;
assert.ok(empty.shadowRoot.innerHTML.includes('Keine Bausteine ausgewählt'));
const editor = new Editor();
editor.setConfig({entity:'media_player.test',mode:'custom',sections:['title','charger','ears']});
editor.hass = hass;
assert.ok(editor.shadowRoot.innerHTML.includes('Bausteine auswählen und sortieren'));
editor.moveSection('ears',-1);
assert.equal(editor._config.sections.join(','),'title,ears,charger');
editor.changeSections('volume',true);
assert.equal(editor._config.sections.join(','),'title,ears,charger,volume');
editor.changeSections('title',false);
assert.equal(editor._config.sections.join(','),'ears,charger,volume');
editor.changeSections('not-a-section',true);
assert.equal(editor._config.sections.join(','),'ears,charger,volume');
console.log('Dashboard layout and visual editor tests passed.');

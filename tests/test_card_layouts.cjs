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
assert.ok(editor.shadowRoot.innerHTML.includes('3. Deine Bausteine'));
assert.ok(editor.shadowRoot.innerHTML.includes('TeddyCloud Karteneditor v0.3.5'));
assert.ok(editor.shadowRoot.innerHTML.includes('Selbst gestalten'));
assert.ok(editor.shadowRoot.innerHTML.includes('Weitere Einstellungen (optional)'));
editor.moveSection('ears',-1);
assert.equal(editor._config.sections.join(','),'title,ears,charger');
editor.changeSections('volume',true);
assert.equal(editor._config.sections.join(','),'title,ears,charger,volume');
editor.changeSections('title',false);
assert.equal(editor._config.sections.join(','),'ears,charger,volume');
editor.changeSections('not-a-section',true);
assert.equal(editor._config.sections.join(','),'ears,charger,volume');
// One-tap presets switch the preview without typing YAML or configuring MQTT.
editor.choosePreset('compact');
assert.equal(editor._config.mode, 'compact');
assert.equal(editor._lastEvent.type,'config-changed');
assert.ok(editor.shadowRoot.innerHTML.includes("class='preset selected'"));
editor.choosePreset('custom');
assert.equal(editor._config.sections.join(','),'ears,charger,volume');
editor.choosePreset('does-not-exist');
assert.equal(editor._config.mode, 'custom');

// A new self-built dashboard starts small rather than exposing all ten blocks.
const firstTime = new Editor();
firstTime.setConfig({entity:'media_player.test',mode:'all'});
firstTime.hass = hass;
assert.ok(firstTime.shadowRoot.innerHTML.includes('So soll deine Karte aussehen'));
assert.ok(firstTime.shadowRoot.innerHTML.includes('Selbst gestalten'));
assert.ok(!firstTime.shadowRoot.innerHTML.includes('3. Deine Bausteine'));
firstTime.choosePreset('custom');
assert.equal(firstTime._config.sections.join(','),'artwork,title,playback,charger,volume');
assert.equal(firstTime._config.layout,'grid');
assert.equal(firstTime._config.columns,2);
assert.ok(firstTime.shadowRoot.innerHTML.includes('3. Deine Bausteine'));
firstTime.change('name',"<script>alert(1)</script>");
assert.ok(!firstTime.shadowRoot.innerHTML.includes('<script>'));

// Pick the only Toniebox automatically, but never replace a deliberate choice.
const auto = new Editor();
auto.setConfig({entity:''});
auto.hass = hass;
assert.equal(auto._config.entity,'media_player.test');
assert.equal(auto._lastEvent.type,'config-changed');
const unrelated = new Editor();
unrelated.setConfig({entity:''});
unrelated.hass = {states:{'media_player.radio':{state:'playing',attributes:{friendly_name:'Radio'}}}};
assert.equal(unrelated._config.entity,'');
const manual = new Editor();
manual.setConfig({entity:'media_player.explicit'});
manual.hass = hass;
assert.equal(manual._config.entity,'media_player.explicit');
const oldPlaceholder = new Editor();
oldPlaceholder.setConfig({entity:'media_player.meine_toniebox_now_playing'});
oldPlaceholder.hass = hass;
assert.equal(oldPlaceholder._config.entity,'media_player.test');

// The artwork caption is no longer rendered; it used to push the actual
// picture out of its tile in artwork, tiles, and custom modes.
for (const mode of ['artwork','tiles','custom']) {
  const c = new Card();
  c.setConfig({entity:'media_player.test',mode});
  c.hass = hass;
  assert.ok(!c.shadowRoot.innerHTML.includes('Tonie-Bild oder Toniebox'),
    'artwork label must not appear in ' + mode);
  assert.ok(c.shadowRoot.innerHTML.includes('board-artwork-media'));
}

// Width spans can be configured independently for every section. Both HTML
// output and the editing preview use the same saved values.
const sized = new Card();
sized.setConfig({entity:'media_player.test',mode:'custom',layout:'grid',columns:3,
  sections:['artwork','title','led','volume'],section_widths:{artwork:3,title:2,led:1,volume:3}});
sized.hass = hass;
const output = sized.shadowRoot.innerHTML;
for (const [id,span] of [['artwork',3],['title',2],['led',1],['volume',3]]) {
  assert.ok(output.includes('board-' + id + '" style="--section-span:' + span + '"'),
    'wrong span for ' + id);
}
assert.ok(!output.includes('Tonie-Bild oder Toniebox'));

// Invalid, oversized or hostile values must not become inline CSS.
const oversized = new Card();
oversized.setConfig({entity:'media_player.test',mode:'custom',layout:'grid',columns:2,
  sections:['title','artwork','volume'],
  section_widths:{title:99,artwork:'0; color:red',volume:-1}});
oversized.hass = hass;
const safeOutput = oversized.shadowRoot.innerHTML;
assert.ok(safeOutput.includes('board-title" style="--section-span:2"'));
assert.ok(safeOutput.includes('board-artwork" style="--section-span:1"'));
assert.ok(safeOutput.includes('board-volume" style="--section-span:1"'));
assert.ok(!safeOutput.includes('color:red'));

// A list layout ignores saved grid widths, but keeps them for future changes.
const stacked = new Card();
stacked.setConfig({entity:'media_player.test',mode:'custom',layout:'stack',
  sections:['artwork','title'],section_widths:{artwork:3}});
stacked.hass = hass;
assert.ok(!stacked.shadowRoot.innerHTML.includes('--section-span:'));

const widthEditor = new Editor();
widthEditor.setConfig({entity:'media_player.test',mode:'custom',layout:'grid',
  columns:3,sections:['artwork','title','ears'],section_widths:{artwork:2}});
widthEditor.hass = hass;
assert.ok(widthEditor.shadowRoot.innerHTML.includes("data-width='artwork'"));
assert.ok(widthEditor.shadowRoot.innerHTML.includes('Volle Breite'));
widthEditor.changeSectionWidth('title',3);
assert.equal(widthEditor._config.section_widths.title,3);
assert.equal(widthEditor._config.section_widths.artwork,2);
assert.equal(widthEditor._lastEvent.type,'config-changed');
widthEditor.changeSectionWidth('title',0);
widthEditor.changeSectionWidth('title',10);
widthEditor.changeSectionWidth('unknown',2);
assert.equal(widthEditor._config.section_widths.title,3);
widthEditor.change('columns',2);
assert.ok(!widthEditor.shadowRoot.innerHTML.includes('3 Spalten'));
assert.ok(widthEditor.shadowRoot.innerHTML.includes("data-width='title'"));
widthEditor.change('layout','stack');
assert.ok(!widthEditor.shadowRoot.innerHTML.includes("data-width='title'"));
assert.equal(widthEditor._config.section_widths.title,3);

// Separate non-admin library card: no dashboard editing or YAML needed.
const LibraryCard = components.get('teddycloud-tonie-library-card');
assert.ok(LibraryCard, 'Tonie library card must be registered');
const libraryCard = new LibraryCard();
libraryCard.setConfig({});
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Meine Tonie-Bibliothek'));
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Bibliothek wird geladen'));
const libraryData = [
  {audio_id:'12345',title:'Der kleine Tonie',image:'https://example.org/tonie.jpg',
    duration_seconds:3600, custom:{},times_seen:2},
  {audio_id:'67890',title:'Ein anderes Hörspiel',image:'',duration_seconds:1800, custom:{}}
];
libraryCard._entries = libraryData;
libraryCard.render();
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Der kleine Tonie'));
assert.ok(libraryCard.shadowRoot.innerHTML.includes('60 Min.'));
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Tonie hinzufügen'));
libraryCard._openEdit('12345');
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Hörspiellänge in Minuten'));
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Bild direkt vom Gerät'));
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Änderungen speichern'));
libraryCard._edit = null;
libraryCard._deleteId = '12345';
libraryCard.render();
assert.ok(libraryCard.shadowRoot.innerHTML.includes('Ja, löschen'));
assert.equal(libraryCard._safeImage('javascript:alert(1)'), '');
assert.equal(libraryCard._safeImage('data:text/html,evil'), '');
assert.equal(libraryCard._safeImage('/local/teddycloud_homeassistant/library/12345.png'), '/local/teddycloud_homeassistant/library/12345.png');
libraryCard._entries = [{audio_id:'888',title:'<script>evil</script>',
  image:'javascript:alert(1)',duration_seconds:null,custom:{}}];
libraryCard._deleteId = null;
libraryCard.render();
assert.ok(!libraryCard.shadowRoot.innerHTML.includes('<script>'));
assert.ok(!libraryCard.shadowRoot.innerHTML.includes('src="javascript'));
assert.ok(window === undefined || true); // registration is inspected via components above
console.log('Dashboard layout, editor and Tonie library tests passed.');

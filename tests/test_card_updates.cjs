/* Simulate a real old custom-element registration surviving a module update. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Audio {
  constructor() { this.attrs = {}; this.events = {}; this.paused = true; this.currentTime = 0; }
  setAttribute(key, value) { this.attrs[key] = value; }
  getAttribute(key) { return this.attrs[key]; }
  removeAttribute(key) { delete this.attrs[key]; }
  addEventListener(name, fn) { this.events[name] = fn; }
  play() { this.paused = false; this.events.play?.(); return Promise.resolve(); }
  pause() { this.paused = true; this.events.pause?.(); }
  load() { this.released = true; }
  remove() { this.removed = true; }
}
class Element {
  constructor() { this.localName = 'teddycloud-tonie-library-card'; }
  attachShadow() {
    this.shadowRoot = {
      innerHTML:'', addEventListener() {},
      querySelectorAll(selector) {
        if (selector !== 'button[data-action="preview"]') return [];
        if (this.markup !== this.innerHTML) {
          this.markup = this.innerHTML;
          this.buttons = [...this.innerHTML.matchAll(/<button[^>]*data-action="preview"[^>]*data-id="([^"]+)"[^>]*>([^<]*)<\/button>/g)].map(m => ({
            dataset:{id:m[1]}, textContent:m[2], setAttribute() {}
          }));
        }
        return this.buttons || [];
      },
      getElementById() { return {appendChild() {}}; }
    };
  }
}
const components = new Map();
const imports = [];
const context = vm.createContext({
  HTMLElement:Element, window:{customCards:[]}, console,
  customElements:{get:name=>components.get(name), define(name, value) {
    assert.ok(!components.has(name), 'A custom element must never be defined twice');
    components.set(name, value);
  }},
  document:{querySelectorAll:()=>[], createElement:()=>new Audio()},
  setInterval:()=>1, clearInterval() {},
});
const source = fs.readFileSync(path.join(__dirname, '../www/teddycloud-homeassistant-card.js'), 'utf8');
const oldSource = fs.readFileSync(path.join(__dirname, 'fixtures/card-v057-library.js'), 'utf8');
function evaluate(code) { vm.runInContext(`(() => {${code}\n})()`, context); }
function button(card) { return card.shadowRoot.querySelectorAll('button[data-action="preview"]')[0].textContent; }
function initialize(card, admin) {
  card._hass = {user:{is_admin:admin}, locale:{language:'de'}};
  card._entries = [{audio_id:'123', title:'My title',times_seen:4,
    preview_url:'https://cdn.tonies.de/o/audio_samples/a/one.mp3'}];
  card.setConfig({name:'Existing library'});
}
async function run() {
  evaluate(oldSource);
  const Registered = components.get('teddycloud-tonie-library-card');
  const normal = new Registered(), admin = new Registered(), editing = new Registered();
  initialize(normal, false); initialize(admin, true); initialize(editing, true);
  editing._openEdit('123');
  const editState = editing._edit;
  const editingMarkup = editing.shadowRoot.innerHTML + '<input value="Unsaved text">';
  editing.shadowRoot.innerHTML = editingMarkup;
  await normal._togglePreview('123');
  const oldAudio = normal._previewAudio;
  assert.equal(oldAudio.controls, true);
  assert.ok(normal.shadowRoot.innerHTML.includes('preview-panel'), 'Reproduce the screenshot');
  // Home Assistant nests cards inside several shadow roots.
  context.document.querySelectorAll = () => [{shadowRoot:{querySelectorAll:()=>[normal, admin, editing]}}];
  evaluate(source);
  assert.equal(components.get('teddycloud-tonie-library-card'), Registered);
  assert.equal(Registered.teddyCardVersion, '0.5.9');
  assert.equal(editing._edit, editState);
  assert.equal(editing.shadowRoot.innerHTML, editingMarkup, 'Do not replace an unsaved admin form');
  assert.equal(oldAudio.paused, true);
  assert.ok(oldAudio.released && oldAudio.removed);
  for (const card of [normal, admin]) {
    assert.ok(!card.shadowRoot.innerHTML.includes('preview-panel'));
    assert.ok(!card.shadowRoot.innerHTML.includes('<audio'));
    assert.equal(button(card), '▶ Hörprobe');
    assert.equal(card._entries[0].times_seen, 4);
    assert.equal(card._config.name, 'Existing library');
  }
  assert.ok(!normal.shadowRoot.innerHTML.includes('data-action="edit"'));
  assert.ok(admin.shadowRoot.innerHTML.includes('data-action="edit"'));
  await normal._togglePreview('123');
  assert.equal(normal._previewAudio.controls, false);
  assert.equal(button(normal), '■ Stop');
  const currentAudio = normal._previewAudio;
  evaluate(source); // Duplicate resource loads must not interrupt playback.
  assert.equal(normal._previewAudio, currentAudio);
  assert.equal(currentAudio.paused, false);
  await normal._togglePreview('123');
  assert.equal(button(normal), '▶ Hörprobe');
  // Instances created through the original registered constructor also use the update.
  const later = new Registered(); initialize(later, false);
  later._hass.locale.language = 'en-GB'; later.render();
  assert.equal(button(later), '▶ Audio sample');
  await later._togglePreview('123');
  assert.equal(button(later), '■ Stop');
  later._stopPreview();
  // Exercise version detection with a test loader instead of actual network imports.
  evaluate(source + '\nwindow.testLoadCardUpdate = teddyLoadCardUpdate;');
  const load = context.window.testLoadCardUpdate;
  const loader = async url => {imports.push(url);};
  const url = '/teddycloud-homeassistant/card-v0510.js?v=0.5.10&build=123456abcdef';
  await Promise.all([load({card_version:'0.5.10',card_url:url}, loader), load({card_version:'0.5.10',card_url:url}, loader)]);
  assert.deepEqual(imports, [url]);
  for (const data of [
    {card_version:'0.5.9',card_url:url}, {card_version:'0.5.8',card_url:url},
    {card_version:'0.5.10',card_url:'https://evil.test/a.js'},
    {card_version:'0.5.10',card_url:'/local/other.js'},
    {card_version:'0.5.10',card_url:'/teddycloud-homeassistant/card-v058.js?v=0.5.10&build=123456abcdef'},
    {card_version:'invalid',card_url:url}, {}
  ]) assert.equal(load(data, loader), undefined);
  assert.equal(imports.length, 1);
  const retryURL = '/teddycloud-homeassistant/card-v060.js?v=0.6.0&build=abcdef123456';
  await assert.rejects(load({card_version:'0.6.0',card_url:retryURL}, async()=>{throw Error('offline');}));
  await load({card_version:'0.6.0',card_url:retryURL}, loader);
  assert.equal(imports.length, 2, 'A failed import can be retried');
  Registered.teddyCardVersion = '0.6.0';
  await normal._togglePreview('123');
  const newestAudio = normal._previewAudio;
  evaluate(source);
  assert.equal(Registered.teddyCardVersion, '0.6.0', 'A late older module cannot downgrade the card');
  assert.equal(normal._previewAudio, newestAudio);
  normal._stopPreview();
  console.log('Already-open v0.5.7 library upgraded: old player removed, localized sample/Stop, roles and safe version imports passed.');
}
run().catch(error=>{console.error(error);process.exitCode=1;});

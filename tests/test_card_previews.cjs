/* Dashboard playback lifecycle with an HTMLAudioElement test double. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const audios = [];
class FakeAudio {
  constructor() { this.paused = true; this.ended = false; this.currentTime = 0; this.attrs = {}; this.listeners = {}; audios.push(this); }
  setAttribute(key, value) { this.attrs[key] = value; }
  getAttribute(key) { return this.attrs[key]; }
  removeAttribute(key) { delete this.attrs[key]; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  emit(name) { this.listeners[name]?.(); }
  play() { this.paused = false; this.emit('play'); return this.playResult || Promise.resolve(); }
  pause() { this.paused = true; this.emit('pause'); }
  load() { this.loadCalls = (this.loadCalls || 0) + 1; }
  remove() { this.removed = true; }
}
class FakeElement {
  attachShadow() {
    this.shadowRoot = {
      innerHTML: '', events: {}, mounted: null,
      addEventListener(name, handler) { this.events[name] = handler; },
      getElementById() { return {appendChild: audio => { this.mounted = audio; }}; },
      querySelectorAll(selector) {
        if (selector !== 'button[data-action="preview"]') return [];
        if (this.buttonHTML !== this.innerHTML) {
          this.buttonHTML = this.innerHTML;
          this.buttons = [...this.innerHTML.matchAll(/<button[^>]*data-action="preview"[^>]*data-id="([^"]+)"[^>]*>([^<]*)<\/button>/g)].map(match => ({
            dataset:{id:match[1]}, textContent:match[2], attrs:{},
            setAttribute(key, value) { this.attrs[key] = value; }
          }));
        }
        return this.buttons || [];
      }
    };
  }
}
const components = new Map();
const context = {
  HTMLElement: FakeElement,
  customElements: {get: name => components.get(name), define: (name, value) => components.set(name, value)},
  document: {createElement(tag) { assert.equal(tag, 'audio'); return new FakeAudio(); }},
  window: {customCards: []}, console, setInterval: () => 1, clearInterval() {},
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../www/teddycloud-homeassistant-card.js'), 'utf8'), context);
const Card = components.get('teddycloud-tonie-library-card');
const sample = name => `https://cdn.tonies.de/o/audio_samples/test/${name}.mp3`;
function makeCard(admin = false, language = 'de') {
  const card = new Card();
  card._hass = {user:{is_admin:admin}, locale:{language}};
  card._entries = [
    {audio_id:'a', title:'Rocky', preview_url:sample('rocky'), times_seen:5},
    {audio_id:'b', title:'Bibi', preview_url:sample('bibi'), times_seen:3},
    {audio_id:'c', title:'Maus', preview_url:null},
    {audio_id:'bad', title:'Invalid URL', preview_url:'https://example.test/wrong.mp3'}
  ];
  card.setConfig({});
  return card;
}
async function run() {
  const card = makeCard();
  assert.equal(audios.length, 0, 'No media element or preload before a user click');
  assert.equal((card.shadowRoot.innerHTML.match(/data-action="preview"/g) || []).length, 2);
  assert.ok(!card.shadowRoot.innerHTML.includes('href='), 'No navigation to a shop');
  assert.ok(!card.shadowRoot.innerHTML.includes('data-action="edit"'));
  await card._togglePreview('c');
  await card._togglePreview('bad');
  assert.equal(audios.length, 0, 'Missing/invalid samples never cause a request');
  // Exercise the same delegated click route used by dashboard buttons.
  card.shadowRoot.events.click({target:{closest:() => ({dataset:{action:'preview',id:'a'}})}});
  await Promise.resolve();
  const first = card._previewAudio;
  assert.equal(first.getAttribute('src'), sample('rocky'));
  assert.equal(first.controls, false);
  assert.equal(first.preload, 'none');
  assert.equal(card.shadowRoot.mounted, null, 'Audio is never attached as a visible player');
  assert.ok(!card.shadowRoot.innerHTML.includes('preview-panel'));
  assert.ok(!card.shadowRoot.innerHTML.includes('<audio'));
  assert.ok(!card.shadowRoot.innerHTML.includes('library-preview-player'));
  assert.equal(card.shadowRoot.querySelectorAll('button[data-action="preview"]')[0].textContent, '■ Stop');
  assert.equal(first.paused, false);
  first.currentTime = 17;
  card.render();
  card._entries[0].times_seen = 6;
  card.render();
  assert.equal(card._previewAudio, first, 'Live updates reuse the media element');
  assert.equal(first.currentTime, 17);
  await card._togglePreview('a');
  assert.equal(first.paused, true);
  assert.equal(card._previewAudio, null, 'The second click stops and releases playback');
  assert.equal(card.shadowRoot.querySelectorAll('button[data-action="preview"]')[0].textContent, '▶ Hörprobe');
  await card._togglePreview('a');
  assert.notEqual(card._previewAudio, first, 'Play after Stop starts a fresh sample');
  assert.equal(card._previewAudio.currentTime, 0);
  card._previewAudio.ended = true;
  card._previewAudio.emit('ended');
  assert.equal(card._previewAudio, null, 'Natural end resets the button to Play');
  assert.equal(card.shadowRoot.querySelectorAll('button[data-action="preview"]')[0].textContent, '▶ Hörprobe');
  await card._togglePreview('a');
  await card._togglePreview('b');
  assert.equal(first.paused, true);
  assert.equal(first.getAttribute('src'), undefined, 'Previous download is released');
  assert.ok(first.loadCalls && first.removed);
  assert.equal(card._previewAudio.getAttribute('src'), sample('bibi'));
  // Starting a sample in another library card also stops the first card.
  const other = makeCard(true, 'en-GB');
  assert.ok(other.shadowRoot.innerHTML.includes('Audio sample'));
  await other._togglePreview('a');
  assert.equal(card._previewAudio, null);
  assert.equal(card._entries[0].times_seen, 6, 'Preview playback does not change collection counts');
  const beforeLanguageChange = other._previewAudio;
  other._hass.locale.language = 'de';
  other.render();
  assert.equal(other._previewAudio, beforeLanguageChange);
  assert.ok(!other.shadowRoot.innerHTML.includes('preview-panel'));
  assert.equal(other.shadowRoot.querySelectorAll('button[data-action="preview"]')[0].textContent, '■ Stop');
  other._previewAudio.emit('error');
  assert.equal(other._previewAudio, null);
  assert.ok(other.shadowRoot.innerHTML.includes('Hörprobe derzeit nicht erreichbar.'));
  await other._togglePreview('a');
  assert.equal(other._previewError, null);
  other._entries = other._entries.filter(entry => entry.audio_id !== 'a');
  other.render();
  assert.equal(other._previewAudio, null, 'Deleting a playing entry stops its sample');
  await other._togglePreview('b');
  other._entries[0].preview_url = null;
  other.render();
  assert.equal(other._previewAudio, null, 'Removing a catalog URL stops its sample');
  await card._togglePreview('a');
  card.disconnectedCallback();
  assert.equal(card._previewAudio, null, 'Leaving the dashboard stops playback');
  // A late play() rejection must not stop a newer sample.
  const pending = makeCard();
  let rejectFirst;
  const promise = new Promise((resolve, reject) => { rejectFirst = reject; });
  const originalPlay = FakeAudio.prototype.play;
  FakeAudio.prototype.play = function () { this.paused = false; this.emit('play'); return promise; };
  const oldPlay = pending._togglePreview('a');
  FakeAudio.prototype.play = originalPlay;
  await pending._togglePreview('b');
  rejectFirst(new Error('old sample aborted'));
  await oldPlay;
  assert.equal(pending._previewId, 'b');
  pending._stopPreview();
  // Failures from the active play promise are displayed and can be retried.
  FakeAudio.prototype.play = () => Promise.reject(new Error('blocked'));
  await pending._togglePreview('a');
  assert.equal(pending._previewAudio, null);
  assert.ok(pending.shadowRoot.innerHTML.includes('Hörprobe derzeit nicht erreichbar.'));
  FakeAudio.prototype.play = originalPlay;
  // An OS interruption of an in-flight play request is not a broken sample.
  FakeAudio.prototype.play = function () {
    this.paused = true;
    return Promise.reject({name:'AbortError'});
  };
  await pending._togglePreview('b');
  assert.equal(pending._previewError, null);
  assert.equal(pending._previewId, 'b');
  pending._stopPreview();
  FakeAudio.prototype.play = originalPlay;
  for (const admin of [false, true]) {
    const refreshCard = makeCard(admin, 'en');
    refreshCard._entries = [{audio_id:'a',title:'Rocky',preview_url:null,times_seen:2}];
    refreshCard._previewCatalogStatus = 'ready';
    refreshCard.render();
    assert.ok(refreshCard.shadowRoot.innerHTML.includes('Refresh audio samples'));
    assert.ok(refreshCard.shadowRoot.innerHTML.includes('no matching audio samples'));
    let resolveRefresh;
    let requests = 0;
    refreshCard._hass.callWS = message => {
      assert.equal(message.type, 'teddycloud_homeassistant/library/refresh');
      assert.deepEqual(Object.keys(message), ['type'], 'No user-supplied search source or URL');
      requests++;
      return new Promise(resolve => {resolveRefresh = resolve;});
    };
    const refresh = refreshCard._refreshPreviews();
    assert.equal(refreshCard._refreshingPreviews, true);
    assert.ok(refreshCard.shadowRoot.innerHTML.includes('Checking the catalog'));
    await refreshCard._refreshPreviews();
    assert.equal(requests, 1, 'Prevent concurrent refreshes from the same card');
    resolveRefresh({entries:[{audio_id:'a',title:'Rocky',preview_url:sample('rocky'),times_seen:2}],preview_catalog_status:'ready'});
    await refresh;
    assert.equal(refreshCard._refreshingPreviews, false);
    assert.ok(refreshCard.shadowRoot.innerHTML.includes('data-action="preview"'));
    assert.equal(refreshCard._entries[0].times_seen, 2);
    await refreshCard._togglePreview('a');
    const audio = refreshCard._previewAudio;
    audio.currentTime = 12;
    refreshCard._hass.callWS = async () => ({entries:refreshCard._entries,preview_catalog_status:'ready'});
    await refreshCard._refreshPreviews();
    assert.equal(refreshCard._previewAudio, audio, 'Refreshing metadata must not restart playback');
    assert.equal(audio.currentTime, 12);
    refreshCard._stopPreview();
    refreshCard._previewCatalogStatus = 'unavailable';
    refreshCard.render();
    assert.ok(refreshCard.shadowRoot.innerHTML.includes('temporarily unavailable'));
    refreshCard._hass.callWS = async () => { throw {code:'unknown_command'}; };
    await refreshCard._refreshPreviews();
    assert.ok(refreshCard.shadowRoot.innerHTML.includes('restart Home Assistant'));
  }
  console.log('Play/Stop-only audio samples: hidden media, restart after Stop, natural end, roles, language, switching and errors passed.');
}
run().catch(error => {console.error(error); process.exitCode = 1;});

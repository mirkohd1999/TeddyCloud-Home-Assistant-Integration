/* Sign private image paths through the user's HA session; no persistent tokens. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let now = 1000000, nextTimer = 1;
const timers = new Map();
class Clock extends Date { static now() { return now; } }
class Element {
  attachShadow() {
    this.shadowRoot = {innerHTML:'',events:{},
      addEventListener(name,fn) { this.events[name] = fn; },
      removeEventListener(name,fn) { if(this.events[name]===fn) delete this.events[name]; },
      querySelectorAll() { return []; }, getElementById() {return null;}};
  }
}
const components = new Map();
const context = {HTMLElement:Element,customElements:{get:n=>components.get(n),define:(n,c)=>components.set(n,c)},
  window:{customCards:[]},console,Date:Clock,setInterval:()=>1,clearInterval(){},
  setTimeout(fn,ms){const id=nextTimer++;timers.set(id,{fn,at:now+ms});return id;},
  clearTimeout(id){timers.delete(id);}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../www/teddycloud-homeassistant-card.js'),'utf8'),context);
const Library = components.get('teddycloud-tonie-library-card');
const Player = components.get('teddycloud-homeassistant-card');
const privatePath = '/api/teddycloud_homeassistant/images/library/123.png?v=123';
const calls = [];
function hass(id,admin=false) {
  return {user:{id,is_admin:admin},locale:{language:'de'},connection:{subscribeMessage:()=>Promise.resolve(()=>{})},
    async callWS(message) {
      calls.push({id,message});
      assert.equal(message.type,'auth/sign_path');
      assert.equal(message.expires,300);
      return {path:message.path+'&authSig=sig-'+id+'-'+calls.length};
    }};
}
function library(session) {
  const card = new Library();
  card._hass = session;
  card._entries = [{audio_id:'123',title:'Private photo',image:privatePath,times_seen:4}];
  card.setConfig({});
  return card;
}
async function flush() { for(let i=0;i<12;i++) await Promise.resolve(); }
async function tick(ms) {
  now+=ms;
  const due = [...timers.entries()].filter(([,timer])=>timer.at<=now);
  for(const [id,timer] of due){timers.delete(id);timer.fn();}
  await flush();
}
async function run() {
  const card = library(hass('alice'));
  assert.ok(!card.shadowRoot.innerHTML.includes('src="/api/'), 'Never insert an unsigned private img source');
  card.render();card.render();await flush();
  assert.equal(calls.length,1,'Pending signatures are deduplicated');
  assert.equal(calls[0].message.path,privatePath);
  assert.ok(card.shadowRoot.innerHTML.includes('authSig=sig-alice-1'));
  assert.equal(card._entries[0].image,privatePath,'Do not store signatures in library metadata');
  const old = card.shadowRoot.innerHTML;
  await tick(240001);
  assert.equal(calls.length,2,'Renew before the five-minute signature expires');
  assert.notEqual(card.shadowRoot.innerHTML,old);
  const signed = card._imageSigner.cache.get(privatePath).signed;
  card.shadowRoot.events.error({target:{getAttribute:()=>signed}});
  await flush();
  assert.equal(calls.length,3,'An image error after HA restart requests a fresh signature');
  const retry = card._imageSigner.cache.get(privatePath).signed;
  card.shadowRoot.events.error({target:{getAttribute:()=>retry}});
  await flush();assert.equal(calls.length,3,'Do not loop on missing files');
  const beforeRestart=calls.length;
  card._acceptLibraryData({entries:card._entries,preview_catalog_status:'ready',image_generation:'new-runtime'});
  await flush();
  assert.equal(calls.length,beforeRestart+1,'A new server runtime invalidates old signatures before img requests');
  card._hass = hass('bob',true);card.render();await flush();
  assert.ok(card.shadowRoot.innerHTML.includes('authSig=sig-bob-'));
  assert.ok(!card.shadowRoot.innerHTML.includes('authSig=sig-alice-'));
  assert.equal(card._entries[0].times_seen,4);
  // The now-playing card and box photo can use the same protected route too.
  const session = hass('player');
  session.states={'media_player.test':{state:'idle',attributes:{media_title:'Photo',cover_url:privatePath}}};
  const player = new Player();player.setConfig({entity:'media_player.test',mode:'compact'});player.hass=session;
  assert.ok(!player.shadowRoot.innerHTML.includes('src="/api/'));
  await flush();assert.ok(player.shadowRoot.innerHTML.includes('authSig=sig-player-'));
  const playerCount=calls.length;
  session.states['media_player.test'].attributes.image_generation='another-runtime';
  player.render();await flush();assert.equal(calls.length,playerCount+1);
  player.setConfig({entity:'media_player.test',mode:'compact',figure_image:'/api/teddycloud_homeassistant/images/figures/../secret.png'});
  assert.ok(!player.shadowRoot.innerHTML.includes('src="/api/'),'Reject malformed private paths');
  // A pending signature from a previous session cannot update the new session.
  let resolveOld;
  const oldSession=hass('old');oldSession.callWS=()=>new Promise(resolve=>{resolveOld=resolve;});
  const pending=library(oldSession);await flush();
  pending._hass=hass('new');pending.render();await flush();
  resolveOld({path:privatePath+'&authSig=old-session'});await flush();
  assert.ok(pending.shadowRoot.innerHTML.includes('authSig=sig-new-'));
  assert.ok(!pending.shadowRoot.innerHTML.includes('old-session'));
  // Non-private user-provided images are not passed to sign_path.
  const before=calls.length;
  pending._entries=[{audio_id:'public',title:'External',image:'https://example.test/photo.png'}];pending.render();await flush();
  assert.equal(calls.length,before);
  assert.ok(pending.shadowRoot.innerHTML.includes('src="https://example.test/photo.png"'));
  // Failed signing leaves a placeholder, with a bounded retry.
  let attempts=0;
  const offline=hass('offline');offline.callWS=async()=>{attempts++;throw Error('offline');};
  const failed=library(offline);await flush();failed.render();await flush();
  assert.equal(attempts,1);assert.ok(!failed.shadowRoot.innerHTML.includes('src="/api/'));
  await tick(30001);assert.equal(attempts,2);
  for(const item of [card,pending,failed])item.disconnectedCallback();
  player.disconnectedCallback();
  assert.equal(timers.size,0,'Leaving cards clears signature-renewal timers');
  const count=calls.length;await tick(300000);assert.equal(calls.length,count);
  console.log('Signed images: no anonymous private sources, both cards, per-user cache, expiry, restart, retry and cleanup passed.');
}
run().catch(error=>{console.error(error);process.exitCode=1;});

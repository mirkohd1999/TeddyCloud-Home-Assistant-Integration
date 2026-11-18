/* Exercise real admin backup controls, session checks and import confirmation. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const downloads=[],urls=[],revoked=[];
class Element {
  attachShadow(){this.shadowRoot={innerHTML:'',events:{},overwrite:false,
    addEventListener(name,fn){(this.events[name]||=[]).push(fn);},
    getElementById(id){return id==='backup-overwrite'?{checked:this.overwrite}:null;},querySelectorAll(){return [];}};}
}
const components=new Map();
const context={HTMLElement:Element,window:{customCards:[]},customElements:{get:n=>components.get(n),define:(n,c)=>components.set(n,c)},
  console,setInterval:()=>1,clearInterval(){},setTimeout:fn=>{fn();return 1;},clearTimeout(){},
  URL:{createObjectURL:blob=>{urls.push(blob);return 'blob:test';},revokeObjectURL:url=>revoked.push(url)},
  document:{createElement:tag=>{assert.equal(tag,'a');return {click(){downloads.push(this.download);}}}}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../www/teddycloud-homeassistant-card.js'),'utf8'),context);
const Card=components.get('teddycloud-tonie-library-card');
async function run(){
 const calls=[];let response;
 const connection={};
 const hass={connection,user:{id:'admin',is_admin:true},language:'de',fetchWithAuth:async (...args)=>{calls.push(args);return response;}};
 const card=new Card();card._subscribe=()=>{};card._entries=[];card.setConfig({});card.hass=hass;
 assert.ok(card.shadowRoot.innerHTML.includes('Sicherung herunterladen'));
 const file={size:100,name:'library.zip'};
 const preview={token:'review-token',new:12,existing:3,conflicts:[{audio_id:'100',title:'<script>unsafe</script>'}],images:2};
 response={ok:true,json:async()=>preview};
 await card._previewBackup(file);
 assert.ok(card.shadowRoot.innerHTML.includes('Import-Vorschau'));
 assert.ok(!card.shadowRoot.innerHTML.includes('<script>'));
 assert.ok(card.shadowRoot.innerHTML.includes('&lt;script&gt;'));
 assert.equal(calls.length,1,'Preview does not apply an import');
 assert.ok(!calls[0][1].headers['X-TeddyCloud-Mode']);
 response={ok:true};await card._applyBackup();
 assert.equal(calls.at(-1)[1].headers['X-TeddyCloud-Mode'],'merge');
 assert.equal(calls.at(-1)[1].headers['X-TeddyCloud-Preview'],'review-token');
 assert.ok(card.shadowRoot.innerHTML.includes('Sicherung erfolgreich importiert'));
 response={ok:true,json:async()=>preview};await card._previewBackup(file);
 card.shadowRoot.overwrite=true;response={ok:true};await card._applyBackup();
 assert.equal(calls.at(-1)[1].headers['X-TeddyCloud-Mode'],'overwrite');
 response={ok:true,blob:async()=>({zip:true})};await card._exportBackup();
 assert.deepEqual(downloads,['teddycloud-library.zip']);assert.equal(urls.length,1);assert.deepEqual(revoked,['blob:test']);
 const count=calls.length;await card._previewBackup({size:33554433});assert.equal(calls.length,count);
 assert.ok(card.shadowRoot.innerHTML.includes('Sicherung zu groß'));
 card.hass={...hass,language:'en'};assert.ok(card.shadowRoot.innerHTML.includes('Download backup'));
 response={ok:false,json:async()=>({error:'backup_library_changed'})};await card._previewBackup(file);
 assert.ok(card.shadowRoot.innerHTML.includes('library changed'));
 card.hass={...hass,user:{id:'normal',is_admin:false}};
 assert.ok(!card.shadowRoot.innerHTML.includes('data-backup-action'));
 const blocked=calls.length;await card._exportBackup();await card._previewBackup(file);assert.equal(calls.length,blocked);
 // A pending authenticated response must not be used after session replacement.
 card.hass=hass;let finish;
 hass.fetchWithAuth=()=>new Promise(resolve=>finish=resolve);
 const pending=card._previewBackup(file);
 card.hass={...hass,connection:{},user:{id:'other',is_admin:false}};
 finish({ok:true,json:async()=>preview});await pending;
 assert.equal(card._backupPreview,null);
 console.log('Backup UI: admin permissions, download, preview, merge/overwrite confirmation, session changes, size limits and translations passed.');
}
run().catch(err=>{console.error(err);process.exitCode=1;});

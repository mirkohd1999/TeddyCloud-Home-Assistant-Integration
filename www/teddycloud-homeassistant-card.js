/* TeddyCloud Home Assistant — custom Lovelace card (no build tooling). */
class TeddyCloudNowPlayingCard extends HTMLElement {
  setConfig(config) {
    // Allow editing and saving the card while the Toniebox is offline.
    this.config = config;
    if (!this.shadowRoot) this.attachShadow({mode:'open'});
    this.shadowRoot.addEventListener('change', event => {
      const el = event.target;
      if (!el.matches('input[data-control]') || !this._hass) return;
      const entityId = el.dataset.entity;
      const value = Number(el.value);
      if (!entityId || !Number.isFinite(value)) return;
      this._hass.callService('number', 'set_value', {entity_id: entityId, value})
        .catch(err => { console.error('TeddyCloud: Einstellung fehlgeschlagen', err); this.render(); });
    });
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
    this.render();
  }
  connectedCallback() {
    this._timer = setInterval(() => {
      const e = this._hass?.states?.[this.config?.entity];
      if (e?.state === "playing" && Number(e.attributes?.media_duration) > 0) this.render();
    }, 1000);
  }
  disconnectedCallback() { clearInterval(this._timer); }
  static getConfigElement() {
    return document.createElement('teddycloud-homeassistant-card-editor');
  }
  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(id =>
      id.startsWith('media_player.') &&
      hass.states[id].attributes?.friendly_name?.endsWith(' Now Playing')
    );
    return {entity: entity || 'media_player.meine_toniebox_now_playing', composition: true};
  }
  getCardSize() { return 8; }
  fmt(t) {
    const s = Math.max(0, Math.floor(t || 0));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2,'0')}`;
  }
  resolveNumber(configKey, nameSuffix) {
    const configured = this.config[configKey];
    if (configured) return this._hass?.states?.[configured] ? configured : null;
    const baseName = this._hass?.states?.[this.config.entity]?.attributes?.friendly_name || '';
    const boxName = baseName.replace(/ Now Playing$/, '');
    return Object.keys(this._hass?.states || {}).find(id => {
      const e = this._hass.states[id];
      return id.startsWith('number.') && e.attributes?.friendly_name === boxName + ' ' + nameSuffix;
    }) || null;
  }
  render() {
    if (!this.shadowRoot || !this.config) return;
    const e = this._hass?.states?.[this.config.entity];
    const attr = e?.attributes || {};
    const title = attr.figure_present === false ? 'Keine Figur aufgestellt' : (attr.media_title || (!e ? 'Toniebox auswählen' : 'Noch keine Titelinformationen'));
    const color = /^#[0-9a-f]{6}$/i.test(this.config.color || attr.box_color || '') ? (this.config.color || attr.box_color) : '#8f77c7';
    const url = attr.figure_present === false ? '' : (this.config.figure_image || attr.cover_url || attr.entity_picture || attr.fallback_cover || this.config.fallback_cover || '');
    // Optionally use an actual Toniebox photo, otherwise a themed stylized box.
    const boxImage = this.config.box_image || '';
    const composition = this.config.composition !== false;
    const mode = ['all', 'player', 'settings'].includes(this.config.mode) ? this.config.mode : 'all';
    const charger = String(attr.charger ?? '').trim().toUpperCase();
    const chargerText = ['ON','1','TRUE'].includes(charger) ? '🔌 Auf Ladestation' : ['OFF','0','FALSE'].includes(charger) ? '🔋 Nicht auf Ladestation' : '🔋 Ladestatus unbekannt';
    const playing = e?.state === 'playing';
    const started = attr.estimated_playback_started ? Date.parse(attr.estimated_playback_started) : NaN;
    const elapsed = playing && Number.isFinite(started) ? Math.max(0,(Date.now()-started)/1000) : null;
    const dur = Number(attr.media_duration) > 0 ? Number(attr.media_duration) : null;
    const progress = dur && elapsed !== null ? Math.min(100, elapsed / dur * 100) : 0;
    const safeAttr = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const safe = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const safeURL = /^(https?:\/\/|\/local\/)/i.test(url) ? safe(url) : '';
    const safeBoxURL = /^(https?:\/\/|\/local\/)/i.test(boxImage) ? safe(boxImage) : '';
    const controls = [
      ['speaker_entity', 'Lautsprecher-Lautstärkelimit', 'Lautsprecher-Limit', [25,50,75,100], '🔊'],
      ['headphone_entity', 'Kopfhörer-Lautstärkelimit', 'Kopfhörer-Limit', [25,50,75,100], '🎧'],
      ['led_entity', 'LED-Helligkeit', 'LED-Helligkeit', [0,50,100], '☀️']
    ].map(([key, suffix, label, values, icon]) => {
      const id = this.resolveNumber(key, suffix);
      const state = id ? this._hass?.states?.[id] : null;
      const value = state && Number(state.state);
      const valid = state && state.state !== 'unknown' && state.state !== 'unavailable' && Number.isFinite(value);
      const labels = values.map(v => key === 'led_entity' ? ({0:'Aus',50:'Gedimmt',100:'An'}[v]) : v+' %');
      return `<div class="setting"><div class="setting-head"><span>${icon} ${safe(label)}</span><strong>${valid ? value+' %' : 'Unbekannt'}</strong></div>
      <input type="range" data-control="${safe(key)}" data-entity="${safe(id || '')}" min="${values[0]}" max="${values[values.length-1]}" step="${values[1]-values[0]}" value="${valid ? value : values[0]}" ${valid ? '' : 'disabled'}>
      <div class="ticks">${labels.map(x => `<span>${safe(x)}</span>`).join('')}</div></div>`;
    }).join('');
    const artBlock = composition ? `<div class="stage" aria-label="Toniebox mit Tonie-Figur">
      ${safeBoxURL ? `<img class="box-photo" src="${safeBoxURL}" alt="Toniebox" loading="lazy">` : `<div class="toy-box" style="--box-color:${color}"><div class="ear left"></div><div class="ear right"></div><div class="speaker"></div></div>`}
      ${safeURL ? `<img class="figure-photo" src="${safeURL}" alt="Erkanntes Tonie-Bild" loading="eager" onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">` : ''}
      <div class="figure-fallback" style="display:${safeURL?'none':'grid'}">🧸</div>
    </div>` : (safeURL ? `<img class="art" src="${safeURL}" alt="Tonie-Bild">` : `<div class="art placeholder">🧸</div>`);
    this.shadowRoot.innerHTML = `<style>
    :host{display:block}ha-card{padding:20px;background:linear-gradient(135deg,${color}24,transparent 70%),var(--ha-card-background,var(--card-background-color,#fff));border-radius:18px}
    .flex{display:flex;gap:16px;align-items:center}
    .stage{position:relative;width:205px;height:210px;flex:0 0 205px;overflow:hidden;border-radius:16px;background:radial-gradient(circle at 45% 37%,#ffffff15,transparent 70%)}
    .toy-box{position:absolute;left:18px;top:35px;width:170px;height:156px;border-radius:19px 24px 10px 12px;background:var(--box-color);box-shadow:inset -14px -6px 23px #0003,inset 12px 11px 20px #fff3,9px 10px 14px #0002;transform:skewY(-2deg)}
    .toy-box::before{content:'';position:absolute;left:13px;top:-10px;width:144px;height:30px;border-radius:70% 65% 35% 35%;background:color-mix(in srgb,var(--box-color),white 35%);transform:skewY(2deg)}
    .ear{position:absolute;top:-24px;width:26px;height:31px;background:#929294;clip-path:polygon(50% 0,100% 100%,0 100%);z-index:1}.ear.left{left:39px}.ear.right{right:34px}
    .speaker{position:absolute;left:28px;top:49px;width:111px;height:80px;opacity:.6;background-image:radial-gradient(#18181a 2.4px,transparent 2.5px);background-size:12px 12px;clip-path:ellipse(50% 49%)}
    .box-photo{position:absolute;inset:4px 0 0 0;width:100%;height:91%;object-fit:contain}
    .figure-photo{position:absolute;inset:8px 8px 4px;width:calc(100% - 16px);height:calc(100% - 12px);object-fit:contain;object-position:center;filter:drop-shadow(1px 4px 5px #0006);z-index:2}
    .figure-fallback{position:absolute;bottom:8px;left:77px;place-items:center;width:63px;height:76px;font-size:57px;z-index:2;filter:drop-shadow(2px 5px 3px #0003)}
    .stage + .detail{min-width:0;flex:1}
    @media(max-width:440px){.flex{flex-direction:column;align-items:stretch}.stage{align-self:center}.title{font-size:19px}}.art{width:122px;height:122px;border-radius:16px;flex-shrink:0;object-fit:contain;object-position:center;background:${color}40}
    .placeholder{display:grid;place-items:center;font-size:50px}.eyebrow{opacity:.7;font-size:12px}.title{font-size:21px;font-weight:700;line-height:1.3;margin-top:6px;overflow-wrap:anywhere}
    .state{margin-top:10px;font-size:13px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:${playing?'#36ad68':'#888'};margin-right:5px}
    .bar{height:8px;background:var(--divider-color,#ddd);border-radius:12px;overflow:hidden;margin-top:20px}.fill{height:100%;background:${color};width:${progress.toFixed(2)}%}
    .times{display:flex;justify-content:space-between;opacity:.72;font-size:12px;margin-top:6px}.foot{font-size:12px;opacity:.75;margin-top:12px}
    @media(max-width:350px){.art{width:85px;height:85px}.title{font-size:17px}}
    .panel{margin-top:18px;padding-top:14px;border-top:1px solid var(--divider-color,#ddd)}
    .panel-title{font-weight:700;margin-bottom:15px}.setting{padding:10px 0 16px}
    .setting + .setting{border-top:1px solid var(--divider-color,#ddd)}
    .setting-head{display:flex;justify-content:space-between;gap:12px;font-size:14px;margin-bottom:12px}
    .setting input{width:100%;accent-color:var(--primary-color,#8f77c7);cursor:pointer}
    .setting input:disabled{opacity:.45;cursor:not-allowed}.ticks{display:flex;justify-content:space-between;font-size:11px;opacity:.7;margin-top:4px}
    .player .panel,.player .status-foot{display:none}
    .settings .flex,.settings .bar,.settings .times,.settings .duration-foot{display:none}
    .settings .panel{margin-top:0;padding-top:0;border-top:0}
    </style><ha-card class="${mode}"><div class="flex">${artBlock}
    <div class="detail"><div class="eyebrow">${safe(this.config.name || e?.attributes?.friendly_name || 'TeddyCloud')}</div><div class="title">${safe(title)}</div>
    <div class="state"><i class="dot"></i>${attr.figure_present === false ? 'Figur abgenommen' : playing?'Wiedergabe gemeldet':'Keine Wiedergabe gemeldet'}</div><div class="state">${chargerText}</div></div></div>
    ${dur ? `<div class="bar"><div class="fill"></div></div><div class="times"><span>${elapsed===null?'–':this.fmt(Math.min(elapsed,dur))}</span><span>${this.fmt(dur)}</span></div><div class="foot duration-foot">⚠︎ Laufzeitfortschritt geschätzt ab MQTT-Ereignis, kein echter Abspielpositionswert</div>` : `<div class="foot duration-foot">Laufzeit unbekannt – kann im Figurenkatalog ergänzt werden.</div>`}
    <div class="panel"><div class="panel-title">⚙️ Toniebox-Einstellungen</div>${controls}</div>
    <div class="foot status-foot">Aktuelle Lautstärke: ${Number.isInteger(Number(attr.volume_level_raw)) && attr.volume_level_raw !== null && attr.volume_level_raw !== undefined && String(attr.volume_level_raw).trim() !== '' && Number(attr.volume_level_raw)>=0 && Number(attr.volume_level_raw)<=16 ? Math.round(Number(attr.volume_level_raw)*100/16)+' %' : 'unbekannt'} · ${attr.charger === 'ON' || attr.charger === '1' ? 'Auf Ladestation' : 'Toniebox'}</div>
    </ha-card>`;
  }
}

/* Visual editor: includes unavailable entities so the box need not be running. */
class TeddyCloudHomeAssistantCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
  }
  setConfig(config) {
    this._config = {...config};
    this.render();
  }
  set hass(value) {
    this._hass = value;
    this.render();
  }
  render() {
    if (!this.shadowRoot || !this._config) return;
    const escape = value => String(value ?? '').replace(/[&<>"']/g,
      char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const entity = this._config.entity || '';
    const entities = Object.entries(this._hass?.states || {})
      .filter(([id]) => id.startsWith('media_player.'))
      .sort(([a], [b]) => a.localeCompare(b, 'de'));
    const choices = entities.map(([id, state]) => `<option value="${escape(id)}" ${entity===id?'selected':''}>
      ${escape(state.attributes?.friendly_name || id)} (${escape(id)})${state.state === 'unavailable' ? ' – Nicht verfügbar' : ''}
    </option>`).join('');
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;color:var(--primary-text-color)}
      .field{display:block;margin:12px 0}
      label{display:block;margin-bottom:6px;font-weight:500}
      select,input{box-sizing:border-box;width:100%;padding:10px;border:1px solid var(--divider-color,#777);
        border-radius:8px;background:var(--card-background-color,#222);color:var(--primary-text-color)}
      .help{font-size:12px;color:var(--secondary-text-color);margin-top:6px}
    </style>
    <div class="field"><label for="entity">Toniebox auswählen</label>
      <select id="entity"><option value="">– Toniebox auswählen –</option>${choices}</select>
      <div class="help">Die Toniebox kann ausgeschaltet sein. Falls sie nicht in der Liste steht,
      die Media-Player-Entitäts-ID unten manuell eingeben.</div>
    </div>
    <div class="field"><label for="manual">Media-Player-Entitäts-ID (optional)</label>
      <input id="manual" placeholder="media_player.meine_toniebox_now_playing" value="${escape(entity)}"></div>
    <div class="field"><label for="mode">Kartenansicht</label><select id="mode"><option value="all" ${(!this._config.mode || this._config.mode==='all')?'selected':''}>Alles zusammen</option><option value="player" ${this._config.mode==='player'?'selected':''}>Nur Toniebox und Titel</option><option value="settings" ${this._config.mode==='settings'?'selected':''}>Nur Einstellungen</option></select></div>
    <div class="field"><label for="name">Anzeigename (optional)</label>
      <input id="name" placeholder="Kinderzimmer" value="${escape(this._config.name || '')}"></div>
    <div class="field"><label for="color">Boxfarbe (Hex)</label>
      <input id="color" placeholder="#c991c5" value="${escape(this._config.color || '#c991c5')}"></div>
    <div class="field"><label><input id="composition" type="checkbox" style="width:auto"
      ${this._config.composition!==false?'checked':''}> Toniebox mit Figur anzeigen</label></div>`;
    this.shadowRoot.getElementById('mode').addEventListener('change', e => this.change('mode',e.target.value));
    this.shadowRoot.getElementById('entity').addEventListener('change', e => {
      this.change('entity',e.target.value);
    });
    this.shadowRoot.getElementById('manual').addEventListener('change', e => {
      this.change('entity',e.target.value.trim());
    });
    for (const field of ['name','color']) {
      this.shadowRoot.getElementById(field).addEventListener('change',e => this.change(field,e.target.value));
    }
    this.shadowRoot.getElementById('composition').addEventListener('change',
      e => this.change('composition',e.target.checked));
  }
  change(field,value) {
    this._config = {...this._config,[field]:value};
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail:{config:this._config}, bubbles:true, composed:true
    }));
    this.render();
  }
}
if (!customElements.get('teddycloud-homeassistant-card-editor')) {
  customElements.define('teddycloud-homeassistant-card-editor',TeddyCloudHomeAssistantCardEditor);
}

customElements.define('teddycloud-homeassistant-card', TeddyCloudNowPlayingCard);
window.customCards = window.customCards || [];
window.customCards.push({type:'teddycloud-homeassistant-card',name:'TeddyCloud Home Assistant',description:'Toniebox, Tonie-Figur, Lautstärke-Limits und LED-Helligkeit', preview:true});

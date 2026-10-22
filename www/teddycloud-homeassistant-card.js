/* TeddyCloud Home Assistant — custom Lovelace card (no build tooling). */
class TeddyCloudNowPlayingCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error('entity: media_player.x is required');
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
    this._timer = setInterval(() => this.render(), 1000);
  }
  disconnectedCallback() { clearInterval(this._timer); }
  getCardSize() { return 4; }
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
    const title = attr.media_title || 'Noch keine Titelinformationen';
    const color = /^#[0-9a-f]{6}$/i.test(this.config.color || attr.box_color || '') ? (this.config.color || attr.box_color) : '#8f77c7';
    const url = this.config.figure_image || attr.cover_url || attr.entity_picture || attr.fallback_cover || this.config.fallback_cover || '';
    // Optionally use an actual Toniebox photo, otherwise a themed stylized box.
    const boxImage = this.config.box_image || '';
    const composition = this.config.composition !== false;
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
      ${safeURL ? `<img class="figure-photo" src="${safeURL}" alt="Erkanntes Tonie-Bild" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">` : ''}
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
    .figure-photo{position:absolute;bottom:0;left:52px;width:112px;height:131px;object-fit:contain;filter:drop-shadow(1px 4px 5px #0006);z-index:2}
    .figure-fallback{position:absolute;bottom:8px;left:77px;place-items:center;width:63px;height:76px;font-size:57px;z-index:2;filter:drop-shadow(2px 5px 3px #0003)}
    .stage + .detail{min-width:0;flex:1}
    @media(max-width:440px){.flex{flex-direction:column;align-items:stretch}.stage{align-self:center}.title{font-size:19px}}.art{width:122px;height:122px;border-radius:16px;flex-shrink:0;object-fit:cover;background:${color}40}
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
    </style><ha-card><div class="flex">${artBlock}
    <div class="detail"><div class="eyebrow">${safe(this.config.name || e?.attributes?.friendly_name || 'TeddyCloud')}</div><div class="title">${safe(title)}</div>
    <div class="state"><i class="dot"></i>${playing?'Wiedergabe gemeldet':'Keine Wiedergabe gemeldet'}</div></div></div>
    ${dur ? `<div class="bar"><div class="fill"></div></div><div class="times"><span>${elapsed===null?'–':this.fmt(Math.min(elapsed,dur))}</span><span>${this.fmt(dur)}</span></div><div class="foot">⚠︎ Laufzeitfortschritt geschätzt ab MQTT-Ereignis, kein echter Abspielpositionswert</div>` : `<div class="foot">Laufzeit unbekannt – kann im Figurenkatalog ergänzt werden.</div>`}
    <div class="panel"><div class="panel-title">⚙️ Toniebox-Einstellungen</div>${controls}</div>
    <div class="foot">Aktuelle Lautstärke: ${safe(attr.volume_level_raw ?? 'unbekannt')} / 16 · ${attr.charger === 'ON' || attr.charger === '1' ? 'Auf Ladestation' : 'Toniebox'}</div>
    </ha-card>`;
  }
}
customElements.define('teddycloud-homeassistant-card', TeddyCloudNowPlayingCard);
window.customCards = window.customCards || [];
window.customCards.push({type:'teddycloud-homeassistant-card',name:'TeddyCloud Home Assistant',description:'TeddyCloud-MQTT-Titel, Cover und geschätzter Fortschritt'});

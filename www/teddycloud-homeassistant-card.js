/* Dashboard building blocks. Older card configurations keep their original layout. */
const TEDDY_SECTIONS = [
  ['artwork', '🧸 Tonie-Bild oder Toniebox'],
  ['title', '🎵 Titel und Boxname'],
  ['playback', '▶️ Wiedergabestatus'],
  ['charger', '🔌 Ladestation'],
  ['progress', '⏱️ Laufzeit / Fortschritt'],
  ['volume', '🔊 Aktuelle Lautstärke'],
  ['speaker', '🔊 Lautsprecher-Limit'],
  ['headphone', '🎧 Kopfhörer-Limit'],
  ['led', '💡 LED-Helligkeit'],
  ['ears', '👂 Ohrtasten-Ereignisse']
];
const TEDDY_SECTION_IDS = TEDDY_SECTIONS.map(([id]) => id);
const TEDDY_DEFAULT_SECTIONS = [...TEDDY_SECTION_IDS];
const TEDDY_MODE_SECTIONS = {
  compact: ['artwork', 'title', 'playback', 'volume'],
  artwork: ['artwork', 'title', 'progress'],
  status: ['title', 'playback', 'charger', 'volume', 'ears'],
  tiles: ['artwork', 'title', 'playback', 'charger', 'volume', 'ears']
};
function teddySelectedSections(config) {
  if (!Array.isArray(config?.sections)) return [...TEDDY_DEFAULT_SECTIONS];
  return [...new Set(config.sections.filter(id => TEDDY_SECTION_IDS.includes(id)))];
}
/* TeddyCloud Home Assistant Integration — custom Lovelace card (no build tooling). */
class TeddyCloudNowPlayingCard extends HTMLElement {
  setConfig(config) {
    // Allow editing and saving the card while the Toniebox is offline.
    this.config = config;
    if (!this.shadowRoot) this.attachShadow({mode:'open'});
    if (!this._controlListenerInstalled) {
      this._controlListenerInstalled = true;
      this.shadowRoot.addEventListener('change', event => {
        const el = event.target;
        if (!el.matches('input[data-control]') || !this._hass) return;
        const entityId = el.dataset.entity;
        const value = Number(el.value);
        if (!entityId || !Number.isFinite(value)) return;
        this._hass.callService('number', 'set_value', {entity_id: entityId, value})
          .catch(err => { console.error('TeddyCloud Home Assistant Integration: Einstellung fehlgeschlagen', err); this.render(); });
      });
    }
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
      (hass.states[id].attributes?.content_audio_id !== undefined || hass.states[id].attributes?.box_color !== undefined)
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
    const artworkMode = ['auto','figure','cover'].includes(this.config.artwork_mode) ? this.config.artwork_mode : 'auto';
    // Online catalog images can be covers, not cut-out figurines. In auto,
    // only an explicitly supplied figure image is known to be intended as a figurine.
    const showFigure = artworkMode === 'figure' || (artworkMode === 'auto' && !!this.config.figure_image);
    const mode = ['all', 'player', 'settings', 'compact', 'artwork', 'status', 'tiles', 'custom'].includes(this.config.mode) ? this.config.mode : 'all';
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
    const showCover = Boolean(url) && (artworkMode === 'cover' || !showFigure);
    const controlRows = [
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
    });
    const controls = controlRows.join('');
    const artBlock = showCover ? `<img class="art cover-art" src="${safeURL}" alt="Tonie-Cover" loading="eager">` : composition ? `<div class="stage" aria-label="Toniebox mit Tonie-Figur">
      ${safeBoxURL ? `<img class="box-photo" src="${safeBoxURL}" alt="Toniebox" loading="lazy">` : `<div class="toy-box" style="--box-color:${color}"><div class="ear left"></div><div class="ear right"></div><div class="speaker"></div></div>`}
      ${safeURL ? `<img class="figure-photo" src="${safeURL}" alt="Erkanntes Tonie-Bild" loading="eager" onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">` : ''}
      <div class="figure-fallback" style="display:${safeURL?'none':'grid'}">🧸</div>
    </div>` : (safeURL ? `<img class="art" src="${safeURL}" alt="Tonie-Bild">` : `<div class="art placeholder">🧸</div>`);

    // Additional presets and the configurable dashboard builder. Legacy
    // all/player/settings are intentionally left untouched for existing cards.
    if (['compact', 'artwork', 'status', 'tiles', 'custom'].includes(mode)) {
      const volumeRaw = attr.volume_level_raw;
      const volumeNumber = Number(volumeRaw);
      const volumeText = volumeRaw !== null && volumeRaw !== undefined &&
        String(volumeRaw).trim() !== '' && Number.isInteger(volumeNumber) &&
        volumeNumber >= 0 && volumeNumber <= 16
        ? Math.round(volumeNumber * 100 / 16) + ' %' : 'Unbekannt';
      const boxName = String(e?.attributes?.friendly_name || '').replace(/ Now Playing$/, '');
      const resolveEar = (suffix) => {
        const match = Object.entries(this._hass?.states || {}).find(([id, state]) =>
          id.startsWith('sensor.') && state.attributes?.friendly_name === boxName + ' ' + suffix);
        return match?.[1] || null;
      };
      const earRow = (suffix, label) => {
        const state = resolveEar(suffix);
        const count = state?.attributes?.press_count;
        const labelText = {'pressed':'Einfach','double-pressed':'Doppelt','triple-pressed':'Dreifach'}[state?.state] || 'Noch kein Tastendruck';
        return '<div class="ear-row"><span>' + safe(label) + '</span><span>' +
          safe(labelText) + (Number.isInteger(count) ? ' · ' + safe(count) + '×' : '') + '</span></div>';
      };
      const smallArt = safeURL
        ? '<img class="small-art" src="' + safeURL + '" alt="Tonie-Bild" loading="lazy">'
        : '<div class="small-art fallback-art">🧸</div>';
      const titleMarkup = '<div class="board-name">' + safe(this.config.name || e?.attributes?.friendly_name || 'Toniebox') +
        '</div><div class="board-track">' + safe(title) + '</div>';
      const playText = attr.figure_present === false ? 'Figur abgenommen' :
        playing ? 'Wiedergabe gemeldet' : 'Keine Wiedergabe gemeldet';
      const progressMarkup = dur
        ? '<div class="board-bar"><div class="board-fill" style="width:' + progress.toFixed(2) +
          '%"></div></div><div class="board-times"><span>' + (elapsed===null?'–':this.fmt(Math.min(elapsed,dur))) +
          '</span><span>' + this.fmt(dur) + '</span></div><div class="board-note">Fortschritt geschätzt</div>'
        : '<div class="board-note">Laufzeit unbekannt</div>';
      const modules = {
        artwork: mode === 'compact' ? smallArt : '<div class="board-artwork">' + artBlock + '</div>',
        title: titleMarkup,
        playback: '<div class="board-value"><span class="board-dot"></span>' + safe(playText) + '</div>',
        charger: '<div class="board-value">' + safe(chargerText) + '</div>',
        progress: progressMarkup,
        volume: '<div class="board-value strong">🔊 ' + safe(volumeText) + '</div>',
        speaker: controlRows[0],
        headphone: controlRows[1],
        led: controlRows[2],
        ears: '<div class="ear-list">' +
          earRow('Großes Ohr (lauter)', 'Großes Ohr') +
          earRow('Kleines Ohr (leiser)', 'Kleines Ohr') + '</div>'
      };
      const selected = mode === 'custom' ? teddySelectedSections(this.config) :
        TEDDY_MODE_SECTIONS[mode];
      const layout = mode === 'compact' ? 'compact' :
        (mode === 'tiles' || mode === 'status' || (mode === 'custom' && this.config.layout === 'grid'))
          ? 'grid' : 'stack';
      const cols = mode === 'custom' ? Math.min(3, Math.max(1, parseInt(this.config.columns, 10) || 2)) : 2;
      const items = selected.map(id => {
        const label = TEDDY_SECTIONS.find(([name]) => name === id)?.[1] || id;
        return '<section class="board-section board-' + id + '"><div class="section-label">' +
          safe(label) + '</div>' + modules[id] + '</section>';
      }).join('');
      this.shadowRoot.innerHTML = `<style>
        :host{display:block}
        ha-card{padding:16px;border-radius:18px;overflow:hidden;background:linear-gradient(135deg,${color}20,transparent 73%),var(--ha-card-background,var(--card-background-color,#fff))}
        .board{display:grid;gap:12px;min-width:0}
        .board.grid{grid-template-columns:repeat(var(--board-cols),minmax(0,1fr))}
        .board.compact{display:flex;align-items:center;flex-wrap:wrap;gap:9px}
        .board-section{min-width:0;padding:13px;border-radius:13px;border:1px solid var(--divider-color,#ddd);background:color-mix(in srgb,var(--card-background-color,#fff),${color} 5%)}
        .board.compact .board-section{padding:0;border:0;background:none}
        .board.compact .board-artwork{width:72px}
        .board.compact .board-title{flex:1 1 120px}
        .board.compact .section-label{display:none}
        .board.compact .board-track{font-size:16px}
        .board.compact .board-playback,.board.compact .board-volume{font-size:12px}
        .section-label{font-size:11px;opacity:.63;margin-bottom:7px}
        .board-name{font-size:12px;opacity:.72;margin-bottom:4px;overflow-wrap:anywhere}
        .board-track{font-size:19px;font-weight:700;line-height:1.3;overflow-wrap:anywhere}
        .board-value{font-size:14px;line-height:1.5;overflow-wrap:anywhere}
        .board-value.strong{font-size:20px;font-weight:650}
        .board-dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:${playing?'#36ad68':'#999'};margin-right:8px}
        .board-bar{height:8px;background:var(--divider-color,#ddd);border-radius:9px;overflow:hidden;margin-top:6px}
        .board-fill{height:100%;background:${color}}
        .board-times,.ear-row{display:flex;justify-content:space-between;gap:12px}
        .board-times{font-size:12px;margin-top:6px;opacity:.8}
        .board-note{font-size:11px;opacity:.7;margin-top:6px}
        .ear-list{display:grid;gap:9px}.ear-row{font-size:12px;flex-wrap:wrap}
        .ear-row span:last-child{font-weight:600}
        .small-art{display:block;width:64px;height:64px;object-fit:contain;border-radius:12px;background:${color}23}
        .fallback-art{display:grid;place-items:center;font-size:32px}
        .board-artwork{display:flex;justify-content:center;align-items:center}
        .board-artwork .art{width:min(100%,205px);height:205px;object-fit:contain;border-radius:14px}
        .board-artwork .placeholder{display:grid;place-items:center;font-size:52px;background:${color}25}
        .stage{position:relative;width:205px;height:210px;overflow:hidden;border-radius:16px;flex-shrink:0;background:radial-gradient(circle at 45% 37%,#ffffff15,transparent 70%)}
        .toy-box{position:absolute;left:18px;top:35px;width:170px;height:156px;border-radius:19px 24px 10px 12px;background:var(--box-color);box-shadow:inset -14px -6px 23px #0003,inset 12px 11px 20px #fff3,9px 10px 14px #0002;transform:skewY(-2deg)}
        .toy-box::before{content:'';position:absolute;left:13px;top:-10px;width:144px;height:30px;border-radius:70% 65% 35% 35%;background:color-mix(in srgb,var(--box-color),white 35%);transform:skewY(2deg)}
        .ear{position:absolute;top:-24px;width:26px;height:31px;background:#929294;clip-path:polygon(50% 0,100% 100%,0 100%);z-index:1}.ear.left{left:39px}.ear.right{right:34px}
        .speaker{position:absolute;left:28px;top:49px;width:111px;height:80px;opacity:.6;background-image:radial-gradient(#18181a 2.4px,transparent 2.5px);background-size:12px 12px;clip-path:ellipse(50% 49%)}
        .box-photo{position:absolute;inset:4px 0 0;width:100%;height:91%;object-fit:contain}
        .figure-photo{position:absolute;inset:8px 8px 4px;width:calc(100% - 16px);height:calc(100% - 12px);object-fit:contain;z-index:2}
        .figure-fallback{position:absolute;bottom:8px;left:77px;place-items:center;width:63px;height:76px;font-size:57px;z-index:2}
        .setting{padding:2px 0 4px}.setting-head{display:flex;justify-content:space-between;gap:7px;font-size:12px;margin-bottom:8px}
        .setting input{width:100%;accent-color:${color};cursor:pointer}
        .setting input:disabled{opacity:.45;cursor:not-allowed}
        .ticks{display:flex;justify-content:space-between;font-size:10px;opacity:.7;margin-top:4px}
        @media(max-width:640px){.board.grid{grid-template-columns:1fr}}
        @media(max-width:370px){ha-card{padding:9px}.board-section{padding:9px}.board-track{font-size:16px}}
      </style><ha-card><div class="board ${layout}" style="--board-cols:${cols}">${items ||
        '<div class="board-note">Keine Bausteine ausgewählt – im Karteneditor auswählen.</div>'}</div></ha-card>`;
      return;
    }
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
    .cover-art{width:205px;height:205px;object-fit:contain;object-position:center;background:transparent}
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
    <div class="detail"><div class="eyebrow">${safe(this.config.name || e?.attributes?.friendly_name || 'TeddyCloud Home Assistant Integration')}</div><div class="title">${safe(title)}</div>
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
      .section-editor{display:grid;gap:6px}.section-row{display:flex;align-items:center;gap:7px;padding:6px 4px;border:1px solid var(--divider-color,#777);border-radius:8px}
      .section-row label{display:flex;align-items:center;gap:7px;flex:1;min-width:0;margin:0;font-weight:400;font-size:13px}
      .section-row input{width:auto;flex-shrink:0}.section-row button{border:1px solid var(--divider-color,#777);border-radius:6px;padding:5px 8px;background:transparent;color:inherit;cursor:pointer}
      .section-row button:disabled{opacity:.3;cursor:default}
    </style>
    <div class="field"><label for="entity">Toniebox auswählen</label>
      <select id="entity"><option value="">– Toniebox auswählen –</option>${choices}</select>
      <div class="help">Die Toniebox kann ausgeschaltet sein. Falls sie nicht in der Liste steht,
      die Media-Player-Entitäts-ID unten manuell eingeben.</div>
    </div>
    <div class="field"><label for="manual">Media-Player-Entitäts-ID (optional)</label>
      <input id="manual" placeholder="media_player.meine_toniebox_now_playing" value="${escape(entity)}"></div>
    <div class="field"><label for="artwork_mode">Bilddarstellung</label><select id="artwork_mode"><option value="auto" ${(!this._config.artwork_mode || this._config.artwork_mode==='auto')?'selected':''}>Automatisch (Katalogbild als Cover)</option><option value="figure" ${this._config.artwork_mode==='figure'?'selected':''}>Figur auf Toniebox</option><option value="cover" ${this._config.artwork_mode==='cover'?'selected':''}>Nur Coverbild</option></select></div>
    <div class="field"><label for="mode">Kartenansicht</label><select id="mode"><option value="all" ${(!this._config.mode || this._config.mode==='all')?'selected':''}>Alles zusammen</option><option value="player" ${this._config.mode==='player'?'selected':''}>Nur Toniebox und Titel</option><option value="settings" ${this._config.mode==='settings'?'selected':''}>Nur Einstellungen</option><option value="compact" ${this._config.mode==='compact'?'selected':''}>Kompakt (schmale Leiste)</option><option value="artwork" ${this._config.mode==='artwork'?'selected':''}>Großes Tonie-Bild</option><option value="status" ${this._config.mode==='status'?'selected':''}>Status-Kacheln</option><option value="tiles" ${this._config.mode==='tiles'?'selected':''}>Dashboard-Kacheln</option><option value="custom" ${this._config.mode==='custom'?'selected':''}>Eigene Zusammenstellung</option></select></div>
    ${this._config.mode === 'custom' ? `
      <div class="field"><label for="layout">Anordnung der Bausteine</label>
        <select id="layout"><option value="stack" ${this._config.layout!=='grid'?'selected':''}>Untereinander</option><option value="grid" ${this._config.layout==='grid'?'selected':''}>Als Kacheln</option></select>
      </div>
      ${this._config.layout === 'grid' ? `<div class="field"><label for="columns">Kachelspalten</label><select id="columns">
        <option value="1" ${Number(this._config.columns)===1?'selected':''}>1 Spalte</option>
        <option value="2" ${(!this._config.columns || Number(this._config.columns)===2)?'selected':''}>2 Spalten</option>
        <option value="3" ${Number(this._config.columns)===3?'selected':''}>3 Spalten</option>
      </select></div>` : ''}
      <div class="field"><label>Bausteine auswählen und sortieren</label>
        <div class="section-editor">
          ${this.sectionEditorRows(escape)}
        </div>
        <div class="help">Bausteine an- oder abwählen und mit ↑ ↓ in der gewünschten Reihenfolge anordnen.</div>
      </div>
    ` : ''}
    <div class="field"><label for="name">Anzeigename (optional)</label>
      <input id="name" placeholder="Kinderzimmer" value="${escape(this._config.name || '')}"></div>
    <div class="field"><label for="color">Boxfarbe (Hex)</label>
      <input id="color" placeholder="#c991c5" value="${escape(this._config.color || '#c991c5')}"></div>
    <div class="field"><label><input id="composition" type="checkbox" style="width:auto"
      ${this._config.composition!==false?'checked':''}> Toniebox mit Figur anzeigen</label></div>`;
    this.shadowRoot.getElementById('artwork_mode').addEventListener('change', e => this.change('artwork_mode',e.target.value));
    this.shadowRoot.getElementById('mode').addEventListener('change', e => this.change('mode',e.target.value));
    this.shadowRoot.getElementById('layout')?.addEventListener('change', e => this.change('layout',e.target.value));
    this.shadowRoot.getElementById('columns')?.addEventListener('change', e => this.change('columns',Number(e.target.value)));
    this.shadowRoot.querySelectorAll('input[data-section]').forEach(input => input.addEventListener('change', e =>
      this.changeSections(e.target.dataset.section, e.target.checked)));
    this.shadowRoot.querySelectorAll('button[data-move]').forEach(button => button.addEventListener('click', e =>
      this.moveSection(e.currentTarget.dataset.move, Number(e.currentTarget.dataset.step))));
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
  sectionEditorRows(escape) {
    const selected = teddySelectedSections(this._config);
    const ordered = [...selected, ...TEDDY_SECTION_IDS.filter(id => !selected.includes(id))];
    return ordered.map(id => {
      const label = TEDDY_SECTIONS.find(([key]) => key === id)?.[1] || id;
      const index = selected.indexOf(id);
      return `<div class="section-row"><label><input type="checkbox" data-section="${escape(id)}" ${index>=0?'checked':''}>
        ${escape(label)}</label>
        <button type="button" data-move="${escape(id)}" data-step="-1" title="Nach oben" ${index<1?'disabled':''}>↑</button>
        <button type="button" data-move="${escape(id)}" data-step="1" title="Nach unten" ${index<0 || index>=selected.length-1?'disabled':''}>↓</button></div>`;
    }).join('');
  }
  changeSections(id, enabled) {
    if (!TEDDY_SECTION_IDS.includes(id)) return;
    let sections = teddySelectedSections(this._config).filter(key => key !== id);
    if (enabled) sections.push(id);
    this.change('sections',sections);
  }
  moveSection(id, step) {
    const sections = teddySelectedSections(this._config);
    const from = sections.indexOf(id), to = from + step;
    if (from < 0 || to < 0 || to >= sections.length) return;
    [sections[from], sections[to]] = [sections[to], sections[from]];
    this.change('sections',sections);
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
window.customCards.push({type:'teddycloud-homeassistant-card',name:'TeddyCloud Home Assistant Integration',description:'Toniebox, Tonie-Figur, Lautstärke-Limits und LED-Helligkeit', preview:true});

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
    const players = Object.entries(hass?.states || {}).filter(([id]) => id.startsWith('media_player.'));
    const candidate = players.find(([id, state]) =>
      state.attributes?.box_color !== undefined ||
      state.attributes?.content_audio_id !== undefined ||
      /tonie|teddy/i.test(id + ' ' + (state.attributes?.friendly_name || '')));
    return {entity: candidate?.[0] || '', mode: 'all', composition: true};
  }
  getCardSize() {
    const mode = this.config?.mode || 'all';
    if (mode === 'compact') return 2;
    if (mode === 'artwork') return 5;
    if (mode === 'status') return 4;
    if (mode === 'tiles') return 6;
    if (mode === 'custom') {
      const n = teddySelectedSections(this.config).length;
      return Math.max(2, Math.min(12, Math.ceil(n / (this.config?.layout === 'grid' ? 2 : 1)) * 2));
    }
    return 8;
  }
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
        artwork: mode === 'compact' ? smallArt : '<div class="board-artwork-media">' + artBlock + '</div>',
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
        // User-defined width of every module in grid mode, clamped to the
        // current number of columns. Old cards without widths stay 1-column.
        const requestedWidth = this.config?.section_widths?.[id];
        const parsedWidth = Number(requestedWidth);
        const span = Number.isInteger(parsedWidth) && parsedWidth >= 1
          ? Math.min(cols, parsedWidth) : 1;
        const widthStyle = mode === 'custom' && layout === 'grid'
          ? ' style="--section-span:' + span + '"' : '';
        // An artwork heading used to push the image sideways because the
        // artwork container and section shared one CSS class.
        const labelHtml = id === 'artwork' ? '' :
          '<div class="section-label">' + safe(label) + '</div>';
        return '<section class="board-section board-' + id + '"' + widthStyle +
          '>' + labelHtml + modules[id] + '</section>';
      }).join('');
      this.shadowRoot.innerHTML = `<style>
        :host{display:block}
        ha-card{padding:16px;border-radius:18px;overflow:hidden;background:linear-gradient(135deg,${color}20,transparent 73%),var(--ha-card-background,var(--card-background-color,#fff))}
        .board{display:grid;gap:12px;min-width:0}
        .board.grid{grid-template-columns:repeat(var(--board-cols),minmax(0,1fr))}
        .board.grid .board-section{grid-column:span var(--section-span,1)}
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
        .board-artwork-media{display:flex;justify-content:center;align-items:center;min-width:0;overflow:hidden}
        .board-artwork-media .art{width:min(100%,205px);height:205px;object-fit:contain;border-radius:14px}
        .board-artwork-media .placeholder{display:grid;place-items:center;font-size:52px;background:${color}25}
        .stage{position:relative;width:205px;max-width:100%;height:210px;overflow:hidden;border-radius:16px;flex-shrink:1;background:radial-gradient(circle at 45% 37%,#ffffff15,transparent 70%)}
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
        @media(max-width:640px){.board.grid{grid-template-columns:1fr}.board.grid .board-section{grid-column:1/-1}}
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
/* Simple visual editor for people who don't want to edit YAML. */
class TeddyCloudHomeAssistantCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this._advancedOpen = false;
    this._fingerprint = null;
  }
  setConfig(config) {
    this._config = {...config};
    this.render();
  }
  _availableBoxes() {
    const all = Object.entries(this._hass?.states || {})
      .filter(([id]) => id.startsWith('media_player.'))
      .sort(([a], [b]) => a.localeCompare(b, 'de'));
    const matches = all.filter(([id, state]) =>
      /tonie|teddy/i.test(id + ' ' + (state.attributes?.friendly_name || '')) ||
      state.attributes?.box_color !== undefined ||
      state.attributes?.content_audio_id !== undefined);
    const boxes = matches.length ? matches : all;
    // An existing, customized entity must stay selectable even when offline.
    const selected = this._config?.entity;
    if (selected && !boxes.some(([id]) => id === selected)) {
      const old = all.find(([id]) => id === selected);
      if (old) boxes.unshift(old);
    }
    return boxes;
  }
  set hass(value) {
    this._hass = value;
    const boxes = this._availableBoxes();
    const fingerprint = boxes.map(([id, state]) =>
      id + ':' + (state.attributes?.friendly_name || '')).join('|');
    if (fingerprint === this._fingerprint) return;
    this._fingerprint = fingerprint;
    // Automatically choose the sole detected Toniebox for new cards. Don't
    // replace a user's explicit choice or a temporarily offline entity.
    const current = this._config?.entity;
    const oneToniebox = boxes.length === 1 && (
      /tonie|teddy/i.test(boxes[0][0] + ' ' + (boxes[0][1].attributes?.friendly_name || '')) ||
      boxes[0][1].attributes?.box_color !== undefined ||
      boxes[0][1].attributes?.content_audio_id !== undefined);
    if (this._config && oneToniebox &&
        (!current || (current === 'media_player.meine_toniebox_now_playing' &&
          !this._hass?.states?.[current]))) {
      if (current !== boxes[0][0]) {
        this._config = {...this._config, entity: boxes[0][0]};
        this._notify();
      }
    }
    this.render();
  }
  _notify() {
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail:{config:this._config}, bubbles:true, composed:true
    }));
  }
  render() {
    if (!this.shadowRoot || !this._config) return;
    const escape = value => String(value ?? '').replace(/[&<>"']/g,
      char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const mode = this._config.mode || 'all';
    const box = this._config.entity || '';
    const choices = this._availableBoxes();
    const options = choices.map(([id, state]) =>
      "<option value='" + escape(id) + "'" + (id === box ? " selected" : "") + ">" +
      escape(state.attributes?.friendly_name || id) + "</option>").join('');
    const presets = [
      ['all','🧸','Alles','Toniebox und Einstellungen'],
      ['player','🎵','Musik','Bild und Titel'],
      ['compact','▬','Kompakt','Schmale Leiste'],
      ['artwork','🖼️','Großes Bild','Tonie im Mittelpunkt'],
      ['tiles','▦','Kacheln','Übersichtliche Kacheln'],
      ['status','📊','Status','Alle wichtigen Infos'],
      ['settings','⚙️','Einstellungen','Lautstärkelimits und LED'],
      ['custom','🧩','Selbst gestalten','Eigene Bausteine wählen']
    ];
    const presetHtml = presets.map(([id, icon, name, description]) =>
      "<button type='button' class='preset" + (mode === id ? " selected" : "") +
      "' data-preset='" + escape(id) + "' aria-pressed='" + (mode === id) + "'>" +
      "<span class='preset-icon'>" + escape(icon) + "</span>" +
      "<span class='preset-body'><strong>" + escape(name) + "</strong>" +
      "<small>" + escape(description) + "</small></span>" +
      "<span class='preset-check'>" + (mode === id ? "✓" : "") + "</span></button>"
    ).join('');
    const custom = mode === 'custom';
    const layout = this._config.layout === 'stack' ? 'stack' : 'grid';
    const columns = Math.min(3, Math.max(1, Number(this._config.columns) || 2));
    const color = /^#[0-9a-f]{6}$/i.test(this._config.color || '') ?
      this._config.color : '#8f77c7';
    const selected = teddySelectedSections(this._config).length;
    const showDetails = this._advancedOpen ||
      Boolean(this.shadowRoot.querySelector?.('details')?.open);
    this.shadowRoot.innerHTML = [
      "<style>",
      ":host{display:block;color:var(--primary-text-color)}",
      ".step{margin:0 0 22px}.step h3{font-size:16px;font-weight:650;margin:0 0 5px}",
      ".help{font-size:12px;line-height:1.4;color:var(--secondary-text-color);margin:5px 0 10px}",
      "select,input[type=text],input[type=color]{box-sizing:border-box;width:100%;padding:10px;border:1px solid var(--divider-color,#777);border-radius:10px;background:var(--card-background-color,#222);color:var(--primary-text-color);font:inherit}",
      ".preset-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:12px}",
      ".preset{display:flex;text-align:left;align-items:center;gap:8px;min-width:0;min-height:70px;padding:10px;border:2px solid var(--divider-color,#777);border-radius:12px;background:var(--card-background-color,#222);color:inherit;cursor:pointer;font:inherit}",
      ".preset.selected{border-color:var(--primary-color,#03a9f4);background:color-mix(in srgb,var(--primary-color,#03a9f4) 12%,var(--card-background-color,#222))}",
      ".preset:focus-visible,.actions button:focus-visible{outline:2px solid var(--primary-color,#03a9f4);outline-offset:2px}",
      ".preset-icon{font-size:23px;flex:none}.preset-body{display:grid;gap:3px;flex:1;min-width:0}",
      ".preset-body strong{font-size:13px}.preset-body small{font-size:11px;color:var(--secondary-text-color);line-height:1.3}",
      ".preset-check{color:var(--primary-color,#03a9f4);font-weight:bold;font-size:18px;flex:none}",
      ".section-editor{display:grid;gap:7px;margin-top:10px}.section-row{display:flex;align-items:center;gap:5px;padding:7px;border:1px solid var(--divider-color,#777);border-radius:9px}",
      ".section-row label{display:flex;align-items:center;gap:8px;flex:1;min-width:0;font-size:13px;cursor:pointer}",
      ".section-row input{width:17px;height:17px;accent-color:var(--primary-color,#03a9f4);flex:none}",
      ".section-row button,.actions button{border:1px solid var(--divider-color,#777);border-radius:7px;padding:7px 10px;background:transparent;color:inherit;cursor:pointer;font:inherit}",
      ".section-row .width-choice{width:auto;max-width:120px;min-width:100px;padding:7px 5px;font-size:12px;flex-shrink:0}",
      ".section-width-label{font-size:11px;color:var(--secondary-text-color);white-space:nowrap}",
      ".section-row button:disabled{opacity:.35;cursor:default}",
      ".field{margin:12px 0}.field label{display:block;font-size:13px;font-weight:500;margin-bottom:5px}",
      ".custom-tools{display:grid;grid-template-columns:1fr 1fr;gap:10px}",
      "details{border-top:1px solid var(--divider-color,#777);padding:14px 0 4px}",
      "summary{font-weight:550;cursor:pointer;user-select:none}",
      ".version{opacity:.55;font-size:10px;margin-top:12px}",
      ".missing{font-size:12px;color:var(--warning-color,#d18b2f)}",
      "@media(max-width:380px){.preset-grid{grid-template-columns:1fr}.custom-tools{grid-template-columns:1fr}}",
      "</style>",
      "<section class='step'><h3>1. Deine Toniebox</h3>",
      "<div class='help'>Wähle die Toniebox aus. Mehr musst du dafür nicht einstellen.</div>",
      "<select id='entity' aria-label='Toniebox auswählen'><option value=''>– Toniebox auswählen –</option>",
      options,"</select>",
      choices.length === 0 ? "<div class='missing'>Keine Toniebox erkannt? Unten unter „Weitere Einstellungen“ kannst du die Entitäts-ID eingeben.</div>" : "",
      "</section>",
      "<section class='step'><h3>2. So soll deine Karte aussehen</h3>",
      "<div class='help'>Einfach eine Ansicht antippen – rechts siehst du sofort die Vorschau.</div>",
      "<div class='preset-grid' role='group' aria-label='Dashboard-Ansicht wählen'>",
      presetHtml,"</div></section>",
      custom ? [
        "<section class='step'><h3>3. Deine Bausteine</h3>",
        "<div class='help'>Wähle nur das aus, was du sehen möchtest. ",
        selected, " Bausteine aktiv. ",layout === 'grid' ?
          'Für jeden Baustein kannst du rechts die Breite einstellen.' :
          'Für eigene Breiten „Kacheln“ auswählen.',"</div>",
        "<div class='custom-tools'><div class='field'><label for='layout'>Anordnung</label>",
        "<select id='layout'><option value='grid'", layout === 'grid' ? " selected" : "",
        ">Kacheln</option><option value='stack'",layout === 'stack' ? " selected" : "",
        ">Untereinander</option></select></div>",
        layout === 'grid' ? [
          "<div class='field'><label for='columns'>Spalten</label><select id='columns'>",
          [1,2,3].map(n => "<option value='" + n + "'" +
            (columns === n ? " selected" : "") + ">" + n + "</option>").join(''),
          "</select></div>"
        ].join('') : "",
        "</div><div class='section-editor'>", this.sectionEditorRows(escape), "</div></section>"
      ].join('') : "",
      "<details id='advanced'",showDetails ? " open" : "","><summary>⚙️ Weitere Einstellungen (optional)</summary>",
      "<div class='field'><label for='name'>Eigener Anzeigename</label>",
      "<input type='text' id='name' placeholder='z. B. Kinderzimmer' value='",escape(this._config.name || ''),"'></div>",
      "<div class='field'><label for='color'>Toniebox-Farbe</label>",
      "<input type='color' id='color' value='",escape(color),"'></div>",
      "<div class='field'><label for='artwork_mode'>Bild anzeigen als</label>",
      "<select id='artwork_mode'>",
      [['auto','Automatisch'],['figure','Figur auf Toniebox'],['cover','Nur Coverbild']].map(([id,name]) =>
        "<option value='" + id + "'" + ((this._config.artwork_mode || 'auto') === id ? " selected" : "") + ">" +
        name + "</option>").join(''),
      "</select></div>",
      "<div class='field'><label><input type='checkbox' id='composition' ",
      this._config.composition !== false ? "checked" : "",
      "> Toniebox mit Figur anzeigen</label></div>",
      "<div class='field'><label for='manual'>Entitäts-ID manuell eingeben (nur bei Bedarf)</label>",
      "<input type='text' id='manual' placeholder='media_player.meine_toniebox' value='",escape(box),"'></div>",
      "</details>",
      "<div class='version'>TeddyCloud Karteneditor v0.3.5 · Auswahl wird automatisch in die Kartenvorschau übernommen</div>"
    ].join('');
    const element = id => this.shadowRoot.getElementById(id);
    element('entity').addEventListener('change', e => this.change('entity', e.target.value));
    this.shadowRoot.querySelectorAll('button[data-preset]').forEach(button =>
      button.addEventListener('click', e => this.choosePreset(e.currentTarget.dataset.preset)));
    element('layout')?.addEventListener('change', e => this.change('layout', e.target.value));
    element('columns')?.addEventListener('change', e => this.change('columns', Number(e.target.value)));
    this.shadowRoot.querySelectorAll('input[data-section]').forEach(input =>
      input.addEventListener('change', e => this.changeSections(e.target.dataset.section, e.target.checked)));
    this.shadowRoot.querySelectorAll('select[data-width]').forEach(input =>
      input.addEventListener('change', e => this.changeSectionWidth(e.target.dataset.width, Number(e.target.value))));
    this.shadowRoot.querySelectorAll('button[data-move]').forEach(button =>
      button.addEventListener('click', e => this.moveSection(e.currentTarget.dataset.move, Number(e.currentTarget.dataset.step))));
    for (const field of ['name','color','artwork_mode']) {
      element(field)?.addEventListener('change', e => this.change(field, e.target.value));
    }
    element('composition')?.addEventListener('change', e => this.change('composition', e.target.checked));
    element('manual')?.addEventListener('change', e => this.change('entity',e.target.value.trim()));
    element('advanced')?.addEventListener('toggle', e => {this._advancedOpen = e.target.open;});
  }
  choosePreset(mode) {
    if (!['all','player','compact','artwork','tiles','status','settings','custom'].includes(mode)) return;
    // New self-built cards start with a useful selection, not 10 busy boxes.
    const extra = mode === 'custom' && !Array.isArray(this._config.sections) ?
      {layout:'grid',columns:2,sections:['artwork','title','playback','charger','volume']} : {};
    this._config = {...this._config,mode,...extra};
    this._notify();
    this.render();
  }
  sectionEditorRows(escape) {
    const selected = teddySelectedSections(this._config);
    const ordered = [...selected, ...TEDDY_SECTION_IDS.filter(id => !selected.includes(id))];
    const grid = this._config.layout !== 'stack';
    const columns = Math.min(3, Math.max(1, Number(this._config.columns) || 2));
    return ordered.map(id => {
      const label = TEDDY_SECTIONS.find(([key]) => key === id)?.[1] || id;
      const index = selected.indexOf(id);
      // Each enabled block gets its own width control. A span is relative to
      // the whole card grid, not a fixed pixel width.
      const configured = Number(this._config.section_widths?.[id]);
      const current = Number.isInteger(configured) && configured > 0
        ? Math.min(columns, configured) : 1;
      const widthSelect = grid && index >= 0 ? (
        "<select class='width-choice' data-width='" + escape(id) +
        "' aria-label='" + escape(label) + " Breite'>" +
        Array.from({length:columns}, (_, i) => {
          const n = i + 1;
          const option = n === columns && n > 1 ? 'Volle Breite' :
            n + (n === 1 ? ' Spalte' : ' Spalten');
          return "<option value='" + n + "'" + (n === current ? ' selected' : '') +
            ">" + option + "</option>";
        }).join('') + "</select>"
      ) : '';
      return "<div class='section-row'><label><input type='checkbox' data-section='" +
        escape(id) + "'" + (index>=0 ? " checked" : "") + "> " + escape(label) +
        "</label>" + widthSelect +
        "<button type='button' data-move='" + escape(id) +
        "' data-step='-1' aria-label='" + escape(label) + " nach oben'" +
        (index<1 ? " disabled" : "") + ">↑</button><button type='button' data-move='" +
        escape(id) + "' data-step='1' aria-label='" + escape(label) + " nach unten'" +
        (index<0 || index>=selected.length-1 ? " disabled" : "") + ">↓</button></div>";
    }).join('');
  }
  changeSectionWidth(id, width) {
    if (!TEDDY_SECTION_IDS.includes(id) || !teddySelectedSections(this._config).includes(id)) return;
    const columns = Math.min(3, Math.max(1, Number(this._config.columns) || 2));
    if (!Number.isInteger(width) || width < 1 || width > columns) return;
    this.change('section_widths', {...this._config.section_widths, [id]:width});
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
  change(field, value) {
    this._config = {...this._config,[field]:value};
    this._notify();
    this.render();
  }
}

if (!customElements.get('teddycloud-homeassistant-card-editor')) {
  customElements.define('teddycloud-homeassistant-card-editor',TeddyCloudHomeAssistantCardEditor);
}

customElements.define('teddycloud-homeassistant-card', TeddyCloudNowPlayingCard);
window.customCards = window.customCards || [];
window.customCards.push({type:'teddycloud-homeassistant-card',name:'TeddyCloud Home Assistant Integration',description:'Toniebox, Tonie-Figur, Lautstärke-Limits und LED-Helligkeit', preview:true});


/* Separate Tonie library card. Editing happens here, not in dashboard edit mode. */
class TeddyCloudTonieLibraryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:'open'});
    this._entries = null;
    this._edit = null;
    this._saving = false;
    this._error = '';
    this._upload = null;
    this._query = '';
    this._connected = false;
    this._subscribePromise = null;
    this._listen();
  }
  static getStubConfig() { return {}; }
  static getConfigElement() {
    return document.createElement('teddycloud-tonie-library-editor');
  }
  getCardSize() { return 7; }
  setConfig(config) {
    this._config = {...config};
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
    this._subscribe();
  }
  connectedCallback() {
    this._connected = true;
    this._subscribe();
    this.render();
  }
  disconnectedCallback() {
    this._connected = false;
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
    // A subscription pending during removal is cleaned up when resolved.
  }
  _listen() {
    this.shadowRoot.addEventListener('click', event => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const action = button.dataset.action;
      const id = button.dataset.id || '';
      if (action === 'edit') this._openEdit(id);
      else if (action === 'add') this._openEdit('');
      else if (action === 'cancel') { this._edit = null; this._error = ''; this._upload = null; this.render(); }
      else if (action === 'save') this._save();
      else if (action === 'delete') { this._deleteId = id; this.render(); }
      else if (action === 'cancel-delete') { this._deleteId = null; this.render(); }
      else if (action === 'confirm-delete') this._delete(id);
    });
    this.shadowRoot.addEventListener('input', event => {
      if (event.target.id !== 'library-search') return;
      this._query = event.target.value.toLocaleLowerCase();
      this._applySearch();
    });
    this.shadowRoot.addEventListener('change', event => {
      if (event.target.id !== 'library-upload') return;
      const file = event.target.files?.[0];
      if (!file) { this._upload = null; return; }
      if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 2097152) {
        this._error = 'Bitte ein JPG-, PNG- oder WebP-Bild unter 2 MB auswählen.';
        this._upload = null;
        this.render();
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        this._upload = reader.result;
        const label = this.shadowRoot.getElementById('library-upload-label');
        if (label) label.textContent = 'Bild ausgewählt: ' + file.name;
      };
      reader.onerror = () => { this._error = 'Bild konnte nicht geladen werden'; this.render(); };
      reader.readAsDataURL(file);
    });
  }
  _subscribe() {
    if (!this._hass || this._subscribePromise || this._unsubscribe) return;
    const connection = this._hass.connection;
    // A single authenticated WebSocket subscription shares updates between
    // family members, even if they cannot edit the Home Assistant dashboard.
    this._subscribePromise = connection.subscribeMessage(
      data => {
        if (!Array.isArray(data?.entries)) return;
        this._entries = data.entries;
        if (!this._edit) this.render();
      },
      {type:'teddycloud_homeassistant/library/subscribe'}
    ).then(unsubscribe => {
      this._subscribePromise = null;
      if (this._connected) this._unsubscribe = unsubscribe;
      else unsubscribe();
    }).catch(error => {
      this._subscribePromise = null;
      this._error = 'Bibliothek nicht erreichbar. Ist die Integration aktualisiert und Home Assistant neu gestartet? ' +
        String(error?.message || error);
      this.render();
    });
  }
  _escape(value) {
    return String(value ?? '').replace(/[&<>"']/g,
      char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  }
  _safeImage(url) {
    if (typeof url !== 'string') return '';
    const value = url.trim();
    return value.startsWith('/local/') || /^https?:\/\/[^/\s]+/i.test(value) ? value : '';
  }
  _image(url, className='cover') {
    const safeURL = this._safeImage(url);
    return safeURL
      ? '<img class="' + className + '" src="' + this._escape(safeURL) + '" alt="Tonie-Bild" loading="lazy">'
      : '<div class="' + className + ' empty">🧸</div>';
  }
  _mins(seconds) {
    const number = Number(seconds);
    return Number.isFinite(number) && number > 0
      ? (number / 60).toLocaleString('de-DE',{maximumFractionDigits:1}) + ' Min.'
      : 'Laufzeit unbekannt';
  }
  _openEdit(id) {
    const found = (this._entries || []).find(item => item.audio_id === id);
    this._edit = {
      audio_id: found?.audio_id || '',
      title: found?.custom?.title ?? found?.title ?? '',
      image: found?.custom?.image ?? found?.image ?? '',
      duration_seconds: found?.custom?.duration_seconds ?? found?.duration_seconds ?? null,
    };
    this._upload = null;
    this._error = '';
    this._deleteId = null;
    this.render();
  }
  async _save() {
    if (this._saving || !this._hass) return;
    const get = id => this.shadowRoot.getElementById(id)?.value ?? '';
    const audioId = get('library-audio').trim();
    const duration = get('library-duration').trim();
    if (!/^[a-z0-9_-]{1,80}$/i.test(audioId)) {
      this._error = 'Bitte eine gültige Audio-ID eingeben.';
      this.render();
      return;
    }
    const minutes = duration ? Number(duration.replace(',','.')) : 0;
    const seconds = Math.round(minutes * 60);
    if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86400) {
      this._error = 'Bitte eine Laufzeit zwischen 0 und 1440 Minuten eingeben.';
      this.render();
      return;
    }
    this._saving = true;
    const data = {
      type:'teddycloud_homeassistant/library/save',
      audio_id:audioId,
      title:get('library-title').trim(),
      image:get('library-image').trim(),
      duration_seconds: seconds,
    };
    if (this._upload) data.image_data = this._upload;
    try {
      await this._hass.callWS(data);
      this._error = '';
      this._edit = null;
      this._upload = null;
    } catch (error) {
      this._error = String(error?.message || error);
    } finally {
      this._saving = false;
      this.render();
    }
  }
  async _delete(audioId) {
    if (!this._hass || this._saving) return;
    this._saving = true;
    try {
      await this._hass.callWS({
        type:'teddycloud_homeassistant/library/delete',audio_id:audioId
      });
      this._deleteId = null;
      this._error = '';
    } catch (error) {
      this._error = String(error?.message || error);
    } finally {
      this._saving = false;
      this.render();
    }
  }
  _applySearch() {
    const q = this._query;
    this.shadowRoot.querySelectorAll('[data-library-entry]').forEach(item => {
      item.hidden = !item.dataset.search.includes(q);
    });
  }
  render() {
    if (!this.shadowRoot || !this._config) return;
    const e = value => this._escape(value);
    const entries = this._entries || [];
    const view = this._edit ? (() => {
      const item = this._edit;
      const editing = Boolean(item.audio_id);
      const minutes = item.duration_seconds ? Math.round(Number(item.duration_seconds) / 6) / 10 : '';
      return '<section class="form-panel"><h3>' +
        (editing ? 'Tonie bearbeiten' : 'Tonie hinzufügen') +
        '</h3><div class="field"><label for="library-audio">Audio-ID</label><input id="library-audio" maxlength="80"' +
        (editing ? ' readonly' : '') + ' value="' + e(item.audio_id) +
        '" placeholder="Audio-ID des Tonies"></div>' +
        '<div class="field"><label for="library-title">Titel</label><input id="library-title" maxlength="200" value="' +
        e(item.title) + '" placeholder="Titel des Hörspiels"></div>' +
        '<div class="field"><label for="library-duration">Hörspiellänge in Minuten</label>' +
        '<input type="number" id="library-duration" min="0" max="1440" step="0.1" value="' +
        e(minutes) + '" placeholder="z. B. 45"></div>' +
        '<div class="field"><label for="library-image">Figurenbild (Bildadresse, optional)</label>' +
        '<input id="library-image" maxlength="2048" value="' + e(item.image) +
        '" placeholder="https://… oder /local/…"></div>' +
        '<div class="field"><label for="library-upload">Oder Bild direkt vom Gerät auswählen</label>' +
        '<input type="file" id="library-upload" accept="image/png,image/jpeg,image/webp">' +
        '<p class="hint" id="library-upload-label">JPG, PNG oder WebP · maximal 2 MB</p></div>' +
        '<div class="edit-actions"><button data-action="cancel" type="button">Abbrechen</button>' +
        '<button class="primary" data-action="save" type="button"' +
        (this._saving ? ' disabled' : '') + '>Änderungen speichern</button></div></section>';
    })() : (
      '<div class="toolbar"><input id="library-search" aria-label="Tonie suchen" placeholder="🔎 Tonies suchen …" value="' +
      e(this._query) + '"><button class="primary" type="button" data-action="add">+ Tonie hinzufügen</button></div>' +
      (!this._entries ? '<p class="hint">Bibliothek wird geladen …</p>' :
        !entries.length ? '<p class="empty-library">Noch keine Tonies gespeichert. Stelle eine Figur auf die Toniebox, damit sie automatisch hier erscheint.</p>' :
          '<div class="library-grid">' + entries.map(item => {
            const title = item.title || 'Unbekannter Tonie';
            const removed = this._deleteId === item.audio_id;
            return '<article class="tonie" data-library-entry data-search="' +
              e((title + ' ' + item.audio_id).toLocaleLowerCase()) + '">' +
              this._image(item.image) +
              '<div class="tonie-body"><strong>' + e(title) + '</strong>' +
              '<span class="duration">' + e(this._mins(item.duration_seconds)) + '</span>' +
              '<span class="id">Audio-ID: ' + e(item.audio_id) + '</span>' +
              (removed ?
                '<p class="warning">Tonie wirklich aus deiner Bibliothek löschen? Er wird beim erneuten Auflegen wieder hinzugefügt.</p>' +
                '<div class="actions"><button data-action="cancel-delete">Abbrechen</button>' +
                '<button class="danger" data-action="confirm-delete" data-id="' + e(item.audio_id) + '">Ja, löschen</button></div>' :
                '<div class="actions"><button data-action="edit" data-id="' + e(item.audio_id) +
                '">✏️ Bearbeiten</button><button data-action="delete" data-id="' +
                e(item.audio_id) + '">Löschen</button></div>') +
              '</div></article>';
          }).join('') + '</div>')
    );
    this.shadowRoot.innerHTML = [
      '<style>',
      ':host{display:block}',
      'ha-card{padding:18px;border-radius:18px}',
      '.header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:6px;flex-wrap:wrap}',
      'h2{font-size:20px;margin:0}h3{font-size:18px;margin:0 0 16px}',
      '.subtitle{font-size:12px;color:var(--secondary-text-color);margin:0 0 16px}',
      '.toolbar{display:flex;gap:9px;margin-bottom:16px;flex-wrap:wrap}',
      '.toolbar input{flex:1;min-width:130px}',
      '.library-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px}',
      '.tonie{min-width:0;border:1px solid var(--divider-color,#777);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}',
      '.tonie[hidden]{display:none}',
      '.cover{width:100%;height:165px;object-fit:contain;background:var(--secondary-background-color,#282828)}',
      '.cover.empty{display:grid;place-items:center;font-size:52px}',
      '.tonie-body{padding:12px;display:flex;flex-direction:column;gap:8px;min-width:0;flex:1}',
      '.tonie-body strong{font-size:14px;overflow-wrap:anywhere;line-height:1.3}',
      '.duration,.id,.hint{font-size:12px;color:var(--secondary-text-color)}',
      '.id{overflow-wrap:anywhere}',
      '.actions,.edit-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:auto}',
      'button{border:1px solid var(--divider-color,#777);border-radius:9px;padding:9px 12px;background:transparent;color:var(--primary-text-color);font:inherit;font-size:12px;cursor:pointer}',
      'button.primary{background:var(--primary-color,#03a9f4);color:var(--text-primary-color,#fff);border-color:transparent;font-weight:600}',
      'button.danger{border-color:var(--error-color,#e53935);color:var(--error-color,#e53935)}',
      'button:disabled{opacity:.5;cursor:not-allowed}',
      'input{box-sizing:border-box;border:1px solid var(--divider-color,#777);border-radius:9px;padding:10px;background:var(--card-background-color,#222);color:var(--primary-text-color);font:inherit;width:100%}',
      'input[readonly]{opacity:.65}',
      '.form-panel{max-width:560px}.field{margin:0 0 15px}',
      '.field label{display:block;margin-bottom:6px;font-size:13px;font-weight:600}',
      '.warning,.error{font-size:12px;color:var(--error-color,#e53935)}',
      '.empty-library{font-size:14px;opacity:.8;text-align:center;padding:26px 10px}',
      '.edit-actions{justify-content:flex-end;padding-top:12px}',
      '</style><ha-card>',
      '<header class="header"><h2>🧸 Meine Tonie-Bibliothek</h2>',
      '<span class="hint">' + entries.length + ' Tonies</span></header>',
      '<p class="subtitle">Deine Figuren – automatisch gemerkt und direkt hier bearbeitbar, auch ohne Administratorrechte.</p>',
      this._error ? '<p class="error" role="alert">' + e(this._error) + '</p>' : '',
      view, '</ha-card>'
    ].join('');
    if (!this._edit) this._applySearch();
  }
}
class TeddyCloudLibraryEditor extends HTMLElement {
  setConfig() {
    this.textContent = 'Die Tonie-Bibliothek wird direkt in der Dashboard-Karte verwaltet. Hier musst du nichts einstellen.';
    this.style.display = 'block';
    this.style.padding = '12px';
  }
  set hass(_hass) {}
}
if (!customElements.get('teddycloud-tonie-library-editor')) {
  customElements.define('teddycloud-tonie-library-editor', TeddyCloudLibraryEditor);
}
if (!customElements.get('teddycloud-tonie-library-card')) {
  customElements.define('teddycloud-tonie-library-card', TeddyCloudTonieLibraryCard);
}
window.customCards.push({
  type:'teddycloud-tonie-library-card',
  name:'TeddyCloud Tonie-Bibliothek',
  description:'Deine Tonie-Sammlung ansehen, bearbeiten, Bilder ändern und Tonies hinzufügen – direkt im Dashboard',
  preview:true
});

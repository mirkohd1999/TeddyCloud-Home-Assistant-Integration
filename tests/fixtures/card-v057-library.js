/* Legacy v0.5.7 library implementation (commit 637913e497f11478adc51d4dd4087688c27b7d7f).
 * Isolated unchanged library class to reproduce an already registered native player.
 * Minimal locale helpers replace the unrelated player/editor parts of that module. */
function teddyLanguage(hass) { return /^en/i.test(hass?.locale?.language || '') ? 'en' : 'de'; }
function teddyText(hass, key) { return key; }
let teddyPreviewOwner = null;

class TeddyCloudTonieLibraryCard extends HTMLElement {
  _t(key) { return teddyText(this._hass, key); }
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
    this._previewAudio = null;
    this._previewId = null;
    this._previewError = null;
    this._previewCatalogStatus = "loading";
    this._refreshingPreviews = false;
    this._listen();
  }
  static getStubConfig() { return {}; }
  static getConfigElement() {
    return document.createElement('teddycloud-tonie-library-editor');
  }
  getCardSize() { return 7; }
  get _isAdmin() { return this._hass?.user?.is_admin === true; }
  setConfig(config) {
    this._config = {...config};
    this.render();
  }
  set hass(hass) {
    const wasAdmin = this._isAdmin;
    const oldLanguage = teddyLanguage(this._hass);
    this._hass = hass;
    if (!this._isAdmin) { this._edit = null; this._upload = null; }
    this._subscribe();
    if (wasAdmin !== this._isAdmin || oldLanguage !== teddyLanguage(hass)) this.render();
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
    this._stopPreview(false);
    // A subscription pending during removal is cleaned up when resolved.
  }
  _listen() {
    this.shadowRoot.addEventListener('click', event => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const action = button.dataset.action;
      const id = button.dataset.id || '';
      if (action === 'refresh-previews') this._refreshPreviews();
      else if (action === 'preview') this._togglePreview(id);
      else if (action === 'preview-stop') this._stopPreview();
      else if (action === 'edit') this._openEdit(id);
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
        this._error = "Bitte ein JPG-, PNG- oder WebP-Bild unter 2 MB auswählen.";
        this._upload = null;
        this.render();
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        this._upload = reader.result;
        const label = this.shadowRoot.getElementById('library-upload-label');
        if (label) label.textContent = this._t("Bild ausgewählt: ") + file.name;
      };
      reader.onerror = () => { this._error = "Bild konnte nicht geladen werden"; this.render(); };
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
        this._previewCatalogStatus = data.preview_catalog_status || "unknown";
        if (!this._edit) this.render();
      },
      {type:'teddycloud_homeassistant/library/subscribe'}
    ).then(unsubscribe => {
      this._subscribePromise = null;
      if (this._connected) this._unsubscribe = unsubscribe;
      else unsubscribe();
    }).catch(error => {
      this._subscribePromise = null;
      this._error = this._t("Bibliothek nicht erreichbar. Ist die Integration aktualisiert und Home Assistant neu gestartet? ") +
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
      ? '<img class="' + className + '" src="' + this._escape(safeURL) + '" alt="' + this._t("Tonie-Bild") + '" loading="lazy">'
      : '<div class="' + className + ' empty">🧸</div>';
  }
  async _refreshPreviews() {
    if (!this._hass || this._refreshingPreviews) return;
    this._refreshingPreviews = true;
    this._error = '';
    this.render();
    try {
      const data = await this._hass.callWS({type:'teddycloud_homeassistant/library/refresh'});
      if (Array.isArray(data?.entries)) this._entries = data.entries;
      this._previewCatalogStatus = data?.preview_catalog_status || 'unknown';
    } catch (error) {
      this._error = error?.code === 'unknown_command'
        ? 'Bitte die Integration in HACS aktualisieren und Home Assistant neu starten.'
        : String(error?.message || error);
    } finally {
      this._refreshingPreviews = false;
      this.render();
    }
  }
  _previewStatus() {
    if (!this._entries?.length) return '';
    if (this._refreshingPreviews || this._previewCatalogStatus === 'loading') return 'Hörproben werden im Katalog geprüft …';
    if (this._previewCatalogStatus === 'unavailable') return 'Hörproben-Katalog vorübergehend nicht erreichbar. Ein neuer Versuch folgt automatisch.';
    if (this._previewCatalogStatus === 'ready' && !this._entries.some(item => this._safePreview(item.preview_url))) return 'Für diese Tonies ist im Katalog derzeit keine zugeordnete Hörprobe verfügbar.';
    return '';
  }
  _safePreview(url) {
    return typeof url === 'string' &&
      /^https:\/\/cdn\.tonies\.de\/o\/audio_samples\/[a-z0-9_./%-]+\.(mp3|wav|m4a|ogg)$/i.test(url) &&
      !url.includes('/../') ? url : '';
  }
  _stopPreview(render = true) {
    const audio = this._previewAudio;
    this._previewAudio = null;
    this._previewId = null;
    if (teddyPreviewOwner === this) teddyPreviewOwner = null;
    if (audio) {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      audio.remove();
    }
    if (render) this.render();
  }
  async _togglePreview(id) {
    const item = (this._entries || []).find(entry => entry.audio_id === id);
    const url = this._safePreview(item?.preview_url);
    if (!url) return;
    this._previewError = null;
    if (this._previewId === id && this._previewAudio?.getAttribute('src') === url) {
      if (!this._previewAudio.paused) { this._previewAudio.pause(); return; }
      if (this._previewAudio.ended) this._previewAudio.currentTime = 0;
    } else {
      this._stopPreview(false);
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.preload = 'none';
      audio.setAttribute('src', url);
      audio.addEventListener('play', () => {
        if (this._previewAudio !== audio) return;
        if (teddyPreviewOwner && teddyPreviewOwner !== this) teddyPreviewOwner._stopPreview();
        teddyPreviewOwner = this;
        this._updatePreviewButtons();
      });
      for (const name of ['pause', 'ended']) {
        audio.addEventListener(name, () => {
          if (this._previewAudio === audio) this._updatePreviewButtons();
        });
      }
      audio.addEventListener('error', () => this._previewFailed(audio, id));
      this._previewAudio = audio;
      this._previewId = id;
    }
    if (teddyPreviewOwner && teddyPreviewOwner !== this) teddyPreviewOwner._stopPreview();
    teddyPreviewOwner = this;
    const audio = this._previewAudio;
    this.render();
    try { await audio.play(); }
    catch (error) {
      // Pausing a still-loading sample can reject play() without a network error.
      if (!(error?.name === 'AbortError' && audio.paused)) this._previewFailed(audio, id);
    }
  }
  _previewFailed(audio, id) {
    // A rejected play() from an already replaced sample is harmless.
    if (this._previewAudio !== audio) return;
    this._stopPreview(false);
    this._previewError = id;
    this.render();
  }
  _updatePreviewButtons() {
    this.shadowRoot.querySelectorAll('button[data-action="preview"]').forEach(button => {
      const playing = button.dataset.id === this._previewId &&
        this._previewAudio && !this._previewAudio.paused && !this._previewAudio.ended;
      button.textContent = (playing ? '⏸ ' : '▶ ') + this._t(playing ? 'Hörprobe pausieren' : 'Hörprobe');
      button.setAttribute('aria-pressed', playing ? 'true' : 'false');
    });
  }
  _mins(seconds) {
    const number = Number(seconds);
    return Number.isFinite(number) && number > 0
      ? (number / 60).toLocaleString(teddyLanguage(this._hass) === 'en' ? 'en-US' : 'de-DE',{maximumFractionDigits:1}) + this._t(" Min.")
      : this._t("Laufzeit unbekannt");
  }
  _openEdit(id) {
    if (!this._isAdmin) return;
    this._stopPreview(false);
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
    if (this._saving || !this._hass || !this._isAdmin) return;
    const get = id => this.shadowRoot.getElementById(id)?.value ?? '';
    const audioId = get('library-audio').trim();
    const duration = get('library-duration').trim();
    if (!/^[a-z0-9_-]{1,80}$/i.test(audioId)) {
      this._error = "Bitte eine gültige Audio-ID eingeben.";
      this.render();
      return;
    }
    const minutes = duration ? Number(duration.replace(',','.')) : 0;
    const seconds = Math.round(minutes * 60);
    if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86400) {
      this._error = "Bitte eine Laufzeit zwischen 0 und 1440 Minuten eingeben.";
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
    const preview = entries.find(item => item.audio_id === this._previewId);
    if (this._previewAudio && (!preview || this._safePreview(preview.preview_url) !== this._previewAudio.getAttribute('src'))) this._stopPreview(false);
    // Keep the same audio node across live library updates, preserving position.
    const previewPanel = this._previewAudio ? '<section class="preview-panel" aria-label="' + this._t('Hörprobe') + '">' +
      '<div class="preview-heading"><strong>' + e(preview.title) + '</strong><button data-action="preview-stop">' +
      this._t('Hörprobe beenden') + '</button></div><div id="library-preview-player"></div></section>' : '';
    const view = this._edit && this._isAdmin ? (() => {
      const item = this._edit;
      const editing = Boolean(item.audio_id);
      const minutes = item.duration_seconds ? Math.round(Number(item.duration_seconds) / 6) / 10 : '';
      return '<section class="form-panel"><h3>' +
        (editing ? this._t("Tonie bearbeiten") : this._t("Tonie hinzufügen")) +
        '</h3>' + (editing ? '<details class="technical"><summary>' + this._t("Technische Details") + '</summary>' : '') +
        '<div class="field"><label for="library-audio">' + this._t("Audio-ID") + '</label><input id="library-audio" maxlength="80"' +
        (editing ? ' readonly' : '') + ' value="' + e(item.audio_id) +
        '" placeholder="' + this._t("Audio-ID des Tonies") + '"></div>' + (editing ? '</details>' : '') +
        '<div class="field"><label for="library-title">' + this._t("Titel") + '</label><input id="library-title" maxlength="200" value="' +
        e(item.title) + '" placeholder="' + this._t("Titel des Hörspiels") + '"></div>' +
        '<div class="field"><label for="library-duration">' + this._t("Hörspiellänge in Minuten") + '</label>' +
        '<input type="number" id="library-duration" min="0" max="1440" step="0.1" value="' +
        e(minutes) + '" placeholder="' + this._t("z. B. 45") + '"></div>' +
        '<div class="field"><label for="library-image">' + this._t("Figurenbild (Bildadresse, optional)") + '</label>' +
        '<input id="library-image" maxlength="2048" value="' + e(item.image) +
        '" placeholder="' + this._t("https://… oder /local/…") + '"></div>' +
        '<div class="field"><label for="library-upload">' + this._t("Oder Bild direkt vom Gerät auswählen") + '</label>' +
        '<input type="file" id="library-upload" accept="image/png,image/jpeg,image/webp">' +
        '<p class="hint" id="library-upload-label">' + this._t("JPG, PNG oder WebP · maximal 2 MB") + '</p></div>' +
        '<div class="edit-actions"><button data-action="cancel" type="button">' + this._t("Abbrechen") + '</button>' +
        '<button class="primary" data-action="save" type="button"' +
        (this._saving ? ' disabled' : '') + '>' + this._t("Änderungen speichern") + '</button></div></section>';
    })() : (
      '<div class="toolbar"><input id="library-search" aria-label="' + this._t("Tonie suchen") + '" placeholder="🔎 ' + this._t("Tonies suchen …") + '" value="' +
      e(this._query) + '"><button type="button" data-action="refresh-previews"' + (this._refreshingPreviews ? ' disabled' : '') + '>' + this._t('Hörproben aktualisieren') + '</button>' + (this._isAdmin ? '<button class="primary" type="button" data-action="add">+ ' + this._t("Tonie hinzufügen") + '</button>' : '') + '</div>' +
      (!this._entries ? '<p class="hint">' + this._t("Bibliothek wird geladen …") + '</p>' :
        !entries.length ? '<p class="empty-library">' + this._t("Noch keine Tonies gespeichert. Stelle eine Figur auf die Toniebox, damit sie automatisch hier erscheint.") + '</p>' :
          '<div class="library-grid">' + entries.map(item => {
            const title = item.title || this._t("Unbekannter Tonie");
            const removed = this._deleteId === item.audio_id;
            const recent = (item.last_heard_boxes || []).filter(box => /^#[0-9a-f]{6}$/i.test(box.color || ''));
            const rings = recent.map((box, index) => '0 0 0 ' + ((index + 1) * 3) + 'px ' + box.color).join(',');
            const highlight = rings ? ' style="box-shadow:' + rings + '"' : '';
            const recentLabel = recent.length ? '<span class="recent">' + this._t("Zuletzt gehört: ") + e(recent.map(box => box.name).join(', ')) + '</span>' : '';
            return '<article class="tonie"' + highlight + ' data-library-entry data-search="' +
              e((title + ' ' + item.audio_id).toLocaleLowerCase()) + '">' +
              this._image(item.image) +
              '<div class="tonie-body"><strong>' + e(title) + '</strong>' + recentLabel +
              '<span class="duration">' + e(this._mins(item.duration_seconds)) + '</span>' +
              (Number(item.times_seen) > 0 ? '<span class="id">' + this._t("Schon ") + e(item.times_seen) + this._t("× erkannt") + '</span>' : '') +
              (item.last_seen ? '<span class="id">' + this._t("Zuletzt erkannt: ") + e(new Date(item.last_seen).toLocaleDateString(teddyLanguage(this._hass) === 'en' ? 'en-US' : 'de-DE')) + '</span>' : '') +
              (this._safePreview(item.preview_url) ? '<button class="preview-button" data-action="preview" aria-pressed="false" data-id="' + e(item.audio_id) + '">▶ ' + this._t('Hörprobe') + '</button>' : '') +
              (this._previewError === item.audio_id ? '<span class="error" role="alert">' + this._t('Hörprobe derzeit nicht erreichbar.') + '</span>' : '') +
              (removed ?
                '<p class="warning">' + this._t("Tonie wirklich aus deiner Bibliothek löschen? Er wird beim erneuten Auflegen wieder hinzugefügt.") + '</p>' +
                '<div class="actions"><button data-action="cancel-delete">' + this._t("Abbrechen") + '</button>' +
                '<button class="danger" data-action="confirm-delete" data-id="' + e(item.audio_id) + '">' + this._t("Ja, löschen") + '</button></div>' :
                '<div class="actions">' + (this._isAdmin ? '<button data-action="edit" data-id="' + e(item.audio_id) +
                '">✏️ ' + this._t("Bearbeiten") + '</button>' : '') + '<button data-action="delete" data-id="' +
                e(item.audio_id) + '">' + this._t("Löschen") + '</button></div>') +
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
      '.recent{font-size:12px;font-weight:600}',
      '.preview-panel{border:1px solid var(--divider-color,#777);border-radius:12px;padding:12px;margin-bottom:16px}.preview-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}.preview-heading strong{font-size:14px;overflow-wrap:anywhere}audio{display:block;width:100%}.preview-button{align-self:flex-start}',
      '.tonie-body strong{font-size:14px;overflow-wrap:anywhere;line-height:1.3}',
      '.duration,.id,.hint{font-size:12px;color:var(--secondary-text-color)}',
      '.id{overflow-wrap:anywhere}',
      '.technical{margin-bottom:15px;font-size:12px;color:var(--secondary-text-color)}.technical summary{cursor:pointer;margin-bottom:8px}',
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
      '<header class="header"><h2>🧸 ' + this._t("Meine Tonie-Bibliothek") + '</h2>',
      '<span class="hint">' + entries.length + ' Tonies</span></header>',
      '<p class="subtitle">' + this._t("Deine Figuren – automatisch gesammelt") + '' +
      (this._isAdmin ? this._t(" – Bearbeiten möglich") : '') + '</p>',
      this._error ? '<p class="error" role="alert">' + e(this._t(this._error)) + '</p>' : '',
      this._previewStatus() ? '<p class="hint" role="status">' + e(this._t(this._previewStatus())) + '</p>' : '',
      previewPanel, view, '</ha-card>'
    ].join('');
    if (this._previewAudio) this.shadowRoot.getElementById('library-preview-player')?.appendChild(this._previewAudio);
    this._updatePreviewButtons();
    if (!this._edit) this._applySearch();
  }
}
customElements.define('teddycloud-tonie-library-card', TeddyCloudTonieLibraryCard);

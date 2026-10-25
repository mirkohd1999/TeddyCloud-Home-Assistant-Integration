# 🧸 TeddyCloud Home Assistant Integration


**Toniebox-Status und Einstellungen direkt in Home Assistant – über TeddyCloud MQTT.**

**TeddyCloud Home Assistant Integration** bindet Tonieboxen über TeddyCloud und die vorhandene MQTT-Integration in Home Assistant ein. Angezeigt werden unter anderem der aktuelle Titel, der gemeldete Wiedergabestatus und – sofern verfügbar – Figurenbilder und Laufzeiten. Lautstärkelimits und LED-Helligkeit lassen sich ebenfalls über Home Assistant einstellen.

Die Einrichtung ist bewusst einfach gehalten: Toniebox automatisch suchen oder manuell hinzufügen, Boxfarbe auswählen und die gewünschte Karte ins Dashboard einfügen.

> **Hinweis:** Das Projekt ist eine inoffizielle Community-Integration und befindet sich noch in der Weiterentwicklung. Es gibt Funktionen, die je nach TeddyCloud-Version und Tonie nicht immer verfügbar sind. Bitte vor größeren Updates ein Backup machen.

## ✨ Funktionen

| Funktion | Beschreibung |
| --- | --- |
| 🔎 Toniebox automatisch finden | Sucht über MQTT nach Tonieboxen; alternativ kann die Box-ID manuell eingetragen werden |
| 🎨 Boxfarbe auswählen | Bei der Einrichtung eine Farbe auswählen oder später ändern |
| 🎵 Titel und Wiedergabe | Zeigt den gemeldeten Titel, die Audio-ID und den Wiedergabestatus |
| 🧸 Tonie-Bilder | Versucht das passende Bild anhand der Audio-ID aus dem Tonies-Katalog zu laden und lokal zu speichern |
| ⏱️ Laufzeit | Zeigt, wenn verfügbar, die Kataloglaufzeit und einen **geschätzten** Fortschritt |
| 🔊 Aktuelle Lautstärke | Wird als Prozentwert angezeigt – **nicht fernsteuerbar** |
| 👂 Ohrtasten | Eigene Sensoren für großes/kleines Ohr: letzter Tastendruck (einfach, doppelt, dreifach), UTC-Zeitpunkt und Ereigniszähler. **Nur Anzeige**, keine Fernsteuerung |
| 👂 Ohrtasten | Großes und kleines Ohr als eigene Sensoren; erkennt einfache, doppelte und dreifache Tastendrücke |
| 🎚️ Lautstärkelimits | Lautsprecher- und Kopfhörerlimit auf 25, 50, 75 oder 100 % einstellen |
| 💡 LED-Helligkeit | Aus, gedimmt oder an |
| 🔌 Ladestation | Zeigt den von TeddyCloud gemeldeten Ladestationsstatus |
| 🖥️ Dashboard | Acht Kartenansichten: Alles, Wiedergabe, Einstellungen, Kompakt, großes Bild, Status-Kacheln, Dashboard-Kacheln und frei zusammenstellbar |
| 📦 Mehrere Tonieboxen | Jede Box kann als eigener Integrationseintrag eingerichtet werden |

**Aktuelle Einschränkungen:** Play/Pause über diese Integration steuern, den tatsächlichen Akku-Prozentstand zuverlässig auslesen oder die echte Wiedergabeposition anzeigen. Ein gemeldeter Ladestationsstatus ist auch keine sichere Aussage darüber, ob der Akku gerade geladen wird.

## 👂 Ohrtasten-Sensoren

Für jede Toniebox werden zwei **Diagnose-Sensoren** angelegt:

- **Großes Ohr (lauter)**: hört auf `<MQTT-Präfix>/box/<Box-ID>/VolUp`
- **Kleines Ohr (leiser)**: hört auf `<MQTT-Präfix>/box/<Box-ID>/VolDown`

Beide Sensoren zeigen den letzten erkannten Tastendruck als `pressed`, `double-pressed` oder `triple-pressed` an. Die zusätzlichen Attribute `last_pressed` (Zeitpunkt in UTC) und `press_count` (seit Laden des Sensors) werden bei jedem neuen Tastendruck aktualisiert, auch wenn derselbe Tastendrucktyp wiederholt wird. Vor dem ersten Ereignis lautet der Zustand `unknown`. Der Ereigniszähler wird bei einem Neustart zurückgesetzt. MQTT-Retained-Meldungen werden nicht als neue Tastendrücke gewertet.

**Wichtig:** Diese MQTT-Topics sind ausschließlich Ereignismeldungen *von* der Toniebox; sie können die Lautstärke nicht fernsteuern. Über TeddyCloud können nur die maximalen Lautstärkelimits konfiguriert werden.

## 📸 Dashboard-Vorschau

Die folgenden Screenshots zeigen die drei Kartenansichten in Home Assistant. Der äußere Dashboard-Hintergrund wurde für eine übersichtlichere Darstellung entfernt.

| Nur Wiedergabe | Alles zusammen | Nur Einstellungen |
| :---: | :---: | :---: |
| <img src="docs/images/dashboard-player-original.webp" alt="Toniebox mit Titel und Bild" width="300"> | <img src="docs/images/dashboard-all-original.webp" alt="Toniebox mit Wiedergabe und Einstellungen" width="300"> | <img src="docs/images/dashboard-settings-original.webp" alt="Lautstärkelimits und LED-Helligkeit" width="300"> |
| `mode: player` | `mode: all` | `mode: settings` |

## ✨ Neu ab v0.3.4: Dashboard ohne Konfigurationsaufwand

Für Endnutzer reicht jetzt **Dashboard bearbeiten → Karte hinzufügen → TeddyCloud Home Assistant Integration**. Die Karte sucht nach vorhandenen Tonieboxen und wählt bei nur einer erkannten Box diese automatisch aus. Im Karteneditor erscheinen **acht große Vorlagen** zum direkten Anklicken. Die Vorschau wird unmittelbar aktualisiert:

- **Alles**, **Musik**, **Kompakt**, **Großes Bild**, **Kacheln**, **Status**, **Einstellungen** und **Selbst gestalten**.
- Nur bei **Selbst gestalten** werden die Auswahl der Bausteine sowie die Anordnung eingeblendet. Standardmäßig sind fünf häufig genutzte Bausteine bereits ausgewählt.
- Wer mehr einstellen möchte, öffnet **Weitere Einstellungen (optional)**. Dort sind Name, Toniebox-Farbe per Farbwähler, Bilddarstellung und manuelle Entitäts-ID untergebracht.
- **Kein YAML und keine manuelle Ressourcenpflege** erforderlich, wenn die Integration in Home Assistant eingerichtet und die Ressource im Storage-Dashboard automatisch registriert ist.
- Die mit v0.3.4 gelieferte Karte wird über eine neue, versionierte Ressourcenadresse `/teddycloud-homeassistant/card-v034.js?v=0.3.4` geladen, damit vorher zwischengespeicherte JavaScript-Versionen nicht versehentlich weiterverwendet werden. Ältere Kartenkonfigurationen und die bisherige Ressourcenadresse bleiben kompatibel.

**Update:** Nach Veröffentlichung von v0.3.4 die Integration über HACS aktualisieren und Home Assistant einmal neu starten. Die Ressourcenadresse wird in normalen Storage-Dashboards automatisch angepasst. Bereits eingerichtete Karten müssen nicht neu erstellt werden.

## 🧩 Dashboard-Baukasten und Kartenvarianten (v0.3.3)

Der visuelle Karteneditor bietet nun **acht Ansichten**. Bereits angelegte Karten mit `mode: all`, `mode: player` oder `mode: settings` bleiben unverändert:

| Modus | Anzeige |
| --- | --- |
| `all` | Bisherige Gesamtansicht mit Player und Einstellungen |
| `player` | Bisherige Wiedergabeansicht |
| `settings` | Bisherige Lautstärke- und LED-Einstellungen |
| `compact` | Platzsparende Leiste mit Bild, Titel, Wiedergabe und Lautstärke |
| `artwork` | Großes Tonie-Bild mit Titel und geschätzter Laufzeit |
| `status` | Status-Kacheln für Wiedergabe, Ladestation, Lautstärke und Ohrtasten |
| `tiles` | Kachel-Dashboard mit Bild, Titel und Statusinformationen |
| `custom` | **Eigener Baukasten:** Bausteine auswählen, sortieren und als Liste oder Kacheln anzeigen |

### Per Karteneditor zusammenstellen

1. Dashboard bearbeiten → **Karte hinzufügen** → **TeddyCloud Home Assistant Integration**.
2. Toniebox auswählen; unter **Kartenansicht** „Eigene Zusammenstellung“ wählen.
3. Die gewünschten Bausteine aktivieren (Bild, Titel, Wiedergabe, Ladestation, Fortschritt, Lautstärke, Lautsprecher-/Kopfhörerlimit, LED, Ohrtasten).
4. Über die Pfeile **↑ / ↓** die Reihenfolge ändern.
5. **Untereinander** oder **Als Kacheln** wählen, bei Kacheln optional 1–3 Spalten einstellen.
6. Speichern. Der Editor übernimmt die neue Zusammenstellung direkt in die Karten-Vorschau.

Die Ohrtasten-Ansicht zeigt die letzten von TeddyCloud gemeldeten Tasten-Ereignisse und den Zähler, falls die Sensoren vorhanden sind. Sie steuert nicht die Lautstärke der Toniebox. Die Regelungen für **Lautstärkelimits und LED** funktionieren nur, wenn die jeweiligen `number`-Entitäten verfügbar sind.

### YAML-Beispiele

Kompakte Karte:

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
mode: compact
```

Frei angeordnete Kacheln:

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
mode: custom
layout: grid
columns: 2
sections:
  - artwork
  - title
  - playback
  - progress
  - volume
  - ears
  - speaker
  - headphone
  - led
```

Mögliche Bausteine: `artwork`, `title`, `playback`, `charger`, `progress`, `volume`, `speaker`, `headphone`, `led`, `ears`. Ihre Reihenfolge in `sections` bestimmt die Anzeige. Die alte Kartenkonfiguration bleibt gültig.

## 📦 Voraussetzungen

- **Home Assistant** mit eingerichteter [MQTT-Integration](https://www.home-assistant.io/integrations/mqtt/)
- Einen funktionierenden [TeddyCloud-Server](https://github.com/toniebox-reverse-engineering/teddycloud), der Toniebox-Daten über MQTT veröffentlicht
- **HACS** zur einfachen Installation (oder eine manuelle Installation der Custom-Integration)
- Für automatische Figurenbilder und Laufzeiten: Internetzugriff von Home Assistant auf den öffentlichen Tonies-Katalog

**Zusätzliche MQTT-Zugangsdaten sind nicht erforderlich.** Die Integration nutzt die bereits eingerichtete MQTT-Verbindung von Home Assistant.

## 🚀 Installation über HACS

1. Öffne **HACS** in Home Assistant.
2. Gehe auf **⋮ → Benutzerdefinierte Repositories**.
3. Füge diese Adresse ein und wähle als Typ **Integration**:

   ```text
   https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration
   ```

4. Suche in HACS nach **TeddyCloud Home Assistant Integration** und lade die Integration herunter.
5. **Starte Home Assistant neu.**
6. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und wähle **TeddyCloud Home Assistant Integration**.

**Manuelle Installation:** Kopiere den Ordner `custom_components/teddycloud_homeassistant` nach `/config/custom_components/` und starte Home Assistant neu.

## 🔎 Toniebox einrichten

### Automatisch suchen

1. Wähle **„Toniebox automatisch suchen“**.
2. Schalte die Toniebox ein oder stelle eine Figur darauf, damit MQTT-Nachrichten gesendet werden.
3. Das MQTT-Präfix kannst du frei eintragen, zum Beispiel `teddyCloud` oder `meinTeddy`. Wenn du es leer lässt, sucht die Integration nach verschiedenen Präfixen.
4. Sobald eine Box erkannt wird, beendet die Suche sich automatisch. Falls keine Nachricht ankommt, stoppt sie nach spätestens **25 Sekunden**.
5. Wähle die gefundene Box aus und vergib einen Namen, zum Beispiel **Meine Toniebox**.
6. Wähle direkt die passende **Boxfarbe** aus.

Falls keine Toniebox auftaucht, kannst du die Einrichtung erneut starten oder die **Box-ID manuell eingeben**.

> Die Suche kann nur Boxen entdecken, von denen MQTT-Meldungen eintreffen oder für die passende gespeicherte (retained) Meldungen vorliegen. Ist die Box komplett still, kann die Suche auch bei funktionierendem MQTT ohne Treffer enden.

### Farben später ändern

Öffne **Einstellungen → Geräte & Dienste → TeddyCloud Home Assistant Integration → Konfigurieren**. Dort kannst du die Farbe auch nachträglich als Hex-Wert einstellen.

## 🖥️ Dashboard-Karte hinzufügen

Öffne dein Dashboard, klicke auf **Bearbeiten → Karte hinzufügen → TeddyCloud Home Assistant Integration**. Wähle im Karteneditor eine Vorlage. Bei nur einer gefundenen Toniebox erfolgt die Auswahl automatisch. **YAML wird nicht benötigt.**

Wer lieber manuell arbeiten möchte, kann weiterhin unter **Bearbeiten → Karte hinzufügen → Manuell** die folgenden Beispiele verwenden.

### Toniebox mit Titel und Bild

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
name: Meine Toniebox
mode: player
artwork_mode: auto
composition: true
```

### Nur die Einstellungen

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
mode: settings
```

### Toniebox und Einstellungen zusammen

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
name: Meine Toniebox
mode: all
artwork_mode: auto
```

**Wichtig:** `media_player.meine_toniebox_now_playing` ist nur eine Beispiel-Entitäts-ID. Hier muss die **eigene Media-Player-Entitäts-ID** eingetragen werden. Sie steht unter **Einstellungen → Geräte & Dienste → Entitäten**.

Der angezeigte Name entspricht dem bei der Einrichtung gewählten Boxnamen, beispielsweise **Meine Toniebox**. Bestehende Entitäts-IDs mit `_now_playing` bleiben aus Kompatibilitätsgründen erhalten.

### Bilddarstellung

Die Karte unterstützt drei Varianten:

- `artwork_mode: auto` – Katalogbilder werden sicherheitshalber als Cover angezeigt; ein ausdrücklich gesetztes Figurenbild kann als Figur dargestellt werden.
- `artwork_mode: figure` – Bild vor der stilisierten Toniebox anzeigen.
- `artwork_mode: cover` – Bild als eigenständiges Cover anzeigen.

Du kannst auch `composition: false` verwenden, wenn du keine stilisierte Box möchtest. Die normale Einstellung ist `composition: true`. Mit `color: '#D82F38'` kannst du eine Kartenfarbe fest vorgeben; ohne diesen Eintrag wird die in der Integration ausgewählte Farbe verwendet.

## 👂 Große und kleine Ohrtaste als Sensoren

Die Integration stellt für jede eingerichtete Toniebox jetzt zwei zusätzliche **lesende Sensoren** bereit:

- **Großes Ohr (lauter)** – MQTT-Topic `{prefix}/box/{box_id}/VolUp`
- **Kleines Ohr (leiser)** – MQTT-Topic `{prefix}/box/{box_id}/VolDown`

Der Sensorzustand zeigt die letzte erkannte Betätigung: `pressed`, `double-pressed` oder `triple-pressed`. TeddyCloud sendet dafür eine MQTT-Nachricht wie `{"event_type":"pressed"}`.

Die Sensorattribute `last_pressed` (Zeitpunkt) und `press_count` (Anzahl der seit dem letzten Start empfangenen Ereignisse) werden bei **jedem** Tastendruck aktualisiert. Dadurch lassen sich auch wiederholte einfache Tastendrücke in Automationen erkennen. Der Zähler beginnt nach einem Neustart der Integration wieder bei null.

Für eine Home-Assistant-Automation kann zum Beispiel auf Änderungen des Attributs `press_count` reagiert werden:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.DEINE_GROSSES_OHR_ENTITAET
    attribute: press_count
actions:
  - action: persistent_notification.create
    data:
      message: "Großes Ohr wurde gedrückt"
```

Die tatsächlich vergebenen Sensor-Entitäts-IDs stehen unter **Einstellungen → Geräte & Dienste → Entitäten**. Beim ersten Start bleibt der Sensor auf `unknown`, bis TeddyCloud einen Tastendruck meldet. Die MQTT-Daten müssen dafür vom TeddyCloud-Server übertragen werden. Die neuen Sensoren lösen selbst **keine Lautstärkeänderung** aus.

## 🧸 Figurenbilder und Laufzeiten

Wenn die Toniebox eine **Audio-ID** über MQTT meldet, versucht die Integration im öffentlichen [tonies-json-Katalog](https://github.com/toniebox-reverse-engineering/tonies-json) den passenden Eintrag zu finden. Dabei wird anhand der **Audio-ID** gesucht, nicht einfach irgendein Bild anhand eines ähnlichen Titels genommen.

Wenn ein Bild gefunden und heruntergeladen werden kann, wird es unter folgendem Pfad zwischengespeichert:

```text
/config/www/teddycloud_homeassistant/figures/
```

Wenn eine Laufzeit im Katalog hinterlegt ist, wird sie angezeigt. Der Fortschrittsbalken bleibt allerdings eine **Schätzung ab einem MQTT-Wiedergabeereignis** – die Integration bekommt keine echte Position aus dem Hörspiel.

Fehlt ein Katalogeintrag, die Bilddatei oder die Internetverbindung, zeigt Home Assistant möglicherweise ein Ersatzbild oder **„Laufzeit unbekannt“**. Auch bei Kreativ-Tonies oder Sondereditionen können Daten fehlen.

### Eigene Daten ergänzen (optional)

In den **Integrationsoptionen** kannst du einzelne Tonies anhand ihrer Audio-ID selbst ergänzen. Beispiel für das Feld **„Katalog als JSON“**:

```json
{
  "1589539605": {
    "title": "Yakari - Best of Kleiner Donner",
    "duration_seconds": 2340
  }
}
```

Du kannst zusätzlich eine eigene Bild-URL als `figure` oder `cover` hinterlegen. Diese Möglichkeit ist optional – für die normale Einrichtung musst du keinen JSON-Katalog pflegen.

Wenn TeddyCloud Bilder als `http://localhost/...` meldet, kann das im Home-Assistant-Browser nicht direkt funktionieren. Unter den Integrationsoptionen gibt es dafür die **TeddyCloud-Adresse für Coverbilder**, mit der solche Adressen auf den tatsächlich erreichbaren Server umgeschrieben werden können.

## 🛠️ Wenn etwas nicht funktioniert

**Die automatische Suche findet nichts:** Stelle eine Figur auf, aktiviere die Toniebox und überprüfe, ob unter deinem Präfix MQTT-Meldungen ankommen, zum Beispiel `teddyCloud/box/DEINE_BOX_ID/Playback`. Alternativ die Box-ID manuell eintragen.

**Die Dashboard-Karte erscheint nicht („Custom element doesn't exist“):** Prüfe, ob die Integration korrekt installiert wurde, starte Home Assistant neu und lade das Dashboard mit **Strg + F5** neu. Unter **Einstellungen → Dashboards → Ressourcen** muss die Kartenressource als **JavaScript-Modul** vorhanden sein:

```text
/teddycloud-homeassistant/card.js
```

Die Integration versucht, die Ressource bei Dashboards im Storage-Modus automatisch zu registrieren. In YAML-Konfigurationen kann es nötig sein, sie selbst einzutragen. Eine bestehende Ressource bitte bearbeiten, statt doppelte Einträge anzulegen. Zur Fehlerprüfung kannst du die Adresse direkt in deinem Home-Assistant-Browser öffnen.

**Titel vorhanden, aber Bild oder Laufzeit fehlen:** Öffne **Entwicklerwerkzeuge → Zustände** und wähle deine Toniebox-Media-Player-Entität. Diese Attribute helfen bei der Suche:

| Attribut | Bedeutung |
| --- | --- |
| `content_audio_id` | Von TeddyCloud gemeldete Audio-ID |
| `catalog_status` | Status der Online-Suche, z. B. `matched`, `unavailable` oder `audio_id_not_found` |
| `catalog_match` | Ob ein passender Eintrag gefunden wurde |
| `cover_url` | Verwendete Bildadresse |
| `media_duration` | Laufzeit, wenn verfügbar, in Sekunden |
| `duration_source` | Herkunft der Laufzeit |
| `charger` | Von TeddyCloud gemeldeter Ladestationsstatus |

Bei `catalog_status: unavailable` helfen die Meldungen unter **Einstellungen → System → Protokolle**. Bei einem fehlgeschlagenen Katalogabruf versucht die Integration es für die aktuelle Figur erneut, solange sie noch erkannt wird. **Bitte nicht auf „Zustand setzen“ klicken** – damit wird nur der angezeigte Zustand überschrieben, nicht die eigentliche Ursache behoben.

**Die Regler ändern nichts:** Die MQTT-Befehle können je nach TeddyCloud-/Toniebox-Konfiguration erst bei einem späteren *Freshness Check* wirksam werden. Prüfe, ob TeddyCloud die passenden Befehls- und Status-Topics unterstützt.

## 🔄 Aktualisieren und entfernen

**Aktualisieren:** In **HACS → TeddyCloud Home Assistant Integration → Erneut herunterladen**, anschließend Home Assistant neu starten. Falls die Karte noch alt aussieht, das Dashboard neu laden. Vor größeren Änderungen empfiehlt sich ein Backup.

**Entfernen:** Entferne die Integration unter **Einstellungen → Geräte & Dienste**. Wenn die **letzte** eingerichtete Toniebox entfernt wird, bereinigt die Integration ihre lokal gespeicherten Figurenbilder, den internen Cache und automatisch angelegte Dashboard-Ressourcen, sofern deren Eigentum eindeutig gespeichert wurde.

**Bewusst nicht gelöscht** werden selbst angelegte Dashboard-Karten, manuell eingerichtete Ressourcen und andere persönliche Dateien. Ältere Ressourcen müssen gegebenenfalls einmal von Hand entfernt werden.

## 💬 Fehler melden und mithelfen

Fehlerberichte, Verbesserungsvorschläge und Ideen sind willkommen. Dafür einfach ein [GitHub-Issue](https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration/issues) erstellen.

Hilfreich sind dabei die Versionen von Home Assistant und TeddyCloud, der beobachtete Fehler sowie passende Protokollmeldungen. Bitte **keine Passwörter, Zugangstoken, Zertifikate oder privaten MQTT-Daten** veröffentlichen.

## ℹ️ Hinweise

Dies ist **kein offizielles Projekt von tonies® oder TeddyCloud**. Die Rechte an den Tonie-Figuren und deren Bildern liegen bei den jeweiligen Rechteinhabern. Die optionalen Online-Bilder/Katalogdaten werden über Drittanbieterquellen abgerufen; dafür muss Home Assistant diese Server erreichen können.

Die interne Integrationskennung bleibt `teddycloud_homeassistant`, um bestehende Installationen und Dashboard-Entitäten möglichst kompatibel zu halten.

Das eigene Integrationslogo mit Toniebox und Teddy liegt im `brand/`-Ordner. Für dessen Darstellung in Home Assistant ist eine ausreichend neue Home-Assistant-Version erforderlich.

## 📄 Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

# 🧸 TeddyCloud Home Assistant Integration

**Tonieboxen mit TeddyCloud MQTT in Home Assistant anzeigen – inklusive Figurenbildern, Ohrtasten-Sensoren, Einstellungen und individuell gestaltbaren Dashboard-Karten.**

[![Aktuelle Version](https://img.shields.io/github/v/release/mirkohd1999/TeddyCloud-Home-Assistant-Integration?label=Version)](https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration/releases/latest)
[![Lizenz](https://img.shields.io/github/license/mirkohd1999/TeddyCloud-Home-Assistant-Integration)](LICENSE)

> **Aktueller Stand: v0.3.7.** Inoffizielle Community-Integration; kein offizielles Produkt von tonies® oder TeddyCloud. Die Integration nutzt die **vorhandene MQTT-Integration in Home Assistant** und benötigt keine eigenen MQTT-Zugangsdaten.

## Inhalt

- [Schnellstart](#-schnellstart)
- [Funktionen und Einschränkungen](#-funktionen-und-einschränkungen)
- [Dashboard-Karte hinzufügen](#-dashboard-karte-hinzufügen)
- [Dashboard selbst gestalten](#-dashboard-selbst-gestalten)
- [Tonie-Bibliothek](#-tonie-bibliothek)
- [Toniebox über MQTT](#-toniebox-über-mqtt)
- [Ohrtasten-Sensoren](#-ohrtasten-sensoren)
- [Figurenbilder und Laufzeit](#-figurenbilder-und-laufzeit)
- [Fehlerbehebung](#-fehlerbehebung)
- [Update, Deinstallation und Kontakt](#-update-deinstallation-und-kontakt)

## 🚀 Schnellstart

### Das brauchst du

- Home Assistant mit eingerichteter [MQTT-Integration](https://www.home-assistant.io/integrations/mqtt/).
- Einen laufenden [TeddyCloud-Server](https://github.com/toniebox-reverse-engineering/teddycloud), der Toniebox-Status per MQTT meldet.
- [HACS](https://www.hacs.xyz/) zum Installieren der Integration (alternativ manuelle Installation).
- Optional: Internetzugriff für Bilder und Laufzeiten aus dem [Tonies-Katalog](https://github.com/toniebox-reverse-engineering/tonies-json).

**Wichtig:** Dies ist eine **HACS-Integration**, kein Home-Assistant-Add-on. Ein separater MQTT-Broker oder neue MQTT-Zugangsdaten werden durch diese Integration nicht eingerichtet.

### Installation über HACS

1. Öffne **HACS → ⋮ → Benutzerdefinierte Repositories**.
2. Füge das Repository als Typ **Integration** hinzu:

   ```text
   https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration
   ```

3. Öffne **TeddyCloud Home Assistant Integration** in HACS und lade die aktuelle Version herunter.
4. **Starte Home Assistant neu.**
5. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**, suche **TeddyCloud Home Assistant Integration** und folge dem Einrichtungsdialog.
6. Wähle **Automatisch suchen** oder **Manuell hinzufügen**. Vergib einen Namen und wähle die Boxfarbe aus.

> **Tipp:** Schalte die Toniebox für die automatische Suche ein oder stelle eine Figur auf. Ohne MQTT-Statusmeldung kann eine ausgeschaltete/stille Box nicht zuverlässig gefunden werden. Die Suche endet nach spätestens etwa 25 Sekunden. Falls nötig, Box-ID manuell eingeben.

**Manuelle Installation:** Den Ordner `custom_components/teddycloud_homeassistant` nach `/config/custom_components/` kopieren und Home Assistant neu starten.

## ✨ Funktionen und Einschränkungen

| Funktion | Beschreibung |
| --- | --- |
| 🔎 Box-Erkennung | Automatische MQTT-Suche oder manuelle Box-ID; mehrere Tonieboxen möglich |
| 🎵 Titel/Wiedergabe | Gemeldeter Titel, Audio-ID und Wiedergabestatus |
| 🧸 Tonie-Bilder | Online-Katalog, eigene Bildangaben oder TeddyCloud-Bild; bei Bedarf lokaler Cache |
| ⏱️ Laufzeit | Wenn vorhanden aus dem Katalog; Wiedergabefortschritt **nur geschätzt** |
| 🔊 Aktuelle Lautstärke | Lesender Prozent-Sensor |
| 🎚️ Lautstärkelimits | Lautsprecher und Kopfhörer: **25 / 50 / 75 / 100 %** |
| 💡 LED | Aus, gedimmt oder an |
| 🔌 Ladestation | Von TeddyCloud gemeldeter Zustand |
| 👂 Ohrtasten | Je ein Sensor für großes/kleines Ohr, einschließlich Mehrfachdruck und Ereigniszähler |
| 🎨 Dashboard | **8 Vorlagen**, Live-Vorschau, frei wählbare Bausteine, Reihenfolge und Breite |
| 📚 Tonie-Bibliothek | Einmal erkannte Tonies dauerhaft merken; Admins bearbeiten, alle angemeldeten Nutzer dürfen löschen |

**Nicht möglich:** Die aktuelle Lautstärke fernsteuern, Play/Pause auslösen, eine echte Abspielposition oder einen zuverlässigen Akku-Prozentstand abfragen. Ein erkannter Ladestationsstatus bedeutet nicht zwingend, dass der Akku gerade lädt. Lautstärkelimits und LED-Einstellungen können erst bei einem späteren *Freshness Check* wirksam werden.

## 🖥️ Dashboard-Karte hinzufügen

**Kein YAML erforderlich:** Die Integration versucht, ihre Dashboard-Ressource bei gewöhnlichen Storage-Dashboards automatisch einzubinden.

1. Öffne in Home Assistant dein Dashboard und klicke auf **Bearbeiten**.
2. Wähle **Karte hinzufügen → TeddyCloud Home Assistant Integration**.
3. Wähle die Toniebox – bei nur einer passenden erkannten Box geschieht dies normalerweise automatisch.
4. Tippe eine der **acht großen Vorlagen** an. Rechts siehst du die Vorschau.
5. Klicke auf **Speichern**.

### Die acht Dashboard-Ansichten

| Vorlage | Modus | Das wird gezeigt |
| --- | --- | --- |
| 🧸 **Alles** | `all` | Player und Toniebox-Einstellungen |
| 🎵 **Musik** | `player` | Tonie-Bild und Titel |
| ▬ **Kompakt** | `compact` | Platzsparende Leiste |
| 🖼️ **Großes Bild** | `artwork` | Großes Bild, Titel und Laufzeit |
| ▦ **Kacheln** | `tiles` | Bild, Titel und Status als Kacheln |
| 📊 **Status** | `status` | Wiedergabe, Ladestation, Lautstärke und Ohren |
| ⚙️ **Einstellungen** | `settings` | Lautsprecherlimit, Kopfhörerlimit und LED |
| 🧩 **Selbst gestalten** | `custom` | Bausteine selbst wählen, sortieren und verbreitern |

Die bisherigen Ansichten und gespeicherten Kartenkonfigurationen bleiben kompatibel. Anzeigename, Boxfarbe, Bilddarstellung und eine manuelle Entitäts-ID findest du unter **Weitere Einstellungen (optional)**.

### Screenshots der klassischen Ansichten

Die folgenden Originalbilder zeigen **Musik**, **Alles** und **Einstellungen**. Die neuen Kachel- und Baukastenansichten siehst du im visuellen Karteneditor.

| Musik | Alles | Einstellungen |
| :---: | :---: | :---: |
| <img src="docs/images/dashboard-player-original.webp" alt="Klassische Musikansicht" width="280"> | <img src="docs/images/dashboard-all-original.webp" alt="Klassische Gesamtansicht" width="280"> | <img src="docs/images/dashboard-settings-original.webp" alt="Klassische Einstellungsansicht" width="280"> |

## 🧩 Dashboard selbst gestalten

Im Editor die Vorlage **Selbst gestalten** auswählen. Fünf häufig genutzte Bausteine sind vorausgewählt; weitere kannst du per Häkchen aktivieren oder ausblenden. Mit **↑ / ↓** bestimmst du ihre Reihenfolge.

| Baustein | Kennung für YAML |
| --- | --- |
| Bild / Toniebox | `artwork` |
| Titel und Boxname | `title` |
| Wiedergabestatus | `playback` |
| Ladestation | `charger` |
| Laufzeit / Fortschritt | `progress` |
| Aktuelle Lautstärke | `volume` |
| Lautsprecher-Limit | `speaker` |
| Kopfhörer-Limit | `headphone` |
| LED-Helligkeit | `led` |
| Ohrtasten | `ears` |

### Eigene Breite je Baustein (ab v0.3.5)

1. **Anordnung → Kacheln** auswählen.
2. Die Gesamtzahl der **Spalten** auf 1, 2 oder 3 einstellen.
3. Für **jeden aktivierten Baustein einzeln** seine Breite wählen: **1 Spalte**, **2 Spalten** oder **Volle Breite**, je nach Gesamtspaltenzahl.
4. Die Live-Vorschau prüfen und speichern.

Beispielsweise kann das Tonie-Bild über **zwei Spalten**, der Titel über **eine Spalte** und der LED-Regler wieder über die **volle Breite** gehen. Auf schmalen Bildschirmen stehen die Kacheln automatisch untereinander.

Die störende Überschrift **„Tonie-Bild oder Toniebox“ über dem Bild** entfällt in **Großes Bild**, **Kacheln** und **Selbst gestalten**.

### YAML-Beispiel (nur optional)

Der visuelle Editor erzeugt diese Konfiguration automatisch. Falls du lieber YAML benutzt:

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox
mode: custom
layout: grid
columns: 2
sections:
  - artwork
  - title
  - playback
  - charger
  - led
section_widths:
  artwork: 2
  title: 1
  playback: 1
  charger: 1
  led: 2
```

**Die Entitäts-ID ist nur ein Beispiel.** Deine tatsächliche ID findest du unter **Einstellungen → Geräte & Dienste → Entitäten**. Auch bisherige IDs mit `_now_playing` bleiben gültig.

Weitere optionale Karteneinstellungen: `name`, `color`, `artwork_mode` (`auto`, `figure`, `cover`) und `composition`. Du kannst diese Einstellungen ohne YAML im Karteneditor vornehmen.

## 📚 Tonie-Bibliothek

Ab **v0.3.6** gibt es eine **zweite Dashboard-Karte: „TeddyCloud Tonie-Bibliothek“**. Sie funktioniert unabhängig davon, welche Toniebox gerade eingeschaltet ist.

### Bibliothek einrichten – einmalig durch einen Dashboard-Administrator

1. Home Assistant nach dem HACS-Update auf v0.3.6 **neu starten**.
2. Dashboard öffnen → **Bearbeiten → Karte hinzufügen**.
3. **TeddyCloud Tonie-Bibliothek** auswählen und speichern.

Danach können **alle angemeldeten Home-Assistant-Nutzer** die Tonies **direkt in dieser Karte ansehen und löschen**. **Hinzufügen und Bearbeiten** (Titel, Laufzeit und Bilder) sind ausschließlich Administratoren erlaubt. Sie benötigen **keine Berechtigung zum Bearbeiten des Dashboards**. Alle Änderungen gelten für die **gemeinsame Bibliothek** dieses Home-Assistant-Systems; Nutzer sehen deshalb dieselben Tonies.

### Was kann die Bibliothek?

- **Automatisch sammeln:** Sobald die Integration eine bislang unbekannte **Audio-ID** von einer Toniebox meldet, wird der Tonie zur Bibliothek hinzugefügt. Auch Tonies, die später nicht mehr aufgelegt sind, bleiben gespeichert.
- **Suchen und stöbern:** Alle gesammelten Tonies als Bilderkacheln mit Titel und Hörspiellänge anzeigen. Die Audio-ID steht beim Bearbeiten unter den standardmäßig eingeklappten **Technischen Details**; beim manuellen Hinzufügen ist sie weiterhin ein sichtbares Pflichtfeld.
- **Titel und Hörspiellänge bearbeiten (nur Admins):** Direkt mit **Bearbeiten** im Dashboard. Die Laufzeit wird in Minuten eingetragen.
- **Figurenbild ändern (nur Admins):** Eine Bildadresse eingeben **oder eine JPG-/PNG-/WebP-Datei vom eigenen Gerät hochladen** (maximal 2 MB). Hochgeladene Bilder werden lokal unter `/config/www/teddycloud_homeassistant/library/` abgelegt; kein externer Bildhost notwendig.
- **Tonie löschen:** Über den Löschknopf und eine zusätzliche Bestätigung aus der Bibliothek entfernen.
- **Wieder hinzufügen:** Wird ein gelöschter Tonie nach dem Abnehmen **erneut aufgelegt**, nimmt die Integration ihn bei einem **neuen Erkennungsereignis** wieder auf. Ein alter zwischengespeicherter Status oder eine laufende Katalogsuche hebt das Löschen nicht sofort auf.
- **Manuell hinzufügen (nur Admins):** Über **+ Tonie hinzufügen** mit Audio-ID, beispielsweise für Figuren, die derzeit nicht aufgestellt werden können.

**Wichtig:** Die automatische Sammlung beginnt mit der Installation dieser Funktion. Tonies, die **vorher** benutzt wurden und seitdem keine Erkennungsdaten mehr gesendet haben, lassen sich **nicht rückwirkend aus einer vollständigen Toniebox-Historie rekonstruieren**. Du kannst sie jederzeit wieder auflegen oder manuell hinzufügen.

Die Bearbeitung von Titel, Bild und Laufzeit wirkt sich zusätzlich auf die **Anzeige der aktuell erkannten Figur** im vorhandenen Toniebox-Media-Player aus. Bereits gespeicherte eigene Angaben gehen dabei nicht verloren, wenn der Online-Katalog andere Werte liefert.

**Datenschutz und Rollen:** Die Bibliothek nutzt Home Assistants **authentifizierte WebSocket-Verbindung**. Es wird **keine offene API** für anonyme Nutzer bereitgestellt. **Alle angemeldeten Home-Assistant-Nutzer können Einträge löschen. Nur Administratoren können Einträge hinzufügen oder bearbeiten**, einschließlich Bild-Uploads. Diese Berechtigung wird auch serverseitig für direkte WebSocket-Anfragen geprüft. Admin-Rechte sind weiterhin erforderlich, um das Dashboard selbst zu bearbeiten und die Bibliothekskarte dort erstmalig hinzuzufügen.

## 📡 Toniebox über MQTT

Die Daten kommen über die vorhandene MQTT-Anbindung:

```text
Toniebox → TeddyCloud → MQTT-Broker → Home Assistant → TeddyCloud-Karte
```

Die Topics für eine Box folgen diesem Schema:

```text
<MQTT-Präfix>/box/<Box-ID>/<Feld>
```

Beispiel: `teddyCloud/box/DEINE_BOX_ID/Playback`.

Pro eingerichteter Toniebox werden ein **Media-Player (nur lesend)**, **drei einstellbare Number-Entitäten** für Lautsprecherlimit, Kopfhörerlimit und LED sowie **Sensoren** für aktuelle Lautstärke und beide Ohrtasten bereitgestellt.

- Das Präfix wird bei der Suche erkannt oder bei der manuellen Einrichtung festgelegt (Standard: `teddyCloud`).
- Name und Farbe der Box kannst du später unter **Einstellungen → Geräte & Dienste → TeddyCloud Home Assistant Integration → Konfigurieren** ändern.
- Befehle für Lautstärkelimits/LED werden auf den entsprechenden `CmdVolLimitSpk/set`-, `CmdVolLimitHdp/set`- bzw. `CmdLed/set`-Topics gesendet. Erst die MQTT-Statusmeldung bestätigt eine Änderung.

## 👂 Ohrtasten-Sensoren

Zwei **lesende Diagnose-Sensoren** zeigen die letzten Druckereignisse:

| Sensor | MQTT-Topic |
| --- | --- |
| Großes Ohr (lauter) | `<Präfix>/box/<Box-ID>/VolUp` |
| Kleines Ohr (leiser) | `<Präfix>/box/<Box-ID>/VolDown` |

Erkannte Zustände: `pressed` (einfach), `double-pressed` (doppelt), `triple-pressed` (dreifach).

Jeder Sensor bietet zusätzlich `last_pressed` (UTC-Zeitpunkt) und `press_count` (Anzahl seit dem letzten Laden des Sensors). Wiederholte gleiche Tastendrücke zählen ebenfalls. Retained-MQTT-Nachrichten werden nicht als neue Tastendrücke gewertet. Vor dem ersten Ereignis kann der Zustand `unknown` sein.

**Automationsbeispiel:** Auf Veränderungen des Attributs `press_count` reagieren:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.DEIN_GROSSES_OHR
    attribute: press_count
actions:
  - action: persistent_notification.create
    data:
      message: "Großes Ohr wurde gedrückt"
```

Die Sensor-Entitäts-ID bitte ersetzen. **Diese Meldungen steuern nicht die aktuelle Toniebox-Lautstärke.**

## 🧸 Figurenbilder und Laufzeit

Meldet TeddyCloud eine Audio-ID, sucht die Integration nach passenden Bildern und Laufzeiten im öffentlichen [tonies-json-Katalog](https://github.com/toniebox-reverse-engineering/tonies-json). Heruntergeladene Figurenbilder werden bei Bedarf hier gespeichert:

```text
/config/www/teddycloud_homeassistant/figures/
```

Fehlen Daten, kann die Karte ein Ersatzbild oder **„Laufzeit unbekannt“** anzeigen. **Der Fortschrittsbalken ist immer eine Schätzung**, keine gemessene Abspielposition.

### Eigene Daten ergänzen (optional)

Unter **Einstellungen → Geräte & Dienste → TeddyCloud Home Assistant Integration → Konfigurieren** können Tonie-Daten pro Audio-ID ergänzt werden:

```json
{
  "1589539605": {
    "title": "Beispiel-Tonie",
    "duration_seconds": 2340
  }
}
```

Optional werden auch Bildadressen über `figure` oder `cover` unterstützt. Falls TeddyCloud `http://localhost/...` für Bilder meldet, kann die Option **TeddyCloud-Adresse für Coverbilder** helfen, die Adresse für den Home-Assistant-Browser erreichbar zu machen.

## 🛠️ Fehlerbehebung

### Die Toniebox wird nicht gefunden

Toniebox einschalten oder eine Figur aufstellen. Prüfen, ob in MQTT ein Status-Topic wie `teddyCloud/box/DEINE_BOX_ID/Playback` ankommt. Falls sie still bleibt, die Box-ID **manuell** eingeben.

### Die Karte fehlt oder sieht noch alt aus

- In HACS prüfen, ob die aktuelle Integration installiert ist.
- **Home Assistant neu starten** und danach das Dashboard neu laden.
- Bei normalen Storage-Dashboards versucht die Integration, die Ressource selbst zu registrieren. Nur wenn das fehlschlägt oder Dashboard-Ressourcen per YAML verwaltet werden, ist eine manuelle Prüfung nötig.

**Ressourcenadresse in v0.3.7:**

```text
/teddycloud-homeassistant/card-v037.js?v=0.3.7
```

Unter **Einstellungen → Dashboards → Ressourcen** muss der Eintrag als **JavaScript-Modul** hinterlegt sein. Die älteren Pfade `card.js`, `card-v034.js` und `card-v035.js` bleiben kompatibel. **Keine doppelten Ressourcen anlegen**: Bestehende Einträge gegebenenfalls aktualisieren.

**Bibliothekskarte meldet „Custom element doesn't exist“?** Das YAML `type: custom:teddycloud-tonie-library-card` ist richtig. Ab **v0.3.7** ist die Registrierung auch dann geschützt, wenn gleichzeitig noch eine ältere TeddyCloud-Kartendatei geladen wurde. HACS-Update auf v0.3.7 installieren und Home Assistant vollständig neu starten. Die Ressource wird bei Storage-Dashboards automatisch auf die neue Adresse umgestellt; bestehende Karten und Bibliotheksdaten bleiben erhalten.

### Tonie-Bild, Titel oder Laufzeit fehlen

Öffne **Entwicklerwerkzeuge → Zustände** und prüfe die Media-Player-Entität.

| Attribut | Bedeutung |
| --- | --- |
| `content_audio_id` | Von TeddyCloud gemeldete Audio-ID |
| `catalog_status` | Katalogsuche, etwa `matched`, `unavailable` oder `audio_id_not_found` |
| `catalog_match` | Passender Online-Eintrag vorhanden |
| `cover_url` | Verwendete Bildadresse |
| `media_duration` | Laufzeit in Sekunden, sofern bekannt |
| `duration_source` | Herkunft der Laufzeit |
| `charger` | Meldung zur Ladestation |

Bei Problemen mit dem Katalog unter **Einstellungen → System → Protokolle** nachsehen. In den Entwicklerwerkzeugen **„Zustand setzen“** behebt keine MQTT- oder Katalogprobleme.

### Lautstärke- oder LED-Regler haben keine Wirkung

Die Regler verändern **Limits und LED**, nicht die aktuelle Lautstärke. Je nach TeddyCloud- und Toniebox-Verhalten werden Befehle erst bei einem späteren *Freshness Check* wirksam. Prüfe die MQTT-Befehls- und Status-Topics.

## 🔄 Update, Deinstallation und Kontakt

**Update:** In HACS die aktuelle Version installieren und Home Assistant neu starten. Vor größeren Updates empfiehlt sich ein Backup.

**Deinstallation:** Integration unter **Einstellungen → Geräte & Dienste** entfernen. Wird die **letzte Box** entfernt, bereinigt die Integration lokal gespeicherte Figurenbilder und die eindeutig von ihr registrierten Ressourcen. **Selbst eingerichtete Dashboard-Karten und manuelle Ressourcen bleiben erhalten.**

**Fehler oder Ideen:** [GitHub-Issue erstellen](https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration/issues). Nenne nach Möglichkeit Home-Assistant-, TeddyCloud- und Integrationsversion sowie relevante Protokolle. **Keine Passwörter, Tokens, Zertifikate oder privaten MQTT-Daten veröffentlichen.**

Die interne Domain `teddycloud_homeassistant` und der Karten-Typ `custom:teddycloud-homeassistant-card` bleiben für bestehende Installationen unverändert. Das Projekt ist **nicht offiziell von tonies® oder TeddyCloud**; die Rechte an Bildern und Katalogdaten liegen bei den jeweiligen Rechteinhabern.

**Lizenz:** [MIT](LICENSE) · **Releases:** [GitHub-Veröffentlichungen](https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration/releases)

# 🧸 TeddyCloud in Home Assistant

**Deine Toniebox in Home Assistant – mit Titel, Figurenbild, Status und einer eigenen Dashboard-Karte.**

Eine Community-Integration für [TeddyCloud](https://github.com/toniebox-reverse-engineering/teddycloud). Sie liest den Toniebox-Status über die **bereits eingerichtete Home-Assistant-MQTT-Integration** und zeigt ihn übersichtlich an. Die aktuelle Lautstärke ist **nur eine Anzeige**; Lautstärkelimits und LED-Helligkeit lassen sich über die vorhandenen TeddyCloud-MQTT-Befehle einstellen.

> **Status: Beta / Community-Projekt.** Die Integration wurde schrittweise anhand echter MQTT- und Home-Assistant-Rückmeldungen verbessert. Nicht jede Kombination aus TeddyCloud-Version, Toniebox und Home Assistant ist getestet. Bitte vor Updates ein Backup erstellen.

## ✨ Funktionen

| Bereich | Was möglich ist |
| --- | --- |
| 🎵 Wiedergabe | Hörspieltitel, Audio-ID und gemeldeter Wiedergabestatus |
| 🧸 Figurenbilder | Automatische Zuordnung über den öffentlichen Tonies-Katalog anhand der **exakten Audio-ID**; lokaler Bildcache |
| ⏱️ Laufzeit | Katalog-Laufzeit, falls verfügbar; **geschätzter**, nicht exakter Fortschritt |
| 🔊 Lautstärke | Aktuelle Lautstärke in Prozent **nur zur Information** |
| 🎚️ Limits | Lautsprecher- und Kopfhörer-Lautstärkelimits einstellen |
| 💡 LEDs | LED aus, gedimmt oder an |
| 🔌 Ladestation | Anzeige, ob die Box auf der Ladestation steht, soweit über MQTT gemeldet |
| 🔎 Einrichtung | Automatische Boxsuche mit optionalem, frei wählbarem MQTT-Präfix |
| 🗂️ Dashboard | Alles zusammen oder separate Karten für Wiedergabe und Einstellungen |
| 📦 Mehrere Boxen | Jede Box als eigenen Integrationseintrag hinzufügen |

**Nicht enthalten:** Fernsteuerung von Play/Pause, eine zuverlässige echte Abspielposition oder ein verlässlicher Akku-Prozentwert. „Auf Ladestation“ bedeutet nicht zwingend, dass der Akku gerade lädt.

## 🚀 Installation über HACS

**Voraussetzungen:** Home Assistant, eine funktionierende MQTT-Integration und ein TeddyCloud-Server, der Toniebox-Statusmeldungen per MQTT sendet.

1. In **HACS → ⋮ → Benutzerdefinierte Repositories** diese Adresse als Typ **Integration** hinzufügen:
   `https://github.com/mirkohd1999/Toniebox-via-TeddyCloud-MQTT`
2. **Toniebox via TeddyCloud MQTT** in HACS herunterladen.
3. Home Assistant **neu starten**.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → TeddyCloud Home Assistant** öffnen.
5. **Toniebox automatisch suchen** wählen. Die Toniebox während der laufenden Suche einschalten oder eine Figur aufstellen.
6. Das Feld **MQTT-Präfix** optional ausfüllen (z. B. `teddyCloud`, `meinTeddy`). **Leer = Präfix automatisch erkennen.** Sobald eine Box gefunden wurde, endet die Suche; ohne Treffer nach maximal 25 Sekunden. Alternativ die Box-ID manuell eintragen.

Es ist **kein zweiter MQTT-Broker-Login** nötig. Die Integration nutzt die vorhandene Home-Assistant-MQTT-Verbindung.

## 🖥️ Dashboard-Karten

Nach Installation und Neustart unter **Dashboard → Bearbeiten → Karte hinzufügen → Manuell** eine Karte anlegen.

### Toniebox, Titel und Figur

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
name: Meine Toniebox
mode: player
composition: true
```

### Lautstärkelimits und LED-Helligkeit separat

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
mode: settings
```

### Alles in einer Karte

```yaml
type: custom:teddycloud-homeassistant-card
entity: media_player.meine_toniebox_now_playing
mode: all
```

**Wichtig:** Die `entity`-ID ist ein Beispiel. Deine tatsächliche Media-Player-ID steht unter **Einstellungen → Geräte & Dienste → Entitäten**. Optional `color: '#c991c5'` für die Farbe der stilisierten Box hinzufügen. Im Karteneditor lässt sich die Ansicht ebenfalls wählen.

### Fehler: „Custom element doesn't exist“

Die Kartenressource wurde nicht geladen. Zuerst die Integration per HACS aktualisieren und **Home Assistant neu starten**; danach das Dashboard mit **Strg + F5** neu laden.

Im Dashboard unter **Ressourcen** sollte **genau eine** JavaScript-Modul-Ressource für `/teddycloud-homeassistant/card.js` vorhanden sein, nach aktuellem Stand:

```text
/teddycloud-homeassistant/card.js?v=0.3.0-dev18
```

Die Integration versucht diese Ressource bei Storage-Dashboards automatisch einzutragen. Im YAML-Ressourcenmodus ist eine manuelle Modulregistrierung erforderlich. Falls die Fehlermeldung bleibt, die URL `/teddycloud-homeassistant/card.js` direkt unter deiner Home-Assistant-Adresse öffnen und auf **404** bzw. JavaScript-Fehler prüfen.

## 🧸 Bilder und Laufzeiten

Der Tonie wird zunächst über TeddyCloud-MQTT erkannt (`ContentAudioId`, `ContentTitle`, `Playback`). Die Integration sucht anschließend im Community-Projekt [tonies-json](https://github.com/toniebox-reverse-engineering/tonies-json) über die **exakte Audio-ID** nach Figurendarstellung und Kataloglaufzeit.

- Fehlen Katalogdaten, bleibt das Ersatzbild bzw. „Laufzeit unbekannt“ sichtbar.
- Bild-URLs und Laufzeiten sind **nicht für jeden Tonie garantiert**. Kreativ-Tonies und Sondereditionen können fehlen.
- Der Fortschrittsbalken schätzt die Zeit seit einem Wiedergabeereignis. Kapitelwechsel, Unterbrechungen und Neustarts können die Anzeige verfälschen.
- TeddyCloud kann ein `http://localhost/...`-Cover senden. Dieses verweist auf den TeddyCloud-Server und ist vom Home-Assistant-Browser häufig nicht direkt erreichbar.
- Online-Bilder benötigen einen erreichbaren Bildhost. Der Bildcache liegt unter `/config/www/teddycloud_homeassistant/figures/`.
- Optional lassen sich in den Integrationsoptionen eigene Bildadressen und Laufzeiten über einen JSON-Katalog hinterlegen; für die normale Einrichtung ist das **nicht erforderlich**.

### Diagnose fehlender Bilder oder Laufzeiten

Unter **Entwicklerwerkzeuge → Zustände** die Toniebox-Media-Player-Entität suchen. Nützliche Attribute:

| Attribut | Bedeutung |
| --- | --- |
| `content_audio_id` | Erkannte Tonie-Audio-ID |
| `catalog_status` | `matched`, `audio_id_not_found`, `unavailable` oder `loading` |
| `catalog_match` | Ob Katalogdaten gefunden wurden |
| `cover_url` | Tatsächlich ausgewählte Bild-URL |
| `media_duration` | Laufzeit in Sekunden, wenn vorhanden |
| `duration_source` | Woher die Laufzeit stammt |

Bei `catalog_status: unavailable` zusätzlich **Einstellungen → System → Protokolle** prüfen. Der Katalogabruf kann etwa wegen Netzwerkproblemen, unvollständiger JSON-Antworten oder nicht erreichbarer Ersatzquellen scheitern. **Nicht** auf „Zustand setzen“ klicken, um den Fehler zu beheben.

## 📡 MQTT und Einschränkungen

Die Integration empfängt Status unter `{prefix}/box/{box_id}/+`. Das Präfix ist **frei wählbar** und muss nicht `teddyCloud` heißen. Die Suche wartet auf passende MQTT-Meldungen; wenn deine Box keine Nachrichten sendet und keine retained MQTT-Werte vorhanden sind, kann sie trotz funktionierender Verbindung nicht automatisch gefunden werden.

Lautstärkelimits und LED-Einstellungen verwenden die von TeddyCloud bereitgestellten MQTT-Kommandos. Manche Änderungen werden erst bei einem späteren **Freshness Check** von der Toniebox angewendet. Siehe [TeddyCloud MQTT-Dokumentation](https://github.com/toniebox-reverse-engineering/teddycloud/blob/master/MQTT_CONTROL.md).

## 🛠️ Aktualisieren

**HACS → TeddyCloud Home Assistant → Erneut herunterladen**, Home Assistant neu starten und das Dashboard bei Bedarf hart neu laden. Bei Installation direkt aus `main` handelt es sich weiterhin um einen Entwicklungsstand.

## ❤️ Mithelfen

Fehler und Verbesserungsvorschläge gerne unter [Issues](https://github.com/mirkohd1999/Toniebox-via-TeddyCloud-MQTT/issues) melden. Hilfreich sind Home-Assistant-Version, TeddyCloud-Version, `catalog_status` und eine anonymisierte MQTT-Meldung. **Keine Passwörter, Zertifikate, Zugangstoken oder privaten MQTT-Daten veröffentlichen.**

Projekt inoffiziell; keine Zugehörigkeit zu tonies® oder den Rechteinhabern der Figuren. Bildrechte verbleiben bei den jeweiligen Rechteinhabern.

## Lizenz

[MIT](LICENSE)

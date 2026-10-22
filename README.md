# TeddyCloud Home Assistant 🧸

**Community-Prototyp v0.1.1 für Home Assistant – lokale TeddyCloud-MQTT-Anzeige.**

Diese Integration ergänzt den bereits in Home Assistant konfigurierten MQTT-Broker um eine **lesende Media-Player-Entität pro Toniebox** sowie eine optionale Lovelace-Karte.

## Features

- Mehrere Boxen, jeweils eigener Name, MQTT-Prefix, Box-ID (CN) und Boxfarbe.
- Aktueller `ContentTitle`, `ContentAudioId`, `Playback`-Status, gemeldete Lautstärke und Ladestation.
- Individueller Katalog je Box: `ContentAudioId` → `title`, `cover` und `duration_seconds`; optional Fallback-Cover.
- Dashboard-Karte für Titel, Cover, Farbe und **geschätzten** Wiedergabefortschritt.
- Kein eigener MQTT-Client und keine separaten MQTT-Zugangsdaten: die **bereits konfigurierte Home-Assistant-MQTT-Integration** wird verwendet.
- Keine Cloud-Anmeldung erforderlich.

## Wichtige technische Grenzen

TeddyCloud meldet über MQTT einen Wiedergabestatus (`Playback`: ON/OFF), Titel, Audio-ID und Cover-Entität. **Die tatsächliche Wiedergabeposition und eine garantierte Tracklänge liefert dieses MQTT-Schema nicht.** Fortschritt wird nur ab einem `Playback=ON`- oder neuen Audio-ID-Ereignis anhand der lokalen Uhr **geschätzt**. Bei Pausen, Puffern, Zeitsprüngen, Neustarts oder Kapitelwechseln ohne Audio-ID-Wechsel ist die Position ungenau. Die Leiste trägt deshalb ausdrücklich „geschätzt“. Ohne eigene Laufzeitangabe wird keine Zeit vorgetäuscht.

**Alle jemals veröffentlichten Tonies** gehören **nicht** zum Paket: Katalog, Bildrechte und Audio-ID-Zuordnung müssten aus einer lizenzierten Datenquelle ergänzt werden. Füge eigene Bilder/URLs und Laufzeiten im Katalog hinzu. Das von TeddyCloud per Home-Assistant-MQTT-Discovery veröffentlichte `image`-Entity wird durch diese erste Karten-Version nicht automatisch als Bild übernommen.

TeddyCloud bietet über MQTT **keine echte Play/Pause-Fernsteuerung** der Toniebox 1. Diese Erweiterung zeigt Status an, behauptet aber keine Steuerung. Dokumentation: [TeddyCloud MQTT_CONTROL.md](https://github.com/toniebox-reverse-engineering/teddycloud/blob/master/MQTT_CONTROL.md).

**Hinweis zur Umbenennung:** Die Integrations-Domain wurde von `teddycloud_now_playing` auf `teddycloud_homeassistant` geändert. Wer den früheren Prototyp installiert hat, muss die alte Integration zunächst entfernen und danach die neue hinzufügen. Vorher Einstellungen und JSON-Katalog sichern.

## Installation (Entwicklerversion)

1. **MQTT-Integration** in Home Assistant einrichten, ggf. Mosquitto-Broker verbinden.
2. Den Ordner `custom_components/teddycloud_homeassistant` nach `/config/custom_components/` kopieren.
3. Home Assistant **neu starten**.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → TeddyCloud Home Assistant**.
5. Eine **Box-ID (CN)** aus MQTT-Topic `teddyCloud/box/BOX_ID/Playback` eintragen. Das Prefix ist meist `teddyCloud`. Weitere Boxen als weitere Einträge hinzufügen.
6. Für die Karte `www/teddycloud-homeassistant-card.js` nach `/config/www/` kopieren.
7. **Einstellungen → Dashboards → Ressourcen**: `/local/teddycloud-homeassistant-card.js` als **JavaScript-Modul** hinzufügen. Danach Browser-Cache neu laden.
8. Manuelle Karte nach `examples/dashboard.yaml` hinzufügen. Die tatsächliche Media-Player-Entitäts-ID verwenden.

## Optionen

In **Geräte & Dienste → TeddyCloud Home Assistant → Konfigurieren**:

- `box_color`: sechsstelliger Hexfarbwert (z. B. `#c991c5`).
- `fallback_cover`: URL zu einem Bild (optional; HTTPS oder `/local/...`).
- `catalog`: JSON-Zuordnung von **ContentAudioId** zu Bild, Titel und Dauer, siehe `examples/catalog.json`.

MQTT-Host, Port, TLS und Zugangsdaten werden zentral in **Einstellungen → Geräte & Dienste → MQTT → Neu konfigurieren** eingestellt. Hier absichtlich **kein zweiter Broker-Login**. Die Topic-Prefix- und Box-ID-Einstellungen werden beim Anlegen eines Eintrags festgelegt; zum Ändern in v0.1.0 Eintrag löschen und neu hinzufügen.

## Bekannte Grenzen / Entwicklungsstand

- Alpha/Prototyp: auf einer realen Home-Assistant-Installation **noch nicht getestet**. Bitte zuerst auf einem Testsystem oder mit Backup installieren.
- Nur Live-MQTT-Daten, keine automatische Historie oder robuste Rekonstruktion der Position nach HA-Neustart.
- Der Katalog wird zunächst manuell als JSON gepflegt (nicht als fertiger Figuren-Browser).
- Home Assistants bestehende TeddyCloud-MQTT-Discovery-Geräte bleiben unabhängig bestehen.
- Keine automatische Coverauflösung aus der TeddyCloud-Image-Entität und keine separate Auswahl einer Box-Farbpalette (Hex-Eingabe vorhanden).

## Contributing

Issues und Pull Requests willkommen. Für ein öffentliches Release: Tests mit mehreren TeddyCloud-/HA-Versionen, HACS-Validierung, UI-Optionen und Lizenzprüfung für mögliche Tonie-Cover-Datenbank ergänzen. **Keine privaten Zertifikate, MQTT-Passwörter oder persönlichen MQTT-Logs committen.**

## Lizenz

MIT (siehe LICENSE).

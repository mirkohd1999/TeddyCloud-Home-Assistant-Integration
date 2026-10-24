# TeddyCloud Home Assistant Integration v0.3.2

## Neu: Ohrtasten als eigene Sensoren

- **Großes Ohr (lauter)** und **Kleines Ohr (leiser)** erscheinen als zwei eigenständige Diagnose-Sensoren an jeder eingerichteten Toniebox.
- TeddyCloud-MQTT-Ereignisse `VolUp` und `VolDown` werden ausgewertet. Möglich sind `pressed`, `double-pressed` und `triple-pressed`.
- Jeder Sensor zeigt den letzten erkannten Tastendruck. Die Attribute `last_pressed` (UTC) und `press_count` (seit Sensorstart) werden bei jedem Tastendruck aktualisiert, auch bei wiederholtem gleichen Tastendruck.
- Retained-Nachrichten und unbekannte oder ungültige MQTT-Inhalte werden nicht als neue Tastendrücke gezählt.
- Die Erkennung nutzt die bereits eingerichtete MQTT-Verbindung in Home Assistant. Es werden keine weiteren Zugangsdaten benötigt.
- Automatisierte Tests der MQTT-Ereignisverarbeitung ergänzen die bestehenden HACS-, hassfest- und Paketprüfungen.

## Weiterhin verfügbar

- Toniebox-Erkennung über TeddyCloud MQTT
- Media-Player mit Wiedergabestatus, aktuellem Titel, Figurenbildern und geschätztem Fortschritt
- Aktuelle Lautstärke als lesender Sensor
- Konfiguration von Lautsprecher- und Kopfhörer-Lautstärkelimits sowie LED-Helligkeit
- Die gebündelte Lovelace-Karte mit Player-, Alles- und Einstellungsansicht
- Mehrere Tonieboxen sowie deutsche und englische Übersetzungen

## Wichtig zur Steuerung

Die Ohrtasten-Sensoren **lesen ausschließlich Ereignisse aus**. Sie können die Lautstärke der Toniebox nicht ferngesteuert verändern. TeddyCloud unterstützt dafür nur die Einstellung der maximalen Lautstärkegrenzen; diese Änderungen greifen gegebenenfalls erst beim nächsten Freshness Check.

## Installation / Aktualisierung

Über HACS das Repository `https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration` als benutzerdefinierte **Integration** installieren bzw. nach Veröffentlichung von `v0.3.2` aktualisieren. Anschließend Home Assistant neu starten und bei den Entitäten der Toniebox nach den beiden neuen Diagnose-Sensoren suchen.

Die bisherigen internen Kennungen `teddycloud_homeassistant` und `custom:teddycloud-homeassistant-card` bleiben erhalten. Die neuen Sensoren erfordern eine TeddyCloud-Version, die `VolUp`/`VolDown`-MQTT-Ereignisse veröffentlicht.

*Veröffentlichungshinweis: Die Manifestversion ist vorbereitet. Erst wenn ein GitHub-Release `v0.3.2` auf dem getesteten `main` veröffentlicht wird, ist diese Version als normales HACS-Update verfügbar.*

# TeddyCloud Home Assistant Integration v0.4.0

Dieser stabile Sammelrelease enthält die Dashboard- und Bibliotheksfunktionen der bisherigen 0.3.x-Versionen sowie die abschließenden Korrekturen.

## Tonie-Bibliothek

- Erkannte Tonies dauerhaft sammeln, suchen und als Bilderkacheln anzeigen.
- Nur Home-Assistant-Administratoren können Tonies hinzufügen, Titel/Laufzeit bearbeiten und Bilder ändern oder hochladen. Die Prüfung erfolgt auch serverseitig.
- Alle angemeldeten Nutzer können Tonies ansehen und nach Bestätigung löschen.
- Audio-IDs werden nicht mehr in den Kacheln angezeigt. Beim Bearbeiten stehen sie unter eingeklappten „Technischen Details“.
- Neuer Untertitel: „Deine Tonies – automatisch gesammelt und übersichtlich an einem Ort.“

## Dashboard und Update

- Acht Vorlagen und individuell einstellbare Bausteinbreiten bleiben enthalten.
- Identische Kartendateien für Integration und manuelle Installation.
- Neue Ressource: `/teddycloud-homeassistant/card-v040.js?v=0.4.0`.
- Automatische Migration bekannter Ressourcen in Storage-Dashboards; bisherige Kartenpfade bleiben erreichbar.
- Bestehende Boxen, Entitäten und gespeicherte Bibliotheksdaten werden weiterverwendet.

## Installation über HACS

Repository als **Integration** hinzufügen: https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration

1. In HACS Version **v0.4.0** herunterladen.
2. Home Assistant vollständig neu starten.
3. Dashboard auf jedem verwendeten Gerät neu laden.
4. Bei YAML-verwalteten Ressourcen die neue Adresse als JavaScript-Modul eintragen.

Die Integration ist kein Add-on. Die vorhandene MQTT-Integration und ein TeddyCloud-Server werden benötigt. Play/Pause, aktuelle Lautstärke-Fernsteuerung und verlässliche Akku-Prozentwerte sind weiterhin nicht verfügbar; der Abspielfortschritt ist geschätzt.

## Ältere Releases

Dieser Release benötigt keine Dateien aus älteren GitHub-Releases. Ältere Release-Einträge können nach erfolgreichem Update entfernt werden; ihre Downloadlinks und die jeweilige Rückkehrmöglichkeit über HACS entfallen dann. Die Git-Tags und mindestens einen bekannten funktionierenden Rückfallrelease behalten. Bereits veröffentlichte Tags nicht verschieben.

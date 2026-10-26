# TeddyCloud Home Assistant Integration v0.5.0

## Bibliothek

- Zuletzt erkannter Tonie je Box mit Rahmen in der konfigurierten Boxfarbe; mehrere Boxen können als mehrere Farbringe erscheinen.
- Diese Zuordnung bleibt über Neustarts erhalten und wird ab der nächsten neuen Erkennung aufgebaut.
- Häufigste Tonies zuerst: neue Erkennungen/Aufstellungen werden gezählt, keine vollständig gehörten Durchläufe. Retained-Meldungen erhöhen den Zähler nicht.
- Mehrere Audio-IDs desselben Kataloginhalts werden als eine Karte dargestellt. Zähler werden summiert, eigene Titel/Bilder/Laufzeiten bevorzugt. Rohdaten bleiben erhalten; bei widersprüchlichen eigenen Angaben wird pro Feld ein vorhandener Wert angezeigt, die anderen bleiben intern erhalten.
- Bearbeiten und Löschen wirken auf die zusammengefassten Einträge. Unterschiedliche Folgen werden nicht anhand ähnlicher Titel zusammengeführt.
- Vorhandene Einträge werden beim Start im Hintergrund mit dem Katalog abgeglichen. Die automatische Zuordnung benötigt einen erreichbaren Katalog und dort eindeutig gemeinsam aufgeführte Audio-IDs.

## Offline-Anzeige

- Nach 5 Minuten ohne frische MQTT-Nachricht wird der Media-Player nicht verfügbar; die eigene Dashboard-Karte zeigt „Toniebox offline“.
- Wartezeit je Box in den Integrationsoptionen einstellbar: 1–120 Minuten.
- Neue Nachrichten stellen den Online-Status wieder her. Retained-Nachrichten verlängern die Frist nicht.
- Die Anzeige ist eine Einschätzung anhand ausbleibender Meldungen, kein sicherer Nachweis einer ausgeschalteten Box.

## Aktualisieren

In HACS v0.5.0 herunterladen, Home Assistant neu starten und das Dashboard neu laden. Für YAML-Ressourcen: `/teddycloud-homeassistant/card-v050.js?v=0.5.0` als JavaScript-Modul eintragen. Storage-Ressourcen werden automatisch aktualisiert.

Admin-Rechte zum Bearbeiten, Löschen für alle angemeldeten Nutzer und der System-Sound-Filter bleiben enthalten. Automatisierte Tests decken Gruppierung, Erhalt eigener Angaben, Farben, Sortierung, Offline-Frist, Rückkehr online und die Dashboard-Ansichten ab. Ein Praxistest auf der eigenen Toniebox bleibt erforderlich.

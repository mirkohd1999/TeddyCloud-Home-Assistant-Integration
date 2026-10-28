# v0.5.5

## Zuverlässigere Zuordnung beim Toniewechsel

- Abnehmen leert die aktive Titel-/Bildzuordnung und beendet ausstehende Erkennung der vorherigen Figur. Gespeicherte Bibliothekseinträge bleiben erhalten.
- Frische MQTT-Titel und Bilder werden eine Sekunde gesammelt. Kurze Umordnungen vor/nach der Audio-ID werden berücksichtigt; unsichere alte Daten werden nicht auf neue IDs übertragen.
- Bereits bekannte Titel und Bilder werden durch MQTT nicht überschrieben. Eindeutige Katalogtreffer und eigene Änderungen haben Vorrang.
- Titel/Bilder, die schon einer anderen, nicht katalogzugeordneten Audio-ID gehören, werden nicht ungeprüft auf neue Einträge kopiert. Gleicher Titel ist kein Grund zum automatischen Zusammenführen.
- Schnelles Abnehmen und erneutes Aufstellen wird in der richtigen Reihenfolge gezählt. Wiederholte identische Audio-ID-Meldungen erzeugen keinen zusätzlichen Eintrag.
- Ausstehende Metadaten-Schreibvorgänge und verspätete Katalogantworten können die nächste Figur nicht verändern.

## Update

In HACS aktualisieren und Home Assistant neu starten. Den betroffenen Tonie danach neu aufstellen. Vorhandene Einträge werden nicht automatisch gelöscht oder nach Titeln zusammengeführt. Der Katalogabgleich beim Start kann bekannte IDs korrigieren.

## Grenzen

MQTT-Titel-/Bildmeldungen enthalten keine eigene Audio-ID. Bei fehlender oder widersprüchlicher Zuordnung bleibt ein Eintrag lieber ohne erkannte Metadaten, statt einen fremden Titel zu übernehmen. Gespeicherte Retained-Titel werden nicht neu zugeordnet. Ein Katalogtreffer oder eine eindeutige neue Meldungsfolge ist dann erforderlich.

## Prüfung

53 Python-Tests und bestehende Dashboard-/Sprachtests bestanden. Neue Tests decken Rocky → Bibi → Rocky mit ID zuerst, Titel zuerst, direktem Wechsel, Abnehmen, fehlendem Titel, alten Bildern, verspäteten Katalogantworten, blockiertem Speicher und schneller erneuter Aufstellung ab. Tests verwenden simulierte MQTT-Meldungen und den echten Player-/Bibliothekscode; kein Test an einer physischen Toniebox.

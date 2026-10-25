# TeddyCloud Home Assistant Integration v0.3.3

## Neu: Mehr Dashboard-Ansichten und visueller Kartenbaukasten

- **Fünf neue Kartenansichten**: platzsparende Kompaktansicht, großes Tonie-Bild, Status-Kacheln, Dashboard-Kacheln und vollständig frei zusammenstellbare Karte.
- **Baukasten im visuellen Karteneditor:** Bild, Titel, Wiedergabe, Ladestation, Laufzeit/Fortschritt, aktuelle Lautstärke, Lautsprecherlimit, Kopfhörerlimit, LED und Ohrtasten einzeln ein- oder ausblenden.
- **Sortierbare Bausteine:** Reihenfolge bequem mit Pfeilen anpassen.
- **Freie Anordnung:** Bausteine untereinander oder im Kachelraster mit 1–3 Spalten. Auf schmalen Displays wechselt die Ansicht zu einer Spalte.
- **Ohrtasten-Status im Dashboard:** Letzte Betätigung und Zähler beider Ohren, sofern die Sensoren aus v0.3.2 verfügbar sind.
- **Bestehende Karten bleiben kompatibel:** die bisherigen Modi `all`, `player` und `settings` wurden beibehalten.
- Automatisierte JavaScript-Tests für die Ansichten und die Zusammenstellung ergänzt.

## Installation / Aktualisierung

Die Integration über HACS aus dem Repository `https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration` aktualisieren, Home Assistant neu starten und das Dashboard bearbeiten. Unter „Kartenansicht“ stehen die neuen Layouts zur Auswahl.

Die Dashboard-Ressource wird automatisch mit Versionsparameter `?v=0.3.3` registriert (bei Storage-Dashboards). Falls die Anzeige nach einem Update unverändert aussieht, Browsercache leeren bzw. die Dashboard-Seite neu laden.

Weitere Infos und YAML-Beispiele stehen in der README im Abschnitt „Dashboard-Baukasten und Kartenvarianten“.

## Unveränderte Einschränkungen

Echte Play/Pause-Fernsteuerung, aktuelle Lautstärke fernsteuern, verlässlicher Akkustand und echte Abspielposition werden von der MQTT-Anbindung nicht bereitgestellt. Die Fortschrittsanzeige ist eine Schätzung. Die Ohr-Tastendrücke sind reine Lese-Ereignisse.

**Hinweis:** Diese Release Notes sind vorbereitet. Für ein HACS-Update muss nach erfolgreich bestandenen Prüfungen ein GitHub-Release `v0.3.3` mit Tag auf dem aktuellen `main` veröffentlicht werden.

# v0.5.1

## Offline-Erkennung mit Tonie-Laufzeit

- LastSeen bestimmt die letzte tatsächliche Box-Aktivität. Wiederholte alte MQTT-Statuswerte verlängern die Offline-Frist nicht mehr.
- Neu erkannte Wiedergabe mit bekannter Laufzeit bleibt bis zum geschätzten Ende plus zwei Minuten online. Gleiche Playback-ON-Meldungen starten diesen Schutz nicht neu.
- Stop oder Abnehmen der Figur beendet den Laufzeitschutz und startet die konfigurierte normale Wartezeit (standardmäßig fünf Minuten).
- Ohne gültiges LastSeen bleibt der Empfang frischer MQTT-Meldungen die Ersatzquelle; ohne Laufzeit gilt die normale Aktivitätsfrist.
- Nachträglich geladene oder bearbeitete Laufzeiten aktualisieren die Frist anhand des ursprünglichen Starts.
- Neue Diagnoseattribute: availability_source und playback_protection_remaining.

## Update

In HACS aktualisieren und Home Assistant neu starten. Die vorhandene Dashboard-Karte kann weiterverwendet werden.

## Grenzen

Die Laufzeit ist eine Schätzung: Ausschalten während der Wiedergabe wird gegebenenfalls erst nach dem geschätzten Ende erkannt. Gespeicherte Playback-Meldungen nach einem HA-Neustart erzeugen keinen neuen Laufzeitschutz. Streams, unbekannte Laufzeiten und Titelsprünge sind nicht zuverlässig über die Gesamtlaufzeit abbildbar.

## Prüfung

Python-Regressionsprüfungen für alte LastSeen-Werte, wiederholte Statusmeldungen, lange Wiedergabe, Ablauf, Figur entfernt, Stop/Neustart, unbekannte und nachgeladene Laufzeiten, Zeitstempel sowie Timer und Entladen. Zusätzlich vorhandene Bibliotheks-, Rechte- und JavaScript-Tests. Kein Test an einer physischen Toniebox.

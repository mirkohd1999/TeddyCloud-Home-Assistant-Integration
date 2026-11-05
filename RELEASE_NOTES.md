# v0.6.6

- Der Teddy erscheint vor der Box, wenn sie offline ist oder keine Figur aufliegt. Unbekannte Figuren werden weiterhin durch das kleine Fragezeichen dargestellt.
- Die bestehenden Ohrtasten-Sensoren zeigen einen kurzen Tastendruck und wechseln nach einer Sekunde wieder auf released. Zähler, Zeitstempel und Doppel-/Dreifachklick-Anzeigen entfallen. Es werden keine Lichtautomationen eingerichtet.
- Bestehende Automationen, die press_count, last_pressed oder Mehrfachklick-Zustände verwenden, müssen angepasst werden. Die Entitäts-IDs bleiben erhalten.

In HACS aktualisieren und Home Assistant neu starten.

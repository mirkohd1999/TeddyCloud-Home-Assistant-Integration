# v0.6.1

- Das gelb-weiße Fragezeichen für unbekannte Figuren wird direkt über Home Assistant geladen.
- Pro Box zeigt ein Binärsensor „Tonie aufgelegt“ an, ob eine Figur erkannt wurde. Beim Abnehmen oder nach Ablauf der geschätzten Wiedergabezeit schaltet er aus.
- Der Sensor „Tonie-Farbe“ ermittelt die dominante sichtbare Farbe des Figurenbilds. Er liefert einen Hexwert und das Attribut `rgb_color` für Lichtautomationen.
- Administratoren können die automatisch ermittelte Farbe pro Figur in der Tonie-Bibliothek überschreiben.

In HACS aktualisieren und Home Assistant neu starten.

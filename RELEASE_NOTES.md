# v0.6.2

- Das integrierte Fragezeichen wird jetzt auch in der Bibliothek angezeigt. Die Player-Karte akzeptiert den lokalen Bildpfad und vermeidet leere Cover-Adressen.
- Administratoren können doppelte Figuren über „Bearbeiten → Als Duplikat zusammenführen mit“ verknüpfen. Die Verknüpfung bleibt gespeichert und gilt auch für Titel, Bild und Laufzeit im Player.
- 84 Python-Tests und die Dashboard-, Sprach-, Rollen-, Hörproben-, Update- und Signaturprüfungen bestanden.

- Das gelb-weiße Fragezeichen für unbekannte Figuren wird direkt über Home Assistant geladen.
- Pro Box zeigt ein Binärsensor „Tonie aufgelegt“ an, ob eine Figur erkannt wurde. Beim Abnehmen oder nach Ablauf der geschätzten Wiedergabezeit schaltet er aus.
- Der Sensor „Tonie-Farbe“ ermittelt die dominante sichtbare Farbe des Figurenbilds. Er liefert einen Hexwert und das Attribut `rgb_color` für Lichtautomationen.
- Administratoren können die automatisch ermittelte Farbe pro Figur in der Tonie-Bibliothek überschreiben.

In HACS aktualisieren und Home Assistant neu starten.

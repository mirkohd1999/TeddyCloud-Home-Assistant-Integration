# v0.6.8

- Die Lichtsteuerung hat eine eigene Dashboard-Karte „TeddyCloud Licht“ mit Ein-/Aus-Button, Dimmer und Automatikschalter. Sie wird nicht mehr in Toniebox-Karten eingeblendet.
- Die Farberkennung für das Licht blendet einfarbige Bildhintergründe aus und bevorzugt deutlich farbige Teile der Figur gegenüber grauen Flächen und Schatten. Beim geprüften Benjamin-Bild wird so Rot (#CF3326) statt Grau als Lampenfarbe verwendet.
- Der vorhandene Tonie-Farbe-Sensor und sein rgb_color-Attribut verwenden die verbesserte Farberkennung ebenfalls. Sensor und Licht erhalten damit dieselbe Farbe; Entitäts-IDs bleiben erhalten.
- Die Lichtkarte zeigt die erkannte Lichtfarbe, einen klaren Automatik-Status und Hinweise auf fehlende Farbdaten beziehungsweise Lampen ohne Farbfunktion. Für automatische Farbwechsel muss „Automatik einschalten“ aktiviert sein.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden. Unter Dashboard bearbeiten → Karte hinzufügen → TeddyCloud Licht eine separate Lichtkarte hinzufügen und die Toniebox auswählen. Die Lampenauswahl bleibt unter Einstellungen → Geräte & Dienste → TeddyCloud → Konfigurieren → Licht.

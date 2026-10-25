# TeddyCloud Home Assistant Integration v0.3.5

## Neu: Jede Dashboard-Kachel einzeln in der Breite anpassen

- **Bildüberschrift entfernt:** Der Text „Tonie-Bild oder Toniebox“ steht nicht mehr störend neben dem Tonie-Bild. Das betrifft die Ansichten „Großes Bild“, „Kacheln“ und „Selbst gestalten“.
- **Einstellbare Breite pro Baustein:** Im visuellen Editor unter **Selbst gestalten → Anordnung: Kacheln** kann jeder aktivierte Baustein seine eigene Breite erhalten, unabhängig von den anderen.
- Wähle die gewünschte Breite als **1 Spalte**, **2 Spalten** oder **Volle Breite**, passend zur Zahl der Spalten (1–3).
- **Individuelle Layouts:** Das Tonie-Bild kann z. B. zwei Spalten belegen, während Titel, Status und Steuerungen daneben oder darunter angeordnet sind.
- **Bestehende Karten bleiben kompatibel:** Ohne individuelle Breitenangaben verhalten sich Bausteine wie bisher. Gespeicherte Breiten bleiben bei Änderungen der Anordnung erhalten.
- **Responsive Darstellung:** Auf kleinen Displays erscheinen Kacheln lesbar untereinander.
- **Fehlerbehebung:** Der Bildbaustein und sein inneres Bild verwenden nun unterschiedliche CSS-Klassen. So schiebt die Überschrift das Bild nicht mehr an den Rand.
- **Neue Kartendatei:** `/teddycloud-homeassistant/card-v035.js?v=0.3.5` für eine zuverlässige Browser-Aktualisierung.

## Aktualisierung

1. In HACS **TeddyCloud Home Assistant Integration v0.3.5** aktualisieren.
2. Home Assistant neu starten.
3. Dashboard bearbeiten → TeddyCloud-Karte → **Selbst gestalten** → **Kacheln**.
4. Spaltenzahl wählen und die **Breite direkt neben jedem Baustein** ändern, dann speichern.

Für automatisch verwaltete Dashboard-Ressourcen wird die neue Kartendatei selbst registriert. Es ist kein YAML und keine manuelle Ressourcen-URL notwendig.

## Unverändert

Die bisherigen acht Kartenansichten, Tonie-Bilder, Lautstärkelimits, LED-Steuerung und Ohrtasten-Sensoren bleiben erhalten. Die aktuelle Lautstärke und Play/Pause sind weiterhin nicht fernsteuerbar.

# v0.6.7

- In den Integrationseinstellungen können pro Toniebox eine oder mehrere Zimmerlampen ausgewählt werden.
- Das Dashboard bietet direkt einen Licht-Ein-/Aus-Button und einen Helligkeitsregler. Über „Selbst gestalten“ ist Zimmerlicht auch als eigener Baustein auswählbar.
- Die optionale Tonie-Lichtautomatik verwendet die bestehenden Sensoren „Tonie-Farbe“ und „Tonie aufgelegt“. Das Licht übernimmt die Figurenfarbe und geht beim Abnehmen, am geschätzten Laufzeitende oder bei offline gemeldeter Box aus. Farbwechsel behalten die Lampenhelligkeit bei.
- Die Automatik ist zunächst ausgeschaltet und kann am Gerät oder im Dashboard aktiviert werden. Der Schalterzustand bleibt nach Neustarts erhalten.
- Farblose Figuren ändern die bisherige Lichtfarbe nicht. Lampen ohne Farbfunktion werden nur ein-/ausgeschaltet; der Dimmer steuert ausschließlich dimmbare Lampen.

In HACS aktualisieren und Home Assistant neu starten. Danach unter Einstellungen → Geräte & Dienste → TeddyCloud → Konfigurieren das Zimmerlicht auswählen. Im Dashboard erscheinen die Lichtsteuerung und der Schalter für die Tonie-Lichtautomatik automatisch in den Standardansichten.

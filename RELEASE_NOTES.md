# v0.6.9

- Figurenerkennung gegen schnelle Wechsel, verspätete Antworten, zwei gleichzeitig aktive Boxen und Neustarts mit gespeicherten MQTT-Meldungen abgesichert. Ein fehlgeschlagener Speichervorgang blockiert nachfolgende Figuren nicht mehr; überholte Bildabfragen werden nach Wartephasen erneut geprüft.
- Neuer Verbindungscheck unter Konfigurieren → Verbindung prüfen: MQTT, Boxaktivität, Katalog und gespeichertes Bild werden getrennt angezeigt. Die normalen Optionen liegen unter Toniebox und Licht einstellen.
- Native Home-Assistant-Diagnose zum Herunterladen, ohne Namen, Audio-IDs, URLs, MQTT-Topics oder Zugangsdaten.
- Administratoren können die Bibliothek samt eigenen Angaben, gespeicherten Bildern und bestätigten Audio-ID-Zuordnungen als ZIP exportieren und importieren. Der Import zeigt zuerst eine Vorschau und behält vorhandene Angaben standardmäßig bei. Überschreiben erfordert eine ausdrückliche Auswahl.
- ZIP-Dateien und Bilddaten werden vor dem Import begrenzt und geprüft. Bei zwischenzeitlichen Bibliotheksänderungen muss die Vorschau erneuert werden. Bilder bleiben privat; das neue Bibliotheksabbild wird erst nach erfolgreichem Speichern veröffentlicht. Wiederholte Importe verdoppeln keine Zähler.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden. Sicherung und Import befinden sich unten in der Tonie-Bibliothekskarte im Bereich Bibliothek sichern und wiederherstellen und sind nur für Administratoren sichtbar.

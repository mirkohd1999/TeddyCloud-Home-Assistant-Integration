# TeddyCloud Home Assistant Integration v0.3.1

## Veröffentlichung

Diese Version bereitet die Integration auf die Aufnahme in den HACS-Katalog und den zukünftigen Home-Assistant-Marketplace vor. Sie behebt insbesondere die bislang unterschiedliche Versionsnummer zwischen GitHub-Release und Integrationsmanifest.

### Funktionen

- Toniebox automatisch über TeddyCloud-MQTT erkennen oder manuell einrichten
- Frei wählbares MQTT-Präfix und mehrere Tonieboxen
- Toniebox-Farbe in den Integrationsoptionen auswählen
- Wiedergabestatus, Titel, Audio-ID und Ladestationsstatus anzeigen
- Figurenbilder anhand der Audio-ID aus dem Community-Katalog suchen und lokal zwischenspeichern
- Laufzeit aus Katalogdaten anzeigen und den Wiedergabefortschritt schätzen
- Aktuelle Lautstärke anzeigen (nur lesend)
- Lautsprecher-/Kopfhörerlimits und LED-Helligkeit über MQTT ändern
- Eigene Lovelace-Karte mit `player`, `settings` und `all` sowie deutschem Karteneditor
- Automatische Kartenressourcen-Registrierung (bei Storage-Dashboards)
- Aufräumen integrationsinterner Bilder und eindeutig eigener Ressourcen beim Entfernen der letzten Box

### Neu für HACS / Marketplace

- Manifestversion und Lovelace-Ressourcenversion auf `0.3.1` abgestimmt
- HACS- und Hassfest-Validierung mit GitHub Actions hinzugefügt
- Automatisierte Python-, JavaScript- und JSON-Paketprüfungen
- GitHub-Maintainer als `codeowners` eingetragen (die optionale Marketplace-Kategorie wird nach Aktualisierung der Hassfest-Prüfung ergänzt)
- Englische UI-Übersetzung zusätzlich zur deutschen Übersetzung
- README und Projektbranding unter **TeddyCloud Home Assistant Integration**

### Installation

1. In HACS unter **Benutzerdefinierte Repositories** die Adresse `https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration` als **Integration** hinzufügen.
2. Integration herunterladen und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration hinzufügen und die Toniebox per MQTT erkennen lassen.
4. Die Dashboard-Karte wie in der [README](README.md) einrichten.

Bereits installierte Systeme können die Integration über HACS aktualisieren. Die internen Kennungen `teddycloud_homeassistant` und `custom:teddycloud-homeassistant-card` bleiben unverändert.

### Bekannte Einschränkungen

- Es wird keine echte Wiedergabeposition von der Toniebox geliefert. Der Fortschritt ist eine Schätzung.
- Die aktuelle Lautstärke kann nicht ferngesteuert werden. Einstellbar sind nur die Limits und LED-Helligkeit.
- Kein verlässlicher Akku-Prozentwert und keine Play/Pause-Fernsteuerung.
- Figurenbilder und Laufzeiten hängen vom externen Katalog ab; einzelne Tonies können fehlen.
- MQTT-Kommandos können erst beim nächsten Freshness Check wirksam werden.
- Manuell eingerichtete Lovelace-Karten und Ressourcen werden beim Entfernen nicht gelöscht.

**Hinweis:** Diese Datei ist der vorbereitete Release-Text. Erst ein echter GitHub-Release mit dem Tag `v0.3.1`, der nach erfolgreichen Prüfungen auf dem aktuellen `main` erstellt wird, stellt diese Version für HACS bereit.

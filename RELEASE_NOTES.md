# v0.6.0

## HACS-Review: Dateizugriffe und geschützte Bilder

- Die Artwork-Suche in MQTT-Callbacks, Entitäts-Properties und Statusattributen verwendet ausschließlich einen Speicherindex. Scans, Validierung, Lesen, Schreiben, Migration und Löschen von Bildern laufen über `hass.async_add_executor_job`.
- Auch die Berechnung der JavaScript-Dateikennung wurde aus dem Modulimport in den Executor verschoben.
- Figurenarchiv und Dashboard-Uploads werden unter `/config/.storage/teddycloud_homeassistant/images/` gespeichert. Der eigene `HomeAssistantView` unter `/api/teddycloud_homeassistant/images/` verlangt Authentifizierung; Dateien werden nicht als anonyme `/local/`-Bilder veröffentlicht.
- Bibliothek und Player verwenden `auth/sign_path` über die jeweilige angemeldete Verbindung. Fünf Minuten gültige Bildpfade werden vor Ablauf erneuert und bleiben ausschließlich im Arbeitsspeicher des Clients. Ein neuer Serverlauf verwirft alte Signaturen vor dem nächsten Bildabruf.
- Vorhandene integrationsinterne Bilder werden beim Start aus `www` in den privaten Bereich verschoben. Bibliotheksverweise werden aktualisiert; eigene Angaben, Zähler und Zuordnungen bleiben erhalten. Konfliktkopien werden privat gesichert. Fremde `/local/`-Dateien werden nicht verändert.

## Vollständige Entfernung durch den Administrator

- Beim Entfernen der letzten konfigurierten TeddyCloud-Box aus Home Assistant werden Bibliotheksdaten, eigene Uploads, Figurenarchiv, private Migrationssicherungen und integrationsinterne Ressourcen-Metadaten gelöscht. TeddyCloud-Kartenressourcen im Storage-Modus werden entfernt.
- Hintergrundabgleich und Downloads werden vorher beendet. Ein abgebrochener Executor-Schreibvorgang muss fertig sein, bevor die Bereinigung startet; verspätete Beobachtungen und Uploads können die gelöschten Daten nicht wieder anlegen.
- Solange eine andere Box eingerichtet bleibt, werden die gemeinsamen Daten behalten. Normale Updates, Neuladen und Neustarts löschen nichts.
- Zur vollständigen Deinstallation zuerst die Integration unter Geräte & Dienste entfernen, danach in HACS deinstallieren. Eigene Dashboard-Konfigurationen und manuelle YAML-Ressourcen werden nicht umgeschrieben; fremde Dateien und Ressourcen bleiben erhalten.

## Update

In HACS auf **v0.6.0** aktualisieren und Home Assistant neu starten. Die Migration läuft vor der Einrichtung der Bibliothek und der Player. Die Dashboard-Ressource wird automatisch auf `/teddycloud-homeassistant/card-v060.js` mit Versions- und Dateikennung aktualisiert.

## Prüfung

83 Python-Tests sowie Dashboard-, Rollen-, Sprach-, Audio-, Karten-Update- und neue Signatur-Tests bestanden. Die Tests erzwingen Dateizugriffe außerhalb des Event-Loop-Threads und prüfen MQTT/Bild-Properties, privaten Upload, Bildmigration, Konflikte, ungültige Pfade, Symlinks, Signaturerneuerung, Benutzerwechsel, Deinstallation mehrerer Boxen und einen abgebrochenen Schreibvorgang während der Bereinigung.

Ein HTTP-Test verwendet den unveränderten Home-Assistant-Request-Wrapper als Vertragsfixture: anonym 401 ohne Dateizugriff, authentifiziert 200, unbekannte Datei 404. Die Kryptografie von `auth/sign_path` bleibt bei Home Assistant Core; Frontend-Tests verwenden die Schnittstelle mit einem Testobjekt. Kein direkter Test auf der Home-Assistant-Installation des Nutzers.

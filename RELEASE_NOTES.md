# TeddyCloud Home Assistant Integration v0.3.0 beta – Release Notes

**Status:** Beta-Kandidat auf Basis des Entwicklungsstands `0.3.0-dev18`.

## Highlights

- Automatische Toniebox-Erkennung über MQTT, unabhängig vom gewählten Präfix; optional gezielte Präfix-Suche
- Deutsche Einrichtungsoberfläche mit sichtbaren Suchhinweisen; Suche endet beim ersten gefundenen Gerät
- Lovelace-Karte mit frei wählbaren Modi `all`, `player` und `settings`
- Figur, Titel und Wiedergabestatus; Figurenbilder anhand exakter Audio-ID aus dem Online-Katalog, sofern verfügbar
- Geschätzte Wiedergabezeit mithilfe verfügbarer Kataloglaufzeiten (keine echte Abspielposition)
- Read-only Anzeige der aktuellen Lautstärke in Prozent
- Einstellbare Lautsprecher-/Kopfhörerlimits und LED-Helligkeit
- Ladestationsstatus ohne irreführende Akku-Prozentwerte
- Verbesserte Katalog-Fallbacks, lokale Bilder und Diagnoseattribute
- Automatische Kartenressourcen-Registrierung mit aktualisierter Browsercache-Version

## Installation und Aktualisierung

1. HACS → Benutzerdefinierte Repositories: `https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration` als **Integration** hinzufügen (falls noch nicht installiert).
2. Integration herunterladen bzw. erneut herunterladen.
3. Home Assistant neu starten und im Dashboard ggf. **Strg + F5** drücken.
4. Integration hinzufügen, Toniebox suchen und Dashboard-Karte konfigurieren; YAML-Beispiele stehen in der README.

## Bekannte Einschränkungen

- Community-Beta: nicht alle Home-Assistant-/TeddyCloud-Konfigurationen sind getestet.
- Katalogdownload kann trotz Fallbacks scheitern; `catalog_status` und Home-Assistant-Protokolle helfen bei der Fehlersuche.
- Exakte Laufzeit und authentische freigestellte Figurenbilder stehen nicht für jeden Tonie zur Verfügung.
- Der Fortschritt ist eine Schätzung, keine verlässliche echte Wiedergabeposition.
- Keine echte Play/Pause-Fernsteuerung oder verlässliche Akku-Prozentanzeige.
- Kartenressource ggf. manuell im Dashboard registrieren, wenn der automatische Eintrag nicht funktioniert.

## Hinweis zur Veröffentlichung

Diese Datei enthält den Text für die GitHub-Release-Seite. Der GitHub-Release-Eintrag und das Git-Tag sind **nicht** allein durch diese Datei erstellt. Für ein öffentliches Release in GitHub unter **Releases → Draft a new release** ein Tag `v0.3.0-beta.1` vom aktuellen `main` wählen und diese Release-Notizen verwenden.

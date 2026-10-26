# HACS-Veröffentlichung und Release-Pflege

Projekt: **TeddyCloud Home Assistant Integration**  
Repository: https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration  
Stabiler Sammelrelease: **v0.5.3** (Manifest **0.5.3**)  
Kategorie: **Integration**, kein Add-on und kein separates Dashboard-Repository.

## Veröffentlichung

1. Änderungen auf `main` übernehmen.
2. Alle Jobs von **Validate HACS integration** müssen erfolgreich sein: HACS, Hassfest und Paket-/Regressionstests.
3. **Publish stable HACS release** veröffentlicht anschließend automatisch den exakt geprüften Commit. Der Workflow erstellt einen regulären Release mit Tag aus der Manifestversion, Release-Text aus `RELEASE_NOTES.md` und Markierung als neuester Release.
4. Bestehende Releases und Tags werden nicht überschrieben. Bei einem bereits vorhandenen Tag ohne Release stoppt der Workflow zur manuellen Prüfung.
5. Auf GitHub kontrollieren: Release nicht als Entwurf/Vorabversion, Version stimmt mit dem Manifest am Tag überein.
6. In einer vorhandenen Home-Assistant-Installation über HACS aktualisieren, neu starten und alle Dashboard-Clients neu laden. Zusätzlich eine Erstinstallation prüfen.

HACS lädt die Integration aus `custom_components/teddycloud_homeassistant/` am Release-Tag. Alle Laufzeitdateien einschließlich Karte, Übersetzungen und Branding liegen dort. Ein zusätzliches ZIP-Asset ist nicht erforderlich; `zip_release` ist nicht aktiviert.

## Abnahme auf Home Assistant

- MQTT-Boxerkennung, Titel, Bild und Einstellungen prüfen.
- Bibliothek mit Admin und normalem Nutzer öffnen: Nur Admin sieht Hinzufügen/Bearbeiten; beide können nach Bestätigung löschen.
- Kein sichtbarer Audio-ID-Text in Tonie-Kacheln; technische Details im Admin-Editor einklappbar.
- Bibliotheksdaten und Entitäts-IDs bleiben beim Update erhalten.
- Neue Ressource `/teddycloud-homeassistant/card-v050.js?v=0.5.3` lädt auf allen Clients.

Automatisierte Tests ersetzen diesen Praxistest nicht.

## Ältere Releases aufräumen

Erst nach erfolgreichem Update auf v0.5.3:

- v0.5.3 als neuesten Release behalten.
- Mindestens einen selbst geprüften vorherigen Release als Rückfallversion behalten.
- Weitere ältere Release-Einträge können gelöscht werden. Ihre Links/Assets und Auswahlmöglichkeiten in HACS entfallen. Installierte Dateien werden dadurch nicht vom Home-Assistant-System entfernt.
- Git-Tags und Commit-Historie behalten; veröffentlichte Tags niemals auf neue Commits verschieben.
- Keine automatische Löschung: Die Auswahl der alten Releases bleibt beim Maintainer.

## Aufnahme in den HACS-Standardkatalog

Die Nutzung als benutzerdefiniertes Repository ist von der Aufnahme in den Standardkatalog unabhängig. Für den Standardkatalog müssen die aktuellen HACS-Anforderungen erfüllt und eine Einreichung akzeptiert werden. Dieser Release allein bedeutet keine Katalogaufnahme.

- Öffentliche Repository-Beschreibung, Topics, README, Lizenz und Issues prüfen.
- HACS- und Hassfest-Prüfungen ohne ignorierte Fehler bestehen lassen.
- Aktuelle Einreichungsanleitung: https://www.hacs.xyz/docs/publish/include/
- Integrationsanforderungen: https://www.hacs.xyz/docs/publish/integration/
- Allgemeine Anforderungen: https://www.hacs.xyz/docs/publish/start/

## Zukünftige Releases

Manifestversion, `CARD_VERSION`, neue Karten-URL, Kompatibilitätspfade sowie README und Release-Notes gemeinsam aktualisieren. Die zwei Kartendateien müssen identisch bleiben. Der Publish-Workflow verwendet die Manifestversion; kein weiterer versionsspezifischer Workflow ist nötig.

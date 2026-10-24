# HACS-Veröffentlichung – Checkliste

**Projekt:** TeddyCloud Home Assistant Integration  
**Repository:** https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration  
**Kategorie:** Integration (nicht Home-Assistant-Add-on und nicht separates Dashboard-Plugin)  
**Nächster Release:** `v0.3.1` (Manifest: `0.3.1`)

## 1. GitHub-Repository vervollständigen

Auf der Repository-Startseite neben **About** auf das Zahnrad klicken:

- **Description:** `Toniebox-Status, Figurenbilder und Einstellungen über TeddyCloud MQTT in Home Assistant.`
- **Topics:** `home-assistant`, `hacs`, `teddycloud`, `toniebox`, `mqtt`, `home-assistant-integration`
- **Website:** optional den README-Link bzw. die Projekt-URL
- **Issues** aktiviert lassen

Die Kurzbeschreibung und Topics werden in den GitHub-Repository-Einstellungen gepflegt, **nicht** in `hacs.json`.

## 2. Automatische Prüfungen

Unter **Actions** müssen die Jobs aus `.github/workflows/validate.yml` erfolgreich sein:

- **HACS validation** (`hacs/action@main`, `category: integration`) — für die Aufnahme in den Katalog ohne Fehlermeldungen und ohne ignorierte Fehler
- **Home Assistant hassfest** (`home-assistant/actions/hassfest@master`)
- **Syntax and packaging checks** (Python, JavaScript, Sprachdateien, Paketdaten)

Ein roter Job ist ein Blocker für die Einreichung. Die Tests ersetzen keine praktische Installation in Home Assistant mit TeddyCloud und MQTT.

## 3. Version v0.3.1 als GitHub-Release veröffentlichen

**Wichtig:** `v0.3.0` existiert bereits, zeigt aber auf den älteren Entwicklungsstand mit Manifestversion `0.3.0-dev31`. Diesen alten Tag bitte nicht nachträglich verschieben.

1. Erst nach erfolgreichen GitHub-Actions auf dem aktualisierten `main` öffnen:
   https://github.com/mirkohd1999/TeddyCloud-Home-Assistant-Integration/releases/new
2. **Choose a tag:** `v0.3.1` (neuen Tag von `main` erstellen)
3. **Release title:** `TeddyCloud Home Assistant Integration v0.3.1`
4. **Description:** Inhalt aus [RELEASE_NOTES.md](RELEASE_NOTES.md) einfügen; die abschließende Erklärung, dass der Release noch nicht veröffentlicht sei, weglassen
5. **Set as latest release:** aktivieren
6. **Set as a pre-release:** nicht aktivieren, falls die Integration praktisch getestet wurde
7. **Publish release** anklicken

Danach prüfen, ob `v0.3.1` wirklich auf den Commit mit `manifest.json: "version": "0.3.1"` zeigt.

## 4. In den offiziellen HACS-Katalog aufnehmen lassen

Das Repository ist schon vorher als **benutzerdefiniertes HACS-Repository** nutzbar. Die Aufnahme in den Standardkatalog ist ein separater Schritt:

1. [hacs/default](https://github.com/hacs/default) forken.
2. Vom Branch `master` einen neuen Branch erstellen.
3. In die Datei [`integration`](https://github.com/hacs/default/blob/master/integration) den Eintrag `mirkohd1999/TeddyCloud-Home-Assistant-Integration` **alphabetisch sortiert** einfügen.
4. Pull Request von deinem Fork nach `hacs/default:master` erstellen. Den Maintainers erlauben, den PR-Branch zu bearbeiten.
5. Review und automatische Prüfungen abwarten. Erst ein angenommener und gemergter Pull Request führt zur Aufnahme in den Katalog.

### PR-Text als Vorlage

**Titel:** `Add TeddyCloud Home Assistant Integration`

**Beschreibung:**

> Adds `mirkohd1999/TeddyCloud-Home-Assistant-Integration` as an integration to the HACS default catalog.
>
> - Public GitHub repository with MIT license and documentation
> - Complete Home Assistant integration in `custom_components/teddycloud_homeassistant/`
> - German and English translations and bundled branding
> - Passing HACS action and hassfest checks
> - Published GitHub release `v0.3.1` matching manifest version `0.3.1`
>
> Provides Toniebox monitoring, artwork, configurable volume limits, LED settings, and a bundled Lovelace card using TeddyCloud MQTT.

**Dokumentation:**
- HACS-Aufnahme: https://hacs.dev/docs/publish/include/
- Home Assistant Marketplace (ab Home Assistant 2026.11): https://contributors.home-assistant.io/marketplace/guides/catalog/

## 5. Funktionstest vor der Freigabe

In Home Assistant mit funktionierendem TeddyCloud MQTT überprüfen:

- Erstinstallation über HACS, Neustart und MQTT-Boxsuche
- Media-Player zeigt Titel, Bild und korrekten Boxnamen
- Karte `mode: all`, `player`, `settings` und Ressource laden ohne JavaScript-Fehler
- Lautsprecher-/Kopfhörerlimits und LED-Helligkeit funktionieren
- Aktualisierung einer bestehenden Installation erhält Entitäts-IDs und Einstellungen
- Entfernen des letzten Integrationseintrags bereinigt nur integrationsinterne Daten

Die Aufnahme in den HACS-Katalog ist **erst nach bestandenen Prüfungen, Release und Freigabe durch HACS** abgeschlossen.

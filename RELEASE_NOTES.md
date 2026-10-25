# TeddyCloud Home Assistant Integration v0.3.6

## Neu: Eigene Tonie-Bibliothek im Home-Assistant-Dashboard

- **Neue Dashboard-Karte:** `custom:teddycloud-tonie-library-card`, im Kartenkatalog als **TeddyCloud Tonie-Bibliothek**.
- **Gesehene Tonies automatisch merken:** Beim Erkennen einer neuen Audio-ID über TeddyCloud MQTT kommt die Figur in die dauerhaft gespeicherte gemeinsame Bibliothek. Die Sammlung funktioniert über mehrere Tonieboxen hinweg und bleibt auch nach einem Neustart erhalten.
- **Einträge direkt im Dashboard bearbeiten**, ohne Dashboard-Konfiguration oder Admin-Rechte: Titel ändern, Hörspiellänge eingeben und Figurenbilder per Webadresse oder als Bilddatei vom Gerät hochladen (PNG/JPG/WebP, bis 2 MB).
- **Suchen, manuell hinzufügen und löschen** mit Sicherheitsbestätigung.
- **Gelöschte Tonies automatisch wieder aufnehmen**, wenn sie nach dem Entfernen durch eine spätere Erkennung erneut aufgestellt werden. Gelöschte Einträge werden nicht sofort durch alte MQTT-Zustände oder Katalogergebnisse wiederhergestellt.
- **Gemeinsame, persistente Daten:** Home Assistant speichert die Sammlung intern über `Store`, lokal hochgeladene Bilder unter `/config/www/teddycloud_homeassistant/library/`.
- **Nicht-Administratoren können Inhalte bearbeiten:** Die Aktionen verwenden ausschließlich authentifizierte Home-Assistant-WebSocket-Befehle. Die Karte muss von jemandem mit Dashboard-Bearbeitungsrechten einmalig hinzugefügt werden.
- Manuell bearbeitete Metadaten werden außerdem beim aktuell aufgelegten Tonie im bestehenden Media-Player angezeigt.
- Neue Tests für Speicherung, Mehrfachboxen, Löschung/Wiedererkennung, Upload-Validierung und sichere Kartenanzeige.

## Installation

1. Version `v0.3.6` über HACS aktualisieren.
2. Home Assistant neu starten.
3. Dashboard bearbeiten → Karte hinzufügen → **TeddyCloud Tonie-Bibliothek** → Speichern.
4. Danach Tonies im normalen Dashboard hinzufügen, bearbeiten oder löschen – auch mit einem normalen Home-Assistant-Benutzerkonto.

Die bestehende Toniebox-Karte behält ihren Namen und ihre Konfiguration. Die Ressourcenadresse wird in Storage-Dashboards automatisch auf `/teddycloud-homeassistant/card-v036.js?v=0.3.6` aktualisiert. Alte Pfade werden weiter unterstützt.

## Grenzen

Die automatische Sammlung beginnt erst, wenn diese Version installiert ist. Bereits früher gehörte Figuren ohne erneute MQTT-Erkennung können nicht aus einer unbekannten Vergangenheit rekonstruiert werden; sie lassen sich erneut auflegen oder per Audio-ID hinzufügen. Auch ältere Figuren benötigen verfügbare Katalog- oder eigene Bilddaten. Play/Pause und die aktuelle Lautstärke bleiben nicht fernsteuerbar.

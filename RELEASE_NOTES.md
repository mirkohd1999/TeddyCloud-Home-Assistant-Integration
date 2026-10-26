# v0.5.2

## Erkannte Tonies zuverlässig in der Bibliothek

- Katalogtreffer warten auf das Anlegen des Bibliothekseintrags. Ein sofortiger Treffer aus dem Cache kann dadurch nicht mehr verloren gehen.
- Titel und Laufzeit erscheinen bereits vor Abschluss des Bilddownloads.
- Zusammengefasste Audio-IDs verwenden einen vorhandenen erkannten Titel, auch wenn der erste Eintrag noch keinen hat. Eigene Titel behalten Vorrang.
- Das Abbrechen einer Katalogsuche beim Figurenwechsel bricht die laufende Bibliothekserfassung nicht ab.

## Update

In HACS aktualisieren und Home Assistant neu starten. Vorhandene Einträge werden beim Start erneut mit dem erreichbaren Katalog abgeglichen. Bei einem betroffenen Eintrag den Tonie anschließend erneut aufstellen.

Ohne Titelmeldung und ohne passenden Katalogtreffer bleibt eine Figur weiterhin unbekannt. Der Katalogzugriff und Bilddownload können je nach Verbindung Zeit benötigen.

## Prüfung

37 Python-Tests, einschließlich sofortigem Katalogtreffer bei blockiertem Bibliotheksspeicher, langsamem Bilddownload, abgebrochener Katalogsuche und zusammengefassten Audio-IDs. Vorhandene Dashboard-Tests und Syntaxprüfungen. Kein Test an einer physischen Toniebox.

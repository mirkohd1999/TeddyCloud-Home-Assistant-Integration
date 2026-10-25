# TeddyCloud Home Assistant Integration v0.4.2

## System-Sounds gehören nicht in die Tonie-Bibliothek

- Einträge mit TeddyClouds eindeutiger „System sounds“-Kennzeichnung werden aus der Bibliotheksansicht und ihrer Zählung ausgeschlossen.
- Der Filter greift auch für bereits gespeicherte Einträge und nach einem Neustart. Manuelles Löschen ist nicht erforderlich.
- Nachträglich eintreffende MQTT- oder Katalogtitel aktualisieren die Einordnung. Es werden keine Audio-IDs dauerhaft gesperrt: Falsch zugeordnete, zeitversetzte Titel können durch echte Figurendaten korrigiert werden.
- Allgemeine Titel wie „Startup“ oder „Jingle Bells“ werden nicht pauschal ausgefiltert.
- Rohdaten bleiben intern erhalten; es werden keine gespeicherten Bilder oder eigenen Angaben gelöscht.

## Update

In HACS v0.4.2 herunterladen und Home Assistant neu starten. Danach das Dashboard neu laden. Die vorhandenen Rechte und rollenabhängigen Untertitel bleiben bestehen.

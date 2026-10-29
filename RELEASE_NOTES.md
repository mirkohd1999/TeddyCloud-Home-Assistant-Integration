# v0.5.10

## Buttons nebeneinander

- **▶ Hörprobe / ■ Stop** und **Löschen** stehen in derselben Buttonzeile einer Tonie-Kachel.
- Administratoren sehen **Bearbeiten** in derselben Zeile. Alle Buttons teilen die verfügbare Breite; lange Beschriftungen dürfen innerhalb eines Buttons umbrechen.
- Auch während der Löschbestätigung bleibt die Hörprobe in der gemeinsamen Zeile bedienbar.
- Die Beschriftung bleibt **Hörprobe** (englisch: **Audio sample**). Kein zusätzlicher Player oder Fortschrittsbalken.
- Versionsprüfung, automatische Ressourcenübernahme, Katalogzuordnung und Benutzerrechte bleiben erhalten.

## Update

In HACS auf **v0.5.10** aktualisieren und Home Assistant neu starten. Die Integration verwaltet die Kartenressource `/teddycloud-homeassistant/card-v0510.js` samt Versions- und Dateikennung automatisch. Falls das neue Modul noch nicht angefordert wurde, das Dashboard einmal neu öffnen.

## Prüfung

73 Python-Tests sowie Dashboard-, Sprach-, Audio- und Karten-Update-Tests bestanden. Die angepassten Kartentests prüfen die gemeinsame Buttonzeile für normale Nutzer und Administratoren, fehlende Hörproben und die Löschbestätigung. Layout und Audio-Lebenszyklus wurden mit simuliertem DOM geprüft.

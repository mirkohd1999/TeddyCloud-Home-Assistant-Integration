# v0.5.7

## Hörproben für vorhandene Tonies nachladen

- In der Tonie-Bibliothek gibt es **Hörproben aktualisieren**. Administratoren und normale angemeldete Nutzer können damit alle vorhandenen Einträge erneut anhand ihrer Audio-IDs abgleichen. Die Quelle bleibt ausschließlich `tonies-json`; es werden keine Shop-Seiten oder weiteren Anbieter durchsucht.
- Die Karte zeigt, ob der Hörproben-Katalog noch geprüft wird, vorübergehend nicht erreichbar ist oder für die Sammlung keine passenden Hörproben enthält.
- Wird wegen eines Verbindungsproblems nur das ältere Katalogformat geladen, wird das aktuelle Format nach etwa 22 Sekunden erneut versucht. Der Rückfall blockiert Hörproben nicht mehr für 24 Stunden und entfernt keine bereits gespeicherten Vorschau-Links.
- Bei regionalen Katalogeinträgen desselben Hörspiels mit gleicher Audio-ID bleibt eine vorhandene Hörprobe erhalten, wenn ein späterer Eintrag keinen Link enthält. Abweichende Geschichten oder Inhaltssprachen erhalten keine fremde Hörprobe.
- Manuelle Aktualisierungen dürfen den Tagescache umgehen; wiederholte Downloads werden mindestens 20 Sekunden begrenzt. Laufende Hörproben werden durch den Abgleich nicht neu gestartet.
- Audiodateien spielen weiterhin direkt im Dashboard und werden von der Integration nicht gespeichert. Erkennungszähler, letzte Figur und eigene Bearbeitungen bleiben erhalten.

## Update

In HACS auf **v0.5.7** aktualisieren und **Home Assistant neu starten**. Danach das Dashboard neu öffnen. Die automatisch registrierte Ressource lautet `/teddycloud-homeassistant/card-v057.js?v=0.5.7`. Bei fehlenden Buttons **Hörproben aktualisieren** drücken. Tonies müssen dafür weder gelöscht noch erneut aufgestellt werden.

## Prüfung

66 Python-Tests sowie Dashboard-, Sprach- und Audio-Lebenszyklustests bestanden. Neue Regressionen prüfen den Rückfall vom aktuellen auf das ältere Katalogformat mit anschließender Wiederherstellung, vorhandene Sammlungen, den manuellen Abgleich für beide Rollen, Begrenzung wiederholter Anforderungen und echte doppelte Grüffelo-Katalogeinträge. Die vollständigen aktuellen Katalogdaten wurden zusätzlich gegen die zehn zuvor geprüften Tonies abgeglichen. Kein Zugriff auf die Home-Assistant-Installation des Nutzers und kein Wiedergabetest auf einer physischen Toniebox.

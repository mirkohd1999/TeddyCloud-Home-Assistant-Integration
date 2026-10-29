# v0.5.8

## Einfache Play-/Stop-Bedienung für Hörproben

- Hörproben werden ausschließlich über **▶ Play** und **■ Stop** direkt in der jeweiligen Tonie-Kachel bedient.
- Der zusätzliche Player mit großem Titel, Fortschrittsbalken, Zeitangaben und Browser-Menü entfällt vollständig.
- Stop beendet die Wiedergabe und gibt den Audiostream frei. Ein erneutes Play startet die Hörprobe von vorn. Am natürlichen Ende kehrt der Button automatisch zu Play zurück.
- Der Wechsel zu einer anderen Hörprobe sowie das Verlassen der Karte stoppt die bisherige Wiedergabe. Bibliotheksaktualisierungen unterbrechen eine laufende Probe nicht.
- Zuordnung, Katalogabgleich, Berechtigungen und direktes Streaming ohne Audiodatei in Home Assistant bleiben erhalten.

## Update

In HACS auf **v0.5.8** aktualisieren, Home Assistant neu starten und das Dashboard neu öffnen. Die automatisch registrierte Kartenressource lautet `/teddycloud-homeassistant/card-v058.js?v=0.5.8`.

## Prüfung

66 Python-Tests sowie Dashboard-, Sprach- und angepasste Audio-Tests bestanden. Die Audio-Tests prüfen fehlende sichtbare Player-Elemente, Play/Stop-Anzeige, Neustart nach Stop, natürliches Ende, Kartenwechsel, Fehler und beide Benutzerrollen. Audio-Lebenszyklus mit Testobjekt geprüft; kein direkter Test auf dem Endgerät des Nutzers.

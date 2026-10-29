# v0.5.6

## Hörproben in der Tonie-Bibliothek

- Tonies mit einer genau zugeordneten Hörprobe erhalten einen **▶ Hörprobe**-Button. Die Wiedergabe läuft direkt in der Dashboard-Karte mit Start/Pause und Fortschrittsanzeige, ohne Weiterleitung auf eine Webseite.
- Einzige Quelle ist der bereits verwendete `tonies-json`-Katalog. Die Zuordnung erfolgt anhand der Audio-ID. Keine Suche nach ähnlichen Titeln, kein zusätzlicher Shop- oder Suchmaschinenabruf.
- Bereits gesammelte und neu erkannte Tonies werden automatisch ergänzt. Der gemeinsame Katalog wird alle 24 Stunden aktualisiert; Verbindungsfehler werden erneut versucht. Ohne eindeutige Zuordnung oder verfügbaren Link bleibt der Button ausgeblendet.
- Home Assistant und TeddyCloud speichern keine Audiodatei. Gespeichert wird nur der Link; nach einem Klick lädt der Browser die Hörprobe direkt vom Anbieter und puffert die Wiedergabe.
- Eine andere Hörprobe, ein gelöschter Eintrag oder das Verlassen des Dashboards beendet die bisherige Wiedergabe. Laufende Vorschauen bleiben bei Bibliotheksaktualisierungen erhalten.
- Für Administratoren und normale angemeldete Benutzer verfügbar. Bedienelemente folgen der deutschen beziehungsweise englischen Home-Assistant-Profilsprache.
- Abspielzähler, Toniebox-Status und die zuletzt gehörte Figur werden durch Hörproben nicht verändert.

## Update

In HACS auf **v0.5.6** aktualisieren und Home Assistant neu starten. Die Dashboard-Ressource wird auf `/teddycloud-homeassistant/card-v056.js?v=0.5.6` umgestellt. Bestehende Tonies erhalten ihre Hörproben nach dem Katalogabgleich, ohne dass jede Figur erneut aufgestellt werden muss.

## Prüfung und Grenzen

60 Python-Tests sowie Dashboard-/Sprachtests und neue Audio-Lebenszyklustests bestanden. Zehn echte, festgehaltene Katalogeinträge prüfen die exakte Zuordnung inklusive englischem Inhalt und fehlender Hörprobe. Bei der vorangegangenen Live-Prüfung waren neun verknüpfte Audiodateien erreichbar; bei einem Tonie war keine Hörprobe vorhanden. Wiedergabe, Wechsel, Pause, Fehler, parallele Karten und Aufräumen wurden mit einem Audio-Testobjekt geprüft. Kein Wiedergabetest in einer laufenden Home-Assistant-Installation.

Die Verfügbarkeit hängt von Katalog und Anbieter ab. Neue oder unbekannte Audio-IDs sowie Tonies ohne veröffentlichte Vorschau erhalten keinen Button. Eine englische Dashboard-Oberfläche übersetzt keine Hörspielinhalte; abgespielt wird die zum erkannten Tonie gehörende Sprachfassung.

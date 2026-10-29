# v0.5.9

## Hörprobe / Stop und Übernahme der Kartenversion

- Der Startbutton heißt **▶ Hörprobe** statt Play. Während der Wiedergabe erscheint **■ Stop**. Bei englischem Home-Assistant-Profil lautet der Startbutton **▶ Audio sample**.
- Die Hörprobe bleibt direkt in der Tonie-Kachel. Kein zusätzlicher Player, Fortschrittsbalken, Zeitangaben oder Browser-Menü.
- Die automatisch registrierte Ressourcenadresse enthält neben der Version eine Kennung aus der tatsächlich installierten JavaScript-Datei. Alte Ressourcenadressen und manuelle Cache-Zusätze werden auf die neue Adresse umgestellt.
- Die Bibliotheksverbindung liefert Version und Ressourcenadresse mit. Eine Bibliothek mit der neuen Versionsprüfung kann neuere Module automatisch nachladen, ohne dass Ressourcen von Hand bearbeitet werden müssen.
- Beim Laden des neuen Moduls werden kompatible Methoden einer bereits registrierten älteren Bibliothekskarte ersetzt und geöffnete Karten neu dargestellt. So verhindert die alte Registrierung nicht länger, dass die neue Darstellung übernommen wird. Ein alter nativer Hörproben-Player wird dabei freigegeben und entfernt.
- Erneutes Laden derselben Version unterbricht keine laufende Hörprobe. Ein verspätetes älteres Modul überschreibt keine neuere Registrierung. Nur versionierte Module der eigenen Home-Assistant-Adresse werden nachgeladen.

## Update

In HACS auf **v0.5.9** aktualisieren und **Home Assistant neu starten**. Die Integration verwaltet die Ressource `/teddycloud-homeassistant/card-v059.js` einschließlich Versions- und Dateikennung automatisch. Kein manuelles Ergänzen von `refresh`-Parametern nötig.

Wenn eine vorher geöffnete ältere Karte noch keine Versionsprüfung hatte und das neue Modul überhaupt nicht angefordert wird, das Dashboard einmal neu öffnen. Eine bereits geladene alte Registrierung wird beim Laden des neuen Moduls aktualisiert. Tonies müssen nicht gelöscht oder neu aufgestellt werden.

## Prüfung

73 Python-Tests sowie Dashboard-, Sprach-, Audio- und neue Karten-Update-Tests bestanden. Eine isolierte unveränderte Bibliotheksklasse aus v0.5.7 reproduziert den alten sichtbaren Player. Der Test lädt das neue Modul im selben Dokument, findet Karten in verschachtelten Shadow Roots, entfernt den alten Player und prüft Hörprobe/Stop, beide Rollen, neue Instanzen und wiederholtes Laden. Weitere Tests prüfen Ressourcenmigration, Dateikennung, Versionsabgleich, begrenzte Moduladressen und Wiederholung nach einem fehlgeschlagenen Import.

Kein direkter Zugriff auf die Home-Assistant-Installation oder das Endgerät des Nutzers; die Übernahme wurde mit simuliertem DOM und Audioelement geprüft.

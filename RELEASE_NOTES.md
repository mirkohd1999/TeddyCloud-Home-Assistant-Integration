# v0.5.4

## Dashboard-Karten automatisch auf Englisch

- Player, Tonie-Bibliothek und beide Karteneditoren folgen der Sprache des jeweiligen Home-Assistant-Nutzers.
- Englisch einschließlich en-GB/en-US aktiviert englische Beschriftungen. Deutsch und andere Sprachen verwenden die bisherige deutsche Oberfläche. Keine Auswertung der Browsersprache und keine neue Karteneinstellung.
- Übersetzte Statusmeldungen, Suchfelder, Bibliotheksformulare, Löschbestätigungen, bekannte Validierungsfehler und barrierefreie Beschriftungen.
- Eigene Namen, Hörspieltitel, technische Entitätszuordnungen und Berechtigungen bleiben erhalten.
- Ein Sprachwechsel aktualisiert die Karten und Editoren. Bibliothekszahlen und Datumsangaben passen sich der gewählten Anzeigesprache an.

## Update

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden. Die neue Kartenressource wird automatisch registriert; bei manueller YAML-Verwaltung `/teddycloud-homeassistant/card-v054.js?v=0.5.4` verwenden.

## Prüfung

39 Python-Tests sowie Dashboard-Tests einschließlich aller Player-Layouts, englischer und deutscher Editoren, Sprachwechsel, Admin-/Nutzerrollen, Fehlertexte, unveränderter eigener Titel und funktionierender Reglerzuordnung. Kein Test an einer physischen Toniebox.

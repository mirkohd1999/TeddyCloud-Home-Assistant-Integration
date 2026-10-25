# TeddyCloud Home Assistant Integration v0.3.4

## Neu: Dashboard in wenigen Klicks einrichten

Der Dashboard-Karteneditor wurde für Endnutzer deutlich vereinfacht:

- **Vorlage antippen statt Dropdown-Menüs durchsuchen**: Acht große, beschriftete Auswahlflächen mit klaren Namen und kurzer Erklärung.
- **Toniebox automatisch auswählen**, wenn genau eine passende Toniebox-Entität vorhanden ist.
- **Live-Vorschau** beim Wechseln der Vorlage.
- **„Selbst gestalten“**: Nur hier erscheint der Baukasten, mit fünf vorausgewählten Bausteinen; weitere Bereiche lassen sich einfach an- und abwählen und mit Pfeilen sortieren.
- **Erweiterte Optionen verborgen**, bis sie wirklich gebraucht werden: Anzeigename, Farbwähler, Bilddarstellung sowie manuelle Entitäts-ID.
- **Neue versionierte Kartendatei** unter `/teddycloud-homeassistant/card-v034.js?v=0.3.4`. Bereits vorhandene, von der Integration erkannte Ressourcen werden in Lovelace-Storage-Dashboards automatisch auf diese Adresse aktualisiert. Die bisherige URL bleibt als Kompatibilitätspfad erreichbar, aber bei neuen Installationen wird die neue URL genutzt.
- **Kein YAML erforderlich**, keine zusätzliche MQTT-Einrichtung, keine Veränderungen an bestehenden Dashboard-Konfigurationen.
- Weitere Tests für Presets, Box-Auswahl, Baukasten und Eingabe-Sicherheit.

## Einrichtung

1. Integration auf `v0.3.4` über HACS aktualisieren, **Home Assistant neu starten**.
2. Dashboard → Bearbeiten → Karte hinzufügen → **TeddyCloud Home Assistant Integration**.
3. Toniebox auswählen (bei einer Toniebox automatisch), die gewünschte Vorlage anklicken und **Speichern**.

Die Integration registriert die Kartenressource bei Storage-Dashboards automatisch; die neue URL muss nicht manuell gepflegt werden. Falls der Karteneditor weiterhin wie früher aussieht, die Home-Assistant-Seite nach dem Neustart einmal neu laden (ggf. Browserfenster vollständig schließen).

## Kompatibilität

Die bestehenden Ansichten `all`, `player`, `settings` und die bereits vorhandenen Konfigurationen mit `mode: custom` bleiben nutzbar. Alle bisherigen MQTT-Sensoren, Ohrtasten, Tonie-Bilder und Lautsprecher-/Kopfhörer-/LED-Einstellungen funktionieren unverändert.

Die neuen Dashboard-Vorlagen ändern **nicht** die vorhandene Einschränkung, dass aktuelle Lautstärke und Play/Pause nicht ferngesteuert werden können.

**Release-Hinweis:** `v0.3.4` ist erst als reguläres HACS-Update verfügbar, nachdem der gleichnamige GitHub-Release auf dem geprüften `main` veröffentlicht wurde.

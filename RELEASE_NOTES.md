# TeddyCloud Home Assistant Integration v0.3.7

## Fehlerbehebung: Tonie-Bibliothek wird im Dashboard nicht gefunden

- Behebt **„Custom element doesn't exist: teddycloud-tonie-library-card“** bei gleichzeitig geladenen älteren und neueren TeddyCloud-Dashboard-Ressourcen.
- Beide Custom Elements werden jetzt nur registriert, falls sie noch nicht existieren. Eine vorhandene Toniebox-Karte blockiert die spätere Registrierung der Bibliothek damit nicht mehr.
- Auch bei mehrfach eingebundenen Ressourcen entstehen keine doppelten Einträge im Kartenkatalog.
- Neue cache-sichere Kartenressource: `/teddycloud-homeassistant/card-v037.js?v=0.3.7`.
- Die Integration kann die automatische Lovelace-Ressourcenregistrierung erneut versuchen, wenn Home Assistant diese beim frühen Start noch nicht bereitgestellt hat.
- Automatisierter Regressionstest lädt die Kartendatei wie auf einer Installation mit vorhandener älterer Player-Karte mehrfach, einschließlich Bibliotheksregistrierung.
- **Keine Änderungen an gespeicherten Tonies, Bildern, Titeln und Laufzeiten.** Die Bibliothek aus v0.3.6 bleibt erhalten.

## Aktualisierung

1. Über HACS auf **v0.3.7** aktualisieren.
2. **Home Assistant vollständig neu starten.**
3. Dashboard bearbeiten → **TeddyCloud Tonie-Bibliothek** als zusätzliche Karte hinzufügen; alternativ manuell:

```yaml
type: custom:teddycloud-tonie-library-card
```

In normalen Storage-Dashboards ist keine manuelle Ressourcenadresse erforderlich. Die Ressource wird automatisch aktualisiert. Bei weiterhin altem Dashboard zuerst den Browser-Tab einmal neu laden. Falls Home Assistant Ressourcen über YAML verwaltet, muss die neue URL dort manuell eingebunden werden.

# v0.5.3

## Toniebox-Farbe bleibt offline erhalten

Home Assistant entfernt bei nicht verfügbaren Entitäten die normalen Zusatzattribute. Die konfigurierte Box-Farbe wird jetzt als dauerhaftes Attribut bereitgestellt, damit die Karte offline nicht zur violetten Standardfarbe wechselt. Das gilt auch beim Neuladen des Dashboards und direkt nach einem HA-Neustart. Die Farbe aus den Box-Optionen hat weiterhin Vorrang vor der ursprünglichen Konfiguration.

## Update

In HACS aktualisieren und Home Assistant neu starten. Die vorhandene Karte kann weiterverwendet werden.

## Prüfung

38 Python-Tests sowie die bestehenden Dashboard- und Bibliothekstests. Der neue Regressionstest prüft verfügbare und nicht verfügbare Zustände, geänderte Box-Farben, erhaltene Basisattribute und eine neu erzeugte Player-Instanz. Kein Test an einer physischen Toniebox.

# Projekt-Doku Rezept-App

Eigene Dokumentation zum Fork. Tandoors Original-Doku liegt in `docs/`.

- `FORTSCHRITT.md` – Stand, Tests, offene Punkte (Protokoll des Nachtlaufs)
- `ENTSCHEIDUNGEN.md` – getroffene Entscheidungen mit Begründung
- `CORE_CHANGES.md` – Änderungen an Tandoor-Kerndateien
- `ARCHITEKTUR.md` – relevante Tandoor-Stellen, Plugin-System
- `API_ERWEITERUNGEN.md` – unsere API (Varianten, effektive Fassung, Bewertungen, Fotos)
- `DEV.md` – lokale Entwicklung (`dev/setup.sh`, `dev/env.sh`, Demo-Daten, Screenshots)
- `SETUP_LXC.md`, `BACKUP.md`, `UPDATE.md` – Betrieb
- `screenshots/` – Stand der Oberfläche bei 390 px

## Lokal klonen (Mac)

GitHub Desktop: **File → Clone Repository** → `NFrankM/recipes` → Local Path `~/Documents/rezept-app`, danach Branch `main-custom` auswählen.

Oder im Terminal:

```bash
git clone https://github.com/NFrankM/recipes ~/Documents/rezept-app
cd ~/Documents/rezept-app
git checkout main-custom
git remote add upstream https://github.com/TandoorRecipes/recipes
```

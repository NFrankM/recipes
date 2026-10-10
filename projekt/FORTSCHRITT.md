# Fortschritt Nachtlauf

## Stand jetzt

Umgebungsprüfung abgeschlossen, Phase 1 startet.

## Umgebung (2026-10-10)

| Werkzeug | Befund | Lösung |
|---|---|---|
| Python | nur System-Python 3.9.6 | CPython 3.12.11 via `uv` nach `.tools/python`, venv in `venv/` (E1) |
| Node | fehlt | Node 22.23.3 (offizielles Tarball) nach `.tools/node` (E1) |
| Docker | fehlt | Phase 1 nur statisch validiert; Dev mit SQLite (E2) |
| PostgreSQL / psql | fehlt | SQLite lokal (E2) |

- `uv pip install -r requirements.txt` ohne `python-ldap`, `django-auth-ldap`, `python3-saml` (brauchen System-Bibliotheken, für die lokale Entwicklung unnötig) → ok
- `npm ci` in `vue3/` → ok (Achtung: npm schreibt dabei `vue3/yarn.lock` um → wird verworfen, siehe DEV.md)
- `python manage.py check` → ok (nur Hinweis auf fehlendes Vite-Manifest vor dem ersten Build)

## Phase 1 – Infrastruktur ✅

**Plan:** Compose-Datei (Tandoor 2.6.15 + PostgreSQL 16, benannte Volumes, Healthcheck, restart-Policy), `.env.example`, Backup-/Restore-Skripte mit Rotation und Prüfsummen, Doku für LXC und Backup. Kein Docker auf dem Mac → statische und Stub-basierte Validierung.

**Erledigt:**
- `deploy/docker-compose.yml` – `vabene1111/recipes:2.6.15` (aktuelle stabile Version laut Upstream-Tags und Docker Hub, `latest` = 2.6.15), `postgres:16-alpine`, Volumes `postgres_data`, `mediafiles`, `staticfiles`, `restart: unless-stopped`, DB-Healthcheck + `depends_on: service_healthy`, Image per `TANDOOR_IMAGE` umstellbar (für Phase 7)
- `deploy/.env.example` – alle Variablen kommentiert, inkl. `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` für Tailscale (http + https via `tailscale serve`)
- `deploy/backup.sh` – pg_dump -Fc + tar.gz der Medien, atomar über Temp-Ordner, Prüfung (`pg_restore --list`, `tar -t`, SHA256SUMS), Rotation 7 täglich / 4 wöchentlich, Log, Exit-Codes 0–7, Mount-Prüfung (NAS weg → Abbruch), Lock gegen Doppelstart
- `deploy/restore.sh` – Prüfsummen, Rückfrage, Restore DB/Medien, `--projekt` für Restore-Test neben dem Live-System
- `projekt/SETUP_LXC.md`, `projekt/BACKUP.md` (NAS-Bind-Mount für unprivilegierte LXC, Cron, Restore-Test-Checkliste)

**Getestet mit:**
- `bash -n deploy/backup.sh deploy/restore.sh` → ok
- YAML gegen das offizielle Compose-Spec-JSON-Schema (`compose-spec.json`, jsonschema) → gültig
- Funktionstest mit Docker-Stub (simuliert `docker compose exec/run`): 30 simulierte Tage → genau 7 daily + 4 weekly (Sonntage) übrig; Fehlerfälle (kein BACKUP_DIR, ungültige Zahl) → Exit 1; Restore stellt Dump und Bilder wieder her; manipulierte Sicherung → Abbruch wegen Prüfsumme; Rückfrage ≠ JA → Abbruch
- `docker compose config` → **nicht möglich** (kein Docker auf dem Mac), muss auf der LXC laufen

## Phase 2 – Architektur & Dev-Umgebung ✅

**Plan:** Repo analysieren (Models, API, Rechte, vue3), ARCHITEKTUR.md schreiben; Dev-Umgebung ohne Docker (SQLite, Vite-HMR) mit Bootstrap-Skript; App `cookbook_ext` mit minimalem Eingriff registrieren; CookLog/Kommentare bewerten.

**Erledigt:**
- `projekt/ARCHITEKTUR.md` – Models (Recipe, Step, Ingredient, Food, Unit, Keyword, CookLog, Comment, Shopping*), API-Stil, Space/User-Berechtigungen, vue3-Aufbau (Routing, Theme, Komponenten, Stores), Plugin-System
- **Wichtigster Fund:** Tandoor hat ein Plugin-System für Backend (`recipes/plugins/`) und Frontend (`vue3/src/plugins/`). `cookbook_ext` liegt dort → **keine** Änderung an Python-/Vue-Kerncode für die Registrierung, nur `.gitignore` (E3, CORE_CHANGES.md)
- `recipes/plugins/cookbook_ext/` angelegt (AppConfig, leerer API-Router, Tests)
- `projekt/dev/setup.sh` (Bootstrap ohne Admin-Rechte), `projekt/dev/env.sh`, `projekt/DEV.md`
- Bewertungen: Entscheidung E4 → CookLog = Bewertung, zusätzlich eigenes `CookLogPhoto` für Fotos

**Getestet mit:**
- `python manage.py check` → ok, `PLUGIN cookbook_ext loaded`
- `pytest recipes/plugins/cookbook_ext -o addopts=""` → 2 passed (Plugin in INSTALLED_APPS und PLUGINS)
- `projekt/dev/setup.sh` erneut ausgeführt → idempotent, ok
- `runserver` → `/` 302 auf `/setup/`, `/setup/` 200; `yarn dev` + `manage.py check` → „Vite Dev Server is running" (HMR aktiv)
- `yarn build` (vue3) → ok
- Tandoors gesamte Test-Suite: `pytest cookbook/tests -n 8` → **1259 passed, 18 skipped, 1 failed** (`test_markdown_renderer` – schlägt auch **ohne** unser Plugin fehl, Upstream-Problem auf `develop`)

## Phase 3 – Theme & Grundoptik ✅

**Plan:** Design-Tokens als Vuetify-Theme, Plus Jakarta Sans lokal, Radien/Buttons/Chips/Felder als Defaults – ohne Tandoors `vuetify.ts` anzufassen (zentrale Stelle: unser Frontend-Plugin). Danach Kontrolle bei 390 px.

**Erledigt:**
- `vue3/src/plugins/cookbook_ext/plugin.ts` – Frontend-Plugin, wird von Tandoor automatisch vor dem Mount geladen
- `theme/applyTheme.ts` – überschreibt das Standard-Theme `light` (Farben + `rz-*`-Tokens, Rand-Variablen) und ergänzt globale Vuetify-Defaults (Karten flach mit Rand und 16 px, Felder outlined 14 px, Chips als Pills, Sterne in accent-dark …). Tandoors eigene Defaults bleiben per Merge erhalten. → **keine Kernänderung**
- `theme/rezept-theme.css` – Plus Jakarta Sans (Variable Font, latin + latin-ext, **lokal gebündelt**, kein Google-CDN; OFL-Lizenz liegt bei), Typografie (Titel 30 px, H2 20 px, Text 15 px), Radien-Klassen `rounded-rz*`, Buttons ohne Großbuchstaben und mind. 44 px hoch, helle App-Bar/untere Leiste
- `theme/tokens.ts` – Tokens aus CLAUDE.md als TS-Konstanten und CSS-Variablen `--rz-*`
- Dev-Hilfen: `manage.py rezept_demo` (Demo-Daten), `projekt/dev/screenshots.py` (Playwright, 390 × 844)

**Getestet mit:**
- `yarn build` → ok; Font-Dateien landen im Bundle
- Screenshots 390 px: `projekt/screenshots/phase3/` (Start, Suche, Rezept, Einkauf, Import) – Schrift, Farben, App-Bar und Radien greifen überall

**Noch stark vom Zieldesign abweichende Screens (390 px):**
| Screen | Abweichung | Wann |
|---|---|---|
| Übersicht/Start (`/`) | Tandoor-Startseite = Essensplan-Tag + „Zufällige Rezepte"-Karussell; es fehlen Titel + Plus-Button, Suchfeld, Filter-Chips und 2-spaltiges Raster | Phase 6 (eigene Übersicht) |
| Untere Leiste | Tandoor: Rezepte / Essensplan / Einkauf / Menü, nur Icons, gefüllte Font-Awesome-Icons; Ziel: Rezepte / Suche / Einkauf / Import mit Beschriftung und Strich-Icons | Phase 6 |
| App-Bar | Tandoor-Logo und Schriftzug „Tandoor" | Phase 6 (eigener Titel) |
| Rezeptansicht | kein großes Foto mit überlappendem Sheet, kein Segment „Original/Unsere Version", Portionen nur als Info statt Stepper, Zutaten pro Schritt als Tabelle mit Checkboxen | Phase 5 (neue Ansicht) |
| Suche (`/advanced-search`) | 2-spaltiges Raster ist da, aber Karten mit Outline-Chips und blasser Zeit-Chip; keine Filter-Chips | Phase 6 |
| Einkaufsliste | funktional ok, aber Tabs als Icons, Eingabefeld „filled" (Tandoor setzt die Variante explizit), keine Gruppierung nach Kategorie sichtbar ohne Supermarkt | Phase 6 |
| Import | Schritt-Leiste und Karten-Liste funktionieren, wirken aber technisch (KI, JSON, URL-Liste) | Phase 6 (vereinfachter Import-Dialog) |
| Icons allgemein | Font Awesome „solid" statt schlichter Strich-Icons; eigene Komponenten nutzen ab Phase 5 Strich-SVGs | Phase 5/6 |

## Probleme

- `git push origin main-custom` scheitert: keine GitHub-Anmeldung im nicht-interaktiven Terminal (`could not read Username`). Alle Commits liegen nur lokal → morgen pushen.
- Kein Docker auf dem Mac: Compose-Datei und Skripte sind nur statisch + per Stub geprüft, nicht mit echten Containern.

## Für Frank zu tun

1. `git push origin main-custom` (Commits liegen nur lokal).
2. Auf Proxmox die LXC anlegen und Tandoor starten: [SETUP_LXC.md](SETUP_LXC.md). Dabei `docker compose config` ausführen (konnte ich nicht testen).
3. NAS einbinden, `backup.conf` anlegen, Cron-Eintrag setzen und einmal den Restore-Test machen: [BACKUP.md](BACKUP.md).

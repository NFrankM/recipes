# Lokale Entwicklung

Backend (Django) + Frontend (Vite-Dev-Server mit Hot Reload). Getestet auf macOS (Apple Silicon) **ohne** Homebrew, Docker oder Admin-Rechte – alle Werkzeuge liegen repo-lokal in `.tools/` (gitignored), siehe Entscheidung E1.

## Einmalig einrichten

```bash
cd ~/Documents/rezept-app
projekt/dev/setup.sh
```

Das Skript lädt `uv`, Python 3.12 und Node 22 nach `.tools/`, legt `venv/` an, installiert alle Python-Pakete (ohne LDAP/SAML, die System-Bibliotheken brauchen) und die Frontend-Pakete mit yarn (wie upstream, `--frozen-lockfile`), erzeugt eine `.env` für die Entwicklung (DEBUG=1, SQLite) und migriert die Datenbank.

Danach einen Admin anlegen:

```bash
source projekt/dev/env.sh
python manage.py createsuperuser
```

Beim ersten Login legt Tandoor automatisch einen Space an.

## Starten (zwei Terminals)

```bash
# Terminal 1 – Frontend mit Hot Reload (http://localhost:5173, wird von Django eingebunden)
source projekt/dev/env.sh
cd vue3 && yarn dev
```

```bash
# Terminal 2 – Backend
source projekt/dev/env.sh
python manage.py runserver
```

Aufruf: **http://localhost:8000**. Django erkennt beim Start den laufenden Vite-Server (Meldung `Vite Dev Server is running`) und lädt das Frontend dann direkt von dort (Hot Reload). Läuft Vite nicht, wird der letzte Build aus `cookbook/static/vue3/` genutzt.

Vom Handy im WLAN testen: `python manage.py runserver 0.0.0.0:8000` und in `.env` `DJANGO_VITE_DEV_SERVER_HOST=<IP des Macs>` setzen – oder einfacher: Build erzeugen (unten) und nur Django starten.

## Datenbank

- **Standard lokal: SQLite** (`db.sqlite3` im Repo-Root, gitignored). Grund: kein Docker auf dem Mac (E2).
- **PostgreSQL per Docker** (sobald Docker Desktop/OrbStack installiert ist), näher an der Produktion (Trigram-Suche):
  ```bash
  docker run -d --name rezept-dev-db -p 5432:5432 \
    -e POSTGRES_DB=tandoor -e POSTGRES_USER=tandoor -e POSTGRES_PASSWORD=tandoor \
    -v rezept-dev-db:/var/lib/postgresql/data postgres:16-alpine
  ```
  In `.env` ergänzen:
  ```
  DB_ENGINE=django.db.backends.postgresql
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
  POSTGRES_DB=tandoor
  POSTGRES_USER=tandoor
  POSTGRES_PASSWORD=tandoor
  ```
  Dann `python manage.py migrate`.

## Tests

```bash
source projekt/dev/env.sh
# unsere Tests
pytest recipes/plugins/cookbook_ext -o addopts="" -q
# Tandoors eigene Tests (dauert; -n auto parallelisiert)
pytest cookbook/tests -o addopts="" -q -n auto
```

`-o addopts=""` schaltet die Coverage-/HTML-Reports aus `pytest.ini` ab (schneller, keine Report-Dateien).

## Frontend-Build

```bash
source projekt/dev/env.sh
cd vue3 && yarn build          # → cookbook/static/vue3/ (inkl. manifest.json)
```

`npm` statt `yarn` geht auch (`npm ci && npm run build`), schreibt aber `vue3/yarn.lock` um → danach `git checkout vue3/yarn.lock`.

## Wo liegt unser Code?

| Teil | Ort |
|---|---|
| Django-App `cookbook_ext` (Models, API, Services, Tests) | `recipes/plugins/cookbook_ext/` |
| Frontend (eigene Views/Komponenten, Routen, Theme) | `vue3/src/plugins/cookbook_ext/` |
| Deployment | `deploy/` |
| Doku | `projekt/` |

Beides wird über Tandoors Plugin-System automatisch geladen (siehe ARCHITEKTUR.md).

## Aufräumen

```bash
rm -rf .tools venv vue3/node_modules db.sqlite3 cookbook/static/vue3
```

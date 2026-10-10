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

## Probleme

- `git push origin main-custom` scheitert: keine GitHub-Anmeldung im nicht-interaktiven Terminal (`could not read Username`). Alle Commits liegen nur lokal → morgen pushen.
- Kein Docker auf dem Mac: Compose-Datei und Skripte sind nur statisch + per Stub geprüft, nicht mit echten Containern.

## Für Frank zu tun

1. `git push origin main-custom` (Commits liegen nur lokal).
2. Auf Proxmox die LXC anlegen und Tandoor starten: [SETUP_LXC.md](SETUP_LXC.md). Dabei `docker compose config` ausführen (konnte ich nicht testen).
3. NAS einbinden, `backup.conf` anlegen, Cron-Eintrag setzen und einmal den Restore-Test machen: [BACKUP.md](BACKUP.md).

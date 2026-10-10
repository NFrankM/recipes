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

## Probleme

## Für Frank zu tun

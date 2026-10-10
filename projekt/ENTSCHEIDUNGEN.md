# Entscheidungen

Entscheidungen, die während der Arbeit ohne Rückfrage getroffen wurden. Format: Frage – Optionen – Wahl – Grund.

## E1 – Toolchain auf dem Mac (2026-10-10)

- **Frage:** Auf dem Mac sind nur System-Python 3.9.6 vorhanden, kein Node, kein Docker, kein PostgreSQL. Tandoor (Django 5.2) braucht Python ≥ 3.10, das Frontend Node 22.
- **Optionen:** (a) Homebrew/Installer – verboten (global, ggf. sudo). (b) Nur Dateien schreiben, nichts ausführen. (c) Portable Toolchains repo-lokal herunterladen.
- **Wahl:** (c) `uv` (Standalone-Binary), damit CPython 3.12 und Node 22 (offizielles Tarball) nach `.tools/` im Repo. `.tools/` ist in `.gitignore`. Caches (uv, npm) ebenfalls in `.tools/`. Die venv liegt wie vorgegeben in `venv/`.
- **Grund:** Kein sudo, nichts außerhalb des Repos, jederzeit mit `rm -rf .tools venv` rückstandslos entfernbar. Python 3.12 entspricht Tandoors CI.

## E2 – Datenbank für die lokale Entwicklung (2026-10-10)

- **Frage:** Kein Docker → kein PostgreSQL lokal.
- **Wahl:** Lokale Entwicklung und Tests mit **SQLite** (Tandoor unterstützt das, `DB_ENGINE` leer → SQLite; Tandoors eigene Tests laufen ebenfalls mit SQLite). Produktion bleibt PostgreSQL 16. In `projekt/DEV.md` ist zusätzlich der Weg mit PostgreSQL per Docker beschrieben, sobald Docker da ist.
- **Grund:** Einzige lauffähige Option ohne Installation. Unsere eigenen Models nutzen keine PostgreSQL-Spezialfunktionen, daher kein Risiko.

## E3 – Wo lebt die eigene Django-App? (2026-10-10)

- **Frage:** `cookbook_ext` als normale App im Repo-Root (Eintrag in `INSTALLED_APPS` + URL-Registrierung im Kern) oder über Tandoors Plugin-System?
- **Optionen:** (a) Root-App, 2–3 Zeilen Kernänderung in `settings.py`/`urls.py`. (b) Tandoor-Plugin unter `recipes/plugins/cookbook_ext/` – wird automatisch in `INSTALLED_APPS` aufgenommen, URLs unter `base_url` eingehängt und der API-Router (`api_router_name`) in `/api/` integriert. Frontend analog unter `vue3/src/plugins/cookbook_ext/plugin.ts` (Routen, Navigation, Übersetzungen werden automatisch geladen).
- **Wahl:** (b) Plugin-System. Einzige Kernänderung ist `.gitignore` (die beiden Plugin-Ordner waren komplett ignoriert; jetzt wird nur unser Plugin wieder aufgenommen).
- **Grund:** Null Änderungen an Python-/Vue-Kerncode für die Registrierung → Upstream-Merges bleiben konfliktfrei. Der Mechanismus ist offiziell von Tandoor vorgesehen.
- **Hinweis:** Der App-Label ist `cookbook_ext`, der Python-Pfad `recipes.plugins.cookbook_ext`.

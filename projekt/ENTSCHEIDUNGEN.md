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

## E4 – Decken CookLog und Kommentare unsere Bewertungen ab? (2026-10-10)

- **Anforderung:** pro Rezept beliebig viele Bewertungen (1–5 Sterne), jeweils mit Datum, Kommentar und optionalen Fotos.
- **Befund im Code:**
  - `CookLog` (recipe, rating int, comment Text, servings, created_by, created_at **editierbar**) – beliebig viele pro Rezept und Benutzer. Das Vue-3-Frontend nutzt CookLog bereits genau so („Aktivität" mit Sternen, Kommentar, Datum in `RecipeActivity.vue`), und Tandoors Suche/Filter nach Bewertung bauen darauf auf (`Recipe.rating` = Durchschnitt der CookLogs).
  - `Comment` (recipe, text) – Altlast aus Tandoor 1, hat weder Sterne noch Datum-Eingabe und wird im Vue-3-Frontend nicht mehr verwendet.
  - **Fotos:** gibt es bei keinem der beiden.
  - Kleinere Lücken: `rating` ist nicht auf 1–5 beschränkt (nur `int`), und `Recipe.rating` zeigt den Schnitt **nur des aktuellen Benutzers**.
- **Optionen:** (a) eigene Tabelle `Review` (dupliziert CookLog, Tandoors Suche nach Sternen würde sie nicht kennen). (b) CookLog als Bewertung nutzen + eigene Tabelle nur für Fotos. (c) Kommentare erweitern.
- **Wahl:** (b) **CookLog = Bewertung**. Zusätzlich in `cookbook_ext` ein Model **`CookLogPhoto`** (cook_log FK, Bild, space, created_by) für beliebig viele Fotos pro Bewertung. Die Begrenzung auf 1–5 Sterne und der Haushalts-Durchschnitt (alle Benutzer, mit Anzahl) kommen über einen eigenen, schlanken Endpunkt bzw. die UI. `Comment` wird nicht genutzt.
- **Grund:** keine Doppelung, Tandoors vorhandene Funktionen (Filter „Bewertung ≥ 4", „zuletzt gekocht", Aktivität) bleiben wirksam, nur die echte Lücke (Fotos) wird ergänzt.
- **Umsetzung:** Das Foto-Model kommt mit Phase 4/5 (Backend-Teil in Phase 4, UI in Phase 5 „Bewertung oder Foto hinzufügen").

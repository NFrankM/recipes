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

## E5 – Datenmodell „Unsere Version" nach Abgleich mit Tandoor (2026-10-10)

Abweichungen vom Entwurf in CLAUDE.md und warum:

1. **Zutaten hängen in Tandoor an Schritten**, nicht am Rezept (`Recipe.steps` → `Step.ingredients`). Deshalb hat `VariantIngredientChange` zusätzlich ein Feld **`step`** (für `add`: in welchen Schritt die neue Zutat gehört; leer = in den letzten Schritt) und **`order`** (Position).
2. **„Menge ändern" ist kein eigener Typ**, sondern `replace`, bei dem nur `amount` (und ggf. `unit`) gesetzt ist. Bei `replace` gilt: leeres Feld = Originalwert behalten. So bleibt es bei den drei Aktionen `replace | add | remove` aus dem Entwurf, und eine einzige Änderung kann Zutat und Menge gleichzeitig ändern.
3. **`on_delete=SET_NULL`** für `ingredient`/`step`: Wird das Originalrezept später bearbeitet und eine Zutat gelöscht, verschwindet unsere Änderung nicht still, sondern wird als „verwaist" gemeldet (`orphaned` in der API) und kann in der UI aufgeräumt werden.
4. **Zusatzschritte** = `VariantStepNote` ohne `step`; `position` = Index in der Original-Schrittliste, **vor** dem der neue Schritt eingefügt wird (≥ Anzahl Schritte → am Ende). Zusätzlich optional `time` (Minuten) für Timer im Kochmodus.
5. **`space`-FK auf allen Models** + `ScopedManager` (Tandoor-Standard, Schutz gegen Space-übergreifende Zugriffe). Der Space wird beim Speichern aus dem Rezept übernommen.
6. **`is_default`**: höchstens eine Standard-Variante pro Rezept (DB-Constraint). Die Rezeptansicht öffnet dann direkt „Unsere Version".
7. **Rechte:** Varianten sind Haushaltssache – alle Benutzer (Gruppe `user`) des Spaces, die das Rezept sehen dürfen, dürfen die Variante bearbeiten (nicht nur der Ersteller). Gäste nur lesen.
8. **Einkaufsliste:** Einträge aus geänderten/ergänzten Zutaten werden **ohne** Verweis auf die Original-Zutat (`ingredient=None`) angelegt, unveränderte mit Verweis. Grund: Tandoor skaliert beim späteren Ändern der Portionen anhand `ingredient.amount` – das wäre bei geänderten Mengen falsch. Nachteil: Ändert man auf der Einkaufsliste nachträglich die Portionen, werden geänderte/ergänzte Einträge nicht mitskaliert (wie bei Tandoors manuellen Einträgen).

## E6 – Neue Rezeptansicht als Standard, ohne Tandoors Router zu ändern (2026-10-10)

- **Frage:** Die neue Ansicht soll unter `/recipe/<id>` erscheinen und alle bestehenden Links (Karten, Suche, Essensplan) sollen dorthin führen. Tandoors Routing steht in `apps/tandoor/main.ts` (Kern).
- **Optionen:** (a) `main.ts` ändern. (b) eigene URL (`/r/<id>`) – Tandoors Links zeigen dann weiter auf die alte Ansicht. (c) Plugin-Route mit **demselben Namen** `RecipeViewPage`: vue-router entfernt beim Hinzufügen einer Route mit vorhandenem Namen die alte (`addRoute` → `removeRoute(name)`), Plugin-Routen werden nach Tandoors Routen hinzugefügt.
- **Wahl:** (c). Tandoors Ansicht bleibt als `RecipeViewPageTandoor` unter `/recipe/<id>/klassisch` erreichbar (Menü „Klassische Ansicht"). Share-Links (`?share=`) und nicht angemeldete Besucher werden automatisch dorthin umgeleitet, weil nur Tandoors Ansicht Share-Links kann.
- **Risiko:** Verhalten hängt an vue-router (getestet mit 4.6.4). Falls ein Upstream-Update das ändert, zeigt `/recipe/<id>` wieder Tandoors Ansicht – nichts geht kaputt. Prüfen nach Updates: Rezept öffnen → erscheint das große Foto mit Sheet?

## E7 – Kleine Design-Entscheidungen in der Rezeptansicht (2026-10-10)

- **App-Bar ausgeblendet** auf der Rezeptseite (Klasse `rz-immersive` am `<html>`), damit das Foto bis oben reicht wie im Mockup; Zurück- und Menü-Button liegen als runde weiße Buttons auf dem Foto. Untere Leiste bleibt.
- **Zutatenliste flach** über alle Schritte (wie Mela), Überschriften-Zutaten als kleine Zwischenzeilen. Die Zuordnung zu Schritten bleibt im Datenmodell.
- **„Anpassen"-Modus** statt Dauer-Bearbeitung: Erst nach Tippen auf „Anpassen" sind Zutaten/Schritte antippbar – verhindert versehentliche Änderungen beim Kochen.
- **Mengen im Editor** gelten für die aktuell eingestellten Portionen und werden intern auf die Grundportionen umgerechnet.
- **Badges:** „geändert" gefüllt, „ergänzt" als Outline, entfernte Zutaten nur im Anpassen-Modus (durchgestrichen) sichtbar; geänderte zeigen klein „statt 200 g Mehl".
- **Einkaufsliste im Original-Modus** nutzt Tandoors vorhandenen Endpunkt, in „Unsere Version" unseren.

## E8 – Phase 6: Übersicht, Navigation, Kochmodus, Einkauf, Import (2026-10-11)

- **Übersicht ersetzt die Startseite** (Routenname `StartPage`, wie E6). Tandoors Startseite (Essensplan-Tag, Zufallsrezepte) bleibt unter `/start-klassisch` und im ⋯-Menü erreichbar. Filter-Chips: Alle, Unsere Versionen, Gut bewertet (≥ 4 Sterne), Neu, dann bis zu 12 Schlagwörter. Sterne auf den Karten = Haushalts-Schnitt (`/api/recipe-rating/`).
- **Untere Navigation** (Rezepte, Suche, Einkauf, Import, mit Beschriftung und Strich-Icons) braucht einen kleinen Hook in `Tandoor.vue` (CORE_CHANGES.md) – ohne geht es nicht, weil Plugins sonst nichts ins Layout rendern können. „Suche" führt zu Tandoors erweiterter Suche (mächtige Filter, kein Grund für einen Nachbau). Essensplan, Bücher, Einstellungen sind über das ⋯-Menü der Übersicht erreichbar.
- **Einkaufsliste:** eigene schlanke Seite `/einkauf` auf Tandoors Daten (`ShoppingListEntry`): gleiche Zutat + Einheit aus mehreren Rezepten zusammengefasst, nach Supermarkt-Kategorie gruppiert (ohne Kategorie → „Sonstiges"), Antippen hakt alle zusammengefassten Einträge ab, Rezepte auf der Liste als Chips (entfernbar), Artikel per Freitext („2 Zitronen", Tandoors Zutaten-Parser). Aktualisiert sich alle 30 s und beim Zurückkehren in die App. **Nicht** nachgebaut: Supermarkt-Sortierung, mehrere Listen, Offline-Warteschlange, Verschieben – dafür bleibt Tandoors Liste unter `/shopping` (Menü-Link).
- **Kochmodus** `/recipe/<id>/kochen?variant=&servings=`: ein Schritt pro Bildschirm, 22 px Text, Zutaten des Schritts oben, Notizen, Wischen oder Buttons. Timer aus Zeitangaben im Text („6–8 Minuten" → 6 Min., „1,5 Std."), sonst aus der Schrittdauer; mehrere Timer parallel, Alarm per Vibration + Ton. **Wake Lock** wird angefordert und nach App-Wechsel erneuert – funktioniert nur über HTTPS (`tailscale serve`, siehe SETUP_LXC.md); das Topf-Symbol oben rechts ist blau, wenn der Bildschirm anbleibt.
- **Import** `/import`: URL (mit „Einfügen"-Knopf) → Vorschau (Bildauswahl, Name editierbar, Schlagwörter an/aus, Zutaten, Schritte, Duplikat-Hinweis) → speichern über Tandoors vorhandene Endpunkte. `?url=` startet direkt (für eine spätere „Teilen"-Funktion). Andere Importarten → Link auf Tandoors Import.
- **Frontend-Tests** ohne neue Abhängigkeit: Nodes eingebauter Testrunner (`node --experimental-strip-types --test …`), damit `package.json`/`yarn.lock` unverändert bleiben.

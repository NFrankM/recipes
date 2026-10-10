# Änderungen am Tandoor-Kern

Hier wird jede Änderung an Tandoor-eigenen Dateien (außerhalb unserer Erweiterungs-App, eigener Vue-Komponenten, `deploy/` und `projekt/`) festgehalten. So bleibt nachvollziehbar, wo es beim Mergen von Upstream-Updates Konflikte geben kann.

| Datum | Datei | Änderung | Grund |
|---|---|---|---|
| 2026-10-10 | `CLAUDE.md`, `PROMPTS.md`, `projekt/` | neu angelegt | Projektkontext und Arbeitsplan (kein Kerncode) |
| 2026-10-10 | `.gitignore` | `/recipes/plugins` → `/recipes/plugins/*` + `!/recipes/plugins/cookbook_ext/`, ebenso für `vue3/src/plugins`; `.tools/` ergänzt | Unsere App liegt als Tandoor-Plugin in den bisher komplett ignorierten Plugin-Ordnern (E3); `.tools/` = lokale Toolchains (E1). Bei Merge-Konflikt: unsere Zeilen behalten. |
| 2026-10-11 | `vue3/src/apps/tandoor/Tandoor.vue` | 3 Zeilen **ergänzt** (keine geändert): Import von `TANDOOR_PLUGINS`, `pluginLayoutComponents`, `<component v-for …>` nach `</v-bottom-navigation>` | Generischer Plugin-Hook „Layout-Komponenten": Unser Plugin rendert darüber die eigene untere Navigation (Rezepte, Suche, Einkauf, Import). Tandoors Leiste wird per CSS ausgeblendet. Bei Merge-Konflikt: die drei markierten Zeilen („Rezept-App") wieder einsetzen. |
| 2026-10-11 | `vue3/src/types/Plugins.ts` | 1 Zeile ergänzt: optionales Feld `layoutComponents?: Component[]` im Typ `TandoorPlugin` | Typ für den Hook oben |

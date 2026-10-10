# API der Erweiterungen (`cookbook_ext`)

Alle Endpunkte hängen in Tandoors `/api/` (über das Plugin-System) und nutzen dieselbe Anmeldung (Session/Token) und dieselben Space-Regeln. OpenAPI: `/openapi/`, Doku-UI: `/docs/api/`.

**Rechte:** Lesen darf, wer das Rezept sehen darf (auch Gäste). Schreiben: Gruppe `user` oder höher, Rezept sichtbar. Varianten sind Haushaltssache – jeder Benutzer im Space darf sie bearbeiten. Fremde Spaces sehen nichts (404/leer).

## Varianten

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/recipe-variant/?recipe=<id>` | Varianten eines Rezepts inkl. `ingredient_changes` und `step_notes` |
| POST | `/api/recipe-variant/` | `{recipe, name="Unsere Version", is_default}` – `is_default=true` setzt andere Varianten des Rezepts auf false |
| GET/PATCH/DELETE | `/api/recipe-variant/<id>/` | Rezept ist nach dem Anlegen nicht änderbar |
| GET | `/api/recipe-variant/<id>/effective/?servings=<n>` | effektive Fassung (siehe unten) |
| POST | `/api/recipe-variant/<id>/shopping/` | `{servings?, mealplan?}` → setzt die effektiven Zutaten auf die Einkaufsliste. Antwort `{msg, list_recipe, entries}` |

## Zutaten-Änderungen

`/api/variant-ingredient-change/?variant=<id>` (CRUD)

```json
{"variant": 1, "action": "replace", "ingredient": 17, "amount": 250}                 // Menge ändern
{"variant": 1, "action": "replace", "ingredient": 17, "food_name": "Dinkelmehl"}     // Zutat ersetzen (Name → wird angelegt, falls neu)
{"variant": 1, "action": "add", "step": 5, "food": 3, "amount": 1, "unit_name": "Päckchen", "note": "", "order": 10}
{"variant": 1, "action": "remove", "ingredient": 18}
```

Bei `replace` gilt: nicht gesetzte Felder (`food`, `amount`, `unit`, `note`) behalten den Originalwert. Lesefelder `food_data`/`unit_data` = `{id, name, plural_name}`.

## Schritt-Notizen und Zusatzschritte

`/api/variant-step-note/?variant=<id>` (CRUD)

```json
{"variant": 1, "step": 5, "text": "Pfanne richtig heiß werden lassen"}      // „Unsere Notiz" an Schritt 5
{"variant": 1, "position": 1, "text": "Teig 20 Minuten ruhen lassen", "time": 20}  // Zusatzschritt vor dem 2. Original-Schritt
```

## Effektive Fassung

`GET /api/effective-recipe/<recipe_id>/?variant=<id>&servings=<n>` – ohne `variant` kommt das Original im gleichen Format (für den Umschalter „Original / Unsere Version").

```json
{
  "recipe": 1, "variant": 2, "variant_name": "Unsere Version",
  "base_servings": 4, "servings": 6.0, "factor": 1.5,
  "steps": [
    {
      "id": 5, "name": "Teig", "instruction": "…", "instructions_markdown": "<p>…</p>", "time": 5,
      "is_added": false, "added_note": null,
      "notes": [{"id": 3, "text": "…", "time": 0, "position": 0}],
      "ingredients": [
        {"status": "changed", "ingredient": 17, "change": 9,
         "food": {"id": 4, "name": "Dinkelmehl", "plural_name": null}, "unit": {"id": 1, "name": "g", "plural_name": null},
         "amount": 300.0, "base_amount": 200.0, "note": "", "is_header": false, "no_amount": false, "order": 0,
         "original": {"food": {"id": 2, "name": "Mehl"}, "unit": {"id": 1, "name": "g"}, "amount": 300.0}},
        {"status": "added", "ingredient": null, "change": 10, "…": "…"}
      ],
      "removed_ingredients": [{"status": "removed", "…": "…"}]
    },
    {"id": null, "is_added": true, "instruction": "Teig 20 Minuten ruhen lassen", "time": 20, "added_note": {"id": 4, "…": "…"}, "…": "…"}
  ],
  "orphaned_changes": [], "orphaned_notes": []
}
```

- `status`: `original` | `changed` (Badge „geändert") | `added` (Badge „ergänzt") | `removed` (nur in `removed_ingredients`)
- `amount` ist bereits auf `servings` skaliert; `base_amount` ist die Menge für `base_servings`
- `orphaned_*`: Änderungen/Notizen, deren Original-Zutat/-Schritt inzwischen gelöscht wurde

## Bewertungen

Bewertungen sind Tandoors **CookLogs** (`/api/cook-log/`, Felder `recipe, rating, comment, servings, created_at`), siehe E4.

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/recipe-rating/?recipe=1&recipe=2` | `[{recipe, average, count, cooked}]` – Durchschnitt/Anzahl über **alle** Benutzer des Spaces (Tandoors `recipe.rating` zählt nur die eigenen) |
| GET | `/api/cook-log-photo/?recipe=<id>` bzw. `?cook_log=<id>` | Fotos zu Bewertungen |
| POST | `/api/cook-log-photo/` | multipart: `cook_log`, `image` (jpg/png/webp/gif; wird wie Rezeptbilder verkleinert und von EXIF-Daten befreit). Nur zur eigenen Bewertung. |
| DELETE | `/api/cook-log-photo/<id>/` | Besitzer oder Admin |

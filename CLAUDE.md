# Rezept-App (Tandoor-Fork)

Eigene Rezept-App für den Haushalt, aufgebaut als Fork von **Tandoor Recipes 2.x**.
Hauptnutzerin ist meine Frau. Sie nutzt die App vor allem am Handy. Optik und Bedienbarkeit sind genauso wichtig wie Funktionen.

## Infrastruktur

- **Hosting:** Proxmox, eigene LXC (Debian) mit Docker + Docker Compose
- **Zugriff:** nur über Tailscale (kein Port-Forwarding ins Internet). Tailscale läuft in der LXC.
- **Datenbank:** PostgreSQL (bewusst nicht MySQL: Tandoors Trigram-Ähnlichkeitssuche braucht PostgreSQL)
- **Medien:** Bilder als Docker-Volume bzw. Bind-Mount
- **Backup:** nächtlich `pg_dump` + Medienordner auf NAS im Intranet, Aufbewahrung rotierend; zusätzlich Proxmox-Backup der LXC
- Tandoor-Migrationen lassen sich **nicht zurückrollen** → vor jedem Update ein Backup und einen Restore-Test machen

## Basis: Tandoor

- Repo: https://github.com/TandoorRecipes/recipes (Fork in meinem GitHub)
- Backend: Django, Frontend: Vue 3 + Vuetify im Ordner `vue3/`
- Lizenz: AGPL-3.0. Privater Betrieb ist ok. Bei Veröffentlichung muss der Quellcode angeboten werden.
- Bereits vorhanden und **nicht neu bauen**: URL-Import (ld+json/microdata), Zutaten-/Food-Stammdaten, Einheiten, Skalierung, Suche, Einkaufslisten, Tags, Bilder, Kochbücher

## Repository

- `origin` = https://github.com/NFrankM/recipes (unser Fork), `upstream` = https://github.com/TandoorRecipes/recipes
- `develop` = unverändertes Upstream (nur per „Sync fork" bzw. `git merge upstream/develop` aktualisieren)
- `main-custom` = unser Arbeitsbranch; Upstream-Updates hier hineinmergen
- Unsere eigene Doku liegt in `projekt/` (nicht in `docs/`, das ist Tandoors mkdocs-Doku)
- Phasen-Prompts: `PROMPTS.md`

## Arbeitsprinzipien

1. **Kern so wenig wie möglich ändern.** Eigene Funktionen gehören in eine eigene Django-App (`cookbook_ext` o. ä.) und eigene Vue-Komponenten/Views. Upstream-Updates sollen weiterhin mergebar bleiben.
2. Unvermeidbare Kernänderungen klein halten und in `projekt/CORE_CHANGES.md` mit Grund dokumentieren.
3. Vor größeren Änderungen einen kurzen Plan zeigen und auf mein OK warten.
4. In kleinen, lauffähigen Schritten arbeiten, mit Tests für eigene Models und APIs.
5. Kommunikation, Commit-Messages und UI-Texte auf Deutsch.
6. Keine Secrets ins Repo. `.env` bleibt lokal, nur `.env.example` wird committet.

## Eigene Funktionen

### Hooks = „Unsere Version" eines Rezepts
Ergänzungen und Änderungen, die **über** dem Originalrezept liegen. Das Original bleibt unverändert.
- Zutat ersetzen, Menge ändern, Zutat ergänzen oder entfernen
- Notiz an einzelnen Schritten, zusätzlicher Schritt
- In der Rezeptansicht gibt es den Umschalter **Original / Unsere Version**. Geänderte Zutaten tragen das Badge „geändert", neue das Badge „ergänzt".
- Skalierung und Einkaufsliste nutzen die gewählte Version.

Datenmodell (Entwurf, vor Umsetzung gegen Tandoors Models prüfen):
- `RecipeVariant` (recipe FK, name, created_by, created_at, is_default)
- `VariantIngredientChange` (variant FK, ingredient FK nullable, action: replace|add|remove, food FK, amount, unit FK, note)
- `VariantStepNote` (variant FK, step FK nullable, position, text)

### Bewertungen & Ergänzungen
Pro Rezept beliebig viele Bewertungen (1–5 Sterne), jeweils mit Datum, Kommentar und optionalen Fotos.
Zuerst prüfen, ob Tandoors `CookLog` und Kommentare das abdecken. Nur wenn nicht, eine eigene Tabelle anlegen.

## Design

Stil angelehnt an die App Mela: klar, ruhig, hell. Weiß und Blaugrau, dunkle Schrift, große Fotos, viel Weißraum.

**Farben**
| Token | Wert | Verwendung |
|---|---|---|
| bg | `#FFFFFF` | Hintergrund |
| surface | `#EEF2F5` | Suchfeld, Chips, Segment-Control |
| surface-soft | `#F2F5F8` | Notizen, hervorgehobene Zeilen |
| border | `#E3E9EE` / `#C9D4DD` | Trennlinien / Outline-Buttons |
| ink | `#1E2A35` | Überschriften, Text |
| ink-2 | `#2E3E4C` | Fließtext |
| muted | `#52687A` | Metadaten |
| accent | `#3E5A70` | Primärbuttons, aktive Tabs, Badges |
| accent-dark | `#2F4A5E` | Sterne, Hover |

**Typografie:** Plus Jakarta Sans (400/500/600/700). Titel 28–32 px bold, H2 18–20 px bold, Text 15 px.
**Formen:** Radius 14–16 px für Karten und Felder, 24 px für das Sheet über dem Foto, Chips als Pills. Touch-Targets mindestens 44 px.
**Kein:** Farbverläufe, Emojis als Icons, harte Schatten. Icons als schlichte Strich-SVGs.

**Screens (Mockup existiert):**
- Übersicht: Titel + Plus-Button, Suchfeld, Filter-Chips, 2-spaltiges Kartenraster, untere Leiste (Rezepte, Suche, Einkauf, Import)
- Rezeptansicht: großes Foto, abgerundetes Sheet darüber, Tags, Sterne, Segment „Original / Unsere Version", Portions-Stepper, Zutatenliste, Button „Auf die Einkaufsliste", nummerierte Schritte mit Notizen, Bewertungen
- Noch offen: Kochmodus, Einkaufsliste, Import-Dialog

Umsetzung über ein eigenes Vuetify-Theme plus eigene Komponenten. Kein separates CSS-Framework.

# Architektur – was für uns relevant ist

Stand: Tandoor `develop` (Oktober 2026, nach 2.6.15). Pfade relativ zum Repo-Root.

## Überblick

```
recipes/            Django-Projekt (settings.py, urls.py, Plugin-Lader)
  plugins/          Plugin-Ordner – hier liegt UNSERE App cookbook_ext
cookbook/           Tandoors Haupt-App (Models, API, Helper, Tests)
  models.py         alle Models
  serializer.py     DRF-Serializer
  views/api.py      DRF-ViewSets (/api/…)
  urls.py           API-Router (+ Einbindung der Plugin-Router)
  helper/           permission_helper.py, shopping_helper.py, scope_middleware.py, …
  tests/            pytest-Tests + Fixtures (conftest.py)
vue3/               Vue-3-Frontend (Vite, Vuetify 3, Pinia, vue-router, vue-i18n)
  src/plugins/      Frontend-Plugin-Ordner – hier liegt UNSER Frontend-Teil
cookbook/static/vue3/   Build-Ausgabe von vue3 (gitignored), wird von django-vite eingebunden
```

Ein Request: nginx (im Container) → gunicorn → Django. Django liefert für alle Nicht-API-Pfade dieselbe Vue-Single-Page-App aus (Catch-all in `cookbook/urls.py`); das Frontend spricht ausschließlich mit `/api/…`.

## Erweiterungspunkte (Plugin-System) – wichtigste Erkenntnis

Tandoor hat ein offizielles Plugin-System, das wir nutzen (Entscheidung E3):

**Backend** – `recipes/settings.py` durchsucht `recipes/plugins/*/apps.py`:
- die (alphabetisch) zweite Klasse im Modul `apps` wird als AppConfig genommen und an `INSTALLED_APPS` angehängt
- `base_url` → `recipes/urls.py` hängt `<plugin>/urls.py:urlpatterns` dort ein
- `api_router_name` → `cookbook/urls.py` übernimmt die Registrierungen dieses DRF-Routers in den `/api/`-Router
- Fehler beim Laden werden **still** geschluckt (nur mit `DEBUG=1` sichtbar) → unser Test `test_plugin.py` prüft, dass das Plugin geladen ist

**Frontend** – `vue3/src/types/Plugins.ts` lädt per `import.meta.glob('@/plugins/*/plugin.ts')` alle Plugins. Ein Plugin (`TandoorPlugin`) liefert:
- `routes` (werden in `apps/tandoor/main.ts` an den Router angehängt), `settingRoutes`
- `navigationDrawer`, `bottomNavigation`, `userNavigation` (Menüeinträge, siehe `composables/useNavigation.ts`)
- `defaultLocale`, `localeFiles` (Übersetzungen, siehe `i18n.ts`)
- `databasePageComponent`, `settingsComponent`, `buildInputs`

Beide Plugin-Ordner standen komplett in `.gitignore` (Tandoor erwartet Plugins als eigene Git-Repos). Wir nehmen per Negation nur `cookbook_ext` wieder auf.

## Models (cookbook/models.py)

Alle Inhalte gehören zu genau einem **Space** (Mandant). Fast jedes Model hat `space = FK(Space)` und `objects = ScopedManager(space='space')` (django-scopes): Abfragen außerhalb eines `scope(space=…)` werfen einen Fehler – Schutz gegen Datenlecks zwischen Spaces.

| Model | Wichtige Felder | Bemerkung für uns |
|---|---|---|
| `Recipe` | name, description, servings (int), servings_text, image, keywords (M2M Keyword), **steps (M2M Step)**, working_time, waiting_time, private, shared (M2M User), created_by, space | `rating` und `last_cooked` sind **Annotationen** (RecipeManager.with_rating/with_last_cooked), keine Felder. `rating` = Durchschnitt der CookLogs **des aktuellen Users**. |
| `Step` | name, instruction (Markdown/Jinja: `{{ scale(…) }}`), **ingredients (M2M Ingredient)**, time (Minuten), order, file, step_recipe (Unterrezept), show_as_header, show_ingredients_table | Ein Step gehört über `recipe_set` zu einem Rezept (M2M, praktisch 1:n). |
| `Ingredient` | food (FK, nullable), unit (FK, nullable), amount (Decimal 32/16), note, is_header, no_amount, order, original_text | **Kein direkter FK auf Recipe** – Weg: `Ingredient → step_set → recipe_set`. Abfrage: `Ingredient.objects.filter(step__recipe=r)`. |
| `Food` | name, plural_name, supermarket_category, ignore_shopping, onhand_users, substitute, recipe (Food kann auf ein Rezept zeigen), properties | Baum (treebeard MP_Node). Eindeutig pro Space über name. |
| `Unit` | name, plural_name, base_unit | Eindeutig pro Space über name. Umrechnung über `UnitConversion`. |
| `Keyword` | name, description | Baum; Tags der Rezepte. |
| `CookLog` | recipe, **rating (int, nullable)**, servings, **comment (Text)**, created_by, **created_at (editierbar, default now)** | = „ich habe das gekocht" + Bewertung. Grundlage für unsere Bewertungen (E4). |
| `Comment` | recipe, text, created_by, created_at | Alt (Tandoor 1). Das Vue-3-Frontend nutzt es nicht mehr; API `/api/comment/` existiert noch. |
| `ViewLog` | recipe, created_by, created_at | „zuletzt angesehen". |
| `ShoppingListRecipe` | recipe, mealplan, servings (Decimal), name, created_by | Klammer „Rezept X für n Portionen auf der Liste". |
| `ShoppingListEntry` | list_recipe (FK), food (Pflicht), unit, **ingredient (FK, nullable)**, amount, checked, shopping_lists (M2M), completed_at, delay_until, created_by | Einkaufslisteneintrag. Ohne `ingredient` wird ein Eintrag beim Portionen-Ändern nicht neu skaliert. |
| `ShoppingList` | name, color | Mehrere benannte Listen (z. B. pro Laden). |
| `SupermarketCategory`, `Supermarket`, `SupermarketCategoryRelation` | | Gruppierung/Sortierung der Einkaufsliste. |
| `UserFile` | name, file, created_by, space | Allgemeine Dateiablage (Bilder in Schritten). |
| `UserSpace` | user, space, groups (guest/user/admin), active | Mitgliedschaft + Rolle im Space. |
| `Household` | name, space | Benutzer eines Haushalts teilen Einkaufsliste/Vorrat. |

## API-Struktur

- Django REST Framework, Router in `cookbook/urls.py`, alles unter `/api/<name>/` (z. B. `/api/recipe/`, `/api/cook-log/`, `/api/shopping-list-entry/`). OpenAPI-Schema: `/openapi/`, Doku-UI unter `/docs/api/`.
- Typisches ViewSet (`cookbook/views/api.py`):
  ```python
  class CookLogViewSet(LoggingMixin, viewsets.ModelViewSet):
      queryset = CookLog.objects
      serializer_class = CookLogSerializer
      permission_classes = [((CustomIsOwner | CustomIsAdmin) | (IsReadOnlyDRF & CustomIsUser)) & CustomTokenHasReadWriteScope]
      pagination_class = DefaultPagination
      def get_queryset(self):
          return self.queryset.filter(space=self.request.space)
  ```
- Serializer setzen `created_by`/`space` in `create()` aus `self.context['request']`.
- Rezept-Detail `GET /api/recipe/<id>/` liefert Steps inkl. Ingredients (verschachtelt) und `rating`.
- Einkaufsliste aus Rezept: `PUT /api/recipe/<id>/shopping/` mit `{servings, ingredients?, list_recipe?, mealplan?}` → `RecipeShoppingEditor` (`cookbook/helper/shopping_helper.py`) legt `ShoppingListRecipe` + `ShoppingListEntry` (amount × servings/recipe.servings) an.
- Frontend-Client: generiert mit openapi-generator (`vue3/src/openapi/`, `ApiApi`), CSRF-Header wird in `runtime.ts` gesetzt. Für unsere eigenen Endpunkte nutzen wir einen kleinen eigenen `fetch`-Client, damit der generierte Kern-Code nicht neu generiert werden muss.

## Berechtigungen (Space/User)

1. **Space-Ermittlung:** `cookbook/helper/scope_middleware.py` setzt für eingeloggte Benutzer `request.space` (aktiver `UserSpace`) und öffnet `scope(space=…)` für den Request.
2. **Rollen:** Gruppen `guest` < `user` < `admin` pro UserSpace. Prüfung über `has_group_permission(request, ['user'])` (höhere Gruppen erfüllen niedrigere).
3. **DRF-Permission-Klassen** (`cookbook/helper/permission_helper.py`): `CustomIsGuest`, `CustomIsUser`, `CustomIsAdmin`, `CustomIsOwner` (created_by/user == request.user), `CustomIsShared`, `CustomIsHousehold`, `CustomRecipePermission` (private Rezepte nur Ersteller/geteilte User; Gäste nur lesend), immer kombiniert mit `CustomTokenHasReadWriteScope` (API-Token-Scopes).
4. **Queryset-Filter:** jedes ViewSet filtert zusätzlich `space=request.space`; Objekte aus anderen Spaces sind dadurch 404.

Für unsere Models heißt das: `space`-FK + `ScopedManager`, Queryset auf `request.space` filtern, Rezept-Sichtbarkeit wie `CustomRecipePermission` prüfen.

## Frontend `vue3/`

- **Einstieg:** `src/apps/tandoor/main.ts` – Routing-Tabelle (vue-router, `createWebHistory`), Pinia, Vuetify, i18n, Plugin-Routen.
- **Wichtige Routen:** `/` StartPage, `/recipe/:id` RecipeViewPage, `/shopping` ShoppingListPage, `/recipe/import` RecipeImportPage, `/mealplan`, `/books`, `/settings/*`, `/list/:model`, `/edit/:model/:id`.
- **Layout:** `src/apps/tandoor/Tandoor.vue` – App-Bar, Navigation-Drawer (ab `lg`), `v-bottom-navigation` auf dem Handy (Rezepte, Essensplan, Einkauf, Menü).
- **Theme:** `src/vuetify.ts` – `createVuetify` mit Themes `light`/`dark` (Tandoor-Braun `#b98766`), globale Komponenten-Defaults, Font-Awesome-Icons (`defaultSet: 'fa'`). Umschalten light/dark in `stores/UserPreferenceStore.ts:updateTheme()` per `theme.change('light'|'dark')` anhand der Benutzereinstellung.
- **Komponenten:** `components/display/` (RecipeView, StepView, IngredientsTable(Row), RecipeCard, RecipeActivity = CookLogs/Bewertungen …), `components/dialogs/` (AddToShoppingDialog, RecipeScalingDialog …), `components/inputs/`, `components/model_editors/`.
- **Stores (Pinia):** `UserPreferenceStore` (User-/Server-Einstellungen, Theme), `ShoppingStore`, `MealPlanStore`, `MessageStore` (Snackbar/Fehler).
- **Build:** `vite build` → `cookbook/static/vue3/` + `manifest.json`; Django bindet per `django-vite` ein. Dev-Modus: Läuft der Vite-Server auf :5173 und ist `DEBUG=1`, nutzt Django automatisch HMR.
- **Übersetzungen:** `src/locales/*.json`; Plugins können eigene Locale-Dateien liefern.

## Docker-Image (für Phase 7)

`Dockerfile`: `python:3.13-alpine`, installiert requirements, `COPY . ./` (inkl. `recipes/plugins/`), nginx + gunicorn, Start über `boot.sh` (migrate, collectstatic, gunicorn). Das Frontend wird in der CI (`.github/workflows/build-docker.yml`, Node 22, yarn) **vor** dem Docker-Build gebaut und liegt dann in `cookbook/static/vue3`. `PLUGINS_BUILD=1` würde beim Start neu bauen (nicht nötig, wenn wir im Image bauen).

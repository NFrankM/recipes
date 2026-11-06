from django.apps import AppConfig


class CookbookExtConfig(AppConfig):
    """
    Eigene Erweiterungen der Rezept-App (Varianten „Unsere Version", Bewertungsfotos …).

    Wird über Tandoors Plugin-System geladen (recipes/settings.py durchsucht recipes/plugins/),
    dadurch sind keine Änderungen an INSTALLED_APPS oder den Kern-URLs nötig.
    Hinweis: Tandoor nimmt per dir(modul)[1] die *zweite* Klasse in diesem Modul als AppConfig –
    deshalb hier nur AppConfig importieren und genau diese eine Klasse definieren.
    """
    name = 'recipes.plugins.cookbook_ext'
    label = 'cookbook_ext'
    verbose_name = 'Rezept-App Erweiterungen'
    default_auto_field = 'django.db.models.BigAutoField'

    VERSION = '0.1.0'
    website = 'https://github.com/NFrankM/recipes'
    github = 'https://github.com/NFrankM/recipes'

    # Nicht-API-URLs des Plugins (aktuell keine) werden unter /ext/ eingehängt
    base_url = 'ext/'
    # Router in urls.py, dessen ViewSets Tandoor in /api/ übernimmt
    api_router_name = 'api_router'

    def ready(self):
        # HTML-Fallback für den URL-Import (Seiten ohne vollständige schema.org-Daten)
        from cookbook.helper.recipe_url_import import recipe_import_postprocess
        from recipes.plugins.cookbook_ext.services.html_fallback import on_recipe_import
        from recipes.plugins.cookbook_ext.services.step_times import on_recipe_import as suggest_step_times
        recipe_import_postprocess.connect(on_recipe_import, dispatch_uid='cookbook_ext_html_fallback')
        # danach: Zeitangaben aus den (ggf. ergänzten) Schritten als Vorschlag für Step.time
        recipe_import_postprocess.connect(suggest_step_times, dispatch_uid='cookbook_ext_step_times')

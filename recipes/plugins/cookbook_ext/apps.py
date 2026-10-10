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

from django.apps import apps
from django.conf import settings


def test_plugin_ist_installiert():
    assert 'recipes.plugins.cookbook_ext.apps.CookbookExtConfig' in settings.INSTALLED_APPS
    assert apps.get_app_config('cookbook_ext').name == 'recipes.plugins.cookbook_ext'


def test_plugin_ist_in_plugin_liste():
    assert any(p['module'] == 'recipes.plugins.cookbook_ext' for p in settings.PLUGINS)

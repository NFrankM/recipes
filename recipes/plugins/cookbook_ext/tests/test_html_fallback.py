"""URL-Import: HTML-Fallback für Seiten ohne (vollständige) schema.org-Recipe-Daten."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from recipes.plugins.cookbook_ext.services.html_fallback import find_ingredients, find_instructions

FIXTURES = Path(__file__).parent / 'fixtures'
URL = 'api_recipe_from_source'


def _html(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


def _import_url(client, url, html):
    resp = MagicMock(ok=True, status_code=200, content=html.encode('utf-8'))
    with patch('cookbook.views.api.safe_request', return_value=resp):
        return client.post(reverse(URL), {'url': url}, content_type='application/json')


def _ingredients(recipe):
    return [i['original_text'] for s in recipe['steps'] for i in s['ingredients']]


def test_wdr_zutaten_aus_br_zeilen():
    lines, servings = find_ingredients(BeautifulSoup(_html('wdr_edamame.html'), 'html.parser'))
    assert lines[0] == '300 g Edamame (ohne Schote, nur Kerne)'
    assert 'Aufstrich' not in lines and 'Außerdem' not in lines  # Gruppenüberschriften sind keine Zutaten
    assert len(lines) == 18
    assert servings == 4


def test_wdr_absaetze_als_schritte_mit_kurzer_zeile_als_name():
    steps = find_instructions(BeautifulSoup(_html('wdr_edamame.html'), 'html.parser'))
    assert len(steps) == 5
    assert steps[-1]['name'] == 'Anrichten'
    assert steps[0]['instruction'].startswith('Am besten startet man mit den gepickelten Zwiebeln')


def test_wdr_import_ueber_api(u1_s1):
    r = _import_url(u1_s1, 'https://www1.wdr.de/verbraucher/rezepte/ulla-aufstrich-aus-edamame-100.html', _html('wdr_edamame.html'))
    assert r.status_code == 200, r.content
    recipe = r.json()['recipe']
    assert len(_ingredients(recipe)) == 18
    assert len(recipe['steps']) == 6  # Anleitung kommt hier vom recipe-scrapers-WDR-Scraper, nur die Zutaten vom Fallback
    assert 'Edamame' in recipe['name']
    food = recipe['steps'][0]['ingredients'][0]
    assert food['amount'] == 300 and food['unit']['name'] == 'g' and food['food']['name'].startswith('Edamame')


def test_duesentrieb_recipe_ohne_zutaten_und_anleitung(u1_s1):
    r = _import_url(u1_s1, 'https://duesentriebskitchen.ch/auberginen-tatar-vegi-tatar/', _html('duesentrieb_auberginen_tatar.html'))
    assert r.status_code == 200, r.content
    recipe = r.json()['recipe']
    assert recipe['name'] == 'Auberginen Tatar (Vegi Tatar)'
    assert _ingredients(recipe)[:2] == ['1,5 Auberginen (ca. 300g)', '4 Essiggurken']
    assert len(_ingredients(recipe)) == 9
    assert len(recipe['steps']) == 5
    assert recipe['servings'] == 2
    assert not any('PS:' in s['instruction'] for s in recipe['steps'])


HTML_OHNE_SCHEMA = """<html><head><title>Omas Brot</title></head><body><h1>Omas Brot</h1>
<h2>Zutatenliste</h2><ul><li>500 g Mehl</li><li>10 g Salz</li></ul>
<h2>Anleitung</h2><ol><li>Alles verkneten.</li><li>Backen.</li></ol><h2>Kommentare</h2><ul><li>Lecker!</li></ul></body></html>"""


def test_seite_ganz_ohne_schema(u1_s1):
    r = _import_url(u1_s1, 'https://example.org/omas-brot', HTML_OHNE_SCHEMA)
    assert r.status_code == 200, r.content
    recipe = r.json()['recipe']
    assert recipe['name'] == 'Omas Brot'
    assert _ingredients(recipe) == ['500 g Mehl', '10 g Salz']
    assert [s['instruction'] for s in recipe['steps']] == ['Alles verkneten.', 'Backen.']


def test_eingefuegtes_html_ohne_schema_kein_stacktrace(u1_s1):
    r = u1_s1.post(reverse(URL), {'data': HTML_OHNE_SCHEMA}, content_type='application/json')
    assert r.status_code == 200, r.content
    assert _ingredients(r.json()['recipe']) == ['500 g Mehl', '10 g Salz']


@pytest.mark.parametrize('how', ['url', 'data'])
def test_seite_ohne_rezept_gibt_meldung(u1_s1, how):
    html = '<html><body><h1>Impressum</h1><p>Nichts zu kochen.</p></body></html>'
    if how == 'url':
        r = _import_url(u1_s1, 'https://example.org/impressum', html)
    else:
        r = u1_s1.post(reverse(URL), {'data': html}, content_type='application/json')
    assert r.status_code == 400
    assert r.json()['error'] is True


def test_vollstaendiges_schema_bleibt_unveraendert(u1_s1):
    data = json.loads((FIXTURES / 'brot_howto_jsonld.json').read_text())
    r = u1_s1.post(reverse(URL), {'data': json.dumps(data)}, content_type='application/json')
    recipe = r.json()['recipe']
    assert len(_ingredients(recipe)) == 5 and len(recipe['steps']) == 4

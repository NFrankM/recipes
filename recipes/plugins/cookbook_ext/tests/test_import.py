"""URL-Import: Schritte aus schema.org HowToStep/HowToSection (Bug „id = …“ in importierten Schritten)."""
import json
from pathlib import Path

import pytest
from django.urls import reverse

from cookbook.helper.recipe_url_import import parse_instruction_steps, parse_instructions

FIXTURES = Path(__file__).parent / 'fixtures'


def _brot():
    return json.loads((FIXTURES / 'brot_howto_jsonld.json').read_text())


def _no_raw_objects(texts):
    for t in texts:
        assert '@id' not in t and "{'" not in t and '{"' not in t and 'id =' not in t, t


def test_howto_sections_rekursiv_mit_fallback():
    steps = parse_instruction_steps(_brot()['recipeInstructions'])
    assert [s['instruction'] for s in steps] == [
        'Alle Zutaten für den Sauerteig gut vermischen und 16 Stunden bei Raumtemperatur reifen lassen.',  # name
        'Sauerteig mit den restlichen Zutaten 8 Minuten kneten.',  # description
        'Teig 1 Std. gehen lassen.',  # text
        'Bei 250 °C fallend auf 220 °C 50 Minuten backen.',  # Section in Section, dict statt Liste
    ]
    assert [s['name'] for s in steps] == ['Roggensauer', 'Hauptteig', 'Stockgare', 'Backen']
    _no_raw_objects(s['instruction'] for s in steps)


@pytest.mark.parametrize('obj', [
    {'@type': 'HowToStep', '@id': 'https://x/#1', 'url': 'https://x/', 'image': 'https://x/a.jpg'},
    {'foo': 'bar'},
    object(),
    None,
    42,
])
def test_rohobjekte_landen_nie_im_schritt(obj):
    assert parse_instructions([obj]) == []


def test_strings_und_einzelner_string():
    assert parse_instructions(['Erst das.', '', 'Dann das.']) == ['Erst das.', 'Dann das.']
    assert parse_instructions('Alles in einem.') == ['Alles in einem.']


def test_name_als_doppelter_text_wird_nicht_schrittname():
    steps = parse_instruction_steps([{'@type': 'HowToStep', 'name': 'Teig kneten', 'text': 'Teig kneten, bis er glatt ist.'}])
    assert steps == [{'name': '', 'instruction': 'Teig kneten, bis er glatt ist.'}]


def test_api_import_brot_jsonld(u1_s1):
    r = u1_s1.post(reverse('api_recipe_from_source'), {'data': json.dumps(_brot())}, content_type='application/json')
    assert r.status_code == 200, r.content
    steps = r.json()['recipe']['steps']
    assert [s['name'] for s in steps] == ['Roggensauer', 'Hauptteig', 'Stockgare', 'Backen']
    assert len(steps[0]['ingredients']) == 5
    _no_raw_objects(s['instruction'] for s in steps)

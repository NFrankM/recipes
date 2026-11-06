"""Zeitangaben aus Schritttexten (Vorschlag für Step.time)."""
import json
from pathlib import Path

import pytest
from django.urls import reverse

from recipes.plugins.cookbook_ext.services.step_times import suggest_minutes


@pytest.mark.parametrize('text, minutes', [
    ('Den Teig 30 Minuten ruhen lassen.', 30),
    ('1 Std. gehen lassen', 60),
    ('Über Nacht im Kühlschrank gehen lassen.', 720),
    ('über Nacht (ca. 12 Stunden) reifen lassen', 720),
    ('Über Nacht kühl stellen, morgens 30 Min. akklimatisieren', 750),
    ('8 Minuten kneten, dann 1 Std. gehen lassen', 68),
    ('1 Std. 30 Min. backen', 90),
    ('1,5 Stunden gehen lassen', 90),
    ('1½ Stunden', 90),
    ('eine halbe Stunde ziehen lassen', 30),
    ('eine Stunde ruhen lassen', 60),
    ('2-3 Stunden gehen lassen', 180),
    ('2 bis 3 Std.', 180),
    ('Bei 250 °C 50 Minuten backen, nach 10 Minuten auf 220 °C reduzieren.', 50),
    ('Alle 30 Minuten dehnen und falten, insgesamt 2 h', 120),
    ('16 h bei Raumtemperatur', 960),
    ('Let rest for 20 minutes', 20),
    ('2 Tage im Kühlschrank', 2880),
    ('30 Sekunden mixen', 1),
    ('Mehl, Salz und 200 g Wasser verrühren.', 0),
    ('Tagliatelle in 2 l Wasser kochen.', 0),
    ('Keine Minute länger!', 0),
    ('', 0),
])
def test_suggest_minutes(text, minutes):
    assert suggest_minutes(text) == minutes


def test_import_schlaegt_zeiten_vor(u1_s1):
    data = json.loads((Path(__file__).parent / 'fixtures' / 'brot_howto_jsonld.json').read_text())
    r = u1_s1.post(reverse('api_recipe_from_source'), {'data': json.dumps(data)}, content_type='application/json')
    assert [s['time'] for s in r.json()['recipe']['steps']] == [960, 8, 60, 50]


TIMING = 'api:step-timing-list'


def _effective_steps(client, recipe):
    return client.get(reverse('api:effective-recipe-detail', args=[recipe.pk])).json()['steps']


def test_zeit_aktiv_warten_parallel_setzen(u1_s1, rezept):
    r = u1_s1.post(reverse(TIMING), {'step': rezept.s2.pk, 'time': 70, 'wait_time': 60, 'parallel': True}, content_type='application/json')
    assert r.status_code == 200, r.content
    rezept.s2.refresh_from_db()
    assert rezept.s2.time == 70  # Tandoors Feld = Gesamtdauer
    steps = _effective_steps(u1_s1, rezept.recipe)
    assert (steps[1]['time'], steps[1]['wait_time'], steps[1]['parallel']) == (70, 60, True)
    assert (steps[0]['wait_time'], steps[0]['parallel']) == (0, False)
    # nur die Gesamtzeit ändern, Rest bleibt
    u1_s1.post(reverse(TIMING), {'step': rezept.s2.pk, 'time': 90}, content_type='application/json')
    steps = _effective_steps(u1_s1, rezept.recipe)
    assert (steps[1]['time'], steps[1]['wait_time'], steps[1]['parallel']) == (90, 60, True)


@pytest.mark.parametrize('data', [{'time': 10, 'wait_time': 20}, {'time': -1}, {'time': 'x'}, {'parallel': 'ja'}])
def test_ungueltige_werte(u1_s1, rezept, data):
    r = u1_s1.post(reverse(TIMING), {'step': rezept.s1.pk, **data}, content_type='application/json')
    assert r.status_code == 400


@pytest.mark.parametrize('arg', [['a_u', 403], ['g1_s1', 403], ['u1_s2', 404], ['u1_s1', 200]])
def test_rechte_zeiten(arg, request, rezept):
    c = request.getfixturevalue(arg[0])
    r = c.post(reverse(TIMING), {'step': rezept.s1.pk, 'time': 5}, content_type='application/json')
    assert r.status_code == arg[1]

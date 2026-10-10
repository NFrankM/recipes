"""API-Tests: Varianten, Änderungen, Notizen, effektive Fassung, Einkaufsliste, Bewertungen, Fotos, Berechtigungen."""
import io
import json
from decimal import Decimal

import pytest
from django.contrib import auth
from django.urls import reverse
from django_scopes import scopes_disabled
from PIL import Image

from cookbook.models import CookLog, ShoppingListEntry, ShoppingListRecipe
from recipes.plugins.cookbook_ext.models import CookLogPhoto, RecipeVariant
from recipes.plugins.cookbook_ext.models import VariantIngredientChange as Change
from recipes.plugins.cookbook_ext.models import VariantStepNote
from recipes.plugins.cookbook_ext.tests.conftest import build_recipe

VARIANTS = 'api:recipe-variant-list'
VARIANT = 'api:recipe-variant-detail'
CHANGES = 'api:variant-ingredient-change-list'
CHANGE = 'api:variant-ingredient-change-detail'
NOTES = 'api:variant-step-note-list'
EFFECTIVE = 'api:effective-recipe-detail'


def post(client, url, data):
    return client.post(url, json.dumps(data), content_type='application/json')


def patch(client, url, data):
    return client.patch(url, json.dumps(data), content_type='application/json')


def foods(effective):
    return {i['food']['name']: i for s in effective['steps'] for i in s['ingredients'] if i['food']}


# --------------------------------------------------------------------------- Varianten

def test_variante_anlegen_und_lesen(rezept, u1_s1):
    r = post(u1_s1, reverse(VARIANTS), {'recipe': rezept.recipe.pk, 'name': 'Unsere Version', 'is_default': True})
    assert r.status_code == 201, r.content
    data = r.json()
    assert data['recipe'] == rezept.recipe.pk and data['is_default'] is True
    assert data['created_by']['id'] == auth.get_user(u1_s1).pk

    r = u1_s1.get(reverse(VARIANTS) + f'?recipe={rezept.recipe.pk}')
    assert r.status_code == 200 and [v['id'] for v in r.json()] == [data['id']]


def test_nur_eine_standardvariante(rezept, u1_s1):
    a = post(u1_s1, reverse(VARIANTS), {'recipe': rezept.recipe.pk, 'name': 'A', 'is_default': True}).json()
    b = post(u1_s1, reverse(VARIANTS), {'recipe': rezept.recipe.pk, 'name': 'B', 'is_default': True}).json()
    with scopes_disabled():
        assert RecipeVariant.objects.get(pk=a['id']).is_default is False
        assert RecipeVariant.objects.get(pk=b['id']).is_default is True
    patch(u1_s1, reverse(VARIANT, args=[a['id']]), {'is_default': True})
    with scopes_disabled():
        assert list(RecipeVariant.objects.filter(is_default=True).values_list('pk', flat=True)) == [a['id']]


def test_doppelter_name_wird_abgelehnt(rezept, variante, u1_s1):
    r = post(u1_s1, reverse(VARIANTS), {'recipe': rezept.recipe.pk, 'name': 'Unsere Version'})
    assert r.status_code == 400 and 'name' in r.json()


def test_rezept_einer_variante_nicht_wechselbar(rezept, variante, u1_s1, space_1):
    anderes = build_recipe(space_1, auth.get_user(u1_s1), name='Waffeln')
    r = patch(u1_s1, reverse(VARIANT, args=[variante.pk]), {'recipe': anderes.recipe.pk})
    assert r.status_code == 400


def test_variante_loeschen_loescht_aenderungen(rezept, variante, u1_s1):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REMOVE, ingredient=rezept.ei)
        VariantStepNote.objects.create(variant=variante, step=rezept.s1, text='x')
    assert u1_s1.delete(reverse(VARIANT, args=[variante.pk])).status_code == 204
    with scopes_disabled():
        assert Change.objects.count() == 0 and VariantStepNote.objects.count() == 0
        rezept.ei.refresh_from_db()  # Original bleibt


# --------------------------------------------------------------------------- Änderungen und Notizen

def test_aenderungen_ueber_api(rezept, variante, u1_s1):
    url = reverse(CHANGES)
    # Menge ändern
    r = post(u1_s1, url, {'variant': variante.pk, 'action': 'replace', 'ingredient': rezept.milch.pk, 'amount': 250})
    assert r.status_code == 201, r.content
    # Ersetzen per Name (neues Lebensmittel wird angelegt)
    r = post(u1_s1, url, {'variant': variante.pk, 'action': 'replace', 'ingredient': rezept.mehl.pk, 'food_name': 'Dinkelmehl 630'})
    assert r.status_code == 201, r.content
    assert r.json()['food_data']['name'] == 'Dinkelmehl 630'
    # Ergänzen mit neuer Einheit per Name
    r = post(u1_s1, url, {'variant': variante.pk, 'action': 'add', 'step': rezept.s1.pk, 'food_name': 'Vanillezucker',
                          'unit_name': 'Päckchen', 'amount': 1})
    assert r.status_code == 201, r.content
    # Entfernen
    r = post(u1_s1, url, {'variant': variante.pk, 'action': 'remove', 'ingredient': rezept.butter.pk})
    assert r.status_code == 201, r.content

    eff = u1_s1.get(reverse(EFFECTIVE, args=[rezept.recipe.pk]) + f'?variant={variante.pk}').json()
    z = foods(eff)
    assert z['Milch']['status'] == 'changed' and z['Milch']['amount'] == 250 and z['Milch']['original']['amount'] == 300
    assert z['Dinkelmehl 630']['status'] == 'changed' and z['Dinkelmehl 630']['original']['food']['name'] == 'Mehl'
    assert z['Vanillezucker']['status'] == 'added' and z['Vanillezucker']['unit']['name'] == 'Päckchen'
    assert 'Butter' not in z
    assert eff['steps'][1]['removed_ingredients'][0]['food']['name'] == 'Butter'

    # Variante liefert ihre Änderungen mit
    v = u1_s1.get(reverse(VARIANT, args=[variante.pk])).json()
    assert len(v['ingredient_changes']) == 4


def test_aenderung_bearbeiten_und_loeschen(rezept, variante, u1_s1):
    c = post(u1_s1, reverse(CHANGES), {'variant': variante.pk, 'action': 'replace', 'ingredient': rezept.milch.pk, 'amount': 250}).json()
    r = patch(u1_s1, reverse(CHANGE, args=[c['id']]), {'amount': 200})
    assert r.status_code == 200 and r.json()['amount'] == 200
    assert u1_s1.delete(reverse(CHANGE, args=[c['id']])).status_code == 204


@pytest.mark.parametrize('payload,feld', [
    ({'action': 'replace'}, 'ingredient'),
    ({'action': 'remove'}, 'ingredient'),
    ({'action': 'add'}, 'food'),
    ({'action': 'quatsch', 'ingredient': None}, 'action'),
])
def test_ungueltige_aenderungen(rezept, variante, u1_s1, payload, feld):
    r = post(u1_s1, reverse(CHANGES), {'variant': variante.pk, **payload})
    assert r.status_code == 400 and feld in r.json(), r.content


def test_zutat_aus_anderem_rezept_abgelehnt(rezept, variante, u1_s1, space_1):
    fremd = build_recipe(space_1, auth.get_user(u1_s1), name='Waffeln')
    r = post(u1_s1, reverse(CHANGES), {'variant': variante.pk, 'action': 'remove', 'ingredient': fremd.mehl.pk})
    assert r.status_code == 400 and 'ingredient' in r.json()


def test_notizen_und_zusatzschritt(rezept, variante, u1_s1):
    r = post(u1_s1, reverse(NOTES), {'variant': variante.pk, 'step': rezept.s2.pk, 'text': 'Pfanne heiß werden lassen'})
    assert r.status_code == 201, r.content
    r = post(u1_s1, reverse(NOTES), {'variant': variante.pk, 'position': 1, 'text': 'Teig ruhen lassen', 'time': 20})
    assert r.status_code == 201, r.content
    assert post(u1_s1, reverse(NOTES), {'variant': variante.pk, 'step': rezept.s1.pk, 'text': '   '}).status_code == 400

    eff = u1_s1.get(reverse(EFFECTIVE, args=[rezept.recipe.pk]) + f'?variant={variante.pk}').json()
    assert [s['is_added'] for s in eff['steps']] == [False, True, False]
    assert eff['steps'][1]['instruction'] == 'Teig ruhen lassen' and eff['steps'][1]['time'] == 20
    assert eff['steps'][2]['notes'][0]['text'] == 'Pfanne heiß werden lassen'
    assert eff['steps'][0]['instructions_markdown']  # gerendertes Markdown vom Original


# --------------------------------------------------------------------------- effektive Fassung

def test_effective_original_und_skalierung(rezept, u1_s1):
    eff = u1_s1.get(reverse(EFFECTIVE, args=[rezept.recipe.pk])).json()
    assert eff['variant'] is None and eff['servings'] == 4 and foods(eff)['Mehl']['amount'] == 200
    eff = u1_s1.get(reverse(EFFECTIVE, args=[rezept.recipe.pk]) + '?servings=6').json()
    assert eff['factor'] == 1.5 and foods(eff)['Mehl']['amount'] == 300 and foods(eff)['Ei']['amount'] == 3


def test_effective_ueber_variante(rezept, variante, u1_s1):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.mehl, amount=Decimal(150))
    eff = u1_s1.get(reverse('api:recipe-variant-effective', args=[variante.pk]) + '?servings=2').json()
    assert foods(eff)['Mehl']['amount'] == 75 and foods(eff)['Mehl']['status'] == 'changed'


def test_effective_variante_von_anderem_rezept_404(rezept, variante, u1_s1, space_1):
    anderes = build_recipe(space_1, auth.get_user(u1_s1), name='Waffeln')
    r = u1_s1.get(reverse(EFFECTIVE, args=[anderes.recipe.pk]) + f'?variant={variante.pk}')
    assert r.status_code == 404


# --------------------------------------------------------------------------- Einkaufsliste

def test_einkaufsliste_uebernimmt_variante(rezept, variante, u1_s1):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.milch, amount=Decimal(200))
        Change.objects.create(variant=variante, action=Change.REMOVE, ingredient=rezept.butter)
        Change.objects.create(variant=variante, action=Change.ADD, step=rezept.s1, food=rezept.food('Zucker'),
                              amount=Decimal(20), unit=rezept.units['g'])
    r = post(u1_s1, reverse('api:recipe-variant-shopping', args=[variante.pk]), {'servings': 8})
    assert r.status_code == 200, r.content
    with scopes_disabled():
        slr = ShoppingListRecipe.objects.get(pk=r.json()['list_recipe'])
        assert slr.servings == 8 and slr.recipe == rezept.recipe
        entries = {e.food.name: e for e in ShoppingListEntry.objects.filter(list_recipe=slr)}
    # Salz (ohne Menge) ist eine Zutat und kommt mit; Überschrift nicht; Butter entfernt
    assert set(entries) == {'Mehl', 'Ei', 'Salz', 'Milch', 'Zucker'}
    assert entries['Mehl'].amount == 400 and entries['Mehl'].ingredient == rezept.mehl
    assert entries['Milch'].amount == 400 and entries['Milch'].ingredient is None  # geändert → ohne Bezug
    assert entries['Zucker'].amount == 40 and entries['Zucker'].unit.name == 'g'


def test_einkaufsliste_ignoriert_ignore_shopping(rezept, variante, u1_s1):
    with scopes_disabled():
        salz = rezept.salz.food
        salz.ignore_shopping = True
        salz.save()
    r = post(u1_s1, reverse('api:recipe-variant-shopping', args=[variante.pk]), {})
    with scopes_disabled():
        names = set(ShoppingListEntry.objects.filter(list_recipe_id=r.json()['list_recipe']).values_list('food__name', flat=True))
    assert 'Salz' not in names and 'Mehl' in names


def test_einkaufsliste_nicht_fuer_gaeste(rezept, variante, g1_s1):
    assert post(g1_s1, reverse('api:recipe-variant-shopping', args=[variante.pk]), {}).status_code == 403


# --------------------------------------------------------------------------- Berechtigungen

@pytest.mark.parametrize('client_fixture,lesen,schreiben', [
    ('a_u', 403, 403),  # nicht angemeldet
    ('g1_s1', 200, 403),  # Gast im selben Space: nur lesen
    ('u1_s1', 200, 201),  # Ersteller
    ('u2_s1', 200, 201),  # anderer Benutzer im Haushalt/Space: darf mitbearbeiten
    ('a1_s1', 200, 201),
    ('u1_s2', 404, 400),  # anderer Space: sieht nichts, kann das Rezept nicht referenzieren
])
def test_berechtigungen(rezept, variante, request, client_fixture, lesen, schreiben):
    c = request.getfixturevalue(client_fixture)
    assert c.get(reverse(VARIANT, args=[variante.pk])).status_code == lesen
    assert c.get(reverse(EFFECTIVE, args=[rezept.recipe.pk]) + f'?variant={variante.pk}').status_code == lesen
    r = post(c, reverse(NOTES), {'variant': variante.pk, 'step': rezept.s1.pk, 'text': 'Hallo'})
    assert r.status_code == schreiben, r.content


def test_anderer_space_sieht_keine_varianten(rezept, variante, u1_s2):
    assert u1_s2.get(reverse(VARIANTS)).json() == []
    assert u1_s2.get(reverse(CHANGES)).json() == []
    r = post(u1_s2, reverse(VARIANTS), {'recipe': rezept.recipe.pk, 'name': 'Fremd'})
    assert r.status_code == 400


def test_gast_darf_nicht_aendern_oder_loeschen(rezept, variante, g1_s1):
    assert patch(g1_s1, reverse(VARIANT, args=[variante.pk]), {'name': 'X'}).status_code == 403
    assert g1_s1.delete(reverse(VARIANT, args=[variante.pk])).status_code == 403
    assert post(g1_s1, reverse(VARIANTS), {'recipe': rezept.recipe.pk, 'name': 'Gast'}).status_code == 403


def test_privates_rezept(space_1, u1_s1, u2_s1):
    privat = build_recipe(space_1, auth.get_user(u1_s1), private=True, name='Geheimrezept')
    with scopes_disabled():
        v = RecipeVariant.objects.create(recipe=privat.recipe, name='Meine', created_by=auth.get_user(u1_s1))
    # Ersteller sieht alles
    assert u1_s1.get(reverse(VARIANT, args=[v.pk])).status_code == 200
    # andere Benutzer im Space nicht
    assert u2_s1.get(reverse(VARIANT, args=[v.pk])).status_code == 404
    assert u2_s1.get(reverse(EFFECTIVE, args=[privat.recipe.pk])).status_code == 404
    assert post(u2_s1, reverse(VARIANTS), {'recipe': privat.recipe.pk, 'name': 'Auch'}).status_code == 400
    # nach dem Teilen schon
    with scopes_disabled():
        privat.recipe.shared.add(auth.get_user(u2_s1))
    assert u2_s1.get(reverse(VARIANT, args=[v.pk])).status_code == 200


# --------------------------------------------------------------------------- Bewertungen und Fotos

def _cook_log(client, recipe, rating, comment='lecker'):
    with scopes_disabled():
        user = auth.get_user(client)
        return CookLog.objects.create(recipe=recipe, rating=rating, comment=comment, created_by=user, space=recipe.space)


def test_bewertungs_zusammenfassung(rezept, u1_s1, u2_s1, u1_s2):
    _cook_log(u1_s1, rezept.recipe, 4)
    _cook_log(u2_s1, rezept.recipe, 5)
    _cook_log(u2_s1, rezept.recipe, None, 'nur gekocht')
    r = u1_s1.get(reverse('api:recipe-rating-list') + f'?recipe={rezept.recipe.pk}&recipe=999999')
    assert r.status_code == 200
    assert r.json() == [
        {'recipe': rezept.recipe.pk, 'average': 4.5, 'count': 2, 'cooked': 3},
        {'recipe': 999999, 'average': None, 'count': 0, 'cooked': 0},
    ]
    # anderer Space erfährt nichts
    assert u1_s2.get(reverse('api:recipe-rating-list') + f'?recipe={rezept.recipe.pk}').json()[0]['count'] == 0
    assert u1_s1.get(reverse('api:recipe-rating-list')).status_code == 400


def _png():
    buf = io.BytesIO()
    Image.new('RGB', (40, 30), (62, 90, 112)).save(buf, 'PNG')
    buf.seek(0)
    buf.name = 'foto.png'
    return buf


def test_foto_hochladen_und_loeschen(rezept, u1_s1, u2_s1, g1_s1):
    log = _cook_log(u1_s1, rezept.recipe, 5)
    r = u1_s1.post(reverse('api:cook-log-photo-list'), {'cook_log': log.pk, 'image': _png()})
    assert r.status_code == 201, r.content
    foto = r.json()
    assert foto['recipe'] == rezept.recipe.pk and foto['image']

    # alle im Space (auch Gäste) sehen die Fotos des Rezepts
    assert [p['id'] for p in g1_s1.get(reverse('api:cook-log-photo-list') + f'?recipe={rezept.recipe.pk}').json()] == [foto['id']]
    # andere dürfen nicht an fremde Bewertungen hängen oder löschen
    r = u2_s1.post(reverse('api:cook-log-photo-list'), {'cook_log': log.pk, 'image': _png()})
    assert r.status_code == 400
    assert u2_s1.delete(reverse('api:cook-log-photo-detail', args=[foto['id']])).status_code == 403
    assert u1_s1.delete(reverse('api:cook-log-photo-detail', args=[foto['id']])).status_code == 204
    with scopes_disabled():
        assert CookLogPhoto.objects.count() == 0


def test_foto_nur_bilder(rezept, u1_s1):
    log = _cook_log(u1_s1, rezept.recipe, 5)
    datei = io.BytesIO(b'kein bild')
    datei.name = 'virus.png'
    r = u1_s1.post(reverse('api:cook-log-photo-list'), {'cook_log': log.pk, 'image': datei})
    assert r.status_code == 400
    datei = io.BytesIO(b'%PDF-1.4')
    datei.name = 'doku.pdf'
    assert u1_s1.post(reverse('api:cook-log-photo-list'), {'cook_log': log.pk, 'image': datei}).status_code == 400


def test_foto_anderer_space(rezept, u1_s1, u1_s2):
    log = _cook_log(u1_s1, rezept.recipe, 5)
    assert u1_s2.post(reverse('api:cook-log-photo-list'), {'cook_log': log.pk, 'image': _png()}).status_code == 400
    assert u1_s2.get(reverse('api:cook-log-photo-list')).json() == []

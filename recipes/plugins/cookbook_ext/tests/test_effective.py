"""Tests für den Service: effektive Zutatenliste und Schritte einer Variante inkl. Skalierung."""
from decimal import Decimal

import pytest
from django_scopes import scopes_disabled

from recipes.plugins.cookbook_ext.models import VariantIngredientChange as Change
from recipes.plugins.cookbook_ext.models import VariantStepNote
from recipes.plugins.cookbook_ext.services.effective import ADDED, CHANGED, ORIGINAL, REMOVED, effective_recipe


def by_food(eff):
    return {i.food.name: i for i in eff.all_ingredients() if i.food}


def test_original_ohne_variante(rezept):
    with scopes_disabled():
        eff = effective_recipe(rezept.recipe)
    assert eff.factor == 1 and eff.servings == 4
    assert [s.name for s in eff.steps] == ['Teig', 'Backen']
    zutaten = by_food(eff)
    assert set(zutaten) == {'Mehl', 'Ei', 'Salz', 'Milch', 'Butter'}
    assert all(i.status == ORIGINAL for i in zutaten.values())
    assert zutaten['Mehl'].amount == 200
    # Überschriften bleiben in der Schrittliste, zählen aber nicht als Zutat
    assert any(i.is_header for i in eff.steps[0].ingredients)
    assert not any(i.is_header for i in eff.all_ingredients())


def test_variante_ohne_aenderungen_entspricht_original(rezept, variante):
    with scopes_disabled():
        eff = effective_recipe(rezept.recipe, variante)
    assert all(i.status == ORIGINAL for i in eff.all_ingredients())
    assert len(list(eff.all_ingredients())) == 5


def test_ersetzen(rezept, variante):
    with scopes_disabled():
        dinkel = rezept.food('Dinkelmehl')
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.mehl, food=dinkel)
        eff = effective_recipe(rezept.recipe, variante)
    z = by_food(eff)
    assert 'Mehl' not in z
    d = z['Dinkelmehl']
    assert d.status == CHANGED
    assert d.amount == 200 and d.unit.name == 'g'  # Menge/Einheit vom Original übernommen
    assert d.original_food.name == 'Mehl' and d.original_amount == 200
    assert d.ingredient == rezept.mehl
    # Reihenfolge bleibt erhalten
    assert [i.food.name for i in eff.steps[0].ingredients if i.food][:2] == ['Dinkelmehl', 'Ei']


def test_menge_aendern(rezept, variante):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.milch, amount=Decimal(250))
        eff = effective_recipe(rezept.recipe, variante)
    milch = by_food(eff)['Milch']
    assert milch.status == CHANGED
    assert milch.amount == 250 and milch.original_amount == 300
    assert milch.food == rezept.milch.food and milch.unit.name == 'ml'


def test_menge_und_einheit_aendern(rezept, variante):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.butter, amount=Decimal(20), unit=rezept.units['g'],
                              note='kalt')
        eff = effective_recipe(rezept.recipe, variante)
    b = by_food(eff)['Butter']
    assert (b.amount, b.unit.name, b.note) == (20, 'g', 'kalt')


def test_ergaenzen_in_schritt_und_ohne_schritt(rezept, variante):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.ADD, step=rezept.s1, food=rezept.food('Vanillezucker'),
                              amount=Decimal(1), unit=rezept.units['EL'], order=10)
        Change.objects.create(variant=variante, action=Change.ADD, food=rezept.food('Zimt'))  # ohne Schritt, ohne Menge
        eff = effective_recipe(rezept.recipe, variante)
    s1, s2 = eff.steps
    assert s1.ingredients[-1].food.name == 'Vanillezucker'
    assert s1.ingredients[-1].status == ADDED and s1.ingredients[-1].amount == 1
    zimt = s2.ingredients[-1]  # ohne Schritt → letzter Schritt
    assert zimt.food.name == 'Zimt' and zimt.status == ADDED and zimt.no_amount
    assert zimt.ingredient is None


def test_entfernen(rezept, variante):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REMOVE, ingredient=rezept.butter)
        eff = effective_recipe(rezept.recipe, variante)
    assert 'Butter' not in by_food(eff)
    removed = eff.steps[1].removed_ingredients
    assert len(removed) == 1 and removed[0].food.name == 'Butter' and removed[0].status == REMOVED


@pytest.mark.parametrize('servings,erwartet_mehl,erwartet_dinkel_neu', [
    (4, 200, 100),
    (2, 100, 50),
    (6, 300, 150),
    (1, 50, 25),
])
def test_skalierung(rezept, variante, servings, erwartet_mehl, erwartet_dinkel_neu):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.ADD, step=rezept.s1, food=rezept.food('Haferflocken'),
                              amount=Decimal(100), unit=rezept.units['g'])
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.milch, amount=Decimal(200))
        eff = effective_recipe(rezept.recipe, variante, servings=servings)
    z = by_food(eff)
    f = Decimal(servings) / 4
    assert eff.factor == f
    assert z['Mehl'].amount == erwartet_mehl
    assert z['Haferflocken'].amount == erwartet_dinkel_neu
    assert z['Milch'].amount == 200 * f and z['Milch'].original_amount == 300 * f
    assert z['Milch'].base_amount == 200
    assert z['Salz'].no_amount  # „ohne Menge" bleibt ohne Menge


def test_skalierung_ungueltige_portionen(rezept):
    with scopes_disabled():
        for wert in (0, -2, 'abc', None, ''):
            eff = effective_recipe(rezept.recipe, servings=wert)
            assert eff.servings == 4 and eff.factor == 1


def test_skalierung_bruchteile(rezept):
    with scopes_disabled():
        eff = effective_recipe(rezept.recipe, servings='1.5')
    assert by_food(eff)['Ei'].amount == Decimal('0.75')


def test_schrittnotizen_und_zusatzschritte(rezept, variante):
    with scopes_disabled():
        VariantStepNote.objects.create(variant=variante, step=rezept.s2, text='Pfanne richtig heiß werden lassen')
        VariantStepNote.objects.create(variant=variante, step=None, position=1, text='Teig 20 Minuten ruhen lassen', time=20)
        VariantStepNote.objects.create(variant=variante, step=None, position=99, text='Mit Puderzucker servieren')
        VariantStepNote.objects.create(variant=variante, step=None, position=99, text='Danach Pfanne einweichen')
        eff = effective_recipe(rezept.recipe, variante)
    namen = [(s.is_added, s.instruction if s.is_added else s.name) for s in eff.steps]
    assert namen == [
        (False, 'Teig'),
        (True, 'Teig 20 Minuten ruhen lassen'),
        (False, 'Backen'),
        (True, 'Mit Puderzucker servieren'),
        (True, 'Danach Pfanne einweichen'),
    ]
    assert eff.steps[1].time == 20
    assert [n.text for n in eff.steps[2].notes] == ['Pfanne richtig heiß werden lassen']
    assert eff.steps[0].notes == []


def test_zusatzschritt_ganz_vorne(rezept, variante):
    with scopes_disabled():
        VariantStepNote.objects.create(variant=variante, step=None, position=0, text='Alles bereitstellen')
        eff = effective_recipe(rezept.recipe, variante)
    assert eff.steps[0].is_added and eff.steps[0].instruction == 'Alles bereitstellen'


def test_original_bleibt_unveraendert(rezept, variante):
    with scopes_disabled():
        Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.mehl, amount=Decimal(1))
        Change.objects.create(variant=variante, action=Change.REMOVE, ingredient=rezept.ei)
        effective_recipe(rezept.recipe, variante, servings=8)
        rezept.mehl.refresh_from_db()
        assert rezept.mehl.amount == 200
        assert rezept.recipe.steps.get(pk=rezept.s1.pk).ingredients.count() == 4
        eff = effective_recipe(rezept.recipe)
    assert by_food(eff)['Mehl'].amount == 200 and 'Ei' in by_food(eff)


def test_verwaiste_aenderung_wenn_originalzutat_geloescht(rezept, variante):
    with scopes_disabled():
        c = Change.objects.create(variant=variante, action=Change.REPLACE, ingredient=rezept.butter, amount=Decimal(3))
        rezept.butter.delete()
        c.refresh_from_db()
        assert c.ingredient is None
        eff = effective_recipe(rezept.recipe, variante)
    assert eff.orphaned_changes == [c]
    assert 'Butter' not in by_food(eff)


def test_variante_eines_anderen_rezepts(rezept, variante, space_1, u1_s1):
    from django.contrib import auth
    from recipes.plugins.cookbook_ext.tests.conftest import build_recipe
    anderes = build_recipe(space_1, auth.get_user(u1_s1), name='Waffeln')
    with scopes_disabled(), pytest.raises(ValueError):
        effective_recipe(anderes.recipe, variante)


def test_model_validierung(rezept, variante, space_1, u1_s1):
    from django.contrib import auth
    from django.core.exceptions import ValidationError
    from recipes.plugins.cookbook_ext.tests.conftest import build_recipe
    fremd = build_recipe(space_1, auth.get_user(u1_s1), name='Waffeln')
    with scopes_disabled():
        with pytest.raises(ValidationError):
            Change(variant=variante, action=Change.REPLACE).clean()  # Zutat fehlt
        with pytest.raises(ValidationError):
            Change(variant=variante, action=Change.REMOVE, ingredient=fremd.mehl).clean()  # fremdes Rezept
        with pytest.raises(ValidationError):
            Change(variant=variante, action=Change.ADD).clean()  # Food fehlt
        with pytest.raises(ValidationError):
            Change(variant=variante, action=Change.ADD, food=rezept.mehl.food, step=fremd.s1).clean()
        with pytest.raises(ValidationError):
            VariantStepNote(variant=variante, step=fremd.s1, text='x').clean()
        Change(variant=variante, action=Change.REPLACE, ingredient=rezept.mehl, amount=1).clean()  # ok

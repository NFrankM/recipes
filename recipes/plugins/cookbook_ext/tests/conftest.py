# Tandoors Test-Fixtures (Spaces, Benutzer u1_s1, a1_s1, g1_s1, …) wiederverwenden
from cookbook.tests.conftest import *  # noqa: F401,F403

from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib import auth
from django_scopes import scopes_disabled

from cookbook.models import Food, Ingredient, Recipe, Step, Unit
from recipes.plugins.cookbook_ext.models import RecipeVariant


def build_recipe(space, user, private=False, name='Pfannkuchen'):
    """
    Pfannkuchen für 4 Portionen:
      Schritt 1 „Teig":  200 g Mehl, 2 Stück Ei, [Überschrift „Für die Pfanne"], Salz (ohne Menge)
      Schritt 2 „Backen": 300 ml Milch, 1 EL Butter
    """
    with scopes_disabled():
        r = Recipe.objects.create(name=name, servings=4, created_by=user, space=space, internal=True, private=private)
        units = {n: Unit.objects.get_or_create(name=n, space=space)[0] for n in ('g', 'Stück', 'ml', 'EL')}

        def food(n):
            return Food.objects.filter(space=space, name=n).first() or Food.add_root(name=n, space=space)

        s1 = Step.objects.create(name='Teig', instruction='Mehl und Eier verrühren.', order=0, time=5, space=space)
        s2 = Step.objects.create(name='Backen', instruction='In der Pfanne ausbacken.', order=1, time=10, space=space)
        mehl = Ingredient.objects.create(food=food('Mehl'), unit=units['g'], amount=Decimal(200), order=0, space=space)
        ei = Ingredient.objects.create(food=food('Ei'), unit=units['Stück'], amount=Decimal(2), order=1, space=space)
        header = Ingredient.objects.create(is_header=True, note='Für die Pfanne', order=2, space=space)
        salz = Ingredient.objects.create(food=food('Salz'), no_amount=True, order=3, space=space)
        milch = Ingredient.objects.create(food=food('Milch'), unit=units['ml'], amount=Decimal(300), order=0, space=space)
        butter = Ingredient.objects.create(food=food('Butter'), unit=units['EL'], amount=Decimal(1), order=1, space=space)
        s1.ingredients.add(mehl, ei, header, salz)
        s2.ingredients.add(milch, butter)
        r.steps.add(s1, s2)
        return SimpleNamespace(recipe=r, s1=s1, s2=s2, mehl=mehl, ei=ei, header=header, salz=salz, milch=milch, butter=butter,
                               units=units, food=food)


@pytest.fixture
def rezept(space_1, u1_s1):
    return build_recipe(space_1, auth.get_user(u1_s1))


@pytest.fixture
def variante(rezept, u1_s1):
    with scopes_disabled():
        return RecipeVariant.objects.create(recipe=rezept.recipe, name='Unsere Version', created_by=auth.get_user(u1_s1))

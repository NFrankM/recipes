"""Kategorien = Keywords unter „Kategorien“."""
import pytest
from django.contrib import auth
from django.urls import reverse
from django_scopes import scopes_disabled

from cookbook.models import Keyword
from recipes.plugins.cookbook_ext.services.categories import DEFAULT_CATEGORIES, ROOT_NAME, add_category, ensure_root

LIST = 'api:recipe-category-list'


def detail(pk):
    return reverse('api:recipe-category-detail', args=[pk])


def names(client):
    return [c['name'] for c in client.get(reverse(LIST)).json()]


def test_startkategorien_beim_ersten_aufruf(u1_s1, space_1):
    assert names(u1_s1) == sorted(DEFAULT_CATEGORIES)
    with scopes_disabled():
        root = Keyword.objects.get(space=space_1, name=ROOT_NAME)
        assert root.is_root() and root.get_children_count() == 6


def test_geloeschte_startkategorie_kommt_nicht_wieder(u1_s1):
    brot = [c for c in u1_s1.get(reverse(LIST)).json() if c['name'] == 'Brot'][0]
    assert u1_s1.delete(detail(brot['id'])).status_code == 204
    assert 'Brot' not in names(u1_s1)
    assert 'Brot' not in names(u1_s1)


def test_anlegen_umbenennen(u1_s1):
    r = u1_s1.post(reverse(LIST), {'name': 'Suppen'}, content_type='application/json')
    assert r.status_code == 201
    assert 'Suppen' in names(u1_s1)
    r = u1_s1.patch(detail(r.json()['id']), {'name': 'Suppen & Eintöpfe'}, content_type='application/json')
    assert r.status_code == 200
    assert 'Suppen & Eintöpfe' in names(u1_s1)
    assert u1_s1.post(reverse(LIST), {'name': '  '}, content_type='application/json').status_code == 400


def test_vorhandenes_keyword_wird_verschoben(space_1, u1_s1, rezept):
    with scopes_disabled():
        kw = Keyword.add_root(name='suppen', space=space_1)
        rezept.recipe.keywords.add(kw)
        root = ensure_root(space_1)
        cat, created = add_category(space_1, 'Suppen')
        assert not created and cat.pk == kw.pk
        kw.refresh_from_db()
        assert kw.get_parent().pk == root.pk
        assert rezept.recipe.keywords.filter(pk=kw.pk).exists()  # Zuordnung bleibt


def test_rezept_kategorien_setzen(u1_s1, rezept):
    cats = {c['name']: c['id'] for c in u1_s1.get(reverse(LIST)).json()}
    with scopes_disabled():
        other = Keyword.add_root(name='vegetarisch', space=rezept.recipe.space)
        rezept.recipe.keywords.add(other)
    url = reverse('api:recipe-category-set-for-recipe')
    r = u1_s1.post(url, {'recipe': rezept.recipe.pk, 'categories': [cats['Brot'], cats['Beilagen']]}, content_type='application/json')
    assert r.status_code == 200, r.content
    r = u1_s1.post(url, {'recipe': rezept.recipe.pk, 'categories': [cats['Kuchen']]}, content_type='application/json')
    with scopes_disabled():
        assert set(rezept.recipe.keywords.values_list('name', flat=True)) == {'Kuchen', 'vegetarisch'}
    listing = {c['name']: c for c in u1_s1.get(reverse(LIST)).json()}
    assert listing['Kuchen']['recipe_count'] == 1 and listing['Brot']['recipe_count'] == 0
    # fremdes Keyword ist keine Kategorie
    r = u1_s1.post(url, {'recipe': rezept.recipe.pk, 'categories': [other.pk]}, content_type='application/json')
    assert r.status_code == 400


@pytest.mark.parametrize('arg', [['a_u', 403, 403], ['g1_s1', 200, 403], ['u1_s1', 200, 201], ['a1_s1', 200, 201]])
def test_rechte(arg, request):
    c = request.getfixturevalue(arg[0])
    assert c.get(reverse(LIST)).status_code == arg[1]
    assert c.post(reverse(LIST), {'name': 'Neu'}, content_type='application/json').status_code == arg[2]


def test_space_getrennt(u1_s1, u1_s2, space_2):
    u1_s1.post(reverse(LIST), {'name': 'Nur bei uns'}, content_type='application/json')
    assert 'Nur bei uns' not in names(u1_s2)
    cat = u1_s1.get(reverse(LIST)).json()[0]
    assert u1_s2.patch(detail(cat['id']), {'name': 'x'}, content_type='application/json').status_code == 404
    assert u1_s2.delete(detail(cat['id'])).status_code == 404


def test_fremdes_rezept_nicht_setzbar(u1_s2, rezept):
    cats = u1_s2.get(reverse(LIST)).json()
    r = u1_s2.post(reverse('api:recipe-category-set-for-recipe'), {'recipe': rezept.recipe.pk, 'categories': [cats[0]['id']]},
                   content_type='application/json')
    assert r.status_code == 404

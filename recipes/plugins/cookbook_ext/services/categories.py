"""
Kategorien (Brot, Kuchen, …) = Kinder des Keywords „Kategorien“.

Tandoors Keywords sind bereits hierarchisch (treebeard) und überall nutzbar (Suche, Filter, Editor, Export).
Deshalb kein eigenes Model: Eine Kategorie ist ein Keyword direkt unter dem Wurzel-Keyword ROOT_NAME.
Rezepte werden über das normale ManyToMany Recipe.keywords zugeordnet.
"""
from django.db import transaction

from cookbook.models import Keyword, Recipe

ROOT_NAME = 'Kategorien'
DEFAULT_CATEGORIES = ['Brot', 'Kuchen', 'Hauptgerichte', 'Beilagen', 'Aufstriche', 'Desserts']


def _find(space, name):
    return Keyword.objects.filter(space=space, name__iexact=name.strip()).first()


@transaction.atomic
def ensure_root(space):
    """ Legt beim ersten Aufruf je Space „Kategorien“ und die Startkategorien an. Danach nie wieder (Gelöschtes bleibt weg). """
    root = Keyword.objects.filter(space=space, name=ROOT_NAME, depth=1).first()
    if root:
        return root
    root = _find(space, ROOT_NAME)
    if root is None:
        root = Keyword.add_root(name=ROOT_NAME, space=space, description='Kategorien der Rezepteapp')
    elif root.depth != 1:
        root.move(Keyword.get_first_root_node(), 'sorted-sibling' if Keyword.node_order_by else 'last-sibling')
        root.refresh_from_db()
    for name in DEFAULT_CATEGORIES:
        add_category(space, name, root)
    return root


def add_category(space, name, root=None):
    """ Neue Kategorie; gibt es das Keyword schon (z. B. vom Import), wird es unter „Kategorien“ verschoben. """
    root = root or ensure_root(space)
    name = name.strip()[:64]
    existing = _find(space, name)
    if existing:
        if existing.pk == root.pk:
            raise ValueError('Dieser Name ist reserviert.')
        if existing.get_parent() is None or existing.get_parent().pk != root.pk:
            existing.move(root, 'sorted-child' if Keyword.node_order_by else 'last-child')
            existing.refresh_from_db()
        return existing, False
    root.refresh_from_db()  # treebeard: numchild/path aktuell halten
    return root.add_child(name=name, space=space), True


def categories(space):
    return ensure_root(space).get_children().order_by('name')


def category_list(request, visible_recipes):
    """ Kategorien mit Anzahl der (sichtbaren) Rezepte und einem Titelbild (neuestes Rezept mit Bild) """
    cats = list(categories(request.space))
    recipes = visible_recipes
    result = []
    for c in cats:
        in_cat = recipes.filter(keywords__path__startswith=c.path).distinct()
        image = in_cat.exclude(image='').exclude(image__isnull=True).order_by('-created_at').values_list('image', flat=True).first()
        result.append({
            'id': c.pk,
            'name': c.name,
            'recipe_count': in_cat.count(),
            'image': request.build_absolute_uri(Recipe(image=image).image.url) if image else None,
        })
    return result


@transaction.atomic
def set_recipe_categories(recipe, category_ids):
    """ Ersetzt die Kategorien eines Rezepts; andere Schlagwörter bleiben unverändert """
    cats = categories(recipe.space)
    allowed = {c.pk: c for c in cats}
    unknown = [i for i in category_ids if i not in allowed]
    if unknown:
        raise ValueError(f'Unbekannte Kategorie: {unknown[0]}')
    recipe.keywords.remove(*[c for c in cats if c.pk not in category_ids])
    recipe.keywords.add(*[allowed[i] for i in category_ids])
    return [allowed[i] for i in category_ids]

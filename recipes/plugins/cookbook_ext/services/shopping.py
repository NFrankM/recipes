"""
Übernimmt die effektive Zutatenliste einer Variante auf die Einkaufsliste.

Nutzt Tandoors Models (ShoppingListRecipe/ShoppingListEntry) direkt, damit die Einträge in Tandoors
Einkaufsliste ganz normal erscheinen (inkl. Gruppierung nach Supermarkt-Kategorie).
Siehe ENTSCHEIDUNGEN.md E5 Punkt 8 zum Feld `ingredient`.
"""
from cookbook.connectors.connector_manager import ActionType, ConnectorManager
from cookbook.helper.permission_helper import get_household_user_ids
from cookbook.models import Food, ShoppingListEntry, ShoppingListRecipe

from .effective import ORIGINAL, effective_recipe


def _exclude_onhand_food_ids(user, space):
    try:
        if not user.userpreference.mealplan_autoexclude_onhand:
            return set()
    except Exception:
        return set()
    user_space = user.userspace_set.filter(space=space).first()
    household_ids = get_household_user_ids(user_space)
    return set(Food.objects.filter(space=space, onhand_users__id__in=household_ids).values_list('id', flat=True))


def add_to_shopping_list(recipe, variant, user, space, servings=None, mealplan=None):
    """
    Legt eine ShoppingListRecipe für Rezept (+ optional Variante) an und befüllt sie mit den
    effektiven, auf `servings` skalierten Zutaten. Gibt die ShoppingListRecipe zurück.
    """
    eff = effective_recipe(recipe, variant, servings)
    onhand = _exclude_onhand_food_ids(user, space)

    slr = ShoppingListRecipe.objects.create(
        recipe=recipe, mealplan=mealplan, servings=eff.servings, space=space, created_by=user,
        name=(variant.name if variant is not None else '')[:32],
    )

    entries = []
    for i in eff.all_ingredients():
        if i.food is None or i.food.ignore_shopping or i.food.pk in onhand:
            continue
        entries.append(ShoppingListEntry(
            list_recipe=slr,
            food=i.food,
            unit=i.unit,
            # nur unveränderte Zutaten behalten den Bezug zur Originalzutat (Tandoor skaliert darüber nach)
            ingredient=i.ingredient if i.status == ORIGINAL else None,
            amount=i.amount,
            created_by=user,
            space=space,
        ))
    ShoppingListEntry.objects.bulk_create(entries)
    ConnectorManager.add_work(ActionType.CREATED, *entries)
    for e in entries:
        if e.food.shopping_lists.count() > 0:
            e.shopping_lists.set(e.food.shopping_lists.all())
    return slr

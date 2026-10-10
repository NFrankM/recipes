"""
Berechnet die „effektive" Fassung eines Rezepts: Original + Änderungen einer Variante, skaliert auf n Portionen.

Das Ergebnis ist eine reine Datenstruktur (Dataclasses) und wird von der API (EffectiveRecipeSerializer),
der Einkaufsliste und den Tests genutzt. Das Original wird nie verändert.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from cookbook.models import Food, Ingredient, Recipe, Step, Unit

from ..models import RecipeVariant, VariantIngredientChange, VariantStepNote

ORIGINAL = 'original'
CHANGED = 'changed'
ADDED = 'added'
REMOVED = 'removed'


@dataclass
class EffectiveIngredient:
    status: str  # original | changed | added | removed
    food: Optional[Food]
    unit: Optional[Unit]
    amount: Decimal  # bereits skaliert
    base_amount: Decimal  # unskaliert (für die Rezept-Grundportionen)
    note: str = ''
    is_header: bool = False
    no_amount: bool = False
    order: int = 0
    ingredient: Optional[Ingredient] = None  # Originalzutat (bei original/changed/removed)
    change: Optional[VariantIngredientChange] = None
    # Originalwerte zum Anzeigen „vorher" (nur bei changed)
    original_food: Optional[Food] = None
    original_unit: Optional[Unit] = None
    original_amount: Optional[Decimal] = None  # skaliert
    original_note: str = ''


@dataclass
class EffectiveStep:
    step: Optional[Step]  # None = Zusatzschritt aus der Variante
    name: str
    instruction: str
    time: int
    is_added: bool = False
    added_note: Optional[VariantStepNote] = None
    notes: list = field(default_factory=list)  # VariantStepNote
    ingredients: list = field(default_factory=list)  # EffectiveIngredient (ohne entfernte)
    removed_ingredients: list = field(default_factory=list)  # EffectiveIngredient mit status removed


@dataclass
class EffectiveRecipe:
    recipe: Recipe
    variant: Optional[RecipeVariant]
    base_servings: int
    servings: Decimal
    factor: Decimal
    steps: list = field(default_factory=list)
    orphaned_changes: list = field(default_factory=list)  # Änderungen, deren Originalzutat/-schritt fehlt
    orphaned_notes: list = field(default_factory=list)

    def all_ingredients(self, include_headers=False):
        """Alle aktiven Zutaten über alle Schritte (ohne entfernte)."""
        for s in self.steps:
            for i in s.ingredients:
                if include_headers or not i.is_header:
                    yield i


def _scale(amount, factor) -> Decimal:
    if amount is None:
        return Decimal(0)
    return Decimal(amount) * factor


def scaling_factor(recipe: Recipe, servings=None) -> tuple[Decimal, Decimal]:
    """Gibt (servings, factor) zurück. Ungültige Werte → Grundportionen des Rezepts."""
    base = Decimal(recipe.servings or 1)
    if base <= 0:
        base = Decimal(1)
    try:
        target = Decimal(str(servings)) if servings not in (None, '') else base
    except Exception:
        target = base
    if target <= 0:
        target = base
    return target, target / base


def effective_recipe(recipe: Recipe, variant: Optional[RecipeVariant] = None, servings=None) -> EffectiveRecipe:
    if variant is not None and variant.recipe_id != recipe.pk:
        raise ValueError('Variante gehört nicht zu diesem Rezept')

    target, factor = scaling_factor(recipe, servings)
    result = EffectiveRecipe(recipe=recipe, variant=variant, base_servings=recipe.servings, servings=target, factor=factor)

    steps = list(recipe.steps.all().order_by('order', 'pk').prefetch_related('ingredients__food', 'ingredients__unit'))
    step_ids = {s.pk for s in steps}

    changes = list(variant.ingredient_changes.select_related('food', 'unit', 'ingredient', 'step').all()) if variant else []
    notes = list(variant.step_notes.all()) if variant else []

    by_ingredient = {}
    adds_by_step = {}
    for c in changes:
        if c.action in (VariantIngredientChange.REPLACE, VariantIngredientChange.REMOVE):
            if c.ingredient_id is None:
                result.orphaned_changes.append(c)
            else:
                # mehrere Änderungen an derselben Zutat: die zuletzt angelegte gewinnt
                by_ingredient[c.ingredient_id] = c
        elif c.action == VariantIngredientChange.ADD:
            target_step = c.step_id if c.step_id in step_ids else (steps[-1].pk if steps else None)
            adds_by_step.setdefault(target_step, []).append(c)

    notes_by_step = {}
    added_steps = []
    for n in notes:
        if n.step_id is None:
            added_steps.append(n)
        elif n.step_id in step_ids:
            notes_by_step.setdefault(n.step_id, []).append(n)
        else:
            result.orphaned_notes.append(n)

    seen_ingredients = set()
    effective_steps = []
    for s in steps:
        es = EffectiveStep(step=s, name=s.name, instruction=s.instruction, time=s.time,
                           notes=notes_by_step.get(s.pk, []))
        for ing in s.ingredients.all():
            seen_ingredients.add(ing.pk)
            change = by_ingredient.get(ing.pk)
            base = EffectiveIngredient(
                status=ORIGINAL, food=ing.food, unit=ing.unit,
                amount=_scale(ing.amount, factor), base_amount=Decimal(ing.amount),
                note=ing.note or '', is_header=ing.is_header, no_amount=ing.no_amount, order=ing.order, ingredient=ing,
            )
            if change is None:
                es.ingredients.append(base)
            elif change.action == VariantIngredientChange.REMOVE:
                base.status = REMOVED
                base.change = change
                es.removed_ingredients.append(base)
            else:  # replace
                new_amount = change.amount if change.amount is not None else ing.amount
                es.ingredients.append(EffectiveIngredient(
                    status=CHANGED,
                    food=change.food or ing.food,
                    unit=change.unit or ing.unit,
                    amount=_scale(new_amount, factor), base_amount=Decimal(new_amount),
                    note=change.note or ing.note or '',
                    is_header=ing.is_header,
                    no_amount=ing.no_amount and change.amount is None,
                    order=ing.order, ingredient=ing, change=change,
                    original_food=ing.food, original_unit=ing.unit, original_amount=_scale(ing.amount, factor),
                    original_note=ing.note or '',
                ))
        for c in sorted(adds_by_step.get(s.pk, []), key=lambda x: (x.order, x.pk)):
            es.ingredients.append(EffectiveIngredient(
                status=ADDED, food=c.food, unit=c.unit,
                amount=_scale(c.amount, factor), base_amount=Decimal(c.amount or 0),
                note=c.note or '', no_amount=c.amount is None, order=c.order, change=c,
            ))
        effective_steps.append(es)

    # Änderungen an Zutaten, die (nicht mehr) im Rezept sind
    for ing_id, c in by_ingredient.items():
        if ing_id not in seen_ingredients:
            result.orphaned_changes.append(c)

    # Zusatzschritte einfügen: position = Index des Original-Schritts, vor dem eingefügt wird
    def added_step(n):
        return EffectiveStep(step=None, name='', instruction=n.text, time=n.time, is_added=True, added_note=n)

    added_by_pos = {}
    for n in sorted(added_steps, key=lambda x: (x.position, x.pk)):
        added_by_pos.setdefault(max(0, min(n.position, len(steps))), []).append(n)
    merged = []
    for i, es in enumerate(effective_steps):
        merged.extend(added_step(n) for n in added_by_pos.get(i, []))
        merged.append(es)
    merged.extend(added_step(n) for n in added_by_pos.get(len(steps), []))
    effective_steps = merged

    # Ein Rezept ohne Schritte: ergänzte Zutaten ohne Ziel-Schritt trotzdem anzeigen
    if not steps and adds_by_step.get(None):
        es = EffectiveStep(step=None, name='', instruction='', time=0, is_added=True)
        for c in adds_by_step[None]:
            es.ingredients.append(EffectiveIngredient(status=ADDED, food=c.food, unit=c.unit, amount=_scale(c.amount, factor),
                                                      base_amount=Decimal(c.amount or 0), note=c.note or '',
                                                      no_amount=c.amount is None, order=c.order, change=c))
        effective_steps.append(es)

    result.steps = effective_steps
    return result

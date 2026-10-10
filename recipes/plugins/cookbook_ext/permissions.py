"""
Berechtigungen der Erweiterungen – angelehnt an Tandoors CustomRecipePermission:

- Lesen: wer das zugehörige Rezept sehen darf (Gruppe guest oder höher, private Rezepte nur Ersteller/geteilt)
- Schreiben: Gruppe user (oder höher) UND das Rezept ist sichtbar
- immer nur im aktiven Space (request.space)
"""
from django.db.models import Q
from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS

from cookbook.helper.permission_helper import CustomRecipePermission, has_group_permission
from cookbook.models import Recipe


def visible_recipes(request):
    """Rezepte, die der Benutzer im aktiven Space sehen darf."""
    return Recipe.objects.filter(space=request.space).filter(
        Q(private=False) | Q(created_by=request.user) | Q(shared=request.user)
    ).distinct()


def recipe_of(obj):
    """Rezept zu einem unserer Objekte (Variante, Änderung, Notiz, Foto)."""
    if isinstance(obj, Recipe):
        return obj
    if hasattr(obj, 'recipe'):
        return obj.recipe
    if hasattr(obj, 'variant'):
        return obj.variant.recipe
    if hasattr(obj, 'cook_log'):
        return obj.cook_log.recipe
    return None


class RecipeChildPermission(permissions.BasePermission):
    message = 'Keine Berechtigung für dieses Rezept.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return has_group_permission(request, ['guest'])
        return has_group_permission(request, ['user'])

    def has_object_permission(self, request, view, obj):
        recipe = recipe_of(obj)
        if recipe is None or recipe.space_id != request.space.pk:
            return False
        if not CustomRecipePermission().has_object_permission(request, view, recipe):
            return False
        if request.method in SAFE_METHODS:
            return True
        return has_group_permission(request, ['user'])


class CookLogPhotoPermission(RecipeChildPermission):
    """Fotos: lesen wie Rezept; anlegen/löschen nur Besitzer der Bewertung (oder Admin)."""

    def has_object_permission(self, request, view, obj):
        if not super().has_object_permission(request, view, obj):
            return False
        if request.method in SAFE_METHODS:
            return True
        return obj.created_by_id == request.user.pk or obj.cook_log.created_by_id == request.user.pk \
            or has_group_permission(request, ['admin'])

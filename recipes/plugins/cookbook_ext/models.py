"""
Models der Rezept-App-Erweiterungen.

„Unsere Version" eines Rezepts (Varianten): Änderungen liegen ÜBER dem Original, das Original
bleibt unverändert. Hintergrund und Abweichungen vom ersten Entwurf: projekt/ENTSCHEIDUNGEN.md (E5).
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django_scopes import ScopedManager

from cookbook.models import CookLog, Food, Ingredient, PermissionModelMixin, Recipe, Space, Step, Unit


class RecipeVariant(models.Model, PermissionModelMixin):
    """Eine eigene Fassung eines Rezepts, z. B. „Unsere Version"."""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=128, default='Unsere Version')
    is_default = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    space = models.ForeignKey(Space, on_delete=models.CASCADE)
    objects = ScopedManager(space='space')

    class Meta:
        ordering = ('-is_default', 'name', 'pk')
        constraints = [
            models.UniqueConstraint(fields=['recipe', 'name'], name='rz_variant_unique_name_per_recipe'),
            models.UniqueConstraint(fields=['recipe'], condition=Q(is_default=True), name='rz_variant_one_default_per_recipe'),
        ]

    def __str__(self):
        return f'{self.recipe.name} – {self.name}'

    def save(self, *args, **kwargs):
        self.space_id = self.recipe.space_id
        super().save(*args, **kwargs)

    def get_owner(self):
        return self.created_by


class VariantIngredientChange(models.Model, PermissionModelMixin):
    """
    Eine Zutaten-Änderung in einer Variante.

    - replace: Originalzutat `ingredient` wird angepasst. Leere Felder (food/amount/unit/note) = Originalwert
               behalten. Nur `amount` gesetzt = „Menge ändern".
    - add:     neue Zutat (food Pflicht) im Schritt `step` (leer = letzter Schritt) an Position `order`.
    - remove:  Originalzutat `ingredient` entfällt.
    """
    REPLACE = 'replace'
    ADD = 'add'
    REMOVE = 'remove'
    ACTIONS = ((REPLACE, 'Ersetzen/Ändern'), (ADD, 'Ergänzen'), (REMOVE, 'Entfernen'))

    variant = models.ForeignKey(RecipeVariant, on_delete=models.CASCADE, related_name='ingredient_changes')
    action = models.CharField(max_length=16, choices=ACTIONS)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    step = models.ForeignKey(Step, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    food = models.ForeignKey(Food, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    amount = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    note = models.CharField(max_length=256, blank=True, default='')
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    space = models.ForeignKey(Space, on_delete=models.CASCADE)
    objects = ScopedManager(space='space')

    class Meta:
        ordering = ('order', 'pk')

    def __str__(self):
        return f'{self.get_action_display()} ({self.variant})'

    def clean(self):
        recipe = self.variant.recipe
        if self.action in (self.REPLACE, self.REMOVE):
            if not self.ingredient_id:
                raise ValidationError({'ingredient': 'Für „Ersetzen" und „Entfernen" muss eine Zutat des Rezepts gewählt werden.'})
            if not Ingredient.objects.filter(pk=self.ingredient_id, step__recipe=recipe).exists():
                raise ValidationError({'ingredient': 'Die Zutat gehört nicht zu diesem Rezept.'})
        if self.action == self.ADD and not self.food_id:
            raise ValidationError({'food': 'Für „Ergänzen" muss ein Lebensmittel angegeben werden.'})
        if self.step_id and not recipe.steps.filter(pk=self.step_id).exists():
            raise ValidationError({'step': 'Der Schritt gehört nicht zu diesem Rezept.'})
        for field in ('food', 'unit'):
            obj = getattr(self, field)
            if obj is not None and obj.space_id != recipe.space_id:
                raise ValidationError({field: 'Gehört zu einem anderen Space.'})

    def save(self, *args, **kwargs):
        self.space_id = self.variant.space_id
        super().save(*args, **kwargs)


class VariantStepNote(models.Model, PermissionModelMixin):
    """
    Notiz zu einem Schritt („Unsere Notiz") oder – ohne `step` – ein zusätzlicher Schritt.
    `position` (nur für Zusatzschritte): Index in der Original-Schrittliste, VOR dem eingefügt wird
    (0 = ganz vorne, ≥ Anzahl Schritte = am Ende).
    """
    variant = models.ForeignKey(RecipeVariant, on_delete=models.CASCADE, related_name='step_notes')
    step = models.ForeignKey(Step, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    position = models.IntegerField(default=0)
    text = models.TextField()
    time = models.IntegerField(default=0, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    space = models.ForeignKey(Space, on_delete=models.CASCADE)
    objects = ScopedManager(space='space')

    class Meta:
        ordering = ('position', 'pk')

    def __str__(self):
        return self.text[:40]

    def clean(self):
        if self.step_id and not self.variant.recipe.steps.filter(pk=self.step_id).exists():
            raise ValidationError({'step': 'Der Schritt gehört nicht zu diesem Rezept.'})

    def save(self, *args, **kwargs):
        self.space_id = self.variant.space_id
        super().save(*args, **kwargs)


class CookLogPhoto(models.Model, PermissionModelMixin):
    """Fotos zu einer Bewertung (Tandoor-CookLog), siehe ENTSCHEIDUNGEN.md E4."""
    cook_log = models.ForeignKey(CookLog, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='cooklog/')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    space = models.ForeignKey(Space, on_delete=models.CASCADE)
    objects = ScopedManager(space='space')

    class Meta:
        ordering = ('pk',)

    def save(self, *args, **kwargs):
        self.space_id = self.cook_log.space_id
        super().save(*args, **kwargs)

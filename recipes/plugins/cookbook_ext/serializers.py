from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from cookbook.models import CookLog, Food, Ingredient, Step, Unit
from cookbook.serializer import UserSerializer

from .models import CookLogPhoto, RecipeVariant, VariantIngredientChange, VariantStepNote
from .permissions import visible_recipes


def _num(value):
    """Decimal → float mit sinnvoller Genauigkeit für die API."""
    if value is None:
        return None
    return float(round(Decimal(value), 4))


def _named(obj):
    if obj is None:
        return None
    return {'id': obj.pk, 'name': obj.name, 'plural_name': getattr(obj, 'plural_name', None)}


class NamedObjectField(serializers.Field):
    """Liest Food/Unit als {id, name, plural_name}."""

    def to_representation(self, value):
        return _named(value)


def _clean(instance):
    try:
        instance.clean()
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)


class VariantIngredientChangeSerializer(serializers.ModelSerializer):
    """
    Schreiben: `food`/`unit` als ID **oder** `food_name`/`unit_name` als Text (wird im Space angelegt, falls neu).
    Lesen: `food_data`/`unit_data` als {id, name, plural_name}.
    """
    food_name = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128)
    unit_name = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128)
    food_data = NamedObjectField(source='food', read_only=True)
    unit_data = NamedObjectField(source='unit', read_only=True)
    amount = serializers.DecimalField(max_digits=32, decimal_places=16, required=False, allow_null=True, coerce_to_string=False)

    class Meta:
        model = VariantIngredientChange
        fields = ('id', 'variant', 'action', 'ingredient', 'step', 'food', 'food_name', 'food_data', 'unit', 'unit_name', 'unit_data',
                  'amount', 'note', 'order', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and getattr(request, 'space', None) is not None:
            space = request.space
            fields['variant'].queryset = RecipeVariant.objects.filter(space=space, recipe__in=visible_recipes(request))
            fields['ingredient'].queryset = Ingredient.objects.filter(space=space)
            fields['step'].queryset = Step.objects.filter(space=space)
            fields['food'].queryset = Food.objects.filter(space=space)
            fields['unit'].queryset = Unit.objects.filter(space=space)
        return fields

    def validate(self, attrs):
        space = self.context['request'].space
        food_name = (attrs.pop('food_name', '') or '').strip()
        unit_name = (attrs.pop('unit_name', '') or '').strip()
        if food_name:
            attrs['food'] = Food.objects.filter(space=space, name__iexact=food_name).first() or Food.add_root(name=food_name, space=space)
        if unit_name:
            attrs['unit'] = Unit.objects.filter(space=space, name__iexact=unit_name).first() or Unit.objects.create(name=unit_name, space=space)

        if self.instance is not None and 'variant' in attrs and attrs['variant'] != self.instance.variant:
            raise serializers.ValidationError({'variant': 'Die Variante einer Änderung kann nicht gewechselt werden.'})

        probe = VariantIngredientChange(**{**self._current(), **attrs})
        _clean(probe)
        return attrs

    def _current(self):
        if self.instance is None:
            return {}
        return {f: getattr(self.instance, f) for f in ('variant', 'action', 'ingredient', 'step', 'food', 'amount', 'unit', 'note', 'order')}


class VariantStepNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantStepNote
        fields = ('id', 'variant', 'step', 'position', 'text', 'time', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and getattr(request, 'space', None) is not None:
            fields['variant'].queryset = RecipeVariant.objects.filter(space=request.space, recipe__in=visible_recipes(request))
            fields['step'].queryset = Step.objects.filter(space=request.space)
        return fields

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError('Die Notiz darf nicht leer sein.')
        return value

    def validate(self, attrs):
        if self.instance is not None and 'variant' in attrs and attrs['variant'] != self.instance.variant:
            raise serializers.ValidationError({'variant': 'Die Variante einer Notiz kann nicht gewechselt werden.'})
        current = {} if self.instance is None else {'variant': self.instance.variant, 'step': self.instance.step}
        _clean(VariantStepNote(**{**current, **{k: v for k, v in attrs.items() if k in ('variant', 'step')}}))
        return attrs


class RecipeVariantSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    ingredient_changes = VariantIngredientChangeSerializer(many=True, read_only=True)
    step_notes = VariantStepNoteSerializer(many=True, read_only=True)

    class Meta:
        model = RecipeVariant
        fields = ('id', 'recipe', 'name', 'is_default', 'created_by', 'created_at', 'updated_at', 'ingredient_changes', 'step_notes')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and getattr(request, 'space', None) is not None:
            fields['recipe'].queryset = visible_recipes(request)
        return fields

    def validate(self, attrs):
        if self.instance is not None and 'recipe' in attrs and attrs['recipe'] != self.instance.recipe:
            raise serializers.ValidationError({'recipe': 'Das Rezept einer Variante kann nicht gewechselt werden.'})
        recipe = attrs.get('recipe') or getattr(self.instance, 'recipe', None)
        name = attrs.get('name', getattr(self.instance, 'name', 'Unsere Version'))
        qs = RecipeVariant.objects.filter(recipe=recipe, name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': 'Für dieses Rezept gibt es schon eine Variante mit diesem Namen.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['space'] = self.context['request'].space
        if validated_data.get('is_default'):
            RecipeVariant.objects.filter(recipe=validated_data['recipe'], is_default=True).update(is_default=False)
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if validated_data.get('is_default'):
            RecipeVariant.objects.filter(recipe=instance.recipe, is_default=True).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)


class CookLogPhotoSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    recipe = serializers.IntegerField(source='cook_log.recipe_id', read_only=True)

    class Meta:
        model = CookLogPhoto
        fields = ('id', 'cook_log', 'recipe', 'image', 'created_by', 'created_at')
        read_only_fields = ('id', 'recipe', 'created_by', 'created_at')

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and getattr(request, 'space', None) is not None:
            fields['cook_log'].queryset = CookLog.objects.filter(space=request.space, recipe__in=visible_recipes(request))
        return fields

    def validate_cook_log(self, cook_log):
        request = self.context['request']
        from cookbook.helper.permission_helper import has_group_permission
        if cook_log.created_by_id != request.user.pk and not has_group_permission(request, ['admin']):
            raise serializers.ValidationError('Fotos können nur zur eigenen Bewertung hinzugefügt werden.')
        return cook_log


# ---------------------------------------------------------------------------
# Effektive Fassung (nur lesen) – aus den Dataclasses des Service
# ---------------------------------------------------------------------------

def serialize_effective(eff):
    def ingredient(i):
        return {
            'status': i.status,
            'ingredient': i.ingredient.pk if i.ingredient else None,
            'change': i.change.pk if i.change else None,
            'food': _named(i.food),
            'unit': _named(i.unit),
            'amount': _num(i.amount),
            'base_amount': _num(i.base_amount),
            'note': i.note,
            'is_header': i.is_header,
            'no_amount': i.no_amount,
            'order': i.order,
            'original': None if i.status != 'changed' else {
                'food': _named(i.original_food),
                'unit': _named(i.original_unit),
                'amount': _num(i.original_amount),
            },
        }

    def note(n):
        return {'id': n.pk, 'text': n.text, 'time': n.time, 'position': n.position}

    steps = []
    for s in eff.steps:
        steps.append({
            'id': s.step.pk if s.step else None,
            'name': s.name,
            'instruction': s.instruction,
            'instructions_markdown': s.step.get_instruction_render() if s.step else None,
            'time': s.time,
            'is_added': s.is_added,
            'added_note': note(s.added_note) if s.added_note else None,
            'notes': [note(n) for n in s.notes],
            'ingredients': [ingredient(i) for i in s.ingredients],
            'removed_ingredients': [ingredient(i) for i in s.removed_ingredients],
        })

    return {
        'recipe': eff.recipe.pk,
        'variant': eff.variant.pk if eff.variant else None,
        'variant_name': eff.variant.name if eff.variant else None,
        'base_servings': eff.base_servings,
        'servings': _num(eff.servings),
        'factor': _num(eff.factor),
        'steps': steps,
        'orphaned_changes': [c.pk for c in eff.orphaned_changes],
        'orphaned_notes': [n.pk for n in eff.orphaned_notes],
    }

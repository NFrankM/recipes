from django.contrib import admin

from .models import CookLogPhoto, RecipeVariant, VariantIngredientChange, VariantStepNote


class VariantIngredientChangeInline(admin.TabularInline):
    model = VariantIngredientChange
    extra = 0
    raw_id_fields = ('ingredient', 'step', 'food', 'unit')
    exclude = ('space',)


class VariantStepNoteInline(admin.TabularInline):
    model = VariantStepNote
    extra = 0
    raw_id_fields = ('step',)
    exclude = ('space',)


@admin.register(RecipeVariant)
class RecipeVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipe', 'is_default', 'created_by', 'updated_at', 'space')
    list_filter = ('space', 'is_default')
    search_fields = ('name', 'recipe__name')
    raw_id_fields = ('recipe', 'created_by')
    exclude = ('space',)
    inlines = (VariantIngredientChangeInline, VariantStepNoteInline)


@admin.register(VariantIngredientChange)
class VariantIngredientChangeAdmin(admin.ModelAdmin):
    list_display = ('variant', 'action', 'ingredient', 'food', 'amount', 'unit', 'step')
    list_filter = ('action', 'space')
    raw_id_fields = ('variant', 'ingredient', 'step', 'food', 'unit')
    exclude = ('space',)


@admin.register(VariantStepNote)
class VariantStepNoteAdmin(admin.ModelAdmin):
    list_display = ('variant', 'step', 'position', 'text')
    raw_id_fields = ('variant', 'step')
    exclude = ('space',)


@admin.register(CookLogPhoto)
class CookLogPhotoAdmin(admin.ModelAdmin):
    list_display = ('cook_log', 'created_by', 'created_at', 'space')
    raw_id_fields = ('cook_log', 'created_by')
    exclude = ('space',)

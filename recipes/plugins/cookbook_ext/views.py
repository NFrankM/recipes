import uuid

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import decorators, mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from cookbook.helper.image_processing import get_filetype, handle_image, is_file_type_allowed
from cookbook.helper.permission_helper import CustomTokenHasReadWriteScope
from cookbook.models import CookLog, MealPlan

from .models import CookLogPhoto, RecipeVariant, VariantIngredientChange, VariantStepNote
from .permissions import CookLogPhotoPermission, RecipeChildPermission, visible_recipes
from .serializers import (CookLogPhotoSerializer, RecipeVariantSerializer, VariantIngredientChangeSerializer,
                          VariantStepNoteSerializer, serialize_effective)
from .services.effective import effective_recipe
from .services.shopping import add_to_shopping_list

SERVINGS_PARAM = OpenApiParameter(name='servings', description='Portionen, auf die skaliert wird (Standard: Portionen des Rezepts)', type=float)


def _int_param(request, name):
    value = request.query_params.get(name)
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError({name: 'Muss eine Zahl sein.'})


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter(name='recipe', description='Nur Varianten dieses Rezepts', type=int)]))
class RecipeVariantViewSet(viewsets.ModelViewSet):
    """Varianten („Unsere Version") eines Rezepts inkl. ihrer Änderungen und Notizen."""
    queryset = RecipeVariant.objects
    serializer_class = RecipeVariantSerializer
    permission_classes = [RecipeChildPermission & CustomTokenHasReadWriteScope]
    pagination_class = None
    pagination_disabled = True  # Tandoor-Konvention (test_schemas): Listen pro Rezept sind klein

    def get_queryset(self):
        qs = self.queryset.filter(space=self.request.space, recipe__in=visible_recipes(self.request)) \
            .select_related('recipe', 'created_by').prefetch_related('ingredient_changes__food', 'ingredient_changes__unit', 'step_notes')
        if (recipe := _int_param(self.request, 'recipe')) is not None:
            qs = qs.filter(recipe_id=recipe)
        return qs

    @extend_schema(parameters=[SERVINGS_PARAM], responses=OpenApiTypes.OBJECT)
    @decorators.action(detail=True, methods=['GET'])
    def effective(self, request, pk=None):
        """Effektive Zutaten und Schritte dieser Variante, skaliert auf `servings`."""
        variant = self.get_object()
        return Response(serialize_effective(effective_recipe(variant.recipe, variant, request.query_params.get('servings'))))

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    @decorators.action(detail=True, methods=['POST'])
    def shopping(self, request, pk=None):
        """Effektive Zutaten dieser Variante auf die Einkaufsliste setzen. Body: {servings?, mealplan?}"""
        variant = self.get_object()
        if request.space.demo:
            return Response({'msg': 'Im Demo-Modus nicht verfügbar'}, status=status.HTTP_403_FORBIDDEN)
        mealplan = None
        if request.data.get('mealplan'):
            mealplan = get_object_or_404(MealPlan, pk=request.data['mealplan'], space=request.space)
        slr = add_to_shopping_list(variant.recipe, variant, request.user, request.space,
                                   servings=request.data.get('servings'), mealplan=mealplan)
        return Response({'msg': f'{variant.recipe.name} ({variant.name}) wurde auf die Einkaufsliste gesetzt.',
                         'list_recipe': slr.pk, 'entries': slr.entries.count()}, status=status.HTTP_200_OK)


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter(name='variant', type=int)]))
class VariantIngredientChangeViewSet(viewsets.ModelViewSet):
    queryset = VariantIngredientChange.objects
    serializer_class = VariantIngredientChangeSerializer
    permission_classes = [RecipeChildPermission & CustomTokenHasReadWriteScope]
    pagination_class = None
    pagination_disabled = True  # Tandoor-Konvention (test_schemas): Listen pro Rezept sind klein

    def get_queryset(self):
        qs = self.queryset.filter(space=self.request.space, variant__recipe__in=visible_recipes(self.request)) \
            .select_related('variant__recipe', 'food', 'unit')
        if (variant := _int_param(self.request, 'variant')) is not None:
            qs = qs.filter(variant_id=variant)
        return qs


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter(name='variant', type=int)]))
class VariantStepNoteViewSet(viewsets.ModelViewSet):
    queryset = VariantStepNote.objects
    serializer_class = VariantStepNoteSerializer
    permission_classes = [RecipeChildPermission & CustomTokenHasReadWriteScope]
    pagination_class = None
    pagination_disabled = True  # Tandoor-Konvention (test_schemas): Listen pro Rezept sind klein

    def get_queryset(self):
        qs = self.queryset.filter(space=self.request.space, variant__recipe__in=visible_recipes(self.request)) \
            .select_related('variant__recipe')
        if (variant := _int_param(self.request, 'variant')) is not None:
            qs = qs.filter(variant_id=variant)
        return qs


class EffectiveRecipeViewSet(viewsets.GenericViewSet):
    """
    GET /api/effective-recipe/<recipe_id>/?variant=<id>&servings=<n>
    Ohne `variant`: das Original im selben Format (praktisch für den Umschalter Original/Unsere Version).
    """
    permission_classes = [RecipeChildPermission & CustomTokenHasReadWriteScope]
    pagination_class = None
    pagination_disabled = True  # Tandoor-Konvention (test_schemas): Listen pro Rezept sind klein

    def get_queryset(self):
        return visible_recipes(self.request)

    @extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH, description='Rezept-ID'),
                               SERVINGS_PARAM, OpenApiParameter(name='variant', type=int)], responses=OpenApiTypes.OBJECT)
    def retrieve(self, request, pk=None):
        recipe = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, recipe)
        variant = None
        if (variant_id := _int_param(request, 'variant')) is not None:
            variant = get_object_or_404(RecipeVariant.objects.filter(space=request.space), pk=variant_id, recipe=recipe)
        return Response(serialize_effective(effective_recipe(recipe, variant, request.query_params.get('servings'))))


@extend_schema_view(list=extend_schema(parameters=[OpenApiParameter(name='recipe', type=int), OpenApiParameter(name='cook_log', type=int)]))
class CookLogPhotoViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """Fotos zu Bewertungen (CookLog). Anlegen per multipart/form-data: cook_log, image."""
    queryset = CookLogPhoto.objects
    serializer_class = CookLogPhotoSerializer
    permission_classes = [CookLogPhotoPermission & CustomTokenHasReadWriteScope]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None
    pagination_disabled = True  # Tandoor-Konvention (test_schemas): Listen pro Rezept sind klein

    def get_queryset(self):
        qs = self.queryset.filter(space=self.request.space, cook_log__recipe__in=visible_recipes(self.request)) \
            .select_related('cook_log', 'created_by')
        if (recipe := _int_param(self.request, 'recipe')) is not None:
            qs = qs.filter(cook_log__recipe_id=recipe)
        if (cook_log := _int_param(self.request, 'cook_log')) is not None:
            qs = qs.filter(cook_log_id=cook_log)
        return qs

    def perform_create(self, serializer):
        upload = serializer.validated_data['image']
        if not is_file_type_allowed(upload.name, image_only=True):
            raise ValidationError({'image': 'Nur Bilder (jpg, png, webp, gif) sind erlaubt.'})
        filetype = get_filetype(upload.name).lower()
        image = handle_image(self.request, upload, filetype)
        if image is None:
            raise ValidationError({'image': 'Die Datei ist kein gültiges Bild.'})
        photo = CookLogPhoto(cook_log=serializer.validated_data['cook_log'], created_by=self.request.user)
        photo.image.save(f'{uuid.uuid4()}{filetype}', image, save=False)
        photo.save()
        serializer.instance = photo


class RecipeRatingViewSet(viewsets.GenericViewSet):
    """
    GET /api/recipe-rating/?recipe=1&recipe=2
    Durchschnitt und Anzahl der Bewertungen (CookLogs mit Sternen) ALLER Benutzer des Spaces je Rezept.
    (Tandoors eigenes Feld `rating` am Rezept zählt nur die Bewertungen des aktuellen Benutzers.)
    """
    permission_classes = [RecipeChildPermission & CustomTokenHasReadWriteScope]
    pagination_class = None
    pagination_disabled = True  # Tandoor-Konvention (test_schemas): Listen pro Rezept sind klein

    @extend_schema(parameters=[OpenApiParameter(name='recipe', type=int, many=True)], responses=OpenApiTypes.OBJECT)
    def list(self, request):
        try:
            ids = [int(x) for x in request.query_params.getlist('recipe')]
        except ValueError:
            raise ValidationError({'recipe': 'Muss eine Zahl sein.'})
        if not ids:
            raise ValidationError({'recipe': 'Mindestens ein Rezept angeben.'})
        rows = CookLog.objects.filter(space=request.space, recipe__in=visible_recipes(request).filter(pk__in=ids)) \
            .values('recipe').annotate(average=Avg('rating', filter=Q(rating__gt=0)), count=Count('pk', filter=Q(rating__gt=0)),
                                       cooked=Count('pk'))
        found = {r['recipe']: r for r in rows}
        return Response([{
            'recipe': rid,
            'average': round(found[rid]['average'], 2) if rid in found and found[rid]['average'] is not None else None,
            'count': found[rid]['count'] if rid in found else 0,
            'cooked': found[rid]['cooked'] if rid in found else 0,
        } for rid in ids])

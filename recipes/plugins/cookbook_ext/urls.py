from rest_framework import routers

from . import views

# Tandoor übernimmt die Registrierungen dieses Routers in seinen /api/-Router
# (siehe cookbook/urls.py: router.extend(...) für alle Plugins).
api_router = routers.DefaultRouter()
api_router.register(r'recipe-variant', views.RecipeVariantViewSet, basename='recipe-variant')
api_router.register(r'variant-ingredient-change', views.VariantIngredientChangeViewSet, basename='variant-ingredient-change')
api_router.register(r'variant-step-note', views.VariantStepNoteViewSet, basename='variant-step-note')
api_router.register(r'effective-recipe', views.EffectiveRecipeViewSet, basename='effective-recipe')
api_router.register(r'cook-log-photo', views.CookLogPhotoViewSet, basename='cook-log-photo')
api_router.register(r'recipe-rating', views.RecipeRatingViewSet, basename='recipe-rating')

# Eigene Nicht-API-Seiten (unter /ext/), aktuell keine
urlpatterns = []

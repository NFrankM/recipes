from rest_framework import routers

# Tandoor übernimmt die Registrierungen dieses Routers in seinen /api/-Router
# (siehe cookbook/urls.py: router.extend(...) für alle Plugins).
api_router = routers.DefaultRouter()

# Eigene Nicht-API-Seiten (unter /ext/), aktuell keine
urlpatterns = []

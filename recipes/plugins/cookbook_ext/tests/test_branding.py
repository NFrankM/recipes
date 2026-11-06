"""Branding: weiße Navigationsleiste statt Tandoor-Gold."""
from django.contrib.auth.models import User
from django_scopes import scopes_disabled

from cookbook.models import UserPreference


def test_neue_benutzer_bekommen_weisse_leiste(db):
    with scopes_disabled():
        u = User.objects.create(username='neu')
        assert UserPreference.objects.get(user=u).nav_bg_color == '#FFFFFF'


def test_bewusst_gewaehlte_farbe_bleibt(db):
    with scopes_disabled():
        u = User.objects.create(username='bunt')
        up = UserPreference.objects.get(user=u)
        up.nav_bg_color = '#ddbf86'  # später bewusst auf Gold gestellt
        up.save()
        up.refresh_from_db()
        assert up.nav_bg_color == '#ddbf86'

"""
Branding „Rezepteapp“: Benutzer mit unverändertem Tandoor-Standard (#ddbf86) bekommen die weiße Navigationsleiste.
(Der Seitenname für E-Mails wird per post_migrate gesetzt, siehe services/branding.py.)
"""
from django.db import migrations

TANDOOR_NAV_DEFAULT = '#ddbf86'
NAV_DEFAULT = '#FFFFFF'


def forwards(apps, schema_editor):
    UserPreference = apps.get_model('cookbook', 'UserPreference')
    UserPreference.objects.filter(nav_bg_color__iexact=TANDOOR_NAV_DEFAULT).update(nav_bg_color=NAV_DEFAULT)


def backwards(apps, schema_editor):
    UserPreference = apps.get_model('cookbook', 'UserPreference')
    UserPreference.objects.filter(nav_bg_color=NAV_DEFAULT).update(nav_bg_color=TANDOOR_NAV_DEFAULT)


class Migration(migrations.Migration):
    dependencies = [
        ('cookbook', '0242_space_household_setup_completed'),
        ('cookbook_ext', '0002_step_timing'),
    ]

    operations = [migrations.RunPython(forwards, backwards)]

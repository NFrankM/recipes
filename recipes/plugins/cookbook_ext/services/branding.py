"""
Branding „Rezepteapp“: Tandoors Standardfarbe der Navigationsleiste (#ddbf86, Gold) passt nicht zum Logo.
Neue Benutzereinstellungen bekommen Weiß; bestehende mit unverändertem Standard stellt Migration 0003 um.
Eine bewusst gewählte Farbe bleibt unangetastet.
"""
TANDOOR_NAV_DEFAULT = '#ddbf86'
NAV_DEFAULT = '#FFFFFF'


def default_nav_color(sender, instance, raw=False, **kwargs):
    """ pre_save für UserPreference: nur beim Anlegen und nur, wenn noch Tandoors Standard gesetzt ist """
    if raw or not instance._state.adding:  # keine DB-Abfrage (UserPreference ist space-gescoped)
        return
    if (instance.nav_bg_color or '').lower() == TANDOOR_NAV_DEFAULT:
        instance.nav_bg_color = NAV_DEFAULT


def site_name(sender, **kwargs):
    """
    post_migrate: Seitenname für E-Mails (allauth-Betreff „[Rezepteapp] …“). Nur Djangos Platzhalter „example.com“
    wird ersetzt; läuft nach dem Anlegen der Standard-Site durch django.contrib.sites.
    """
    from django.apps import apps
    from django.conf import settings
    if not apps.is_installed('django.contrib.sites'):
        return
    from django.contrib.sites.models import Site
    try:
        Site.objects.filter(pk=getattr(settings, 'SITE_ID', 1), name='example.com').update(name='Rezepteapp')
    except Exception:
        pass  # Tabelle noch nicht vorhanden

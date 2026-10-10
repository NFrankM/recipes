"""
Screenshots der App in Handybreite (390 x 844) – für Design-Abgleich.

Voraussetzung: Server läuft (python manage.py runserver), Demo-Daten (python manage.py rezept_demo),
Playwright-Chromium installiert (python -m playwright install chromium).

    python projekt/dev/screenshots.py [--base http://127.0.0.1:8000] [--out projekt/screenshots] [pfad ...]
"""
import argparse
import pathlib
import re

from playwright.sync_api import sync_playwright

STANDARD_SEITEN = {
    'start': '/',
    'rezept': '/recipe/{recipe}',
    'suche': '/advanced-search',
    'einkauf': '/shopping',
    'import': '/recipe/import',
    'einstellungen': '/settings/cosmetic',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8000')
    ap.add_argument('--out', default='projekt/screenshots')
    ap.add_argument('--user', default='demo')
    ap.add_argument('--password', default='demo1234')
    ap.add_argument('--recipe', default='1')
    ap.add_argument('--suffix', default='')
    ap.add_argument('--full', action='store_true', help='ganze Seite statt nur Bildschirmhöhe')
    ap.add_argument('seiten', nargs='*', help='name=pfad, z. B. rezept=/recipe/1')
    a = ap.parse_args()

    seiten = dict(STANDARD_SEITEN)
    if a.seiten:
        seiten = dict(s.split('=', 1) for s in a.seiten)

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='de-DE')
        page = ctx.new_page()
        page.goto(a.base + '/accounts/login/')
        page.fill('input[name=login]', a.user)
        page.fill('input[name=password]', a.password)
        page.click('button[type=submit]')
        page.wait_for_load_state('networkidle')
        for name, pfad in seiten.items():
            page.goto(a.base + pfad.format(recipe=a.recipe))
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(800)
            datei = out / f"{re.sub(r'[^a-z0-9_-]', '_', name)}{a.suffix}.png"
            page.screenshot(path=str(datei), full_page=a.full)
            print(datei)
        browser.close()


if __name__ == '__main__':
    main()

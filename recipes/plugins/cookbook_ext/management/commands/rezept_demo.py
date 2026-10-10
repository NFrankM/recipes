"""
Legt lokale Demo-Daten an (NUR für Entwicklung/Screenshots, nie in Produktion ausführen):
Benutzer, Space, einige Rezepte mit Bild, Zutaten und Schritten.

    python manage.py rezept_demo [--user demo] [--password demo1234]
"""
import io
import random
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django_scopes import scopes_disabled
from PIL import Image, ImageDraw

from cookbook.helper.permission_helper import create_space_for_user
from cookbook.models import Food, Ingredient, Keyword, Recipe, Step, Unit

REZEPTE = [
    {
        'name': 'Shakshuka mit Feta',
        'description': 'Eier in würziger Tomaten-Paprika-Soße, mit Feta und frischem Koriander.',
        'servings': 2, 'working_time': 15, 'waiting_time': 20,
        'keywords': ['Vegetarisch', 'Frühstück', 'Schnell'],
        'color': (196, 92, 62),
        'steps': [
            ('Zwiebel und Paprika in Streifen schneiden und in Olivenöl 5 Minuten anschwitzen.', 5,
             [(1, 'Stück', 'Zwiebel'), (2, 'Stück', 'Paprika rot'), (2, 'EL', 'Olivenöl')]),
            ('Knoblauch, Kreuzkümmel und Paprikapulver kurz mitrösten, dann die Tomaten zugeben und 10 Minuten köcheln.', 10,
             [(2, 'Zehe', 'Knoblauch'), (1, 'TL', 'Kreuzkümmel'), (400, 'g', 'Tomaten (Dose)')]),
            ('Mulden in die Soße drücken, Eier hineinschlagen und zugedeckt 6–8 Minuten stocken lassen.', 8,
             [(4, 'Stück', 'Ei')]),
            ('Mit zerbröseltem Feta und Koriander bestreuen und sofort servieren.', 0,
             [(100, 'g', 'Feta'), (0.5, 'Bund', 'Koriander')]),
        ],
    },
    {
        'name': 'Ofengemüse mit Joghurt-Dip',
        'description': 'Buntes Gemüse vom Blech, dazu ein frischer Kräuterjoghurt.',
        'servings': 4, 'working_time': 20, 'waiting_time': 35,
        'keywords': ['Vegetarisch', 'Ofen'],
        'color': (122, 150, 96),
        'steps': [
            ('Ofen auf 200 °C Umluft vorheizen. Gemüse in mundgerechte Stücke schneiden.', 0,
             [(600, 'g', 'Kartoffeln'), (2, 'Stück', 'Zucchini'), (1, 'Stück', 'Paprika rot'), (1, 'Stück', 'Zwiebel')]),
            ('Mit Öl, Salz und Rosmarin mischen und 35 Minuten backen.', 35,
             [(3, 'EL', 'Olivenöl'), (1, 'TL', 'Salz'), (2, 'Zweig', 'Rosmarin')]),
            ('Joghurt mit Zitronensaft, Knoblauch und Kräutern verrühren.', 0,
             [(300, 'g', 'Joghurt'), (1, 'EL', 'Zitronensaft'), (1, 'Zehe', 'Knoblauch')]),
        ],
    },
    {
        'name': 'Zitronen-Ricotta-Pasta',
        'description': 'Cremige Pasta in 15 Minuten.',
        'servings': 2, 'working_time': 15, 'waiting_time': 0,
        'keywords': ['Pasta', 'Schnell'],
        'color': (226, 196, 112),
        'steps': [
            ('Pasta in Salzwasser al dente kochen, eine Tasse Kochwasser aufheben.', 10,
             [(250, 'g', 'Spaghetti')]),
            ('Ricotta mit Zitronenabrieb, Parmesan und etwas Kochwasser cremig rühren, mit der Pasta mischen.', 0,
             [(200, 'g', 'Ricotta'), (1, 'Stück', 'Zitrone'), (40, 'g', 'Parmesan')]),
        ],
    },
]


def _demo_bild(rgb):
    w, h = 1200, 900
    img = Image.new('RGB', (w, h), (238, 242, 245))
    d = ImageDraw.Draw(img)
    d.ellipse((w * 0.18, h * 0.12, w * 0.82, h * 0.98), fill=(255, 255, 255))
    d.ellipse((w * 0.25, h * 0.22, w * 0.75, h * 0.88), fill=rgb)
    rnd = random.Random(sum(rgb))
    for _ in range(14):
        x, y, r = rnd.randint(380, 820), rnd.randint(260, 700), rnd.randint(14, 34)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(min(255, c + 40) for c in rgb))
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=85)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'Legt lokale Demo-Daten an (nur Entwicklung).'

    def add_arguments(self, parser):
        parser.add_argument('--user', default='demo')
        parser.add_argument('--password', default='demo1234')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Nur mit DEBUG=1 erlaubt (Demo-Daten gehören nicht in Produktion).')

        with scopes_disabled():
            user, created = User.objects.get_or_create(username=options['user'], defaults={'is_superuser': True, 'is_staff': True})
            if created:
                user.set_password(options['password'])
                user.save()
            user_space = user.userspace_set.first() or create_space_for_user(user, name='Unser Haushalt')
            space = user_space.space
            space.space_setup_completed = True
            space.save()

            for r in REZEPTE:
                if Recipe.objects.filter(space=space, name=r['name']).exists():
                    continue
                recipe = Recipe.objects.create(
                    name=r['name'], description=r['description'], servings=r['servings'],
                    working_time=r['working_time'], waiting_time=r['waiting_time'],
                    internal=True, created_by=user, space=space,
                )
                recipe.image.save(f'demo_{recipe.pk}.jpg', _demo_bild(r['color']), save=True)
                for kw in r['keywords']:
                    k = Keyword.objects.filter(space=space, name=kw).first() or Keyword.add_root(name=kw, space=space)
                    recipe.keywords.add(k)
                for order, (text, minutes, ingredients) in enumerate(r['steps']):
                    step = Step.objects.create(instruction=text, time=minutes, order=order, space=space)
                    for i_order, (amount, unit_name, food_name) in enumerate(ingredients):
                        unit, _ = Unit.objects.get_or_create(space=space, name=unit_name)
                        food = Food.objects.filter(space=space, name=food_name).first() or Food.add_root(name=food_name, space=space)
                        step.ingredients.add(Ingredient.objects.create(
                            food=food, unit=unit, amount=Decimal(str(amount)), order=i_order, space=space))
                    recipe.steps.add(step)
                self.stdout.write(f'Rezept angelegt: {recipe.name}')

        self.stdout.write(self.style.SUCCESS(f"Fertig. Login: {options['user']} / {options['password'] if created else '(unverändert)'}"))

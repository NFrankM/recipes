"""
Zeitangaben aus Schritttexten erkennen („30 Minuten ruhen lassen“, „1 Std. gehen lassen“, „über Nacht“).

Ergebnis ist nur ein Vorschlag für Step.time (Minuten); in der Rezeptansicht und im Editor lässt er sich ändern.
Mehrere Angaben in einem Schritt werden addiert („8 Minuten kneten, dann 1 Std. gehen lassen“ = 68),
Angaben nach „nach“, „alle“, „jede“ zählen nicht („nach 10 Minuten die Temperatur senken“).
Bei Spannen („2–3 Stunden“) zählt der größere Wert – für die Planung die sichere Seite.
"""
import re

OVERNIGHT_MINUTES = 720
MAX_MINUTES = 3 * 24 * 60

WORDS = {
    'ein': 1, 'eine': 1, 'einer': 1, 'einen': 1, 'a': 1, 'an': 1, 'one': 1,
    'zwei': 2, 'two': 2, 'drei': 3, 'three': 3, 'vier': 4, 'four': 4, 'fünf': 5, 'five': 5, 'sechs': 6, 'six': 6,
    'sieben': 7, 'acht': 8, 'neun': 9, 'zehn': 10, 'ten': 10, 'elf': 11, 'zwölf': 12, 'zwanzig': 20, 'dreißig': 30,
    'eineinhalb': 1.5, 'anderthalb': 1.5, 'halbe': 0.5, 'eine halbe': 0.5, 'einer halben': 0.5, 'half an': 0.5, 'half': 0.5,
}
NUMBER = r'(?:\d+(?:[.,]\d+)?(?:\s*½)?|½|' + '|'.join(sorted((re.escape(w) for w in WORDS), key=len, reverse=True)) + r')'
UNIT = (r'(?P<unit>stunden?|std\.?|h|hours?|hrs?\.?|'
        r'minuten?|minutes?|mins?\.?|'
        r'sekunden?|sek\.?|sec\.?|seconds?|'
        r'tage?n?|days?)(?![a-zäöüß])')
DURATION = re.compile(
    r'(?P<prefix>\b(?:nach|alle|jede[nrs]?|after|every)\s+)?'
    r'(?<![\wäöüß])(?P<a>' + NUMBER + r')(?:\s*(?:-|–|bis|to|oder|or)\s*(?P<b>' + NUMBER + r'))?\s*' + UNIT,
    re.I,
)
OVERNIGHT = re.compile(r'über\s+nacht|overnight', re.I)


def _num(text):
    text = text.strip().lower()
    if text in WORDS:
        return WORDS[text]
    half = 0.5 if '½' in text else 0
    text = text.replace('½', '').strip()
    if not text:
        return half
    try:
        return float(text.replace(',', '.')) + half
    except ValueError:
        return None


def _factor(unit):
    u = unit.lower()
    if u.startswith(('st', 'h')):
        return 60
    if u.startswith(('se', 'sec')):
        return 1 / 60
    if u.startswith(('tag', 'day')):
        return 24 * 60
    return 1


def suggest_minutes(text):
    """ Vorschlag in Minuten (int) oder 0, wenn nichts erkannt wurde """
    if not text:
        return 0
    total = 0.0
    longest = 0.0
    for m in DURATION.finditer(text):
        if m.group('prefix'):
            continue
        a = _num(m.group('a'))
        b = _num(m.group('b')) if m.group('b') else None
        value = max(x for x in (a, b) if x is not None) if (a is not None or b is not None) else None
        if value is None:
            continue
        minutes = value * _factor(m.group('unit'))
        longest = max(longest, minutes)
        total += minutes
    if OVERNIGHT.search(text) and longest < 6 * 60:
        total += OVERNIGHT_MINUTES  # „über Nacht (ca. 12 Stunden)“ nicht doppelt zählen
    if 0 < total < 1:
        return 1  # „30 Sekunden mixen“ → 1 Minute statt 0
    return int(round(min(total, MAX_MINUTES)))


def on_recipe_import(sender, recipe_json, **kwargs):
    """ Empfänger für recipe_import_postprocess: Step.time vorschlagen, wenn die Quelle keine Zeit liefert """
    for step in recipe_json.get('steps', []):
        if not step.get('time'):
            minutes = suggest_minutes(step.get('instruction', ''))
            if minutes:
                step['time'] = minutes

"""
HTML-Fallback für den URL-Import.

Viele Seiten haben gar keine oder unvollständige schema.org-Recipe-Daten (z. B. WDR: nur „Article“,
Düsentrieb: Recipe ohne Zutaten und Anleitung). Dann suchen wir im HTML nach Überschriften wie „Zutaten“
oder „Zubereitung“ und übernehmen die Listen bzw. Absätze darunter. Zutatenzeilen laufen durch Tandoors
IngredientParser, genau wie beim normalen Import.

Eingebunden über das Signal ``recipe_import_postprocess`` aus ``cookbook.helper.recipe_url_import``.
"""
import re

from bs4 import NavigableString, Tag

from cookbook.helper.recipe_url_import import clean_instruction_string, normalize_string

INGREDIENT_HEADING = re.compile(r'^\s*(zutaten(liste)?|ingredients?|du brauchst|das brauchst du|einkaufsliste)\b', re.I)
INSTRUCTION_HEADING = re.compile(r'^\s*(zubereitung|anleitung|instructions?|so geht.?s|so wird.?s gemacht|directions|method|preparation)\b', re.I)
SERVINGS = re.compile(r'(\d+)\s*(?:bis\s*\d+\s*)?(portionen|personen|stück|stueck)', re.I)

HEADINGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
BLOCKS = HEADINGS | {'p', 'div', 'section', 'li', 'dt', 'header', 'span'}
LISTS = {'ul', 'ol'}
MAX_HEADING_LEN = 60
MAX_LINES = 80


def _text(el):
    return normalize_string(el.get_text(' ', strip=True)) if isinstance(el, Tag) else normalize_string(str(el))


def _is_heading(el, pattern=None):
    """ Überschrift = h1–h6 oder kurzes Element, dessen gesamter Text eine bekannte Überschrift ist """
    if not isinstance(el, Tag):
        return False
    text = _text(el)
    if not text or len(text) > MAX_HEADING_LEN:
        return el.name in HEADINGS and pattern is None
    patterns = [pattern] if pattern else [INGREDIENT_HEADING, INSTRUCTION_HEADING]
    if any(p.match(text) for p in patterns):
        return True
    return el.name in HEADINGS and pattern is None


def _find_anchor(soup, pattern):
    """ Erstes Element, dessen Text mit der Überschrift beginnt – auf den umschließenden Block normalisiert """
    for el in soup.find_all(list(HEADINGS | {'p', 'strong', 'b', 'dt', 'span', 'div', 'li', 'th', 'legend'})):
        text = _text(el)
        if not text or len(text) > MAX_HEADING_LEN or not pattern.match(text):
            continue
        if el.find(list(LISTS)):
            continue  # Container, nicht die Überschrift selbst
        # <p><strong>Zutaten</strong></p> → der Absatz ist die Überschrift
        while el.parent is not None and el.parent.name in BLOCKS and _text(el.parent) == text:
            el = el.parent
        return el
    return None


def _lines(p):
    """ Zeilen eines Absatzes, getrennt an <br>. Fett gesetzter Zeilenanfang = Gruppenüberschrift """
    lines, current, header = [], '', None
    for child in p.children:
        if isinstance(child, Tag) and child.name == 'br':
            lines.append(current)
            current = ''
            continue
        if isinstance(child, Tag) and child.name in ('strong', 'b') and not current.strip() and not lines:
            # <strong>Aufstrich</strong><br/> bzw. <strong>Gepickelte Zwiebeln<br/></strong>
            header = _text(child)
            continue
        current += child.get_text(' ') if isinstance(child, Tag) else str(child)
    lines.append(current)
    return header, [normalize_string(line) for line in lines if normalize_string(line)]


def _section(anchor, stop_pattern):
    """
    Inhalt nach der Überschrift bis zur nächsten Überschrift.
    Liefert (Listeneinträge, Absätze) – Absätze als Liste von (Gruppe, Zeilen).
    """
    items, paragraphs = [], []
    node = anchor
    # Hat die Überschrift keine Geschwister mit Inhalt (z. B. allein in einem <div>), eine Ebene höher weitersuchen
    for _ in range(3):
        if any(isinstance(s, Tag) and _text(s) for s in node.next_siblings):
            break
        if node.parent is None:
            break
        node = node.parent

    for sib in node.next_siblings:
        if isinstance(sib, NavigableString):
            if normalize_string(str(sib)):
                paragraphs.append((None, [normalize_string(str(sib))]))
            continue
        if not isinstance(sib, Tag) or sib.name in ('script', 'style', 'noscript', 'figure', 'img', 'iframe', 'form', 'button'):
            continue
        if _is_heading(sib) or (stop_pattern and _is_heading(sib, stop_pattern)):
            break
        if sib.name in LISTS:
            items += [_text(li) for li in sib.find_all('li', recursive=False) if _text(li)]
        elif sib.find(list(LISTS)) and not sib.find(list(HEADINGS)):
            for lst in sib.find_all(list(LISTS)):
                items += [_text(li) for li in lst.find_all('li', recursive=False) if _text(li)]
        elif sib.name in ('p', 'div', 'span', 'section'):
            if sib.find(list(HEADINGS)) or any(_is_heading(c) for c in sib.find_all(['p', 'strong', 'b'])
                                              if (stop_pattern and _is_heading(c, stop_pattern))):
                break
            header, lines = _lines(sib)
            if lines or header:
                paragraphs.append((header, lines))
        if len(items) + sum(len(p[1]) for p in paragraphs) > MAX_LINES:
            break
    return items, paragraphs


def find_ingredients(soup):
    """ Zutatenzeilen unter „Zutaten“ o. ä.; Listen haben Vorrang vor Absätzen """
    anchor = _find_anchor(soup, INGREDIENT_HEADING)
    if anchor is None:
        return [], None
    items, paragraphs = _section(anchor, INSTRUCTION_HEADING)
    servings = _servings(_text(anchor))
    if items:
        lines = items
    else:
        lines = [line for _header, ls in paragraphs for line in ls]
    for _header, ls in paragraphs:
        if servings is None and len(ls) == 1:
            servings = _servings(ls[0]) if SERVINGS.fullmatch(ls[0].strip()) else None
    lines = [line for line in lines if not SERVINGS.fullmatch(line.strip())]
    return lines, servings


def find_instructions(soup):
    """ Schritte unter „Zubereitung“ o. ä.; kurze Zeilen ohne Satzzeichen werden zum Namen des nächsten Schritts """
    anchor = _find_anchor(soup, INSTRUCTION_HEADING)
    if anchor is None:
        return []
    items, paragraphs = _section(anchor, INGREDIENT_HEADING)
    steps = []
    if items:
        return [{'name': '', 'instruction': clean_instruction_string(i)} for i in items]
    name = ''
    for header, lines in paragraphs:
        if header and not lines:
            name = header
            continue
        text = '\n'.join(lines)
        if len(lines) == 1 and len(text) <= 40 and not re.search(r'[.!?:]$', text):
            name = text  # z. B. „Anrichten“
            continue
        if text:
            steps.append({'name': (header or name)[:128], 'instruction': clean_instruction_string(text)})
            name = ''
    return steps


def _servings(text):
    m = SERVINGS.search(text or '')
    return int(m.group(1)) if m else None


def _page_title(soup):
    og = soup.find('meta', property='og:title')
    if og and og.get('content'):
        return normalize_string(og['content'])
    h1 = soup.find('h1')
    if h1:
        return _text(h1)
    return _text(soup.title) if soup.title else ''


def _has_instructions(recipe_json):
    description = recipe_json.get('description') or ''
    for s in recipe_json['steps']:
        text = s.get('instruction', '')
        if description:
            text = text.replace(f'*{description}*  \n\n', '')
        if text.strip():
            return True
    return False


def _ingredient(line, ingredient_parser):
    try:
        amount, unit, food, note = ingredient_parser.parse(line)
        return {'amount': amount, 'food': {'name': food}, 'unit': {'name': unit} if unit else None, 'note': note, 'original_text': line}
    except Exception:
        return {'amount': 0, 'food': {'name': line}, 'unit': None, 'note': '', 'original_text': line}


def apply_html_fallback(recipe_json, soup, ingredient_parser, show_ingredients_table=True):
    """ Ergänzt fehlende Zutaten/Schritte in recipe_json aus dem HTML. Gibt zurück, was ergänzt wurde. """
    added = []
    if soup is None:
        return added

    if not _has_instructions(recipe_json):
        steps = find_instructions(soup)
        if steps:
            old_ingredients = [i for s in recipe_json['steps'] for i in s.get('ingredients', [])]
            description = recipe_json.get('description') or ''
            recipe_json['steps'] = [{**s, 'ingredients': [], 'show_ingredients_table': show_ingredients_table} for s in steps]
            recipe_json['steps'][0]['ingredients'] = old_ingredients
            if len(description) > 256:
                recipe_json['steps'][0]['instruction'] = f'*{description}*  \n\n' + recipe_json['steps'][0]['instruction']
            added.append('steps')

    if not any(s.get('ingredients') for s in recipe_json['steps']):
        lines, servings = find_ingredients(soup)
        if lines:
            recipe_json['steps'][0]['ingredients'] = [_ingredient(line, ingredient_parser) for line in lines]
            added.append('ingredients')
            if servings and recipe_json.get('servings', 1) in (None, 0, 1):
                recipe_json['servings'] = servings

    if added and not recipe_json.get('name'):
        recipe_json['name'] = _page_title(soup)[:128]
    return added


def on_recipe_import(sender, recipe_json, scrape, request, ingredient_parser, **kwargs):
    """ Empfänger für recipe_import_postprocess """
    try:
        show = request.user.userpreference.show_step_ingredients
    except Exception:
        show = True
    return apply_html_fallback(recipe_json, getattr(scrape, 'soup', None), ingredient_parser, show)

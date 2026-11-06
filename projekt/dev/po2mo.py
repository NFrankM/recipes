"""
Minimaler Ersatz für `msgfmt` (GNU gettext fehlt auf dem Mac): kompiliert eine .po-Datei zu .mo.
Überspringt fuzzy-Einträge, leere Übersetzungen und veraltete (#~) Einträge – wie msgfmt.

    python projekt/dev/po2mo.py cookbook/locale/de/LC_MESSAGES/django.po            # schreibt django.mo daneben
    python projekt/dev/po2mo.py --check cookbook/locale/de/LC_MESSAGES/django.po    # vergleicht nur mit vorhandener .mo
    python projekt/dev/po2mo.py --patch=Rezepteapp cookbook/locale/de/LC_MESSAGES/django.po
        # übernimmt in die vorhandene .mo NUR Einträge, deren Übersetzung „Rezepteapp“ enthält (Rest bleibt wie von Upstream)
"""
import ast
import gettext
import io
import struct
import sys


def parse(path):
    entries, cur, key, fuzzy = [], {}, None, False

    def flush():
        nonlocal cur, fuzzy
        if 'msgid' in cur and not fuzzy:
            entries.append(cur)
        cur, fuzzy = {}, False

    for raw in open(path, encoding='utf-8'):
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith('#~'):
            continue
        if line.startswith('#,'):
            if cur:
                flush()
            fuzzy = 'fuzzy' in line
            continue
        if line.startswith('#'):
            continue
        if line.startswith('"'):
            cur[key] += ast.literal_eval(line)
            continue
        k, _, v = line.partition(' ')
        if k in ('msgctxt', 'msgid') and 'msgstr' in ''.join(cur):
            f = fuzzy
            flush()
            fuzzy = f if k == 'msgid' and 'msgctxt' in cur else False
        key = k
        cur[key] = ast.literal_eval(v)
    flush()

    catalog = {}
    for e in entries:
        msgid = e['msgid']
        if 'msgctxt' in e:
            msgid = e['msgctxt'] + '\x04' + msgid
        if 'msgid_plural' in e:
            strs = [e[k] for k in sorted((k for k in e if k.startswith('msgstr[')), key=lambda x: int(x[7:-1]))]
            if not any(strs):
                continue
            catalog[msgid + '\x00' + e['msgid_plural']] = '\x00'.join(strs)
        elif e.get('msgstr'):
            catalog[msgid] = e['msgstr']
    return catalog


def build(catalog):
    keys = sorted(catalog)
    ids = b''
    strs = b''
    offsets = []
    for k in keys:
        kb, vb = k.encode('utf-8'), catalog[k].encode('utf-8')
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b'\x00'
        strs += vb + b'\x00'
    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    out = struct.pack('Iiiiiii', 0x950412de, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    out += struct.pack(f'{len(koffsets)}i', *koffsets) + struct.pack(f'{len(voffsets)}i', *voffsets)
    return out + ids + strs


def load_mo(path):
    t = gettext.GNUTranslations(open(path, 'rb'))
    return t._catalog


def main():
    check = '--check' in sys.argv
    po = [a for a in sys.argv[1:] if not a.startswith('--')][0]
    mo = po[:-3] + '.mo'
    patch = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--patch=')), None)
    try:
        old = load_mo(mo)
    except FileNotFoundError:
        old = {}
    catalog = parse(po)
    if patch:
        catalog = {**old, **{k: v for k, v in catalog.items() if patch in v and k}}
    data = build(catalog)
    new = gettext.GNUTranslations(io.BytesIO(data))._catalog
    changed = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    print(f'{len(new)} Einträge, {len(changed)} abweichend von {mo}')
    for k in changed[:20]:
        print('  ', repr(k)[:80], '|', repr(old.get(k))[:60], '→', repr(new.get(k))[:60])
    if not check:
        open(mo, 'wb').write(data)
        print('geschrieben:', mo)


if __name__ == '__main__':
    main()

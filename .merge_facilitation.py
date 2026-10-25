#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge .facilitation.py metadata into the exercises array in index.html.

Idempotent: if a `format:` field is already present the exercise is skipped, so
re-running the script will not duplicate fields.
"""
import importlib.util, io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('facilitation', os.path.join(HERE, '.facilitation.py'))
fac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fac)

HTML = os.path.join(HERE, 'index.html')
html = io.open(HTML, encoding='utf-8').read()


def js_str(s):
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    s = s.replace('\n', '\\n').replace('\r', '\\r')
    return '"' + s + '"'


def js_val(v, indent):
    pad = ' ' * indent
    if isinstance(v, str):
        return js_str(v)
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, dict):
        inner = ',\n'.join(f'{pad}    {js_str(k)}: {js_val(val, indent + 4)}'
                           for k, val in v.items())
        return '{\n' + inner + '\n' + pad + '}'
    if isinstance(v, list):
        return '[' + ', '.join(js_val(x, indent) for x in v) + ']'
    raise TypeError(type(v))


def build(name):
    fmt, intensity, contact = fac.CLASSIFY[name]
    meta = {'format': fmt, 'intensity': intensity, 'contact': contact}
    for src, key in ((fac.TIP, 'tip'), (fac.ADAPT, 'adapt'), (fac.SAFETY, 'safety'),
                     (fac.ANSWER_KEY, 'answerKey'), (fac.TAKEAWAY, 'takeaway')):
        if name in src:
            meta[key] = src[name]
    return meta


NAME_RE = re.compile(r'^\s*name: "(?:[^"\\]|\\.)*",$', re.M)
# `source:` is emitted immediately after `id:`, i.e. BEFORE `name:`,
# so each name line must be paired with the nearest source line above it.
SRC_RE = re.compile(r'^\s*source: "\w+",$', re.M)
HAVE_RE = re.compile(r'^\s*format: "\w+",$', re.M)
# an answerKey block: `answerKey: {` … entries … `},` with the closing brace
# at the same indent as the field itself
KEY_RE = re.compile(r'^([ \t]*)answerKey: \{.*?^\1\},\n', re.M | re.S)

sources = [(m.start(), m.end()) for m in SRC_RE.finditer(html)]

# collect targets first, then patch from the end so offsets stay valid
targets = []
for m in NAME_RE.finditer(html):
    name = re.match(r'^\s*name: "((?:[^"\\]|\\.)*)",$', m.group(0)).group(1)
    if name not in fac.CLASSIFY:
        continue
    indent = len(m.group(0)) - len(m.group(0).lstrip())
    # nearest source line strictly above this name line
    above = [s for s in sources if s[1] <= m.start()]
    if not above:
        continue
    targets.append((above[-1][1], indent, name))

merged, missing, added_fields = 0, [], []
keys_updated = []
for pos, indent, name in reversed(targets):
    # additive + idempotent: only insert the fields this exercise still lacks.
    # the window must end where the next exercise's `source:` line begins,
    # otherwise a neighbour's field looks like this one is already present.
    nxt = next((s for s, _ in sources if s > pos), len(html))
    window = html[pos:nxt]
    existing = set(re.findall(r'^\s*(\w+):', window, re.M))

    # an answerKey that already exists is rewritten from the source of truth,
    # so the key and the instruction cannot drift apart
    if name in fac.ANSWER_KEY and 'answerKey' in existing:
        want = (f'{" " * (indent + 4)}answerKey: '
                f'{js_val(fac.ANSWER_KEY[name], indent + 4)},\n')
        cur = KEY_RE.search(window)
        if cur and cur.group(0) != want:
            window = window[:cur.start()] + want + window[cur.end():]
            html = html[:pos] + window + html[nxt:]
            keys_updated.append(name)

    todo = [(k, v) for k, v in build(name).items() if k not in existing]
    if not todo:
        continue
    block = '\n'.join(f'{" " * (indent + 4)}{k}: {js_val(v, indent + 4)},'
                      for k, v in todo)
    html = html[:pos] + '\n' + block + html[pos:]
    merged += 1
    added_fields.extend(k for k, _ in todo)

io.open(HTML, 'w', encoding='utf-8').write(html)
print(f'updated {merged} exercises, {len(added_fields)} fields inserted')
if added_fields:
    from collections import Counter
    print('  by field:', dict(Counter(added_fields)))
if keys_updated:
    print('  answerKey rewritten from .facilitation.py:', ', '.join(keys_updated))
if missing:
    print('PROBLEMS:', missing)

unknown = sorted(set(fac.CLASSIFY) - {n for _, _, n in targets})
if unknown:
    print('CLASSIFY keys with no matching exercise:', unknown)

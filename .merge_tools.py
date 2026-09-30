#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge contexts and facilitation tools into index.html.

Idempotent and additive: only inserts fields an exercise does not already have,
and skips exercises that are already present.
"""
import importlib.util, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# CONTEXT lives in the tools module; CLASSIFY/TIP/… live in .facilitation.py
tools = load('.facilitation_tools.py', 'facilitation_tools')
ctx = tools

HTML = os.path.join(HERE, 'index.html')
html = io.open(HTML, encoding='utf-8').read()


def js_str(s):
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    return '"' + s.replace('\n', '\\n').replace('\r', '\\r') + '"'


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


def render(fields, indent):
    return '\n'.join(f'{" " * indent}{k}: {js_val(v, indent)},'
                     for k, v in fields.items() if v is not None)


NAME_RE = re.compile(r'^\s*name: "(?:[^"\\]|\\.)*",$', re.M)
SRC_RE = re.compile(r'^\s*source: "\w+",$', re.M)
HAVE_RE = re.compile(r'^\s*(\w+):', re.M)

# ---------- 1. contexts ---------------------------------------------------
sources = [(m.start(), m.end()) for m in SRC_RE.finditer(html)]
targets = []
for m in NAME_RE.finditer(html):
    name = re.match(r'^\s*name: "((?:[^"\\]|\\.)*)",$', m.group(0)).group(1)
    if name not in ctx.CONTEXT:
        continue
    above = [s for s in sources if s[1] <= m.start()]
    if not above:
        continue
    targets.append((above[-1][1], len(m.group(0)) - len(m.group(0).lstrip()), name))

ctx_added = 0
for pos, indent, name in reversed(targets):
    nxt = next((s for s, _ in sources if s > pos), len(html))
    existing = set(re.findall(r'^\s*(\w+):', html[pos:nxt], re.M))
    if 'context' in existing:
        continue
    block = f'{" " * (indent + 4)}context: {js_val(ctx.CONTEXT[name], indent + 4)},'
    html = html[:pos] + '\n' + block + html[pos:]
    ctx_added += 1

# ---------- 2. facilitation tools -----------------------------------------
existing_ids = set(re.findall(r'^\s*id: (\d+),', html, re.M))
new_ids = [t['id'] for t in tools.FACILITATION]
to_add = [t for t in tools.FACILITATION if t['id'] not in existing_ids]
if to_add:
    block = ''.join(
        '            {\n'
        + f'                id: {t["id"]},\n'
        + f'                source: "facilitation",\n'
        + f'                name: {js_str(t["name"])},\n'
        + f'                time: {js_str(t["time"])},\n'
        + f'                duration: {t["duration"]},\n'
        + f'                group: {js_str(t["group"])},\n'
        + f'                types: [{", ".join(js_str(x) for x in t["types"])}],\n'
        + f'                description: {js_str(t["description"])},\n'
        + f'                materials: [{", ".join(js_str(m) for m in t["materials"])}],\n'
        + '                steps: [\n'
        + ',\n'.join('                    ' + js_str(s) for s in t['steps'])
        + '\n                ],\n'
        + f'                purpose: {js_str(t["purpose"])},\n'
        + f'                business: {js_str(t["business"])},\n'
        + '                format: "facilitation",\n'
        + '                intensity: 1,\n'
        + '                contact: false,\n'
        + f'                takeaway: {js_str(t["takeaway"])},\n'
        + f'                tip: {js_str(t["tip"])},\n'
        + f'                adapt: {js_str(t["adapt"])},\n'
        + (f'                context: {js_str(t["context"])},\n' if t.get('context') else '')
        + (('                answerKey: {\n'
            + ',\n'.join(f'                    {js_str(k)}: {js_val(v, 20)}'
                        for k, v in t['answerKey'].items())
            + '\n                },\n') if t.get('answerKey') else '')
        + '            },\n'
        for t in to_add)

    # the previous last entry has no trailing comma: add one, then insert the
    # new objects immediately before the array terminator
    marker = '\n        ];'
    i = html.index(marker)
    head, tail = html[:i], html[i:]
    if not head.rstrip().endswith(','):
        head = head.rstrip() + ','
    html = (head
            + '\n\n            // === ИНСТРУМЕНТЫ ФАСИЛИТАЦИИ ===\n'
            + block.rstrip().rstrip(',')
            + tail)

io.open(HTML, 'w', encoding='utf-8').write(html)
print(f'contexts added: {ctx_added}')
print(f'facilitation tools added: {len(to_add)} (ids {", ".join(str(t["id"]) for t in to_add)})')
if existing_ids & set(new_ids):
    print('already present, skipped:', sorted(existing_ids & set(new_ids)))

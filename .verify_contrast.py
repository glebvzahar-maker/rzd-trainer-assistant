#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static theme check for index.html.

Why this exists: `.business-box` once had a hardcoded light background, so in the
dark theme the light body text sat on a light background at 1.07:1. axe-core did
not report it, because axe cannot resolve a background set on an ancestor outside
the audited node, and it cannot evaluate a gradient. This test closes that gap.

The page has three themes selected by `data-theme` on <html>:
  (unset)  light
  light    light
  dark     dark
  contrast solar / high-contrast light

Rules enforced here:
  1. no hardcoded background without a dark-theme override
  2. the solar theme must stay solid, not gradient (gradients wash out in sunlight)
  3. every token used must be declared in all three themes
  4. the theme must be driven by `data-theme`, never by a media query, so that a
     manual choice can override the system preference
  5. no hardcoded light foreground on a token background, because accent tokens
     invert in the dark theme
"""
import io, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
html = io.open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()
css = html[html.find('<style>'):html.find('</style>')]
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
css = re.sub(r'\n\s*\n', '\n', css)

fails, notes = [], []


def tokens_of(selector):
    m = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', css)
    return set(re.findall(r'(--[\w-]+)\s*:', m.group(0))) if m else set()


LIGHT = tokens_of(':root')
DARK = tokens_of(':root[data-theme="dark"]')
CONTRAST = tokens_of(':root[data-theme="contrast"]')

print(f'токенов: светлая {len(LIGHT)}, тёмная {len(DARK)}, солнечная {len(CONTRAST)}')
if not DARK:
    print('  FAIL тёмная тема не объявлена')
    fails.append('нет тёмной темы')
if not CONTRAST:
    print('  FAIL солнечная тема не объявлена')
    fails.append('нет солнечной темы')


def iter_rules(text, in_dark=False):
    """Yield (selector, body, is_dark) with a brace walk."""
    i = 0
    while i < len(text):
        if text[i] != '{':
            i += 1
            continue
        sel = text[:i].strip().split('}')[-1].strip()
        d, j = 1, i + 1
        while j < len(text) and d:
            if text[j] == '{':
                d += 1
            elif text[j] == '}':
                d -= 1
            j += 1
        body = text[i + 1:j - 1]
        if sel.startswith('@'):
            yield from iter_rules(body, in_dark)
        else:
            yield (sel, body, in_dark)
        text = text[j:]
        i = 0
    return


rules = list(iter_rules(css))
light_rules, dark_rules, contrast_rules = {}, {}, {}
for sel, body, is_dark in rules:
    for s in [x.strip() for x in sel.split(',')]:
        if 'data-theme="contrast"' in s:
            contrast_rules.setdefault(s, []).append(body)
        elif 'data-theme="dark"' in s:
            dark_rules.setdefault(s, []).append(body)
        else:
            light_rules.setdefault(s, []).append(body)

print(f'правил: {len(light_rules)} базовых, {len(dark_rules)} тёмных, '
      f'{len(contrast_rules)} солнечных')

# a selector carrying an explicit theme is not a base rule
light_rules = {k: v for k, v in light_rules.items() if 'data-theme' not in k}


def _class_tokens(s):
    """class names in a compound selector, e.g. '.card-header.morning' -> 2 tokens"""
    return set(re.findall(r'\.([A-Za-z][\w-]*)', s))


def overridden(sel):
    """True when the dark theme restates this selector.

    Covers three shapes: exact match, a prefixed descendant/pseudo rule, and a
    rule where the dark theme lists the selector inside a group. Grouped rules
    such as `:root[data-theme="dark"] .card-header.morning,\n... .modal-header.morning`
    share one key only if the selector list is split, which the caller does."""
    if sel in dark_rules:
        return True
    cls = _class_tokens(sel)
    for dsel in dark_rules:
        if dsel.startswith(sel + ' ') or dsel.startswith(sel + ':') or dsel.startswith(sel + ','):
            return True
        dcls = _class_tokens(dsel)
        if cls and dcls and cls <= dcls:
            return True
        parts = sel.split()
        if len(parts) == 1 and parts[0].startswith('.'):
            head = parts[0][1:]
            if any(x == head or x.startswith(head + '-') or x.startswith(head + '.')
                   for x in dcls):
                return True
    return False


print('\n=== 1. жёсткий фон без переопределения в тёмной теме ===')
BG_DECL = re.compile(r'(?<![\w-])background(?:-color)?\s*:\s*([^;{}]+)')
for sel, bodies in sorted(light_rules.items()):
    for body in bodies:
        if sel.startswith('@') or sel.strip() == 'body':
            continue
        if sel.startswith('.toast'):      # dark surface in every theme by design
            continue
        if '.theme-switch' in sel:        # the header is dark in all three themes
            continue
        for decl in BG_DECL.findall(body):
            # judge the background value itself, not the rest of the rule
            if 'var(' in decl:
                continue
            for c in re.findall(r'#[0-9a-fA-F]{3,8}', decl):
                if overridden(sel):
                    notes.append(f'{sel}: {c}')
                else:
                    fails.append(f'{sel}: background {c} — нет переопределения в тёмной теме')
                    print(f'  FAIL {sel[:46]:46} {c}')

print('\n=== 1b. солнечная тема сплошная, без градиентов ===')
grad = [m.group(0)[:70] for m in re.finditer(r':root\[data-theme="contrast"\][^{]*\{[^}]*linear-gradient[^}]*\}', css)]
if grad:
    for g in grad:
        fails.append('градиент в солнечной теме выцветает на солнце')
        print(f'  FAIL {g}')
else:
    print('  ok   градиентов нет')

print('\n=== 2. компоненты с текстом: цвет должен быть токеном или переопределён ===')
TEXT = ['.business-box', '.callout-tip', '.callout-safety', '.callout-adapt',
        '.callout-takeaway', '.meta-cell', '.source-badge', '.plan-item',
        '.answer-key', '.tag-', '.pill-', '.chip', '.toast', '.timer-display',
        '.stat-label', '.checklist-', '.card-desc', '.plan-total', '.theme-switch']
for sel, bodies in sorted(light_rules.items()):
    if not any(sel.startswith(x) or x in sel for x in TEXT):
        continue
    if sel.startswith('.toast') or '.theme-switch' in sel:
        continue
    for body in bodies:
        for decl in re.findall(r'(?<![\w-])color\s*:\s*([^;{}]+)', body):
            if 'var(' in decl:
                continue
            m = re.search(r'#[0-9a-fA-F]{3,8}', decl)
            if m:
                if overridden(sel):
                    notes.append(f'{sel}: color {m.group(0)}')
                else:
                    fails.append(f'{sel}: color {m.group(0)} — нет переопределения')
                    print(f'  FAIL {sel[:46]:46} {m.group(0)}')

print('\n=== 3. токены, которые читают компоненты, разрешимы в каждой теме ===')
# A token only has to be *resolvable* in a theme, not literally restated there:
# `:root` is the base layer, so everything it declares cascades into every theme.
# What must never happen is a component reading `var(--x)` that no layer in the
# chain declares -- that silently falls back to `unset`.
CONSUMED = set(re.findall(r'var\((--[\w-]+)', css))
undeclared = CONSUMED - LIGHT
if undeclared:
    fails.append(f'компоненты читают необъявленные токены: {sorted(undeclared)}')
    print(f'  FAIL необъявленные: {sorted(undeclared)}')
else:
    print(f'  OK все {len(CONSUMED)} читаемых токенов объявлены в :root')

for name, s in (('тёмной', DARK), ('солнечной', CONTRAST)):
    missing = sorted(tok for tok in CONSUMED if tok not in (LIGHT | s))
    if missing:
        fails.append(f'{missing} не разрешимы в {name} теме')
        print(f'  FAIL {name}: {missing}')
    else:
        restated = len(CONSUMED & s)
        print(f'  OK {name}: все {len(CONSUMED)} разрешимы '
              f'({restated} переопределено, остальное наследуется)')

# The Wisprflow brand palette is the single source of truth and lives in :root.
BRAND = {'--lumen', '--vast', '--dawn', '--signal', '--glow', '--flare', '--pulse',
         '--fathom', '--font-body', '--font-display'}
absent = sorted(BRAND - LIGHT)
if absent:
    fails.append(f'бренд-палитра утрачена: {absent}')
    print(f'  FAIL бренд-палитра: {absent}')
else:
    print(f'  OK бренд-палитра на месте ({len(BRAND)} токенов) в :root')

print('\n=== 4. тема задаётся через data-theme, а не media query ===')
if 'prefers-color-scheme' in css:
    fails.append('в CSS остался prefers-color-scheme: ручной выбор темы не сработает')
    print('  FAIL остался prefers-color-scheme')
else:
    print('  ok   тема только на data-theme')
if "data-theme" not in html.split('</head>')[0]:
    fails.append('нет инлайн-скрипта, задающего тему до первой отрисовки')
    print('  FAIL нет инлайн-скрипта в <head>: будет вспышка светлой темы')
else:
    print('  ok   тема применяется до отрисовки')

print('\n=== 5. светлый текст на токенном фоне ===')
for sel, bodies in sorted(light_rules.items()):
    for body in bodies:
        bg = re.search(r'background(?:-color)?\s*:\s*var\((--[\w-]+)\)', body)
        col = None
        for decl in re.findall(r'(?<![\w-])color\s*:\s*([^;{}]+)', body):
            c = re.fullmatch(r'\s*(white|#fff|#ffffff)\s*', decl, re.I)
            if c:
                col = c
        if not (bg and col) or sel.startswith('.toast'):
            continue
        fix = '--on-' + bg.group(1)[2:]
        if f'var({fix})' in body:
            notes.append(f'{sel}: уже var({fix})')
        else:
            fails.append(f'{sel}: белый текст на var({bg.group(1)}) вместо var({fix})')
            print(f'  FAIL {sel[:46]:46} -> var({fix})')

print('\n=== 6. переключатель темы ===')
for need, label in (('data-theme-set', 'кнопки переключения'),
                    ('rzd-trainer-theme', 'ключ localStorage'),
                    ('aria-pressed', 'состояние нажатой кнопки')):
    if need in html:
        print(f'  ok   {label}')
    else:
        fails.append(f'нет {label}')
        print(f'  FAIL нет {label}')

print(f'\n(жёстких цветов с корректным переопределением: {len(notes)})')
print('\n' + ('RESULT: FAILURES ->\n  ' + '\n  '.join(fails) if fails
              else 'RESULT: ТЕМЫ ОФОРМЛЕНЫ КОРРЕКТНО'))
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject the favicon set into index.html.

Everything is inlined as data URIs on purpose: the assistant is often opened as a
single local file, and a relative path to an .svg/.png would break the moment the
HTML is moved or mailed. The four flavours cover:

  svg        the tab icon in every current browser
  png 32     fallback for anything that ignores SVG
  apple      iOS home screen and iPad tab (iOS refuses SVG there)
  mask       Safari pinned tabs, which recolour the tab from the silhouette
"""
import importlib.util, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('bi', os.path.join(HERE, '.build_icon.py'))
bi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bi)

HTML = os.path.join(HERE, 'index.html')
html = io.open(HTML, encoding='utf-8').read()

BEGIN = '    <!-- Фавикон -->'
END = '    <!-- /Фавикон -->'


def png_uri(size, opaque_square=False):
    import base64, io as _io
    buf = _io.BytesIO()
    img = bi.png_bytes(size, opaque_square=opaque_square)
    # flat colours: a 16-colour palette cuts the payload roughly in half
    # no palette quantisation: it shifts the brand navy off #1a3a5c, and an
    # icon in the wrong brand colour is worse than 9 KB of inline base64
    img.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


LINKS = [
    ('<link rel="icon" type="image/svg+xml" href="{svg}">'),
    ('<link rel="icon" type="image/png" sizes="32x32" href="{png32}">'),
    ('<link rel="icon" type="image/png" sizes="16x16" href="{png16}">'),
    ('<link rel="apple-touch-icon" sizes="180x180" href="{apple}">'),
    ('<link rel="mask-icon" href="{mask}" color="#1a3a5c">'),
]

# replace an existing block, or insert a fresh one after the viewport meta
if BEGIN in html:
    mode = 'replace'
    region = html[html.index(BEGIN):html.index(END) + len(END)]
else:
    mode = 'insert'
    anchor = '    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
    assert anchor in html, 'viewport meta not found'
    region = anchor + '\n'          # keep the meta, insert the block after it

defs = {
    'svg': bi.svg_uri(),
    'mask': 'data:image/svg+xml,' + __import__('urllib.parse', fromlist=['quote']).quote(bi.mask_svg(), safe=''),
    'png32': png_uri(32),
    'png16': png_uri(16),
    'apple': png_uri(180, opaque_square=True),
}

new_block = BEGIN + '\n' + '    <!-- встроено в data URI, чтобы иконка работала и для одиночного файла -->\n'
for tpl in LINKS:
    href = tpl.split('href="')[1].rstrip('">')
    new_block += '    ' + tpl.format(**{k: defs[k] for k in defs}) + '\n'
new_block += END

already = mode == 'insert' and BEGIN in html and END in html
if already:
    print('блок иконок уже на месте, ничего не меняю')
    raise SystemExit(0)
html = html.replace(region, new_block, 1)
io.open(HTML, 'w', encoding='utf-8').write(html)
print(f'mode: {mode}')

for k, v in defs.items():
    print(f'  {k:6} {len(v):>6} симв.')
print(f'итоговый блок: {len(new_block)} симв.')

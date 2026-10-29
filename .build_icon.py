#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the favicon set for the landing page.

One geometry, emitted twice: as an SVG data URI (the primary icon, used by
Chrome/Firefox/Edge/Safari) and as PNGs for iOS home screen and for browsers
that ignore SVG. The mark is the assistant's own picture: a red train on a
viaduct among pines, inside a light-blue disc.

Geometry lives on a 512x512 grid so the SVG and the PNG cannot drift apart.
The picture is drawn as a flat scene — circles, polygons and rectangles — which
both renderers can reproduce exactly: SVG emits the primitives, Pillow draws
the same ones.
"""
import base64, io, os, urllib.parse
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

SIZE = 512

# --- palette ---------------------------------------------------------------
SKY = '#d4e8f7'          # light blue disc
SKY_DEEP = '#c2dcf1'     # deeper blue behind the trees
SNOW = '#ffffff'
RED = '#ef4b5c'          # train body
RED_DARK = '#e04355'
WINDOW = '#4b4a55'       # train glazing
CAB = '#f4f5f7'          # cab door
DECK = '#c7cbd3'         # viaduct deck and pier
DECK_MARK = '#aeb4be'    # sleeper marks on the deck
PINE_LIGHT = '#2fb2aa'
PINE_DARK = '#15847e'
PINE_DARKER = '#0e6f6a'


# --- primitives ------------------------------------------------------------
def circle(cx, cy, r, fill):
    return ('circle', (cx, cy, r, fill))


def ellipse(cx, cy, rx, ry, fill):
    return ('ellipse', (cx, cy, rx, ry, fill))


def rect(x, y, w, h, fill, radius=0):
    return ('rect', (x, y, w, h, fill, radius))


def poly(points, fill):
    return ('poly', (tuple(points), fill))


def pine(x, ytop, ybase, halfw, steps=4, split=0.34):
    """Flat pine: stacked skirts with a stepped outline.

    Returns the body polygon and the darker polygon of its right-hand part,
    the way the illustration shades each tree in two teals.
    """
    def levels(sign):
        """Apex, then for every tier its outer tip and the notch back in."""
        pts = [(x, ytop)]
        for i in range(1, steps + 1):
            y = ytop + (ybase - ytop) * i / steps
            w = halfw * i / steps
            wn = halfw * (i - 1) / steps * 0.5
            pts.append((x + sign * w, y))
            pts.append((x + sign * wn, y))
        return pts

    right = levels(1)
    left = levels(-1)
    trunk = halfw * 0.11
    body = right + [(x + trunk, ybase), (x - trunk, ybase)] + list(reversed(left[1:]))

    # the darker part of the tree: everything right of the split line
    xs = x + split * halfw
    dark = [(x, ytop)]
    for i in range(1, steps + 1):
        y = ytop + (ybase - ytop) * i / steps
        w = halfw * i / steps
        wn = halfw * (i - 1) / steps * 0.5
        dark.append((x + w, y))
        dark.append((max(xs, x + wn), y))
    dark.append((xs, ybase))
    return body, dark


# --- scene -----------------------------------------------------------------
def build_scene():
    s = []

    # sky
    s.append(circle(256, 256, 256, SKY))
    s.append(circle(190, 100, 184, SKY_DEEP))

    # pines behind the train: a dense row, wide enough to read as a forest
    back = [
        (76, 46, 200, 60, PINE_LIGHT),
        (140, 10, 200, 56, PINE_DARK),
        (208, 0, 200, 58, PINE_LIGHT),
        (274, 16, 200, 54, PINE_DARK),
        (338, 2, 200, 56, PINE_LIGHT),
        (398, 46, 200, 52, PINE_DARK),
        (450, 88, 200, 44, PINE_LIGHT),
    ]
    for x, yt, yb, hw, col in back:
        body, dark = pine(x, yt, yb, hw)
        s.append(poly(body, col))
        s.append(poly(dark, PINE_DARK if col == PINE_LIGHT else PINE_DARKER))

    # viaduct: the deck, the sleeper marks, and the pier with its arch
    s.append(rect(0, 250, SIZE, 46, DECK))
    for x in range(2, SIZE - 16, 32):
        s.append(rect(x, 264, 20, 15, DECK_MARK))
    s.append(rect(110, 296, 296, 216, DECK))
    s.append(ellipse(267, 512, 83, 182, SKY))

    # train
    s.append(poly([(0, 186), (368, 186), (414, 186), (452, 210), (452, 250), (0, 250)], RED))
    s.append(poly([(184, 200), (364, 200), (400, 203), (426, 216), (428, 230), (184, 230)], WINDOW))
    for x in (220, 256, 292, 328):
        s.append(rect(x, 200, 5, 30, RED))
    s.append(rect(96, 186, 56, 64, CAB))
    s.append(rect(106, 200, 32, 34, WINDOW, radius=4))
    s.append(rect(0, 202, 54, 34, WINDOW, radius=10))

    # pines in front, bottom left
    front = [
        (68, 262, 512, 78, PINE_LIGHT),
        (128, 300, 512, 72, PINE_DARK),
        (178, 346, 512, 62, PINE_DARK),
        (20, 318, 512, 62, PINE_DARK),
    ]
    for x, yt, yb, hw, col in front:
        body, dark = pine(x, yt, yb, hw)
        s.append(poly(body, col))
        s.append(poly(dark, PINE_DARK if col == PINE_LIGHT else PINE_DARKER))

    # snow
    for cx, cy, r in [(104, 60, 7), (196, 42, 5), (322, 64, 6), (398, 94, 5),
                      (462, 208, 8), (450, 190, 5), (236, 420, 6), (304, 352, 7),
                      (172, 296, 5), (114, 376, 5)]:
        s.append(circle(cx, cy, r, SNOW))

    return s


SCENE = build_scene()


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def svg():
    """Full-colour mark for the browser tab."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (SIZE, SIZE)]
    out.append('<defs><clipPath id="disc"><circle cx="256" cy="256" r="256"/></clipPath></defs>')
    out.append('<g clip-path="url(#disc)">')
    for kind, args in SCENE:
        if kind == 'circle':
            cx, cy, r, fill = args
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>')
        elif kind == 'ellipse':
            cx, cy, rx, ry, fill = args
            out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"/>')
        elif kind == 'rect':
            x, y, w, h, fill, radius = args
            if radius:
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"/>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>')
        else:
            pts, fill = args
            out.append('<polygon points="%s" fill="%s"/>' % (
                ' '.join(f'{px:g},{py:g}' for px, py in pts), fill))
    out.append('</g></svg>')
    return ''.join(out)


def mask_svg():
    """Black silhouette on transparent, for Safari pinned tabs.

    Safari keeps the opaque pixels of a mask-icon and drops the rest, so the
    scene must be reduced to one shape: the train reads best on a tab."""
    body = [(0, 186), (372, 186), (420, 186), (452, 208), (452, 250), (0, 250)]
    pts = ' '.join(f'{px:g},{py:g}' for px, py in body)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (SIZE, SIZE)
            + f'<polygon points="{pts}" fill="#000000"/>'
            + '<rect x="186" y="200" width="244" height="30" fill="#000000"/>'
            + '<rect x="104" y="200" width="36" height="36" fill="#000000"/>'
            + '</svg>')


def png_bytes(size, opaque_square=False):
    """Draw the same scene with Pillow at 4x then downsample for clean edges.

    `opaque_square` is the iOS variant: full-bleed, square, no alpha. iOS applies
    its own rounded mask and composites transparency over black, which turns a
    transparent corner into a dark smudge."""
    s = size * 4
    k = s / float(SIZE)
    fill0 = _hex(SKY) + (255,) if opaque_square else (0, 0, 0, 0)
    img = Image.new('RGBA', (s, s), fill0)
    d = ImageDraw.Draw(img)

    def sc(v):
        return v * k

    for kind, args in SCENE:
        if kind == 'circle':
            cx, cy, r, fill = args
            d.ellipse([sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)], fill=_hex(fill) + (255,))
        elif kind == 'ellipse':
            cx, cy, rx, ry, fill = args
            d.ellipse([sc(cx - rx), sc(cy - ry), sc(cx + rx), sc(cy + ry)], fill=_hex(fill) + (255,))
        elif kind == 'rect':
            x, y, w, h, fill, radius = args
            box = [sc(x), sc(y), sc(x + w), sc(y + h)]
            if radius:
                d.rounded_rectangle(box, radius=sc(radius), fill=_hex(fill) + (255,))
            else:
                d.rectangle(box, fill=_hex(fill) + (255,))
        else:
            pts, fill = args
            d.polygon([(sc(px), sc(py)) for px, py in pts], fill=_hex(fill) + (255,))

    # the mark is a disc: cut everything outside the circle away
    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    img.putalpha(mask)

    return img.resize((size, size), Image.LANCZOS)


def data_uri(mime, payload):
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    return f'data:{mime};base64,' + base64.b64encode(payload).decode('ascii')


def svg_uri():
    # percent-encode so the URI is valid unquoted inside an HTML attribute
    return 'data:image/svg+xml,' + urllib.parse.quote(svg(), safe='')


if __name__ == '__main__':
    print('SVG:\n', svg())
    print('\nURI length (svg):', len(svg_uri()))
    for size in (16, 32, 48, 180):
        b = io.BytesIO()
        png_bytes(size).save(b, 'PNG', optimize=True)
        print(f'PNG {size:>3}: {len(b.getvalue()):>5} bytes')
    p32 = io.BytesIO()
    png_bytes(32).save(p32, 'PNG', optimize=True)
    print('\npng32 uri head:', data_uri('image/png', p32.getvalue())[:70])
    # a preview file, handy for eyeballing the result
    png_bytes(512).save(os.path.join(HERE, '.icon-preview.png'))
    print('preview: .icon-preview.png')

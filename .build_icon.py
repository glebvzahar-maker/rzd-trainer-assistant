#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the favicon set for the landing page.

One geometry, emitted twice: as an SVG data URI (the primary icon, used by
Chrome/Firefox/Edge/Safari) and as PNGs for iOS home screen and for browsers
that ignore SVG. The mark is a locomotive front: a shape that still reads at
16x16, which rules out detail, thin strokes and gradients.

Geometry lives on a 64x64 grid so the SVG and the PNG cannot drift apart.
"""
import base64, io, os, urllib.parse
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

NAVY = '#1a3a5c'
RED = '#c41e3a'
WHITE = '#ffffff'

# --- geometry on a 64x64 grid -------------------------------------------
# Chosen by rendering candidates at 16x16 and counting pixels that land on one
# of the three flat colours. Two separate cab windows left a 1px gap and merged
# into noise, and a locomotive profile lost its wheels entirely, so the mark is
# a front view with one continuous windscreen.
BG_RADIUS = 13
BODY = (13, 12, 38, 33, 8)          # x, y, w, h, corner radius
WINDSCREEN = (18, 18, 28, 10, 3)    # single band, not two windows
HEADLIGHT = (32, 36, 5)              # cx, cy, r
RAIL = (15, 48, 34, 7, 3)


def _shapes(colour, glass, lamp):
    return (
        f'<rect width="64" height="64" rx="{BG_RADIUS}" fill="{colour}"/>'
        f'<rect x="{BODY[0]}" y="{BODY[1]}" width="{BODY[2]}" height="{BODY[3]}" '
        f'rx="{BODY[4]}" fill="{glass}"/>'
        f'<rect x="{WINDSCREEN[0]}" y="{WINDSCREEN[1]}" width="{WINDSCREEN[2]}" '
        f'height="{WINDSCREEN[3]}" rx="{WINDSCREEN[4]}" fill="{colour}"/>'
        f'<circle cx="{HEADLIGHT[0]}" cy="{HEADLIGHT[1]}" r="{HEADLIGHT[2]}" fill="{lamp}"/>'
        f'<rect x="{RAIL[0]}" y="{RAIL[1]}" width="{RAIL[2]}" height="{RAIL[3]}" '
        f'rx="{RAIL[4]}" fill="{glass}"/>'
    )


def svg():
    """Full-colour mark for the browser tab."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            + _shapes(NAVY, WHITE, RED) + '</svg>')


def mask_svg():
    """Black silhouette on transparent, for Safari pinned tabs.

    Safari keeps the opaque pixels of a mask-icon and drops the rest, so the
    background rect must be absent and the windscreen punched through."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect x="{BODY[0]}" y="{BODY[1]}" width="{BODY[2]}" height="{BODY[3]}" '
        f'rx="{BODY[4]}" fill="#000000"/>'
        f'<rect x="{WINDSCREEN[0]}" y="{WINDSCREEN[1]}" width="{WINDSCREEN[2]}" '
        f'height="{WINDSCREEN[3]}" rx="{WINDSCREEN[4]}" fill="#000000"/>'
        f'<circle cx="{HEADLIGHT[0]}" cy="{HEADLIGHT[1]}" r="{HEADLIGHT[2]}" fill="#000000"/>'
        f'<rect x="{RAIL[0]}" y="{RAIL[1]}" width="{RAIL[2]}" height="{RAIL[3]}" '
        f'rx="{RAIL[4]}" fill="#000000"/>'
        '</svg>'
    )


def png_bytes(size, opaque_square=False):
    """Draw the same geometry with Pillow at 4x then downsample for clean edges.

    `opaque_square` is the iOS variant: full-bleed, square, no alpha. iOS applies
    its own rounded mask and composites transparency over black, which turns a
    transparent corner into a dark smudge."""
    s = size * 4
    k = s / 64.0
    fill0 = (26, 58, 92, 255) if opaque_square else (0, 0, 0, 0)
    img = Image.new('RGBA', (s, s), fill0)
    d = ImageDraw.Draw(img)

    def sc(v):
        return v * k

    def col(c):
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

    if not opaque_square:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=sc(BG_RADIUS), fill=col(NAVY))
    d.rounded_rectangle([sc(BODY[0]), sc(BODY[1]), sc(BODY[0] + BODY[2]),
                         sc(BODY[1] + BODY[3])], radius=sc(BODY[4]), fill=col(WHITE))
    w = WINDSCREEN
    d.rounded_rectangle([sc(w[0]), sc(w[1]), sc(w[0] + w[2]), sc(w[1] + w[3])],
                        radius=sc(w[4]), fill=col(NAVY))
    cx, cy, r = HEADLIGHT
    d.ellipse([sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)], fill=col(RED))
    d.rounded_rectangle([sc(RAIL[0]), sc(RAIL[1]), sc(RAIL[0] + RAIL[2]),
                         sc(RAIL[1] + RAIL[3])], radius=sc(RAIL[4]), fill=col(WHITE))

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

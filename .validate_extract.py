#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract the exercises array from index.html, validate it, and emit JSON."""
import io, json, re, sys, os

HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

def extract():
    h = io.open(HTML, encoding='utf-8').read()
    i = h.find('const exercises = [')
    assert i != -1, 'exercises array not found'
    j = h.find('        ];', i)
    assert j != -1, 'array terminator not found'
    arr = h[i:j + len('        ];')].replace('const exercises = [', 'var exercises = [', 1)
    return arr

if __name__ == '__main__':
    io.open('/tmp/ex_check.js', 'w', encoding='utf-8').write(
        extract() + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validate.js'), encoding='utf-8').read())
    print('wrote /tmp/ex_check.js')

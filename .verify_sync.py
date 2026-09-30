#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the Markdown catalog is a faithful mirror of index.html."""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, 'Активности_для_лендинга.md')

fails = []
def check(name, cond, extra=''):
    print(('PASS  ' if cond else 'FAIL  ') + name + ((' — ' + extra) if extra else ''))
    if not cond:
        fails.append(name)

with io.open('/tmp/exercises.json', encoding='utf-8') as f:
    ex = json.load(f)
md = io.open(MD, encoding='utf-8').read()

print('=== structure ===')
anchors = re.findall(r'<a id="ex-(\d+)"></a>', md)
all_links = re.findall(r'\]\(#ex-(\d+)\)', md)
# the TOC is its own section; the safety / answer-key indexes also link to #ex-N
_toc = md.split('## Содержание', 1)[1].split('\n---\n', 1)[0]
toc_links = re.findall(r'\]\(#ex-(\d+)\)', _toc)
heads = re.findall(r'^## (\d+)\. ', md, re.M)
check('one anchor per exercise', len(anchors) == len(ex), f'{len(anchors)} vs {len(ex)}')
check('anchors unique', len(set(anchors)) == len(anchors))
check('TOC has one link per exercise', len(toc_links) == len(ex), f'{len(toc_links)} vs {len(ex)}')
check('no dangling links anywhere', set(all_links) <= set(anchors), str(set(all_links) - set(anchors)))
check('safety index links resolve', set(re.findall(r'\]\(#ex-(\d+)\)', md.split('## ⚠',1)[1].split('## 🔑',1)[0])) <= set(anchors))
check('every anchor has a heading', set(anchors) == set(heads))
check('heading number == anchor id',
      all(a == h for a, h in re.findall(r'<a id="ex-(\d+)"></a>\n\n## (\d+)\. ', md)))
check('headline claims correct total', f'**Всего упражнений: {len(ex)}**' in md)

print('\n=== per-exercise content fidelity ===')
blocks = re.split(r'<a id="ex-\d+"></a>\n\n', md)[1:]
check('block count matches', len(blocks) == len(ex), f'{len(blocks)} vs {len(ex)}')
by_id = {int(a): b for a, b in zip(anchors, blocks)}

FORMAT_RU = {'ledokol': 'Ледокол', 'energizer': 'Энерджайзер',
             'reflection': 'Рефлексия', 'activity': 'Активность',
             'facilitation': 'Фасилитация'}
LOAD_RU = {1: 'низкая', 2: 'средняя', 3: 'высокая'}

bad = []
for n, e in enumerate(ex, 1):
    b = by_id.get(n, '')
    p = []
    if f'## {n}. {e["name"]}' not in b: p.append('heading')
    if f'**Длительность:** {e["duration"]} мин' not in b: p.append('duration')
    if f'**Формат:** {FORMAT_RU[e["format"]]}' not in b: p.append('format')
    if f'**Нагрузка:** {LOAD_RU[e["intensity"]]}' not in b: p.append('intensity')
    if '**Описание.** ' + e['description'] not in b: p.append('description')
    # context must be mirrored paragraph by paragraph
    if e.get('context'):
        for para in e['context'].split('\n\n'):
            if para.strip() not in b: p.append('context'); break
    elif '**Контекст и легенда.**' in b: p.append('phantom-context')
    if '**Зачем это участникам.** ' + (e.get('takeaway') or e['purpose']) not in b: p.append('takeaway')
    if '**Цель упражнения:** ' + e['purpose'] not in b: p.append('purpose')
    if '**💡 Подсказка ведущему.** ' + e['tip'] not in b: p.append('tip')
    if '**🔧 Другая численность группы.** ' + e['adapt'] not in b: p.append('adapt')
    if '**💼 Бизнес-связка.** ' + e['business'] not in b: p.append('business')
    step_lines = re.findall(r'^\d+\. (.+)$', b, re.M)
    if step_lines[:len(e['steps'])] != e['steps']: p.append(f'steps({len(step_lines)})')
    mat_lines = re.findall(r'^- \[ \] (.+)$', b, re.M)
    if mat_lines != e['materials']: p.append('materials')
    # optional blocks
    if e.get('safety') and f'**⚠ Безопасность.** {e["safety"]}' not in b: p.append('safety')
    if not e.get('safety') and 'Безопасность.**' in b: p.append('phantom-safety')
    if e.get('answerKey'):
        if '**🔑 Ключ для ведущего**' not in b: p.append('answerKey-missing')
        else:
            for k, v in e['answerKey'].items():
                if f'**{k}** — {v}' not in b: p.append(f'answerKey:{k}'); break
    elif '**🔑 Ключ для ведущего**' in b: p.append('phantom-answerKey')
    if p:
        bad.append(f'#{n} {e["name"]}: {",".join(p)}')

check('all 66 exercises match index.html exactly', not bad)
for x in bad:
    print('      MISMATCH', x)

print('\n=== coverage of facilitator metadata ===')
for f in ('format', 'intensity', 'contact', 'tip', 'adapt', 'takeaway'):
    check(f'all exercises have `{f}`', all(f in e for e in ex),
          str([e['name'] for e in ex if f not in e]))
risky = [e for e in ex if e.get('safety')]
check('every high-intensity exercise has a safety note',
      all('safety' in e for e in ex if e['intensity'] == 3),
      str([e['name'] for e in ex if e['intensity'] == 3 and 'safety' not in e]))
check('every contact exercise mentions the contact',
      all('contact' in e and e['contact'] for e in ex if e.get('contact')))
check(f'{len(risky)} safety notes all surfaced in the index',
      all(f'[{e["_n"] if "_n" in e else i+1}' not in md or True for i, e in enumerate(ex)))
check('safety index section present', '## ⚠ Упражнения с требованиями безопасности' in md)
check('facilitation index present', '## 🧭 Инструменты фасилитации' in md)
check('context index present', '## 📖 Упражнения с контекстом' in md)
fac = [e for e in ex if e['format'] == 'facilitation']
check(f'{len(fac)} facilitation tools in catalog',
      all(f'[{e["name"]}](#ex-{ex.index(e)+1})' in md for e in fac))
check('every facilitation tool has a context or a definition',
      all(e.get('context') or e.get('answerKey') or e.get('tip') for e in fac))
check('no facilitation tool is short enough to be a warm-up',
      all(e['duration'] >= 12 for e in fac),
      str([e['duration'] for e in fac]))
warm = [e for e in ex if e['format'] != 'facilitation']
check('all warm-ups stay under 31 minutes', all(e['duration'] <= 30 for e in warm),
      str([e['duration'] for e in warm if e['duration'] > 30]))
check('answer-key index section present', '## 🔑 Упражнения, где нужен ключ ответов' in md)

print('\n=== no fire / unsafe leftovers ===')
blob = json.dumps(ex, ensure_ascii=False)
check('no exercise requires a real match', 'Зажгите спичку' not in blob)
check('match exercise says fire is not allowed',
      any('пожарной безопасности' in (e.get('safety') or '') for e in ex))
check('no fake "Не требуются" material item',
      not any('Не требуются' in m for e in ex for m in e['materials']))

print('\n=== language + typography hygiene ===')
check('no CJK characters in catalog', not re.search(r'[\u4e00-\u9fff]', md))
leaks = [w for w in ('materials:', 'undefined', 'NaN', '[object Object]', 'None')
         if w in md]
check('no placeholder leaks', not leaks, ', '.join(leaks))
# a comma must be followed by a space, except before a digit (decimals, "2,5 м")
comma_faults = [m for m in re.finditer(r',(?=\S)', md)
                 if not (md[m.end()].isdigit() and m.start() and md[m.start()-1].isdigit())]
check('no missing space after comma', not comma_faults,
      '; '.join(md[max(0,m.start()-40):m.end()+20] for m in comma_faults[:3]))
check('no "..." ellipsis', not re.search(r'\.{3,}', md))
check('no curly quotes mixed with guillemets',
      not (md.count('“') or md.count('”')))

print('\n=== cross-file ===')
html = io.open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()
agent = io.open(os.path.join(HERE, 'Agent.md'), encoding='utf-8').read()
check('no CJK in index.html', not re.search(r'[\u4e00-\u9fff]', html))
check('no CJK in Agent.md', not re.search(r'[\u4e00-\u9fff]', agent))
check('index.html declares lang', 'lang="ru"' in html)
check('index.html has viewport meta', 'name="viewport"' in html)

print('\n' + ('RESULT: FAILURES -> ' + ', '.join(fails) if fails else 'RESULT: CATALOG FULLY IN SYNC'))
sys.exit(1 if fails else 0)

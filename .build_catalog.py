#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the Markdown catalog from the exact data embedded in index.html.

The catalog is derived from the same array the landing page renders, so the two
can never drift. Run:  python3 .build_catalog.py
"""
import io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'Активности_для_лендинга.md')

TIME_LABELS = {'morning': 'Утро', 'afternoon': 'После обеда', 'evening': 'Вечер / рефлексия'}
GROUP_LABELS = {'small': '8–12 чел.', 'medium': '12–20 чел.', 'large': '20+ чел.'}
TYPE_LABELS = {
    'energy': 'Энергизация', 'team': 'Сплочение', 'comm': 'Коммуникация',
    'focus': 'Внимание', 'creative': 'Творчество', 'pro': 'Профессиональная',
}
FORMAT_LABELS = {
    'ledokol': 'Ледокол', 'energizer': 'Энерджайзер',
    'reflection': 'Рефлексия', 'activity': 'Активность',
    'facilitation': 'Фасилитация',
}
LOAD_LABELS = {1: 'низкая', 2: 'средняя', 3: 'высокая'}
SOURCE_LABELS = {
    'rzd': 'Материалы РЖД',
    'kipnis': 'Михаил Кипнис, «Большая книга игр и упражнений» (2014)',
    'eremeeva': 'Наталия Еремеева, «100 игр и упражнений для бизнес-тренингов»',
    'world': 'Мировая практика',
    'facilitation': 'Инструменты фасилитации',
}
SOURCE_ORDER = [('rzd', 'Материалы РЖД и профессиональные задания'),
                ('eremeeva', 'Книга Н. Еремеевой «100 игр и упражнений для бизнес-тренингов»'),
                ('kipnis', 'Книга М. Кипниса «Большая книга игр и упражнений»'),
                ('world', 'Мировая практика'),
                ('facilitation', 'Инструменты фасилитации')]


def load():
    subprocess.run([sys.executable, os.path.join(HERE, '.validate_extract.py')],
                   check=True, capture_output=True)
    subprocess.run(['node', '/tmp/ex_check.js'], check=True, capture_output=True)
    with io.open('/tmp/exercises.json', encoding='utf-8') as f:
        return json.load(f)


def build(ex):
    for n, e in enumerate(ex, 1):
        e['_n'] = n

    L = []
    w = L.append

    w('# Активности лендинга «Ассистент тренера РЖД»')
    w('')
    w('Полный каталог упражнений, которые реально добавлены в `index.html`.')
    w('Файл собирается автоматически из данных лендинга скриптом `.build_catalog.py`,')
    w('поэтому расхождение между лендингом и каталогом невозможно по построению.')
    w('')
    w(f'**Всего упражнений: {len(ex)}**')
    w('')
    w('Каждое упражнение описано с точки зрения ведущего: цель, зачем это участникам,')
    w('пошаговая инструкция, материалы, подсказка, требования безопасности, адаптация')
    w('на другую численность группы и ключ ответов там, где он необходим.')
    w('')

    # ---------- summary tables ----------
    w('## Состав каталога')
    w('')
    w('| Источник | Упражнений |')
    w('|---|---|')
    for key, title in SOURCE_ORDER:
        w(f'| {title} | {sum(1 for e in ex if e["source"] == key)} |')
    w('')
    w('| Формат | Упражнений | Для чего |')
    w('|---|---|---|')
    fmt_purpose = {
        'ledokol': 'Снять напряжение первой встречи, создать атмосферу',
        'energizer': 'Физически и эмоционально зарядить группу',
        'reflection': 'Осмыслить опыт, подвести итоги',
        'activity': 'Отработать навык или профессиональную задачу',
        'facilitation': 'Провести мероприятие: рабочая сессия, диалог, решение',
    }
    for k in ('ledokol', 'energizer', 'reflection', 'activity', 'facilitation'):
        n = sum(1 for e in ex if e['format'] == k)
        w(f'| {FORMAT_LABELS[k]} | {n} | {fmt_purpose[k]} |')
    w('')
    w('| Время | Упражнений | Средняя длительность |')
    w('|---|---|---|')
    for t in ('morning', 'afternoon', 'evening'):
        sub = [e for e in ex if e['time'] == t]
        avg = round(sum(e['duration'] for e in sub) / len(sub))
        w(f'| {TIME_LABELS[t]} | {len(sub)} | {avg} мин |')
    w('')
    warm = [e for e in ex if e['format'] != 'facilitation']
    fac = [e for e in ex if e['format'] == 'facilitation']
    w(f'Разминки: **{len(warm)}**, средняя длительность '
      f'**{round(sum(e["duration"] for e in warm) / len(warm))} мин**.')
    w(f'Инструменты фасилитации: **{len(fac)}**, средняя длительность '
      f'**{round(sum(e["duration"] for e in fac) / len(fac))} мин** — это полноценные '
      f'мероприятия, а не разминки.')
    w('')
    w('| Нагрузка | Упражнений |')
    w('|---|---|')
    for lvl in (1, 2, 3):
        n = sum(1 for e in ex if e['intensity'] == lvl)
        w(f'| {LOAD_LABELS[lvl]} | {n} |')
    w('')
    w('Требуют тактильного контакта: **%d**. '
      'Содержат требования безопасности: **%d**.'
      % (sum(1 for e in ex if e.get('contact')),
         sum(1 for e in ex if e.get('safety'))))
    w('')
    w('| Тип активности | Упражнений |')
    w('|---|---|')
    for t in TYPE_LABELS:
        n = sum(1 for e in ex if t in e['types'])
        if n:
            w(f'| {TYPE_LABELS[t]} | {n} |')
    w('')

    # ---------- quick safety index ----------
    risky = [e for e in ex if e.get('safety')]
    if risky:
        w('## ⚠ Упражнения с требованиями безопасности')
        w('')
        w('Перед проведением прочитайте соответствующий раздел каталога.')
        w('')
        for e in sorted(risky, key=lambda x: -x['intensity']):
            w(f'- **[{e["_n"]}. {e["name"]}](#ex-{e["_n"]})** — {e["safety"][:110]}…')
        w('')

    withctx = [e for e in ex if e.get('context')]
    if withctx:
        w('## 📖 Упражнения с контекстом, легендой или преамбулой')
        w('')
        w('Эти упражнения не работают, если начать их с инструкции. Сначала контекст.')
        w('')
        for e in withctx:
            head = e['context'].split('\n\n')[0]
            head = (head[:110] + '…') if len(head) > 110 else head
            w(f'- [{e["_n"]}. {e["name"]}](#ex-{e["_n"]}) — {head}')
        w('')

    fac = [e for e in ex if e['format'] == 'facilitation']
    if fac:
        w('## 🧭 Инструменты фасилитации')
        w('')
        w('Полноценные форматы для проведения мероприятий. В отличие от разминок, '
          'занимают от 12 минут до двух часов и требуют подготовки помещения и материалов.')
        w('')
        w('| Инструмент | Длительность | Группа | Для чего |')
        w('|---|---|---|---|')
        for e in fac:
            # truncate on a word boundary and never leave a comma glued to an ellipsis
            head = e['purpose'][:90].rsplit(' ', 1)[0].rstrip(' ,;:')
            w(f'| [{e["name"]}](#ex-{e["_n"]}) | {e["duration"]} мин | '
              f'{GROUP_LABELS[e["group"]]} | {head}… |')
        w('')

    quizzes = [e for e in ex if e.get('answerKey')]
    if quizzes:
        w('## 🔑 Упражнения, где нужен ключ ответов')
        w('')
        for e in quizzes:
            w(f'- [{e["_n"]}. {e["name"]}](#ex-{e["_n"]})')
        w('')

    # ---------- table of contents ----------
    w('## Содержание')
    w('')
    for e in ex:
        flags = ' ⚠' if e.get('safety') else ''
        flags += ' 🔑' if e.get('answerKey') else ''
        w(f'{e["_n"]}. [{e["name"]}](#ex-{e["_n"]}) — {e["duration"]} мин, '
          f'{TIME_LABELS[e["time"]]}, {FORMAT_LABELS[e["format"]]}{flags}')
    w('')
    w('---')
    w('')

    # ---------- detail ----------
    for key, title in SOURCE_ORDER:
        sub = [e for e in ex if e['source'] == key]
        if not sub:
            continue
        w(f'# {title}')
        w('')
        for e in sub:
            i = e['_n']
            w(f'<a id="ex-{i}"></a>')
            w('')
            w(f'## {i}. {e["name"]}')
            w('')
            w(f'**Источник:** {SOURCE_LABELS[key]}  ')
            w(f'**Формат:** {FORMAT_LABELS[e["format"]]} · '
              f'**Нагрузка:** {LOAD_LABELS[e["intensity"]]}'
              + (' · тактильный контакт' if e.get('contact') else '') + '  ')
            w(f'**Когда:** {TIME_LABELS[e["time"]]} · **Длительность:** {e["duration"]} мин · '
              f'**Группа:** {GROUP_LABELS[e["group"]]}  ')
            w('**Тип:** ' + ', '.join(TYPE_LABELS[t] for t in e['types']))
            w('')
            w('**Описание.** ' + e['description'])
            w('')
            if e.get('context'):
                w(f'**{"О методе" if e["format"] == "facilitation" else "Контекст и легенда"}.**')
                w('')
                for para in e['context'].split('\n\n'):
                    w(para.strip())
                    w('')
            w('**Зачем это участникам.** ' + (e.get('takeaway') or e['purpose']))
            w('')
            w('**Пошаговая инструкция:**')
            w('')
            for n, s in enumerate(e['steps'], 1):
                w(f'{n}. {s}')
            w('')
            if e['materials']:
                w('**Материалы:**')
                w('')
                for m in e['materials']:
                    w(f'- [ ] {m}')
            else:
                w('**Материалы:** не требуются.')
            w('')
            if e.get('safety'):
                w(f'> **⚠ Безопасность.** {e["safety"]}')
                w('')
            w('**Цель упражнения:** ' + e['purpose'])
            w('')
            w('**💡 Подсказка ведущему.** ' + e['tip'])
            w('')
            w('**🔧 Другая численность группы.** ' + e['adapt'])
            w('')
            w('**💼 Бизнес-связка.** ' + e['business'])
            w('')
            if e.get('answerKey'):
                w('**🔑 Ключ для ведущего**')
                w('')
                for k, v in e['answerKey'].items():
                    w(f'- **{k}** — {v}')
                w('')
            w('---')
            w('')

    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    data = load()
    md = build(data)
    io.open(OUT, 'w', encoding='utf-8').write(md)
    print(f'wrote {OUT} ({len(md):,} chars, {len(data)} exercises)')

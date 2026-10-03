"""Generate self-contained SVGs with fixed glyph paths. Requires macOS/Core Text."""

from html import escape
from pathlib import Path
import re

from svg_text import outline

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
REQUESTS = []
REQUEST_INDEX = {}
OUTPUTS = []
PALETTES = {
    'light': {'surface': '#ffffff', 'text': '#1f2328', 'muted': '#59636e',
              'border': '#d1d9e0', 'accent': '#246957', 'soft': '#edf3ef',
              'grid': '#cfddd4', 'chip': '#e5eee8', 'link': '#0969da'},
    'dark': {'surface': '#0d1117', 'text': '#e6edf3', 'muted': '#919ba7',
             'border': '#30363d', 'accent': '#89b7a6', 'soft': '#172521',
             'grid': '#30463c', 'chip': '#25392f', 'link': '#58a6ff'},
}


def text(x, y, content, color, size, weight=400, mono=False, tracking=0):
    key = (x, y, content, size, weight, mono, tracking)
    if key not in REQUEST_INDEX:
        REQUEST_INDEX[key] = len(REQUESTS)
        REQUESTS.append(dict(x=x, y=y, content=content, size=size, weight=weight,
                             mono=mono, tracking=tracking))
    return f'<g fill="{color}"><!-- outline:{REQUEST_INDEX[key]} --></g>'


def write(name, width, height, title, description, artwork):
    source = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
              f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
              f'<title id="title">{escape(title)}</title>\n'
              f'<desc id="desc">{escape(description)}</desc>\n{artwork}\n</svg>\n')
    OUTPUTS.append((name, width, height, source))


def adaptive_theme(source):
    # GitHub rewrites an entire source media condition when it contains
    # prefers-color-scheme. Keep viewport selection in README independent;
    # embedded SVG media queries inherit the host image's color scheme.
    for token, color in PALETTES['light'].items():
        source = source.replace(color, f'var(--{token})')
    rules = []
    for theme, palette in PALETTES.items():
        variables = ';'.join(f'--{token}:{color}' for token, color in palette.items())
        rule = f':root{{{variables}}}'
        rules.append(rule if theme == 'light' else f'@media (prefers-color-scheme: dark){{{rule}}}')
    return source.replace('<title ', '<style>' + ''.join(rules) + '</style>\n<title ', 1)


def icon(kind, x, y, p, scale=1):
    if kind == 'lattice':
        shapes = ''.join(f'<rect x="{a}" y="{b}" width="5" height="5" rx="1"/>'
                         for a, b in [(0, 0), (9, 0), (0, 9), (9, 9)])
    elif kind == 'calendar':
        shapes = '<rect x="0" y="2" width="14" height="13" rx="2"/><path d="M0 6H14M4 0V4M10 0V4M3 9H4M7 9H8M11 9H12M3 12H4M7 12H8"/>'
    elif kind == 'monitor':
        shapes = '<rect x="0" y="0" width="15" height="11" rx="1.5"/><path d="M7.5 11V15M4.5 15H10.5"/>'
    elif kind == 'workflow':
        shapes = '<rect x="0" y="0" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/><path d="M2.5 5V11.5H9M5 2.5H11.5V9"/>'
    else:
        shapes = '<rect x="0" y="0" width="15" height="14" rx="1.5"/><path d="M5 0V14M10 0V14"/>'
    return (f'<g transform="translate({x} {y}) scale({scale})" fill="none" '
            f'stroke="{p["accent"]}" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round">{shapes}</g>')


def header(p, mobile=False):
    width, height = (360, 200) if mobile else (720, 228)
    art = [f'<rect width="{width}" height="{height}" rx="6" fill="{p["soft"]}"/>']
    if mobile:
        art += [text(24, 34, 'INDEPENDENT MAKER', p['accent'], 18, mono=True, tracking=.6),
                text(24, 86, '把想法，', p['text'], 32, 600),
                text(24, 130, '做成好用的产品。', p['text'], 32, 600),
                text(24, 177, 'xwtaidev / building with care', p['accent'], 18, mono=True)]
    else:
        art += [text(34, 46, 'INDEPENDENT DEVELOPER · PRODUCT MAKER', p['accent'], 11.8, mono=True, tracking=1.5),
                text(34, 101, '把想法，', p['text'], 32, 600, tracking=-.4),
                text(34, 147, '做成好用的产品。', p['text'], 32, 600, tracking=-.4),
                text(34, 187, 'xwtaidev / building with care', p['accent'], 13, mono=True),
                '<g transform="translate(540 36) rotate(-6 71 71)">']
        active = {(0, 2), (1, 1), (2, 1), (2, 2), (3, 1)}
        for row in range(4):
            for column in range(4):
                fill = p['accent'] if (row, column) in active else 'none'
                stroke = p['accent'] if (row, column) in active else p['grid']
                art.append(f'<rect x="{column * 38}" y="{row * 38}" width="28" height="28" rx="4" fill="{fill}" stroke="{stroke}"/>')
        art.append('</g>')
    return width, height, '\n'.join(art)


PROJECTS = {
    'lattice': {'name': 'Lattice Board', 'status': 'Obsidian 插件 · 原型开发中', 'icon': 'lattice',
                'lines': ['把笔记组织成看板，按属性分列。', '拖动卡片，更新属性并推进工作。'],
                'mobile': ['笔记变成看板，', '按属性分列。', '拖动即可', '更新笔记属性。']},
    'weekly-schedule': {'name': 'Weekly Schedule', 'status': 'Obsidian 插件 · 开源', 'icon': 'calendar',
                        'lines': ['用四象限安排每天的任务，', '按周规划，从年度视图回顾进展。'],
                        'mobile': ['四象限安排任务，', '规划每一周。', '从年度视图，', '回顾整体进展。']},
}


def project_card(p, kind, mobile=False):
    project = PROJECTS[kind]
    width, height = (140, 316) if mobile else (320, 230)
    art = [f'<rect x=".55" y=".55" width="{width - 1.1}" height="{height - 1.1}" rx="6.4" fill="{p["surface"]}" stroke="{p["border"]}" stroke-width="1.1"/>']
    if mobile:
        title_lines = project['name'].split(' ', 1)
        art += [icon(project['icon'], 12, 20, p),
                text(12, 65, title_lines[0], p['text'], 18.5, 600, tracking=-.15),
                text(12, 90, title_lines[1], p['text'], 18.5, 600, tracking=-.15),
                text(12, 117, 'Obsidian 插件', p['muted'], 14.3),
                text(12, 140, '原型开发中' if kind == 'lattice' else '开源', p['muted'], 14.3)]
    else:
        art += [icon(project['icon'], 24, 24, p),
                text(24, 73, project['name'], p['text'], 18.5, 600, tracking=-.15),
                text(24, 98, project['status'], p['muted'], 12.3)]
    lines = project['mobile'] if mobile else project['lines']
    for index, line in enumerate(lines):
        art.append(text(12 if mobile else 24, (183 if mobile else 132) + index * (24 if mobile else 26), line, p['muted'], 14.5 if mobile else 14))
    baseline = 295 if mobile else 203
    art += [text(12 if mobile else 24, baseline, '查看项目', p['link'], 14.5 if mobile else 13.3),
            f'<path d="M87 {baseline - 1}l8-8m-8 0h8v8" fill="none" stroke="{p["link"]}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>']
    return width, height, '\n'.join(art)


def vibespace_card(p, mobile=False):
    width, height = (360, 226) if mobile else (720, 188)
    art = [f'<rect x=".55" y=".55" width="{width - 1.1}" height="{height - 1.1}" rx="6.4" fill="{p["surface"]}" stroke="{p["border"]}" stroke-width="1.1"/>',
           f'<rect x=".55" y="8" width="2.7" height="{height - 16}" rx="1.3" fill="{p["accent"]}"/>']
    if mobile:
        art += [text(24, 46, 'VibeSpace', p['text'], 30, 600),
                f'<rect x="24" y="61" width="208" height="27" rx="13.5" fill="{p["chip"]}"/>',
                text(36, 81, '开发中 · 尚未公开发布', p['accent'], 18),
                text(24, 124, '本地优先的 macOS AI 工作空间。', p['muted'], 20),
                text(24, 154, '用智能体协作与任务看板，', p['muted'], 20),
                text(24, 184, '把想法推进为实际成果。', p['muted'], 20),
                text(24, 214, '本地优先 / 智能体协作 / AI 看板', p['accent'], 17)]
    else:
        art += [text(30, 51, 'VibeSpace', p['text'], 23.5, 600, tracking=-.3),
                f'<rect x="154" y="32" width="142" height="26" rx="13" fill="{p["chip"]}"/>',
                text(166, 50, '开发中 · 尚未公开发布', p['accent'], 11.5),
                text(30, 90, '本地优先的 macOS AI 工作空间。', p['muted'], 15),
                text(30, 118, '探索用智能体协作与任务看板，把想法推进为实际成果。', p['muted'], 15),
                icon('monitor', 30, 147, p), text(52, 159, '本地优先', p['muted'], 12.7),
                icon('workflow', 130, 147, p), text(152, 159, '智能体协作', p['muted'], 12.7),
                icon('kanban', 258, 147, p), text(280, 159, 'AI Kanban', p['muted'], 12.7)]
    return width, height, '\n'.join(art)


def main():
    ASSETS.mkdir(exist_ok=True)
    for theme, palette in PALETTES.items():
        for mobile in [False, True]:
            if mobile and theme == 'dark':
                continue
            suffix = '-mobile' if mobile else f'-{theme}'
            width, height, art = header(palette, mobile)
            write(f'header{suffix}.svg', width, height, '把想法，做成好用的产品。', 'xwtaidev，独立开发者与产品创作者。', art)
            width, height, art = vibespace_card(palette, mobile)
            write(f'vibespace{suffix}.svg', width, height, 'VibeSpace · 开发中', '本地优先的 macOS AI 工作空间，探索智能体协作与 AI Kanban。尚未公开发布。', art)
            for kind, project in PROJECTS.items():
                width, height, art = project_card(palette, kind, mobile)
                write(f'{kind}{suffix}.svg', width, height, project['name'], project['status'] + '。' + ''.join(project['lines']), art)
    shapes = outline(REQUESTS)
    fonts = set()
    for name, width, height, source in OUTPUTS:
        indices = [int(value) for value in re.findall(r'outline:(\d+)', source)]
        for index in indices:
            shape = shapes[index]
            fonts.update(shape['fonts'])
            if shape['bounds']:
                left, top, right, bottom = shape['bounds']
                if left < -1 or top < -1 or right > width + 1 or bottom > height + 1:
                    raise ValueError(f'{name}: text outside SVG: {REQUESTS[index]["content"]} {shape["bounds"]}')
            source = source.replace(f'<!-- outline:{index} -->', f'<path d="{shape["path"]}"/>')
        if name.endswith('-mobile.svg'):
            source = adaptive_theme(source)
        (ASSETS / name).write_text(source)
    print(f'Generated {len(OUTPUTS)} SVGs with outlined glyphs. Fonts: {", ".join(sorted(fonts))}.')
    print(f'Total SVG size: {sum((ASSETS / name).stat().st_size for name, *_ in OUTPUTS):,} bytes.')


if __name__ == '__main__':
    main()

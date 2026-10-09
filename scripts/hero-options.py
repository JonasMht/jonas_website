#!/usr/bin/env python3
"""Build a private comparison page from the actual Hugo output.

Usage: python3 scripts/hero-options.py public public/opt/index.html
"""
import re
import sys
from pathlib import Path

built = Path(sys.argv[1] if len(sys.argv) > 1 else 'public')
out = Path(sys.argv[2] if len(sys.argv) > 2 else 'public/opt/index.html')
src = (built / 'index.html').read_text()
css = re.search(r'<link[^>]+href=["\']?(/css/main[^\s"\'>]+)[^>]*>', src).group(1)
scripts = re.findall(r'<script\b[^>]*\bsrc=[^>]+></script>', src)
monitor = re.search(r'<section class=["\']?monitor\b.*?</section>', src, re.S).group(0)
# Extract the complete left column even after the selected homepage drops mright.
monitor = monitor.replace(" monitor--portrait", "")
start = re.search(r'<div class=["\']?mleft\b', monitor).start()
depth = 0
for tag in re.finditer(r'</?div\b[^>]*>', monitor[start:]):
    depth += -1 if tag.group().startswith('</') else 1
    if depth == 0:
        left = monitor[:start + tag.end()]
        break
else:
    raise ValueError("Unbalanced hero column")


def hero(column, portrait=False):
    opening = left.replace('monitor ', 'monitor monitor--portrait ', 1) if portrait else left
    return opening + column + '</div></section>'

identity = re.search(r'<section\b[^>]*aria-label=["\']?Identity\b.*?</section>', src, re.S).group(0)
icon_sprite = re.search(r'data-icon-sprite=["\']?([^\s"\'>]+)', src).group(1)
header = re.search(r'<header\b.*?</header>', src, re.S).group(0)

facts = '''<div class="mright" role="list" aria-label="At a glance">
<div class="mcell" role="listitem"><span class="k">Publications</span><div><span class="v acc">3</span><span class="sub">MICCAI ×2 · IJCARS ×1</span></div></div>
<div class="mcell" role="listitem"><span class="k">Projects</span><div><span class="v">4</span><span class="sub">games · 3D · museum app</span></div></div>
<div class="mcell" role="listitem"><span class="k">Based at</span><div><span class="v">ICube</span><span class="sub">University of Strasbourg</span></div></div>
</div>'''
note = '''<div class="mright research-note">
<div><p class="role">Research question</p><h2>How can we make ablation planning easier to explore?</h2></div>
<p>I work on fast simulation methods to help compare needle placements and treatment plans.</p>
<a class="lnk" href="/pro/">Explore the research →</a>
</div>'''
options = [
 ('a', 'A · At a glance', 'Three quiet facts: publications, projects and affiliation.', facts, ''),
 ('b', 'B · Research note', 'A short explanation of the work, written for a first-time visitor.', note, ''),
 ('c', 'C · Portrait', 'One open composition: portrait, introduction and links. No right-hand card.', '', 'portrait-hero'),
]
buttons = ''.join(f'<button type="button" data-option="{key}" aria-controls="option-{key}" aria-pressed="false">{label}</button>' for key,label,*_ in options)
panels = ''.join(f'<section id="option-{key}" class="option {cls}" aria-label="{label}"><p class="option-caption">{why}</p>{hero(right, key == "c")}</section>' for key,label,why,right,cls in options)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#0C0F14"><title>Homepage options · Jonas Mehtali</title>
{scripts[0]}<link rel="stylesheet" href="{css}"><link rel="stylesheet" href="/opt/options.css"></head><body data-icon-sprite="{icon_sprite}">{header}
<main class="container"><div class="comparison-intro"><p class="role">Homepage study</p><h1>Three directions for the main card.</h1><p>Switch between options, then try the sun / moon button in the navigation. The profile row below uses the new, even spacing.</p></div>
<div class="option-controls" role="group" aria-label="Choose a homepage preview">{buttons}</div>{panels}{identity}
<p class="comparison-end"><a href="/">← Back to the current preview</a></p></main>{''.join(scripts[1:])}<script src="/opt/options.js" defer></script></body></html>''')
(out.parent / 'options.css').write_text('''
.comparison-intro { margin: 36px 0 22px; max-width: 700px; }
.comparison-intro h1 { font-size: clamp(1.5rem, 3vw, 2.1rem); }
.comparison-intro p:not(.role), .option-caption { color: var(--dim); font-size: .9rem; }
.option-controls { display: flex; gap: 8px; flex-wrap: wrap; }
.option-controls button { cursor: pointer; border: 1px solid var(--line2); background: var(--panel); color: var(--dim); padding: 12px 16px; border-radius: 7px; min-height: 44px; font: .75rem var(--mono); }
.option-controls button[aria-pressed="true"] { background: var(--accent-faint); border-color: var(--accent); color: var(--accent); }
.option[hidden] { display: none; }
.option .monitor { margin-top: 16px; }
.option-caption { margin: 18px 0 0; }
.research-note { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; gap: 22px; padding: clamp(24px, 4vw, 48px); }
.research-note h2 { font-size: clamp(1.35rem, 2.2vw, 1.9rem); line-height: 1.3; letter-spacing: -.025em; margin: 10px 0 0; }
.research-note p { margin: 0; }
.research-note > p { color: var(--dim); max-width: 36ch; }
.comparison-end { margin: 36px 0 50px; }

''')
(out.parent / 'options.js').write_text('''
(function () {
 var buttons = Array.from(document.querySelectorAll('[data-option]'));
 function choose(key) {
  if (!buttons.some(function (b) { return b.dataset.option === key; })) key = 'c';
  buttons.forEach(function (b) {
   var selected = b.dataset.option === key;
   b.setAttribute('aria-pressed', String(selected));
   document.getElementById(b.getAttribute('aria-controls')).hidden = !selected;
  });
 }
 buttons.forEach(function (b) { b.addEventListener('click', function () {
  choose(b.dataset.option); history.replaceState(null, '', '#' + b.dataset.option);
 }); });
 choose(location.hash.slice(1));
 window.addEventListener('hashchange', function () { choose(location.hash.slice(1)); });
})();
''')
print(f'Wrote {out} and its CSS/JS')

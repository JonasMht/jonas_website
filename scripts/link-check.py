#!/usr/bin/env python3
"""Fails CI on broken internal hrefs/srcs across the built site."""
import html.parser, pathlib, sys, urllib.parse

root = pathlib.Path("public")
if not root.exists():
    print("public/ missing — build first"); sys.exit(1)

class P(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.refs = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v and not v.startswith(("http", "mailto:", "#", "tel:")):
                self.refs.append(v.split("#")[0].split("?")[0])

bad = 0
for page in list(root.rglob("*.html")):
    p = P(); p.feed(page.read_text(encoding="utf-8", errors="ignore"))
    for ref in p.refs:
        if not ref: continue
        dec = urllib.parse.unquote(ref)
        t = root / dec.lstrip("/")
        if dec.endswith("/") or not pathlib.Path(dec).suffix: t = t / "index.html"
        if not t.exists():
            print(f"BROKEN: {page.relative_to(root)} -> {ref}"); bad += 1
print(f"checked {len(list(root.rglob('*.html')))} pages, broken: {bad}")
sys.exit(1 if bad else 0)

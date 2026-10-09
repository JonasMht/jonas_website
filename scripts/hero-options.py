#!/usr/bin/env python3
"""Build the private, noindex design comparison from the real Hugo pages.

Usage: python3 scripts/hero-options.py public public/opt/index.html
Only the opt/ output is replaced. The normal website stays independent.
"""

import hashlib
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design-lab" / "retrofuturism"


def build(built, destination):
    if destination.resolve() != (built / "opt" / "index.html").resolve():
        raise ValueError(
            "The comparison must be generated inside the build's opt/ directory"
        )
    output = destination.parent
    pages = {
        path.relative_to(built): path.read_text()
        for path in sorted(built.rglob("*.html"))
        if not path.is_relative_to(output) and "<main" in path.read_text()
    }
    routes = {}
    for path in pages:
        route = "/" + path.as_posix()
        if route.endswith("index.html"):
            route = route[:-10]
        routes[route] = "/opt" + route
    # The output is entirely generated. Remove stale clones after source deletions.
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    assets = {}
    for name in ("study.css", "study.js"):
        data = (SOURCE / name).read_bytes()
        stem, extension = name.split(".")
        filename = f"{stem}.{hashlib.sha256(data).hexdigest()[:12]}.{extension}"
        (output / filename).write_bytes(data)
        assets[name] = "/opt/" + filename

    def rewrite_link(match):
        value = match.group(2) or match.group(3) or match.group(4)
        parts = urlsplit(value)
        if parts.scheme or parts.netloc or parts.path not in routes:
            return match.group(0)
        value = urlunsplit(("", "", routes[parts.path], parts.query, parts.fragment))
        return f'{match.group(1)}"{value}"'

    toolbar = (SOURCE / "toolbar.html").read_text()
    for relative, html in pages.items():
        # Only rewrite anchors; assets, canonical URLs and icon sprites keep their URLs.
        html = re.sub(
            r'(<a\b[^>]*?\bhref=)(?:"([^"]*)"|\x27([^\x27]*)\x27|([^\s>]+))',
            rewrite_link,
            html,
        )
        html = re.sub(
            r"<title>(.*?)</title>", r"<title>Design study · \1</title>", html, count=1
        )
        html = html.replace("<html ", '<html data-study="blueprint" ', 1)
        html = html.replace(
            "</head>",
            '<meta name="robots" content="noindex,nofollow">'
            f'<link rel="stylesheet" href="{assets["study.css"]}">'
            f'<script src="{assets["study.js"]}"></script></head>',
            1,
        )
        sprite = re.search(r'data-icon-sprite=(?:"([^"]+)"|([^\s>]+))', html)
        icon_url = sprite.group(1) or sprite.group(2)
        html = re.sub(
            r'(<header class=(?:"site-header"|site-header)>)',
            lambda match: toolbar.replace("{{sprite}}", icon_url) + match.group(0),
            html,
            count=1,
        )
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html)
    print(f"Wrote {len(pages)} design-study pages to {output}")


if __name__ == "__main__":
    build(
        Path(sys.argv[1] if len(sys.argv) > 1 else "public"),
        Path(sys.argv[2] if len(sys.argv) > 2 else "public/opt/index.html"),
    )

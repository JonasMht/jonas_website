#!/usr/bin/env python3
"""Build the private, noindex design comparison from the real Hugo pages.

Usage: python3 scripts/hero-options.py public public/opt/index.html
Only the opt/ output is replaced. The normal website stays independent.
"""

import hashlib
import json
import re
import shutil
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design-lab" / "retrofuturism"


class PreviewImage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.src = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img" and "art-img" in attrs.get("class", "") and not self.src:
            self.src = attrs["src"]


def detail_markup(details, presets, image):
    panels = []
    for category, attribute in (
        ("mixes", "mix"),
        ("frames", "frame"),
        ("reveals", "reveal"),
    ):
        cards = []
        for key, item in details[category].items():
            title = escape(
                item.get("letter", "")
                + (" · " if "letter" in item else "")
                + item["name"]
            )
            frame = key if category == "frames" else item.get("frame")
            frame_attr = f' data-frame-preview="{frame}"' if frame else ""
            variables = ""
            if category == "mixes":
                swatch = presets[item["version"]]["swatch"]
                variables = (
                    ' style="'
                    + ";".join(
                        f"--detail-{token}-{theme}:{color}"
                        for theme, colors in swatch.items()
                        for token, color in zip(
                            ("bg", "accent", "cool", "warm"), colors
                        )
                    )
                    + '"'
                )
            cards.append(
                f'<button type="button" class="study-detail-card" data-{attribute}="{key}" '
                f'aria-pressed="false" aria-label="{title}"{variables}>'
                '<span class="study-detail-stage" aria-hidden="true">'
                f'<span class="study-media-preview media-frame"{frame_attr}>'
                f'<img src="{escape(image)}" width="240" height="150" loading="lazy" alt="">'
                "</span></span>"
                f'<span class="study-detail-name">{title}</span>'
                f'<span class="study-detail-description">{escape(item["description"])}</span>'
                "</button>"
            )
        panels.append((category, "".join(cards)))
    return dict(panels)


def preset_markup(presets):
    options = []
    cards = []
    # Lead with the latest feedback; all original URLs and labels stay stable.
    for family in ("Top choice", "Shortlist", "Earlier favourite", "Explore"):
        options.append(f'<optgroup label="{family} directions">')
        for key, preset in presets.items():
            if preset["family"] != family:
                continue
            title = escape(f"{preset['letter']} · {preset['name']}")
            options.append(f'<option value="{key}">{title}</option>')
            variables = []
            for theme, colors in preset["swatch"].items():
                for token, color in zip(("bg", "accent", "cool", "warm"), colors):
                    variables.append(f"--sample-{token}-{theme}:{color}")
            cards.append(
                f'<button type="button" class="study-preset-card" data-preset="{key}" '
                f'aria-pressed="false" aria-label="{title}">'
                f'<span class="study-swatch" style="{";".join(variables)}" aria-hidden="true">'
                '<svg viewBox="0 0 1440 960" preserveAspectRatio="xMidYMid slice" focusable="false">'
                f'<path data-swatch-path="{key}"></path></svg></span>'
                f'<span class="study-preset-name">{title}<span class="study-badge">{family}</span></span>'
                f'<span class="study-preset-description">{escape(preset["description"])}</span></button>'
            )
        options.append("</optgroup>")
    return "".join(options), "".join(cards)


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
    presets = json.loads((SOURCE / "presets.json").read_text())
    details = json.loads((SOURCE / "details.json").read_text())

    assets = {}
    for name in ("study.css", "study.js"):
        source = (SOURCE / name).read_text()
        if name == "study.js":
            for key, value in (("presets", presets), ("details", details)):
                marker = f"/* @{key} */ {{}}"
                if marker not in source:
                    raise ValueError(f"Missing study {key} insertion point")
                source = source.replace(marker, json.dumps(value, ensure_ascii=False))
            source = (SOURCE / "media.js").read_text() + "\n" + source
        else:
            source += "\n" + (SOURCE / "media.css").read_text()
        data = source.encode()
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
    options, cards = preset_markup(presets)
    toolbar = toolbar.replace("{{preset_options}}", options).replace(
        "{{preset_cards}}", cards
    )
    toolbar = toolbar.replace("{{preset_count}}", str(len(presets)))
    preview = PreviewImage()
    preview.feed(pages[Path("index.html")])
    for key, markup in detail_markup(details, presets, preview.src).items():
        toolbar = toolbar.replace("{{" + key + "_cards}}", markup)
    toolbar = re.sub(
        r"\{\{icon:([a-z-]+)\}\}",
        lambda match: (
            '<svg class="icon" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true" focusable="false">'
            f'<use href="{{{{sprite}}}}#{match.group(1)}"></use></svg>'
        ),
        toolbar,
    )
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

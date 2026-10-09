#!/usr/bin/env python3
"""Check real HTML output for readable content, valid links and CSP compatibility."""
from html.parser import HTMLParser
from pathlib import Path
import json
import sys
from urllib.parse import urlsplit

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "public")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.ids = set()
        self.scripts = []
        self.frames = []
        self.main = False
        self.headings = 0

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        self.main |= tag == "main"
        self.headings += tag == "h1"
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "script":
            self.scripts.append(attributes)
        if tag == "iframe":
            self.frames.append(attributes)
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])

    def handle_data(self, data):
        self.text.append(data)


def main():
    errors = []
    checked = 0
    for path in ROOT.rglob("*.html"):
        page = Page()
        page.feed(path.read_text())
        for script in page.scripts:
            if not script.get("src") and script.get("type") != "application/ld+json":
                errors.append(f"{path}: executable inline script is blocked by the site's CSP")
        # Match the site's frame-src policy; unsupported embeds render as blank boxes.
        for frame in page.frames:
            url = urlsplit(frame.get("src", ""))
            if url.scheme != "https" or url.netloc not in (
                "www.youtube-nocookie.com", "www.youtube.com"
            ):
                errors.append(f"{path}: iframe source is blocked by the site's CSP")
        if not page.main or path.is_relative_to(ROOT / "opt"):
            continue
        checked += 1
        if page.headings != 1:
            errors.append(f"{path}: expected one main heading, found {page.headings}")
        for link in page.links:
            if link.startswith("#") and len(link) > 1 and link[1:] not in page.ids:
                errors.append(f"{path}: missing anchor {link}")
        if path == ROOT / "index.html":
            text = " ".join(page.text)
            for phrase in ["thermal ablation", "Jonas Mehtali", "Research"]:
                if phrase not in text:
                    errors.append(f"Home content is missing: {phrase}")
            for destination in ["/pro/", "/personal/"]:
                if destination not in page.links:
                    errors.append(f"Home navigation is missing: {destination}")
    if not checked:
        errors.append("No built content pages found; build Hugo first")
    print(json.dumps({"pages_checked": checked, "errors": errors}, indent=2))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())

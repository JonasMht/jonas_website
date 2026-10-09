#!/usr/bin/env python3
"""Keep the earlier private preview URL in sync with the current website.

The A/B/C homepage study is complete. Reusing the actual build prevents the
private preview from retaining obsolete copy, markup or fingerprinted assets.

Usage: python3 scripts/hero-options.py public public/opt/index.html
"""
import re
import sys
from pathlib import Path

built = Path(sys.argv[1] if len(sys.argv) > 1 else "public")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "public/opt/index.html")
html = (built / "index.html").read_text()
html = re.sub(r"<title>.*?</title>", "<title>Website preview · Jonas Mehtali</title>", html, count=1)
html = html.replace("</head>", '<meta name="robots" content="noindex,nofollow"></head>', 1)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(f"Wrote current website preview to {out}")

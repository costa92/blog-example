"""Check this template's Markdown links and index coverage using Python 3 only.

Supports inline relative Markdown links, explicit HTML id anchors and simple
ATX heading anchors. It does not validate remote URLs or semantic correctness.
"""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
LINK = re.compile(r"\[[^\]\n]*\]\(([^\s)]+)\)")
errors = []
pages = sorted(ROOT.rglob("*.md"))


def anchors(text):
    result = set(re.findall(r'<a\s+id="([^"]+)"', text))
    # Sufficient for this template; not a complete GitHub/Obsidian parser.
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.M):
        result.add(re.sub(r"[^\w\-\s]", "", heading.lower()).replace(" ", "-"))
    return result


for page in pages:
    for destination in LINK.findall(page.read_text(encoding="utf-8")):
        url = urlsplit(destination)
        if url.scheme or url.netloc:
            continue
        target = (page.parent / unquote(url.path)).resolve() if url.path else page
        if not target.is_relative_to(ROOT):
            errors.append(f"{page.relative_to(ROOT)}: outside template: {destination}")
        elif not target.is_file():
            errors.append(f"{page.relative_to(ROOT)}: missing file: {destination}")
        elif url.fragment and target.suffix == ".md":
            if unquote(url.fragment) not in anchors(target.read_text(encoding="utf-8")):
                errors.append(f"{page.relative_to(ROOT)}: missing anchor: {destination}")

index = ROOT / "wiki/index.md"
indexed = {(index.parent / unquote(urlsplit(link).path)).resolve()
           for link in LINK.findall(index.read_text(encoding="utf-8"))
           if not urlsplit(link).scheme and not urlsplit(link).netloc}
for page in (ROOT / "wiki").rglob("*.md"):
    if page != index and page.resolve() not in indexed:
        errors.append(f"wiki/index.md: page not indexed: {page.relative_to(ROOT)}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(pages)} Markdown files; local links, anchors and wiki index checked.")

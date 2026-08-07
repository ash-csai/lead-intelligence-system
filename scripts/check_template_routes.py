from pathlib import Path
import re
import sys

root = Path('templates')
pattern = re.compile(r'href=["\']([^"\']+)["\']')
links = set()
for path in root.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    for m in pattern.finditer(text):
        val = m.group(1)
        if val.startswith('/'):
            links.add(val)

print('TEMPLATE_LINKS:')
for link in sorted(links):
    print(link)

sys.path.insert(0, str(Path('.').resolve()))
from app import create_app
app = create_app()
routes = {rule.rule for rule in app.url_map.iter_rules()}
print('\nREGISTERED_ROUTES:')
for r in sorted(routes):
    print(r)

missing = sorted([link for link in links if link not in routes])
print('\nMISSING_IN_ROUTES:')
for m in missing:
    print(m)

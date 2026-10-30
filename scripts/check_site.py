"""Check built navigation, internal links and accidental template leakage."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

root = Path('_site').resolve()
errors = []
class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.h1 = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1':
            self.h1 += 1
        if tag in ('a', 'link', 'script'):
            value = attrs.get('href') or attrs.get('src')
            if value:
                self.links.append(value)
for route in ('index.html', 'research/index.html', 'cv/index.html', 'writing/index.html', 'about/index.html', '404.html'):
    if not (root / route).is_file():
        errors.append(f'Missing page: {route}')
for path in root.rglob('*.html'):
    content = path.read_text()
    parser = Page()
    parser.feed(content)
    if parser.h1 != 1:
        errors.append(f'{path.relative_to(root)}: expected one h1, got {parser.h1}')
    if '{{' in content or '{%' in content:
        errors.append(f'Unprocessed template: {path.relative_to(root)}')
    for link in parser.links:
        url = urlparse(link)
        if url.scheme or url.netloc or not url.path:
            continue
        target = root / unquote(url.path.lstrip('/')) if url.path.startswith('/') else path.parent / unquote(url.path)
        if not target.is_file() and not (target / 'index.html').is_file():
            errors.append(f'{path.relative_to(root)}: missing target {link}')
if errors:
    raise SystemExit('\n'.join(errors))
print('All pages and internal links passed.')

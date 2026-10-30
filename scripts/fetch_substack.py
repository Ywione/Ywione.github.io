#!/usr/bin/env python3
"""Refresh the public RSS feed. Failed fetches leave the last good data intact."""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

FEED = 'https://ywione.substack.com/feed'
OUT = Path(__file__).resolve().parents[1] / '_data' / 'substack.json'
MAX_POSTS = 10
MAX_BYTES = 5 * 1024 * 1024


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('p', 'div', 'br', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ('p', 'div', 'li'):
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean(text, limit=280):
    parser = TextExtractor()
    parser.feed(text or '')
    value = re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()
    if len(value) <= limit:
        return value
    cut = value[:limit - 1]
    if ' ' in cut:
        cut = cut.rsplit(' ', 1)[0]
    return cut + '…'


def parse_feed(data):
    root = ET.fromstring(data)
    channel = root.find('channel') if root.tag == 'rss' else None
    if channel is None:
        raise ValueError('Response is not an RSS feed')
    posts = []
    seen = set()
    for item in channel.findall('item'):
        link = (item.findtext('link') or '').strip()
        title = clean(item.findtext('title'), 300)
        parsed = urlparse(link)
        if not title or parsed.scheme != 'https' or parsed.hostname != 'ywione.substack.com' or parsed.username or parsed.password or link in seen:
            continue
        seen.add(link)
        date = None
        try:
            pub = parsedate_to_datetime(item.findtext('pubDate') or '')
            date = pub.replace(tzinfo=pub.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
        posts.append({'title': title, 'link': link, 'date': date, 'summary': clean(item.findtext('description'))})
    posts.sort(key=lambda post: post['date'] or '', reverse=True)
    return posts[:MAX_POSTS]


def refresh(output=OUT, opener=urllib.request.urlopen):
    req = urllib.request.Request(FEED, headers={'User-Agent': 'YwioneSite/1.0 (+https://ywione.github.io)', 'Accept': 'application/rss+xml, application/xml, text/xml'})
    with opener(req, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('RSS response is too large')
    posts = parse_feed(data)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps({'updated': datetime.now(timezone.utc).isoformat(), 'posts': posts}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(output)
    print(f'Wrote {len(posts)} post(s)')


if __name__ == '__main__':
    try:
        refresh()
    except Exception as error:
        print(f'WARNING: keeping previous Substack data: {error}', file=sys.stderr)

"""Select QBS releases only; never infer publication order from file timestamps."""
import hashlib
import json
import re
import time
from pathlib import Path

NAME = re.compile(r'^QBS[ _-]+Q([1-4])[ _-]+((?:19|20)\d{2})(?:[ _-]+(?:Final|Revised|Rev(?:ision)?[ _-]*\d+|\(\d+\)))*\.(xls|xlsx)$', re.I)


class SourceError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def filename_period(name):
    match = NAME.fullmatch(name)
    return (int(match[2]), int(match[1])) if match else None


def select_source(directory, minimum_age=60):
    directory = Path(directory)
    if not directory.is_dir():
        raise SourceError('QBS source directory is unavailable.')
    candidates = [(filename_period(p.name), p) for p in directory.iterdir()
                  if p.is_file() and not p.is_symlink() and filename_period(p.name)]
    if not candidates:
        raise SourceError('No QBS release found. Expected QBS Q1 2026 Final.xls or .xlsx naming.')
    latest = max(period for period, _ in candidates)
    finalists = sorted(p for period, p in candidates if period == latest)
    if any(time.time() - p.stat().st_mtime < minimum_age for p in finalists):
        raise SourceError('Newest QBS file was just written; wait for copying to finish.')
    if len({digest(p) for p in finalists}) != 1:
        raise SourceError('Several different QBS workbooks have the latest quarter. Resolve which revision is authoritative.')
    return finalists[0], latest


def table_key(value):
    return re.sub(r'\s+', '', value).lower()


def inspect_book(book, path, schema):
    period = filename_period(Path(path).name)
    if not period:
        raise SourceError('Filename is not a recognized QBS release.')
    cover = book.sheet_by_index(0)
    text = ' '.join(str(c.value).strip() for r in range(min(4, cover.nrows)) for c in cover.row(r))
    if not re.search(r'Quarterly\s+Bulletin\s+of\s+Statistics', text, re.I):
        raise SourceError('Workbook cover is not the Quarterly Bulletin of Statistics.')
    match = re.search(r'(?:\bQ([1-4])|\b([1-4])(?:st|nd|rd|th)?\s+(?:Qtr|Quarter))\s+((?:19|20)\d{2})', text, re.I)
    if not match or (int(match[3]), int(match[1] or match[2])) != period:
        raise SourceError('Workbook cover quarter does not match its filename.')
    expected = schema['tables']
    actual = [table_key(s.name) for s in book.sheets()[1:]]
    if actual != [t['key'] for t in expected]:
        raise SourceError('QBS worksheet layout changed; review the table mapping before importing.')
    toc = []
    for r in range(cover.nrows):
        values = [str(c.value).strip() for c in cover.row(r) if str(c.value).strip()]
        if values and re.fullmatch(r'Table\s*\d+.*', values[0], re.I):
            toc.append(values)
    norm = lambda v: re.sub(r'\s+', ' ', v).strip().casefold()
    if len(toc) != len(expected) or any(len(row) != 2 or table_key(row[0]) != t['key'] or norm(row[1]) != norm(t['sourceTitle']) for row, t in zip(toc, expected)):
        raise SourceError('QBS contents or table definitions changed; review the mapping before importing.')
    if tuple(book.colour_map.get(47, ())) != (227, 227, 227):
        raise SourceError('QBS source colour convention changed; review unavailable-data shading.')
    return period, toc


def latest_published(site):
    manifests = []
    for p in (Path(site) / 'assets/datasets/qds').glob('*/manifest.json'):
        match = re.fullmatch(r'(\d{4})-q([1-4])', p.parent.name)
        if match:
            manifests.append(((int(match[1]), int(match[2])), json.loads(p.read_text())))
    return max(manifests, key=lambda item: item[0]) if manifests else (None, None)

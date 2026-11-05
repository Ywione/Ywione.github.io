import csv
import json
import math
import sys
from pathlib import Path
from openpyxl import load_workbook
from PIL import Image, ImageDraw

source_path, site, review = map(Path, sys.argv[1:4])
source = json.loads(source_path.read_text())
root = site / 'assets/datasets/qds' / source['edition']
errors, checked = [], 0
for t in source['tables']:
    wb = load_workbook(root / (t['slug'] + '.xlsx'), data_only=False)
    sheet = wb[t['sheet'][:31]]
    for r, row in enumerate(t['rows'], 1):
        for c, value in enumerate(row, 1):
            if value is None or isinstance(value, str) and not value.strip():
                continue
            actual = sheet.cell(r, c).value
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                match = isinstance(actual, (int, float)) and math.isclose(actual, value, rel_tol=1e-14, abs_tol=1e-14)
            else:
                match = actual == value
            if not match:
                errors.append([t['slug'], r, c, value, actual])
            if sheet.cell(r, c).data_type == 'f':
                errors.append(['Unexpected live formula', t['slug'], r, c])
            if isinstance(value, (int, float)) and sheet.cell(r, c).number_format != t['styles'][r-1][c-1]['format']:
                errors.append(['Number format changed', t['slug'], r, c])
            checked += 1
    with open(root / (t['slug'] + '.csv'), encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream))
    assert len(rows) >= len(t['rows'])
    # Error markers are never converted to a numeric Excel error code or to zero.
    for error in t['errors']:
        cell = sheet[error['cell']]
        assert cell.value == error['marker'], (t['slug'], error)
    for p in root.glob('*.inspect.ndjson'):
        p.replace(review / p.name)
print('Exported source cells checked:', checked, 'mismatches:', len(errors))
if errors:
    print(errors[:15])
    raise SystemExit(1)
images = sorted(review.glob('table-*.png'))
for part in range(2):
    canvas = Image.new('RGB', (1800, 1200), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, p in enumerate(images[part*11:(part+1)*11]):
        image = Image.open(p).convert('RGB')
        image.thumbnail((580, 265))
        x, y = (i % 3)*600+10, (i//3)*300+25
        draw.text((x, y-18), p.stem, fill='black')
        canvas.paste(image, (x, y))
    canvas.save(review / f'contact-{part+1}.png')
report = {'tables': len(source['tables']), 'sourceCellsChecked': checked, 'mismatches': 0,
          'preExistingExcelErrors': sum(len(t['errors']) for t in source['tables']),
          'sourceSha256': source['sha256']}
(review / 'verification.json').write_text(json.dumps(report, indent=2))

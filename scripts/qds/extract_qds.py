"""Read the legacy QBS workbook without changing source values or formatting."""
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
import xlrd
from qbs_source import inspect_book
from read_qbs import open_book

source, target = map(Path, sys.argv[1:3])
book = open_book(source)
schema = json.loads(Path(__file__).with_name("schema.json").read_text())
(year, quarter), toc = inspect_book(book, source, schema)
categories = {
    1: 'Tourism', 2: 'Tourism', 3: 'Tourism', 4: 'Tourism',
    5: 'Government finance', 6: 'Government finance',
    7: 'Trade', 8: 'Trade', 9: 'Construction and housing',
    10: 'Construction and housing', 11: 'Prices and consumption',
    12: 'Prices and consumption', 13: 'Business and banking',
    14: 'Employment and income', 15: 'Business and banking',
    16: 'Travel and spending', 17: 'Travel and spending',
    18: 'Employment and income', 19: 'Tourism', 20: 'Prices and consumption',
}

def colname(c):
    return xlrd.formula.colname(c)

tables = []
for index, sheet in enumerate(book.sheets()[1:]):
    number = int(re.search(r'\d+', sheet.name).group())
    slug = f'table-{number:02d}'
    if '(b)' in sheet.name.lower():
        slug += '-b'
    elif 'ISIC' in sheet.name.upper():
        slug += '-isic-4'
    meaningful = [(r, c) for r in range(sheet.nrows) for c in range(sheet.ncols)
                  if sheet.cell_type(r, c) not in (0, 6) and str(sheet.cell_value(r, c)).strip()]
    maxrow = max(r for r, c in meaningful) + 1
    maxcol = max(c for r, c in meaningful) + 1
    # Ignore formatting-only rows/columns beyond the populated source range.
    rows, styles, error_cells, unavailable = [], [], [], []
    for r in range(maxrow):
        row, rowstyles = [], []
        for c in range(maxcol):
            cell = sheet.cell(r, c)
            xf = book.xf_list[cell.xf_index]
            font = book.font_list[xf.font_index]
            value = cell.value
            if cell.ctype in (0, 6):
                value = None
            elif cell.ctype == xlrd.XL_CELL_ERROR:
                value = xlrd.error_text_from_code[cell.value]
                error_cells.append({'cell': f'{colname(c)}{r+1}', 'marker': value})
            elif cell.ctype == xlrd.XL_CELL_DATE:
                value = xlrd.xldate_as_datetime(cell.value, book.datemode).isoformat()
            elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                value = bool(cell.value)
            unavailable_flag = (xf.background.fill_pattern == 1 and
                                xf.background.pattern_colour_index == 47)
            if unavailable_flag and value is not None:
                unavailable.append(f'{colname(c)}{r+1}')
            row.append(value)
            rowstyles.append({
                'format': book.format_map[xf.format_key].format_str,
                'bold': bool(font.bold), 'italic': bool(font.italic),
                'unavailable': unavailable_flag,
                'superscript': font.escapement == 1,
            })
        rows.append(row)
        styles.append(rowstyles)
    merges = [list(m) for m in sheet.merged_cells
              if m[0] < maxrow and m[2] < maxcol and m[1] <= maxrow and m[3] <= maxcol]
    first_data = maxrow
    first_year = None
    for r, row in enumerate(rows[1:], 1):
        numbers = [v for v in row if isinstance(v, (int, float)) and not isinstance(v, bool)]
        labels = ' '.join(v for v in row[:2] if isinstance(v, str))
        nonblank = [v for v in row if v is not None and str(v).strip()]
        year_only = len(nonblank) == 1 and (
            isinstance(nonblank[0], (int, float)) and 1900 <= nonblank[0] <= 2100
            or isinstance(nonblank[0], str) and re.fullmatch(r'(19|20)\d\d\s*(?:\(R\)|R|P)?', nonblank[0].strip(), re.I))
        if year_only:
            if first_year is None:
                first_year = r
        if len(numbers) >= 2:
            years_only = all(1900 <= v <= 2100 and v == int(v) for v in numbers)
            is_period = bool(re.search(r'Qtr|January|April|July|October', labels, re.I))
            is_annual = isinstance(row[0], (int, float)) and 1900 <= row[0] <= 2100
            is_employment = number == 18 and r >= 5 and bool(labels.strip())
            if is_period or is_annual or (is_employment and not years_only):
                first_data = r
                break
    header_end = min(first_year if first_year is not None else first_data, first_data)
    title = toc[index][1]
    if number == 18 and 'ISIC' in sheet.name.upper():
        title = 'Total Employment by Major Occupational Group and Economic Activity (ISIC Rev. 4)'
    elif number == 18:
        title = 'Total Employment by Major Occupations and Industry Groups (legacy classification)'
    elif number == 15:
        title = 'Combined Balance Sheet of Bermuda Banks and Deposit Companies: ' + ('Consolidated Liabilities' if '(b)' in sheet.name.lower() else 'Consolidated Assets')
    elif number == 10:
        title = 'Residential Dwelling Units: Gross Additions, Gross Deductions and Net Total'
    units = [v.strip() for v in rows[0] if isinstance(v, str) and v.strip().startswith('$')]
    # Actual observed years, not a claim of complete coverage or latest available data.
    observed_years = []
    for r, row in enumerate(rows):
        candidates = row if number == 18 and r == 2 else row[:2]
        for value in candidates:
            if isinstance(value, (int, float)) and value == int(value) and 1900 <= value <= year:
                # Year labels are standalone for quarterly tables; annual consumption is first column.
                if r == 2 and number == 18 or len([v for v in row if v is not None]) == 1 or number == 20:
                    observed_years.append(int(value))
            elif isinstance(value, str) and re.fullmatch(r'(19|20)\d\d\s*(?:\(R\)|R|P)?', value.strip(), re.I):
                observed_years.append(int(value.strip()[:4]))
    sources = []
    for row in rows:
        for value in row:
            if isinstance(value, str) and re.search(r'Source:', value, re.I):
                text = value.strip().lstrip("'")
                if text not in sources:
                    sources.append(text)
    tables.append({
        'slug': slug, 'number': number, 'label': toc[index][0].title(),
        'title': title, 'subject': categories[number], 'sheet': sheet.name,
        'range': f'A1:{colname(maxcol-1)}{maxrow}',
        'rows': rows, 'styles': styles, 'merges': merges,
        'headerEnd': header_end, 'firstData': first_data,
        'sourceHiddenRows': [r+1 for r, info in sheet.rowinfo_map.items() if info.hidden and r < maxrow],
        'sourceHiddenColumns': [colname(c) for c, info in sheet.colinfo_map.items() if info.hidden and c < maxcol],
        'columnWidths': [min(45, max(3, sheet.colinfo_map[c].width/256)) if c in sheet.colinfo_map else 12 for c in range(maxcol)],
        'units': ', '.join(units), 'sources': sources,
        'coverage': f'{min(observed_years)}–{max(observed_years)}' if observed_years else 'See source headings',
        'errors': error_cells, 'unavailableCells': unavailable,
    })
payload = {'edition': f'{year}-q{quarter}', 'editionLabel': f'Q{quarter} {year}',
           'sourceTitle': 'Quarterly Bulletin of Statistics — Annex I',
           'publisher': 'Government of Bermuda, Department of Statistics',
           'sourceFile': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'symbols': ['Grey shading: Not available for updating',
                       'Numbers may not add to total due to rounding',
                       'R: Revised', 'e: Estimate', '**: Divisor is zero'],
           'tables': tables,
           'dataSha256': hashlib.sha256(json.dumps(tables, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()}
target.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
print(json.dumps({'tables': len(tables), 'cells': sum(sum(v is not None for row in t['rows'] for v in row) for t in tables),
                  'sourceErrors': sum(len(t['errors']) for t in tables), 'jsonBytes': target.stat().st_size}))

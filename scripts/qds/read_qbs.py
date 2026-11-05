"""Read XLS/XLSX source values and formatting through the same small interface."""
import datetime
import xml.etree.ElementTree as ET
import zipfile
from types import SimpleNamespace as Record


def open_book(path):
    import xlrd
    if str(path).lower().endswith('.xls'):
        return xlrd.open_workbook(str(path), formatting_info=True)
    from openpyxl import load_workbook
    from openpyxl.styles.colors import COLOR_INDEX
    from openpyxl.utils.cell import column_index_from_string
    values = load_workbook(path, data_only=True)
    formulas = load_workbook(path, data_only=False)
    palette = COLOR_INDEX
    with zipfile.ZipFile(path) as archive:
        style_xml = ET.fromstring(archive.read('xl/styles.xml'))
        custom = style_xml.findall('{*}colors/{*}indexedColors/{*}rgbColor')
        if custom:
            palette = [c.attrib['rgb'] for c in custom]
    book = Record(xf_list=[], font_list=[], format_map={}, colour_map={47: (227, 227, 227)}, datemode=0)
    sheets, styles = [], {}
    for raw in formulas:
        cached = values[raw.title]
        cells = []
        if raw.max_row * raw.max_column > 2_000_000:
            raise ValueError('Unexpectedly large QBS worksheet; inspect its used range.')
        for row in raw:
            result = []
            for cell in row:
                value = cached.cell(cell.row, cell.column).value
                if cell.data_type == 'f' and value is None:
                    raise ValueError(f'Missing cached formula result: {raw.title}!{cell.coordinate}. Save calculated results in Excel first.')
                if isinstance(value, (datetime.datetime, datetime.date)):
                    value = value.isoformat()
                kind = 0 if value is None else 4 if isinstance(value, bool) else 2 if isinstance(value, (int, float)) else 1
                if cached.cell(cell.row, cell.column).data_type == 'e':
                    # Keep the original marker literally, with xlrd's error type for provenance.
                    value = next((k for k, v in xlrd.error_text_from_code.items() if v == value), None)
                    if value is None:
                        raise ValueError(f'Unrecognized Excel error at {raw.title}!{cell.coordinate}')
                    kind = 5
                key = cell.style_id
                if key not in styles:
                    colour = cell.fill.fgColor
                    rgb = colour.rgb if colour.type == 'rgb' else palette[colour.indexed] if colour.type == 'indexed' and colour.indexed < len(palette) else None
                    grey = bool(cell.fill.patternType == 'solid' and rgb and rgb[-6:].upper() == 'E3E3E3')
                    if cell.fill.patternType == 'solid' and colour.type == 'theme':
                        raise ValueError('Theme-based source shading needs review before importing.')
                    idx = len(book.xf_list); styles[key] = idx
                    book.font_list.append(Record(bold=cell.font.bold, italic=cell.font.italic, escapement=1 if cell.font.vertAlign == 'superscript' else 0))
                    book.format_map[idx] = Record(format_str=cell.number_format)
                    book.xf_list.append(Record(font_index=idx, format_key=idx, background=Record(fill_pattern=1 if grey else 0, pattern_colour_index=47 if grey else 0)))
                result.append(Record(value=value if value is not None else '', ctype=kind, xf_index=styles[key]))
            cells.append(result)
        columns = {}
        for key, dimension in raw.column_dimensions.items():
            first = dimension.min or column_index_from_string(key)
            last = dimension.max or first
            for c in range(first - 1, last):
                columns[c] = Record(width=(dimension.width or 12)*256, hidden=dimension.hidden)
        sheets.append(Sheet(raw.title, cells,
                            [[m.min_row-1, m.max_row, m.min_col-1, m.max_col] for m in raw.merged_cells.ranges],
                            {r-1: Record(hidden=d.hidden) for r, d in raw.row_dimensions.items()}, columns))
    book.sheets = lambda: sheets
    book.sheet_by_index = lambda i: sheets[i]
    return book


class Sheet:
    def __init__(self, name, cells, merges, rows, columns):
        self.name, self.cells = name, cells
        self.nrows, self.ncols = len(cells), len(cells[0]) if cells else 0
        self.merged_cells, self.rowinfo_map, self.colinfo_map = merges, rows, columns

    def row(self, r):
        return self.cells[r]

    def cell(self, r, c):
        return self.cells[r][c]

    def cell_value(self, r, c):
        return self.cell(r, c).value

    def cell_type(self, r, c):
        return self.cell(r, c).ctype

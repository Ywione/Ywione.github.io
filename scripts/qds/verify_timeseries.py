"""Reconcile each long-format observation and audit cell with its source."""
import csv
import datetime
import json
import math
import re
import sys
from pathlib import Path
import openpyxl

def coordinates(address):
    m = re.fullmatch(r'([A-Z]+)(\d+)', address)
    col = 0
    for char in m[1]: col = col * 26 + ord(char) - 64
    return int(m[2])-1, col-1

def verify(source, site):
    count = 0
    for table in source['tables']:
        ts = table['timeSeries']; records = ts['records']
        stem = site / 'assets/datasets/qds' / source['edition'] / (table['slug']+'-timeseries')
        saved = json.loads(stem.with_suffix('.json').read_text())
        assert saved['records'] == records
        with stem.with_suffix('.csv').open(encoding='utf-8-sig',newline='') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == len(records)
        workbook = openpyxl.load_workbook(stem.with_suffix('.xlsx'),data_only=False)
        sheet = workbook['Time series']
        assert sheet.max_row == len(records)+1
        assert [c.value for c in sheet[1]] == ts['fields']
        assert sheet.freeze_panes == 'A2' and len(sheet.tables) == 1
        mapped = set()
        for number, (record, flat) in enumerate(zip(records,rows),2):
            r,c = coordinates(record['source_cell']); raw = table['rows'][r][c]
            assert (r,c) not in mapped
            mapped.add((r,c))
            assert record['source_value'] == raw
            value = raw * (100 if '%' in table['styles'][r][c]['format'] else 1) if isinstance(raw,(int,float)) else None
            assert record['value'] == value
            for column,key in enumerate(ts['fields'],1):
                expected = record[key]; actual = sheet.cell(number,column).value
                assert sheet.cell(number,column).data_type != 'f', (table['slug'],number,key)
                if key == 'date' and expected:
                    assert isinstance(actual,datetime.datetime) and actual.date().isoformat() == expected
                elif isinstance(expected,(int,float)):
                    assert isinstance(actual,(int,float)) and math.isclose(expected,actual,rel_tol=1e-14,abs_tol=1e-12)
                else:
                    assert actual == expected or (actual is None and expected == ''), (table['slug'],number,key,actual,expected)
                if isinstance(expected,(int,float)):
                    assert math.isclose(float(flat[key]),expected,rel_tol=1e-14,abs_tol=1e-12)
                else:
                    assert flat[key] == ('' if expected is None else str(expected)), (table['slug'],number,key)
        audit = {coordinates(x['source_cell']) for x in ts['audit']}
        with (stem.parent/(table['slug']+'-audit.csv')).open(encoding='utf-8-sig',newline='') as f:
            saved_audit = list(csv.DictReader(f))
        assert len(saved_audit) == len(ts['audit'])
        for actual, expected in zip(saved_audit,ts['audit']):
            assert actual['source_cell'] == expected['source_cell'] and actual['reason'] == expected['reason']
            raw = expected['source_value']
            assert math.isclose(float(actual['source_value']),raw,rel_tol=1e-14,abs_tol=1e-12) if isinstance(raw,(int,float)) else actual['source_value'] == raw
        assert not mapped & audit
        for r,row in enumerate(table['rows']):
            for c,value in enumerate(row):
                if isinstance(value,(int,float)) or str(value).startswith('#'):
                    assert (r,c) in mapped | audit, (table['slug'],r,c)
        count += len(records)
        print(table['slug'],len(records),'observations verified')
    print('Verified',count,'observations across',len(source['tables']),'tables; all numeric/error source cells accounted for.')

if __name__ == '__main__':
    verify(json.loads(Path(sys.argv[1]).read_text()),Path(sys.argv[2]))

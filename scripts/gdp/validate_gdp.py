"""Check generated downloads against every supplied numeric observation."""
import calendar, csv, hashlib, json, math, sys
from pathlib import Path
import openpyxl

site=Path(sys.argv[1]); source=Path(sys.argv[2])
for kind,expected,columns in [('annual',163,range(2,10)),('quarterly',200,range(3,8))]:
    folder=site/'assets/datasets/gdp'; filename=f'bermuda-{kind}-gdp.xlsx'
    assert (folder/filename).read_bytes()==(source/filename).read_bytes()
    original=openpyxl.load_workbook(source/filename,data_only=True)[f'{kind.title()} GDP']
    data=json.loads((folder/f'{kind}-timeseries.json').read_text()); records=data['records']
    # Coverage check is independent of the generated records.
    cells={original.cell(r,c).coordinate for r in range(8,original.max_row+1) for c in columns if original.cell(r,c).value is not None}
    assert len(records)==expected and {r['source_cell'] for r in records}==cells
    assert len(set((r['date'],r['series']) for r in records))==len(records)
    for r in records:
        value=original[r['source_cell']].value
        assert math.isclose(r['value'],value*(100 if r['units']=='%' else 1),rel_tol=1e-13)
        y,m,d=map(int,r['date'].split('-')); assert d==calendar.monthrange(y,m)[1]
    with (folder/f'{kind}-timeseries.csv').open(encoding='utf-8-sig',newline='') as f:
        csvrows=list(csv.DictReader(f))
    exported=openpyxl.load_workbook(folder/f'{kind}-timeseries.xlsx',data_only=True)['Time series']
    assert exported.max_row==len(records)+1 and len(csvrows)==len(records)
    for record,crow,xrow in zip(records,csvrows,exported.iter_rows(min_row=2,values_only=True)):
        for key,actual in zip(data['fields'],xrow):
            expected_value=record[key]
            if key=='date': assert actual.date().isoformat()==expected_value
            elif key=='value':
                assert math.isclose(actual,expected_value,rel_tol=1e-13)
                assert float(crow[key])==expected_value
            else: assert (actual or '')==expected_value, (key,actual,expected_value)
    print(f'{kind}: {len(records)} observations match source, CSV and Excel; original preserved byte-for-byte')

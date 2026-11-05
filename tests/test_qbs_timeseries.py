import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/qds'))
from timeseries import normalize

HEADERS = json.loads((Path(__file__).resolve().parents[1]/'scripts/qds/timeseries-headers.json').read_text())

def table(slug, data):
    headers=HEADERS[slug]; first=max(r for r,c,v in headers)+1
    rows=[[None]*26 for _ in range(first)]
    for r,c,v in headers: rows[r][c]=v
    rows += [[r.get(c) for c in range(26)] for r in data]
    return dict(slug=slug,number=int(slug.split('-')[1]),sheet=slug,units='',firstData=first,rows=rows,
                styles=[[dict(format='General',unavailable=False) for _ in r] for r in rows])

class TimeSeriesTests(unittest.TestCase):
    def test_quarters_annual_zero_missing_and_errors(self):
        t=table('table-01',[{0:2024},{0:'1st Qtr',2:0,3:12,4:'#DIV/0!'},{0:'Year',2:48},{0:2025},{0:'1st Qtr'}])
        rows=normalize(t)['records']
        self.assertEqual(len(rows),14)
        zero=next(x for x in rows if x['source_value']==0)
        self.assertEqual((zero['date'],zero['value']),('2024-03-31',0))
        err=next(x for x in rows if x['source_marker']=='#DIV/0!')
        self.assertIsNone(err['value'])
        self.assertTrue(any(x['date']=='2024-12-31' and x['frequency']=='Annual' for x in rows))

    def test_missing_year_is_not_carried_forward(self):
        t=table('table-01',[{0:2024},{0:'1st Qtr',2:1},{0:'4th Qtr',2:2},{},{0:'1st Qtr',2:3}])
        row=next(x for x in normalize(t)['records'] if x['value']==3)
        self.assertEqual(row['date'],'')
        self.assertIn('year missing',row['status'])

    def test_published_percentage_and_conflict(self):
        t=table('table-01',[{0:'% Change'},{0:2024},{0:'1st Qtr',2:.05},{0:2024},{0:'1st Qtr',2:.06}])
        for r in t['styles']: r[2]['format']='0.0%'
        rows=[r for r in normalize(t)['records'] if r['value'] is not None]
        self.assertEqual([r['value'] for r in rows],[5,6])
        self.assertTrue(all('conflicting source period' in r['status'] for r in rows))

    def test_reference_month(self):
        t=table('table-04',[{0:2024},{1:'April',4:10}])
        r=normalize(t)['records'][0]
        self.assertEqual((r['date'],r['frequency']),('2024-04-30','Reference month'))

    def test_index_bases_remain_separate(self):
        t=table('table-11',[{9:'April 2006 = 100.0'},{0:2014},{0:'1st Qtr',1:120},{9:'April 2015 = 100.0'},{0:2014},{0:'1st Qtr',1:98}])
        rows=[r for r in normalize(t)['records'] if r['value'] is not None]
        self.assertEqual(len({r['index_base'] for r in rows}),2)
        self.assertTrue(all('conflicting' not in r['status'] for r in rows))

    def test_changed_headers_stop_import(self):
        t=table('table-01',[{0:2024},{0:'1st Qtr',2:10}])
        t['rows'][1][2]='Unexpected category'
        with self.assertRaisesRegex(ValueError,'headings changed'): normalize(t)

if __name__=='__main__': unittest.main()

"""Export the two explicitly named GDP workbooks; never scan unrelated files."""
import argparse, calendar, csv, hashlib, html, json, math, shutil
from pathlib import Path
from datetime import date
import openpyxl

p = argparse.ArgumentParser()
p.add_argument('--source-dir', type=Path, default=Path('/Users/ywionedarrell/Documents/Consulting/Data'))
p.add_argument('--site', type=Path, required=True)
a = p.parse_args()
out = a.site / 'assets/datasets/gdp'
out.mkdir(parents=True, exist_ok=True)
fields = ['date','series','value','units','period','frequency','measure','index_base','status','source_id','publication_month','source_url','source_sheet','source_cell']
manifest = {}
for kind in ('annual','quarterly'):
    filename = f'bermuda-{kind}-gdp.xlsx'
    src = a.source_dir / filename
    w = openpyxl.load_workbook(src, data_only=True)
    sheet = w[f'{kind.title()} GDP']
    sources = {r[0]: r for r in w['Sources'].iter_rows(min_row=5, values_only=True) if r[0]}
    notes = [f'{r[0]}: {r[1]}' for r in w['Notes'].iter_rows(min_row=5, values_only=True) if r[0] and r[1] and 'check' not in str(r[0]).lower() and 'refresh' not in str(r[0]).lower()]
    records=[]
    for row in range(8,sheet.max_row+1):
        v=[sheet.cell(row,c).value for c in range(1,12)]
        if not v[0]: continue
        if kind=='annual':
            period=str(v[0]); end=f'{v[0]}-12-31'
            specs=[(2,'Nominal GDP','BD$ million','Value','Current prices'),(3,'Real GDP','BD$ million','Value','2013 prices'),(4,'Nominal GDP growth — calculated','%','Calculated YoY','Current prices'),(5,'Real GDP growth — calculated','%','Calculated YoY','2013 prices'),(6,'Nominal GDP growth — published','%','Published YoY','Current prices'),(7,'Real GDP growth — published','%','Published YoY','2013 prices'),(8,'GDP deflator','Index, 2013 = 100','Value','2013 = 100'),(9,'Nominal GDP per capita','BD$ per person','Value','Current prices')]
        else:
            period=v[0]; year=int(period[:4]); month=int(period[-1])*3
            end=date(year,month,calendar.monthrange(year,month)[1]).isoformat()
            specs=[(3,'Nominal GDP','BD$ million','Value','Current prices'),(4,'Real GDP — 2013 prices','BD$ million','Value','2013 prices'),(5,'Real GDP — 2006 prices','BD$ million','Value','2006 prices'),(6,'Nominal GDP growth — published','%','Published YoY','Current prices'),(7,f'Real GDP growth — published, {v[7]} prices','%','Published YoY',f'{v[7]} prices')]
        for col,name,unit,measure,base in specs:
            value=v[col-1]
            if value is None: continue
            assert isinstance(value,(int,float)) and math.isfinite(value), (kind,row,col,value)
            ids=[v[9]] if kind=='annual' else [v[8] if col in (3,6) else v[9] if col==4 or (col==7 and v[7]==2013) else v[10]]
            if kind=='annual' and col in (4,5): ids=list(dict.fromkeys(ids+[sheet.cell(row-1,10).value]))
            assert all(i in sources for i in ids), ids
            refs=[sources[i] for i in ids]
            urls=[r[5] for r in refs if str(r[5]).startswith('https://')]
            records.append(dict(zip(fields,[end,name,value*100 if unit=='%' else value,unit,period,kind.title(),measure,base,v[10] if kind=='annual' else 'Provisional; subject to revision','; '.join(ids),'; '.join(str(r[2] or 'Unknown') for r in refs),'; '.join(urls),sheet.title,sheet.cell(row,col).coordinate])))
    assert records and len({(r['date'],r['series']) for r in records})==len(records)
    common=['Dates mark the end of each calendar year or quarter. Each row contains one observation. Missing observations are omitted, never replaced with zero.', 'Percentage values use the percent scale: 5 means 5%. Published growth is distinct from growth calculated from selected annual levels.', 'Values are snapshots of the supplied workbook’s cached results. Original workbooks retain formulas, revision history and full source references. Source workbook compilation date: 5 November 2026.']
    description = ('GDP by industry at purchasers’ prices. Nominal and real GDP, growth, the GDP deflator and GDP per capita.' if kind=='annual' else 'GDP by expenditure, not seasonally adjusted or annualised. Nominal GDP, real GDP and published year-over-year growth.')
    caveats = (['Real GDP uses 2013 prices. The 1996–2020 history retains an unknown publication vintage; 2021–2025 comes from the latest annual report. 2025 is provisional.', 'Calculated growth compares selected annual levels; published growth uses each report’s comparison and can differ. The supplied 2007 real GDP figure differs from the rebasing note by BD$0.072 million and is retained.', 'Annual industry GDP and quarterly expenditure GDP are different measures; annual values need not equal the sum of quarters.'] if kind=='annual' else ['Real GDP at 2006 and 2013 prices is kept in separate series, including overlapping quarters; the two series are not spliced.', 'Nominal GDP combines release vintages. Published growth is retained from the selected release, not recalculated from the combined history.', 'All quarterly observations are provisional. The Q1 2026 release flags imports and related aggregates as not comparable with earlier releases; GDP includes these aggregates.'])
    coverage=f"{records[0]['period']}–{records[-1]['period']}"
    data=dict(title=f'Bermuda {kind} GDP',fields=fields,records=records,notes=common+caveats+notes,description=description,coverage=coverage)
    (out/f'{kind}-timeseries.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    with (out/f'{kind}-timeseries.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(records)
    shutil.copy2(src,out/filename)
    manifest[kind]=dict(source=filename,sha256=hashlib.sha256(src.read_bytes()).hexdigest(),observations=len(records),coverage=coverage)
    esc=html.escape; stem=f'/assets/datasets/gdp/{kind}-timeseries'
    downloads=f'<p><a href="{stem}.xlsx" download>Download Excel</a> · <a href="{stem}.csv" download>Download CSV</a> · <a href="/assets/datasets/gdp/{filename}" download>Original source workbook</a></p>'
    controls=''.join(f'<div><label for="ts-{key}">{label}</label><select id="ts-{key}"><option value="">All</option></select></div>' for key,label in [('series','Series'),('year','Year'),('frequency','Frequency'),('measure','Measure'),('basis','Price base')])
    shown=sorted([r for r in records if r['measure']=='Value'],key=lambda r:(r['date'],r['series']),reverse=True)[:100]
    rows=''.join('<tr>'+''.join(f'<td>{esc(str(x))}</td>' for x in [r['date'],r['series'],f"{r['value']:,.6f}".rstrip('0').rstrip('.'),r['units'],r['frequency'],r['index_base'],r['status']])+'</tr>' for r in shown)
    body=f'''---
layout: default
title: "Bermuda {kind} GDP"
permalink: /datasets/gdp/{kind}/
description: "{description}"
---
<link rel="stylesheet" href="/assets/css/qds.css">
<p><a href="/datasets/">Datasets</a></p>
<p class="meta">{coverage} · Source compilation: 5 November 2026</p>
<p>{description}</p>
{downloads}
<h2>Definitions and comparability</h2>
{''.join('<p>'+esc(n)+'</p>' for n in caveats)}
<h2>Time series</h2>
<p>One row per observation: date, series, value and units. Dates mark period ends. Use the Measure filter to view growth rates; the initial view shows levels and indices. Missing observations are omitted. A percentage value of 5 means 5%.</p>
<div class="qds-series" data-url="{stem}.json">
<div class="qds-series-controls" hidden>{controls}</div>
<p id="ts-count" class="meta" aria-live="polite">Latest {len(shown)} level and index observations. Downloads contain all {len(records)} observations.</p>
<div class="qds-table-shell" tabindex="0" role="region" aria-label="GDP observations; scroll for more columns"><table class="qds-grid qds-long"><caption class="sr-only">{data['title']} time series</caption><thead><tr>{''.join('<th scope="col">'+s+'</th>' for s in ['Date','Series','Value','Units','Frequency','Price base','Status'])}</tr></thead><tbody id="ts-body">{rows}</tbody></table></div>
<div class="qds-pagination" hidden><button type="button" id="ts-prev">Previous</button> <span id="ts-page"></span> <button type="button" id="ts-next">Next</button></div>
<noscript><p>Enable JavaScript to filter all observations, or use the complete downloads.</p></noscript></div>
<h2>Sources</h2><p>Government of Bermuda, Department of Statistics. The supplied compiled workbook includes publication dates, source links and revision history. Downloads retain source identifiers and cell references. Historical observations have not been independently re-extracted for this website.</p>
<ul>{''.join('<li>'+esc(str(r[1]))+' — '+('<a href="'+esc(str(r[5]),quote=True)+'">Official publication</a>' if str(r[5]).startswith('https://') else esc(str(r[5])))+'</li>' for r in sources.values())}</ul>
{downloads}
<script src="/assets/js/qds.js" defer></script>
'''
    (a.site/'gdp').mkdir(exist_ok=True)
    (a.site/'gdp'/f'{kind}.html').write_text(body)
    (a.site/'_datasets'/f'{kind}-gdp.md').write_text(f'''---
title: "Bermuda {kind} GDP"
description: "{description}"
coverage: "{coverage}"
frequency: "{kind.title()}"
updated: "2026-11-06"
excel: "{stem}.xlsx"
csv: "{stem}.csv"
source_name: "Government of Bermuda, Department of Statistics"
source_url: "https://www.gov.bm/bermuda-economic-statistics"
---

[View and filter the time series](/datasets/gdp/{kind}/). Downloads use long format: date, series, value and units, with price bases and source references. The original compiled workbook is also available on the dataset page.
''')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))

"""Reshape QBS cached values; never aggregate, interpolate, or repair source data."""
import calendar
import json
import re
import sys
from pathlib import Path

VERSION = 1
FIELDS = ['date', 'series', 'value', 'units', 'period', 'frequency', 'measure',
          'classification', 'index_base', 'status', 'source_marker', 'revision',
          'availability', 'source_sheet', 'source_cell', 'source_value', 'source_format']

# Column letters refer to the supplied Annex I worksheets. Changes to headings
# must be reviewed, rather than inferred by string similarity.
MAPS = {
 'table-01': ('CDEFGHI', 'Cruise passengers|Air visitors: USA|Air visitors: Canada|Air visitors: UK|Air visitors: other countries|Total air visitors|Total cruise and air visitors'),
 'table-02': ('CDEFGHI', 'Resort hotels|Small hotels, cottage colonies and clubs|Housekeeping accommodations|Guest houses|Private homes|Not stated|Total'),
 'table-03': ('CDEFG', 'Air visitors: accommodation and food|Air visitors: shopping, entertainment, transport and other|Air visitors: total|Cruise visitors|Total expenditure'),
 'table-04': ('EFGH', 'Hotels|Cottage colonies and housekeeping|Guest houses and micro-units|All establishments'),
 'table-05': ('BCDEFGHIJKL', 'Customs duty|Payroll tax|International company tax|Hotel occupancy tax|Land tax|Vehicle licences|Passenger tax|Stamp duty|Telecommunications tax|All other revenue|Total current revenue'),
 'table-06': ('DEFGHIK', 'Wages, salaries and employee overhead|Other goods and services|Grants and contributions|Interest on public debt|Total current expenditure|Capital expenditure|Total expenditure'),
 'table-07': ('CDEFGHIJKL', 'Food, beverages and tobacco|Clothing|Fuels|Chemicals|Basic materials and semi-manufactures|Machinery|Transport equipment|Finished equipment|Miscellaneous|Total'),
 'table-08': ('CEHKMN', 'USA|UK|Caribbean|Canada|All other countries|Total'),
 'table-09': ('CEGIKMOQSU', 'New projects started|Work put in place: residential|Work put in place: offices, shops and warehouses|Work put in place: hotels and guesthouses|Work put in place: schools, hospitals and community centres|Work put in place: roads, bridges and airports|Work put in place: industrial plant and other|Total work put in place|Public sector|Private sector'),
 'table-10': ('CEGIKNPRTVX', 'Units completed: studio|Units completed: one bedroom|Units completed: two bedrooms|Units completed: three bedrooms and over|Total units completed|Units lost: studio|Units lost: one bedroom|Units lost: two bedrooms|Units lost: three bedrooms and over|Total units lost|Net total units'),
 'table-11': ('BDFHJLNPRT', 'All items|Food|Rent|Clothing and footwear|Tobacco and liquor|Fuel and power|Household goods, services and supplies|Transport and vehicles|Education, recreation, entertainment and reading|Health and personal care'),
 'table-12': ('CEGIJLNP', 'Total|Food stores|Liquor stores|Motor vehicle dealers|Service stations|Building materials|Apparel stores|All other store types'),
 'table-13': ('CDEFGHIJKLM', 'New registrations: local|New registrations: exempted|New registrations: international exempted partnerships|New registrations: non-resident|Total new registrations|On register: local|On register: exempted|On register: international exempted partnerships|On register: non-resident|On register: non-resident insurance|Total on register'),
 'table-14': ('BCDEFHJKLM', 'International business|Hotels and restaurants|Banking, insurance and real estate|Business services|Wholesale and retail|Public administration and defence|Construction|Transport and communication|All other|Total'),
 'table-15': ('BCDEFGH', 'Cash|Demand and time deposits|Investments|Loans and advances|Premises and equipment|Other assets|Total assets'),
 'table-15-b': ('CDEFGH', 'Demand deposits|Savings deposits|Time deposits|Other liabilities|Capital|Total liabilities'),
 'table-16': ('CDEFGHIKM', 'Purpose: vacation|Purpose: local business|Purpose: international business|Purpose: other reasons|Destination: USA|Destination: Canada|Destination: UK|Destination: other countries|Total trips'),
 'table-17': ('CDEFGHIJKL', 'Clothing and footwear|Electronic and photographic equipment|Household items, furniture and appliances|Toys and sports goods|Tapes and compact discs|Computer hardware and software|Jewellery and watches|Tools, machinery and parts|Miscellaneous|Total'),
 'table-19': ('DEFGHI', 'Hotels (source column D)|Hotels (source column E)|Hotels (source column F)|Cottage colonies and housekeeping|Guest houses and micro-units|Total'),
 'table-20': ('BDFHJLNPRTVXZ', 'Food and non-alcoholic beverages|Alcohol, tobacco and narcotics|Clothing and footwear|Housing, water, electricity, gas and other fuels|Furnishings, equipment and house maintenance|Health|Transport|Communication|Recreation and culture|Education|Restaurants and hotels|Miscellaneous goods and services|Total'),
}
COUNT_UNITS = {1:'visitors', 2:'visitors', 4:'employment', 10:'dwelling units', 13:'business registrations', 16:'trips', 18:'employment'}
NOTES = [
 'One observation per row. No totals or growth rates have been recalculated.',
 'Dates use the last day of the reported quarter or year. Annual dates are period labels, not survey dates. Hotel employment uses the end of the named reference month.',
 'Annual observations and quarterly observations are separate frequencies. Annual source rows can be totals, averages or stocks; do not sum them with quarterly rows.',
 'Published percentage changes are a separate measure. Percentage-formatted source fractions are multiplied by 100; a value of 5 with units % means 5%. The comparison basis remains as published.',
 'Blank values remain blank. Source errors and other non-numeric symbols are retained in source_marker. Genuine numeric zero remains zero. Entirely blank period rows are omitted.',
 'Index bases and changed classifications remain separate. They have not been linked or spliced.',
 'Source values, formats and cell references allow each observation to be traced to the original-layout download. Source shading is recorded in availability.',
 'Unassigned numeric cells, year headings, reference weights and footnote numbers are recorded in the audit file, not silently treated as dated observations.',
]

def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()

def filled(value):
    return value is not None and str(value).strip() != ''

def year(value):
    if isinstance(value, (int, float)) and value == int(value) and 1900 <= value <= 2100:
        return int(value), ''
    m = re.fullmatch(r'((?:19|20)\d{2})\s*(?:\(?([RPe])\)?)?', clean(value), re.I)
    return (int(m[1]), m[2] or '') if m else (None, '')

def letter(col):
    result = ''
    while col >= 0:
        result = chr(65 + col % 26) + result
        col = col // 26 - 1
    return result

def end_date(y, m):
    return f'{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]}' if y else ''

def normalize(table):
    expected_headers = json.loads(Path(__file__).with_name('timeseries-headers.json').read_text())[table['slug']]
    headers = [[r,c,clean(v)] for r,row in enumerate(table['rows'][:table['firstData']]) for c,v in enumerate(row) if r>0 and isinstance(v,str) and clean(v) and not year(v)[0]]
    if headers != expected_headers:
        raise ValueError(f"{table['slug']}: source headings changed; review the series mapping before publishing")
    records, used, reference = [], set(), set()
    slug = table['slug']
    pct, y, revision, base, modern, year_cols, group = False, None, '', '', False, {}, ''
    last_quarter = 0
    units = table['units'] or COUNT_UNITS.get(table['number'], '')
    warnings = []
    if slug == 'table-14':
        warnings.append('The first income block has no year label in the source. Its observations have blank dates and a missing-year flag; no year has been guessed.')
    if slug == 'table-19':
        warnings.append('Three source columns are identically labelled Hotels. They remain separate and are identified by their source columns; their coverage is not inferred.')

    def add(r, c, name, month, frequency, period, classification=''):
        raw = table['rows'][r][c]
        style = table['styles'][r][c]
        value = raw if isinstance(raw, (float, int)) and not isinstance(raw, bool) else None
        if value is not None and '%' in style['format']:
            value *= 100
        status = 'reported' if value is not None else ('source error' if str(raw).startswith('#') else 'source marker' if filled(raw) else 'blank in source')
        if not y:
            status += '; year missing'
        record = dict(zip(FIELDS, [end_date(y, month), name, value,
            '%' if pct else f'Index ({base})' if base else units,
            period, frequency, 'Published percentage change' if pct else 'Value', classification,
            base, status, clean(raw) if value is None else '', revision,
            'Not available for updating' if style['unavailable'] else '', table['sheet'], f'{letter(c)}{r+1}', raw, style['format']]))
        records.append(record)
        used.add((r, c))

    for r, row in enumerate(table['rows']):
        texts = [clean(v) for v in row if isinstance(v, str) and v.strip()]
        joined = ' '.join(texts)
        if re.search(r'%\s*Change', joined, re.I):
            pct, y, revision, base, modern, year_cols, group = True, None, '', '', False, {}, ''
            last_quarter = 0
            continue
        if table['number'] == 18:
            label = clean(row[1] if slug.endswith('isic-4') else row[0])
            candidates = {c:year(v) for c,v in enumerate(row) if year(v)[0]}
            if not label and len(candidates) >= 3:
                year_cols = candidates
                reference.update((r,c) for c in candidates)
                continue
            if re.search(r'Occupational Group|Industry Group|Division of Economic Activity', label, re.I):
                group = 'Occupation' if 'Occupation' in label else 'Industry'
                continue
            if not label or not group or label.startswith(('Source:', '1 ', '1.', 'February', 'P =')):
                continue
            if not any(filled(row[c]) for c in year_cols):
                continue
            for c, (y, revision) in year_cols.items():
                add(r,c,group + ': ' + label,12,'Annual',str(y), 'ISIC Rev. 4' if slug.endswith('isic-4') else 'Legacy industry classification')
            continue
        # Explicit base and classification headings are state changes, not dates.
        base_match = re.search(r'(April\s+(?:2006|2015)\s*=\s*100(?:\.0)?)', joined, re.I) if slug == 'table-11' else re.search(r'(Average Monthly Sales\s*(?:2006|2015)\s*=\s*100(?:\.0)?)', joined, re.I) if slug == 'table-12' else None
        if base_match:
            base = base_match[1]
        if slug == 'table-02' and any('Rental House/Apt' in text for text in texts):
            modern = True
        if slug == 'table-11' and any('Weights' in text for text in texts):
            reference.update((r,c) for c,v in enumerate(row) if isinstance(v,(float,int)))
            continue
        columns, names = MAPS[slug]
        mapping = list(zip([ord(c)-65 for c in columns], names.split('|')))
        classification = ''
        if slug == 'table-02':
            classification = 'Accommodation categories from 2014' if modern else 'Earlier accommodation categories'
            if modern:
                mapping = list(zip(range(2,7), ['Hotels or similar','Friends and relatives and rental house/apartment','Bed and breakfast / guest house','Other','Total']))
            elif pct:
                mapping = mapping[:5]
        if slug == 'table-19' and pct:
            mapping = [(c,'Other' if c == 7 else name) for c,name in mapping]
        first = 1 if slug == 'table-17' else 0
        this_year, flag = year(row[first])
        if this_year:
            y, revision = this_year, flag
            last_quarter = 0
            reference.add((r,first))
            if slug != 'table-20':
                continue
        label = clean(row[1] if slug in ('table-04','table-19') else row[first])
        # Most quarterly sheets place the quarter in A; some use B alongside year headings.
        if not label or this_year:
            label = clean(row[1]) if len(row)>1 and slug != 'table-20' else label
        if slug == 'table-12' and label == '1st Qtr3':
            label = '1st Qtr'
            note = 'The retail source label “1st Qtr3” is read as first quarter; the trailing 3 is retained here as a source-label annotation.'
            if note not in warnings: warnings.append(note)
        quarter = re.fullmatch(r'([1-4])(?:st|nd|rd|th)\s*[QO]tr\.?\s*([RPe])?', label, re.I)
        month_map = {'January':1,'April':4,'July':7,'October':10}
        if slug == 'table-20' and this_year:
            month, frequency, period = 12, 'Annual', str(y)
        elif quarter:
            q = int(quarter[1]); month, frequency = q*3, 'Quarterly'
            if q == 1 and last_quarter and not any(filled(v) for v in table['rows'][r-1]):
                y, revision = None, ''
            last_quarter = q
            period = f'{y}-Q{q}' if y else f'Q{q} (year missing)'
            if quarter[2]: revision = quarter[2]
        elif label.lower() == 'year':
            month, frequency, period = 12, 'Annual', str(y) if y else 'Year (year missing)'
        elif slug == 'table-04' and label in month_map:
            month, frequency = month_map[label], 'Reference month'
            period = f'{y}-{month:02d}' if y else f'{label} (year missing)'
        else:
            continue
        if not any(filled(row[c]) for c,_ in mapping):
            continue
        if slug in ('table-11','table-12') and not base:
            raise ValueError(f'{slug}: index observation without a recognised base at row {r+1}')
        for c,name in mapping:
            add(r,c,name,month,frequency,period,classification)
    if not records:
        raise ValueError(f'{slug}: no observations recognised')
    keys = {}
    for obs in records:
        key = tuple(obs[k] for k in ('period','series','frequency','measure','classification','index_base'))
        if key in keys:
            obs['status'] += '; conflicting source period'
            if 'conflicting source period' not in keys[key]['status']:
                keys[key]['status'] += '; conflicting source period'
        keys[key] = obs
    if any('conflicting source period' in x['status'] for x in records):
        warnings.append('The source repeats some period and series labels. All conflicting observations are retained and flagged; use source_cell to distinguish them. No date correction or deduplication has been assumed.')
    if any(not x['date'] for x in records) and slug != 'table-14':
        warnings.append('Some source observations have no year label. Their dates are blank and their status is flagged; no year has been inferred.')
    audit = []
    for r,row in enumerate(table['rows']):
        for c,v in enumerate(row):
            if (r,c) not in used and (isinstance(v,(int,float)) or str(v).startswith('#')):
                audit.append({'source_cell':f'{letter(c)}{r+1}', 'source_value':v,
                    'reason':'Year heading or reference value' if (r,c) in reference else 'Not assigned: no unambiguous dated series',
                    'row_context':' | '.join(clean(x) for x in row if isinstance(x,str) and x.strip())})
    records.sort(key=lambda x:(x['date'] or '0000',x['frequency'],x['series'],x['measure'],x['index_base']))
    return {'version':VERSION, 'fields':FIELDS, 'records':records, 'notes':NOTES + warnings,
            'audit':audit, 'sourceNotes': list(dict.fromkeys(clean(v) for row in table['rows'] for v in row if isinstance(v,str) and (re.match(r"\s*'?Source:",v,re.I) or re.match(r'\s*\d+[. ]',v) and len(v)>35)))}

def main():
    path = Path(sys.argv[1]); source = json.loads(path.read_text())
    for table in source['tables']:
        table['timeSeries'] = normalize(table)
        print(table['slug'], len(table['timeSeries']['records']), 'observations;',len(table['timeSeries']['audit']),'audit cells')
    Path(sys.argv[2]).write_text(json.dumps(source,ensure_ascii=False))

if __name__ == '__main__':
    main()

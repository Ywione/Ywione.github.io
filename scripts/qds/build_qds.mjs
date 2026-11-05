import fs from 'node:fs/promises';
import { exportTimeSeries, timeSeriesHTML } from './build_timeseries.mjs';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [inputPath, sitePath, reviewPath] = process.argv.slice(2);
const source = JSON.parse(await fs.readFile(inputPath, 'utf8'));
const edition = source.edition;
const pagesOnly = process.argv.includes('--pages-only');
const filesPath = path.join(sitePath, 'assets/datasets/qds', edition);
const pagesPath = path.join(sitePath, 'qds');
await fs.mkdir(filesPath, { recursive: true });
await fs.mkdir(pagesPath, { recursive: true });
await fs.mkdir(reviewPath, { recursive: true });
const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const col = n => { let s=''; for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s; };
const populated = value => value !== null && value !== undefined && String(value).trim() !== '';
const rowYear = row => { const nonblank=row.filter(populated);if(nonblank.length!==1)return null;const value=nonblank[0];if(typeof value==='number' && value>=1900 && value<=2100 && Number.isInteger(value))return value;if(typeof value==='string' && /^(19|20)\d{2}\s*(?:\(R\)|R|P)?$/i.test(value.trim()))return Number(value.trim().slice(0,4));return null; };
const dataUrl = table => `/assets/datasets/qds/${edition}/${table.slug}`;
const tableUrl = table => `/datasets/qds/${edition}/${table.slug}/`;
const publisherUrl = 'https://www.gov.bm/bermuda-economic-statistics';
function display(value, format) {
  if (value == null) return '';
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE';
  if (typeof value !== 'number') return value;
  if (!format || format === 'General' || format === '@') return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(15)));
  const first = format.split(';')[0];
  const decimal = (first.match(/\.([0#]+)/)?.[1] || '').length;
  if (format.includes('%')) return `${(value * 100).toFixed(decimal)}%`;
  if (value === 0 && format.includes('"-"')) return '-';
  const text = Math.abs(value).toLocaleString('en-US', {useGrouping:first.includes(','),minimumFractionDigits:decimal,maximumFractionDigits:decimal});
  if (value < 0) return format.includes('(') ? `(${text})` : `-${text}`;
  return text;
}
function csvLine(row) {
  return row.map(value => { const s=String(value ?? '');return /[",\r\n]/.test(s) ? `"${s.replaceAll('"','""')}"` : s; }).join(',');
}
function metadataRows(table) {
  return [[],[`Source: ${source.publisher}. ${source.sourceTitle}, ${source.editionLabel}.`],
    [`Source workbook: ${source.sourceFile}; worksheet: ${table.sheet}; range: ${table.range}.`],
    ['Static snapshot of source worksheet values. No formulas are recalculated.'],
    ['R: Revised; e: Estimate; **: Divisor is zero; totals may differ due to rounding.'],
    [`Source Excel errors retained as literal markers: ${table.errors.length}.`],
    [`Source cells marked not available for updating: ${table.unavailableCells.join(', ') || 'None'}.`]];
}
function findHeaderEnd(table, start, end) {
  if (start === 1) return table.headerEnd;
  for(let r=start;r<end;r++) {
    const row=table.rows[r];const count=row.filter(populated).length;
    if(rowYear(row))return r;
    if(table.number===18 && r>start+2 && row.some(v=>typeof v==='number') && row.some(v=>typeof v==='string' && v.trim()))return r;
    if(table.number===20 && typeof row[0]==='number' && row[0]>=1900 && row[0]<=2100)return r;
  }
  return Math.min(start+7,end);
}
function htmlGrid(table,start,end,label) {
  const rows=[];for(let r=start;r<end;r++)if(table.rows[r].some(populated))rows.push(r);
  const cols=Array.from({length:table.rows[0].length},(_,c)=>c).filter(c=>rows.some(r=>populated(table.rows[r][c])));
  const headerEnd=findHeaderEnd(table,start,end);
  const mergeMap=new Map(),covered=new Set();
  for(const [r0,r1,c0,c1] of table.merges) {
    const rs=rows.filter(r=>r>=r0 && r<r1), cs=cols.filter(c=>c>=c0 && c<c1);
    if(!rs.length || !cs.length || !rows.includes(r0) || !cols.includes(c0))continue;
    mergeMap.set(`${r0}:${c0}`,[rs.length,cs.length]);
    for(const r of rs)for(const c of cs)if(r!==r0 || c!==c0)covered.add(`${r}:${c}`);
  }
  function rowHtml(r) {
    const row=table.rows[r];const year=rowYear(row);
    return `<tr${year ? ` data-year="${year}" class="qds-year"` : ''}>`+cols.map((c,i)=>{
      if(covered.has(`${r}:${c}`))return '';
      const value=row[c],style=table.styles[r][c],text=/^Table\s*\d+\s*(?:\([Bb]\))?$/i.test(String(value ?? '').trim())?'':display(value,style.format);
      const header=r<headerEnd || (typeof value==='string' && i<=1 && populated(value));
      const tag=header?'th':'td';
      const classes=[typeof value==='number'?'qds-number':'',style.unavailable?'qds-unavailable':'',style.bold?'qds-bold':''].filter(Boolean).join(' ');
      const merge=mergeMap.get(`${r}:${c}`);
      const attrs=[classes?`class="${classes}"`:'',header?`scope="${r<headerEnd?'col':'row'}"`:'',merge?.[0]>1?`rowspan="${merge[0]}"`:'',merge?.[1]>1?`colspan="${merge[1]}"`:'',`data-source-cell="${col(c)}${r+1}"`,style.unavailable?'title="Not available for updating in the source workbook"':''].filter(Boolean).join(' ');
      return `<${tag} ${attrs}>${style.superscript?`<sup>${escape(text)}</sup>`:escape(text)}</${tag}>`;
    }).join('')+'</tr>';
  }
  const heads=rows.filter(r=>r<headerEnd),body=rows.filter(r=>r>=headerEnd);
  return `<div class="qds-table-shell" tabindex="0" role="region" aria-label="${escape(label)}; scroll to see all columns and rows"><table class="qds-grid"><caption class="sr-only">${escape(table.title)}: ${escape(label)}.</caption>${heads.length?`<thead>${heads.map(rowHtml).join('')}</thead>`:''}<tbody>${body.map(rowHtml).join('')}</tbody></table></div>`;
}
const summary=[];
for (const [index, table] of source.tables.entries()) {
  const nrows=table.rows.length,ncols=table.rows[0].length;
  if (!pagesOnly && !process.argv.includes('--keep-originals')) {
  const wb=Workbook.create(),sheet=wb.worksheets.add(table.sheet.slice(0,31));
  const used=sheet.getRangeByIndexes(0,0,nrows,ncols);
  // Literal formula/error markers are preserved as source values, not live formulas.
  used.values=table.rows.map(row=>row.map(v=>typeof v==='string' && v.startsWith('=')?`'${v}`:v));
  used.format.font={name:'Arial',size:11,color:'#222222'};
  used.format.verticalAlignment='center';used.format.rowHeight=20;used.format.wrapText=true;
  used.format.numberFormat=table.styles.map(row=>row.map(s=>s.format));
  sheet.showGridLines=false;
  const widths=table.columnWidths.map((w,c)=>table.rows.some(row=>populated(row[c]))?Math.min(44,Math.max(10,w)):3);
  widths.forEach((w,c)=>sheet.getRangeByIndexes(0,c,nrows,1).format.columnWidth=w);
  if(table.headerEnd>1)sheet.getRangeByIndexes(1,0,table.headerEnd-1,ncols).format.fill='#EEF1F3';
  const occupied=new Set();
  for(const [r0,r1,c0,c1] of table.merges){sheet.mergeCells(`${col(c0)}${r0+1}:${col(c1-1)}${r1}`);for(let r=r0;r<r1;r++)for(let c=c0;c<c1;c++)occupied.add(`${r}:${c}`);}
  for(let r=0;r<nrows;r++) {
    const countNumbers=table.rows[r].filter(v=>typeof v==='number').length;
    let height=20;
    for(let c=0;c<ncols;c++) {
      const value=table.rows[r][c],style=table.styles[r][c];
      const cell=sheet.getCell(r,c);
      if(style.bold)cell.format.font={bold:true};
      if(style.italic)cell.format.font={italic:true};
      if(style.unavailable)cell.format.fill='#E3E3E3';
      let span=1;
      if(typeof value==='string' && value.length>35 && countNumbers<2 && !occupied.has(`${r}:${c}`)){
        let end=c+1;while(end<ncols && !populated(table.rows[r][end]) && !occupied.has(`${r}:${end}`))end++;
        if(end>c+1){sheet.mergeCells(`${col(c)}${r+1}:${col(end-1)}${r+1}`);span=end-c;for(let cc=c;cc<end;cc++)occupied.add(`${r}:${cc}`);}
      }
      const originalMerge=table.merges.find(m=>m[0]===r && m[2]===c);
      if(originalMerge)span=originalMerge[3]-c;
      if(typeof value==='string' && value.trim()) {
        const chars=widths.slice(c,c+span).reduce((a,b)=>a+b,0)*.85;
        height=Math.max(height,Math.ceil(value.length/Math.max(8,chars))*15+5);
      }
    }
    sheet.getRangeByIndexes(r,0,1,ncols).format.rowHeight=Math.min(180,height);
  }
  const provenance=metadataRows(table);
  provenance.forEach((row,i)=>{
    if(!row.length)return;
    const r=nrows+1+i;sheet.mergeCells(`A${r+1}:${col(ncols-1)}${r+1}`);
    sheet.getCell(r,0).values=[[row[0]]];
    sheet.getRangeByIndexes(r,0,1,ncols).format={font:{name:'Arial',size:10,color:'#555555'},wrapText:true,rowHeight:Math.max(22,Math.ceil(row[0].length/(widths.reduce((a,b)=>a+b,0)*.8))*14)};
  });
  sheet.freezePanes.freezeRows(Math.max(1,table.headerEnd));
  wb.recalculate();
  // Check every populated source cell before export.
  const actual=used.values;
  for(let r=0;r<nrows;r++)for(let c=0;c<ncols;c++)if(populated(table.rows[r][c]) && actual[r][c]!==table.rows[r][c])throw new Error(`${table.sheet} ${col(c)}${r+1}: value changed`);
  const preview=await wb.render({sheetName:sheet.name,range:`A1:${col(ncols-1)}${Math.min(nrows,table.firstData+5)}`,scale:1,format:'png'});
  await fs.writeFile(path.join(reviewPath,`${table.slug}.png`),new Uint8Array(await preview.arrayBuffer()));
  const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(filesPath,`${table.slug}.xlsx`));
  try { await fs.rename(path.join(filesPath,`${table.slug}.xlsx.inspect.ndjson`),path.join(reviewPath,`${table.slug}.xlsx.inspect.ndjson`)); } catch(error) { if(error.code!=='ENOENT')throw error; }
  const displayed=table.rows.map((row,r)=>row.map((v,c)=>display(v,table.styles[r][c].format)));
  const csv=displayed.concat(metadataRows(table)).map(csvLine).join('\r\n')+'\r\n';
  await fs.writeFile(path.join(filesPath,`${table.slug}.csv`),'\uFEFF'+csv);
  }
  await exportTimeSeries(source,table,filesPath,reviewPath,pagesOnly);
  const percentStart=table.rows.findIndex(row=>row.some(v=>typeof v==='string' && /%\s*Change/i.test(v)));
  let notesStart=nrows;
  for(let r=Math.max(0,nrows-12);r<nrows;r++){
    if(table.rows[r].every(v=>typeof v!=='number') && table.rows[r].some(v=>typeof v==='string' && (/^\s*'?Source:/i.test(v)||/^\d+[. ]/.test(v)))){notesStart=r;break;}
  }
  const notes=table.rows.slice(notesStart).flat().filter(v=>typeof v==='string' && v.trim()).map(s=>s.trim());
  const years=[...new Set(table.rows.slice(1,percentStart<0?nrows:percentStart).map(rowYear).filter(Boolean))].sort((a,b)=>b-a);
  const yearControl=years.length>2?`<p class="qds-year-control" hidden><label for="qds-year">Jump to year</label> <select id="qds-year"><option value="">Choose a year</option>${years.map(y=>`<option>${y}</option>`).join('')}</select></p>`:'';
  const errorNote=table.errors.length?`<p class="small-note">The supplied worksheet contains ${table.errors.length} Excel error markers (${[...new Set(table.errors.map(e=>e.marker))].map(escape).join(', ')}). These are retained from the source, not recalculated or replaced with zero.</p>`:'';
  const content=`---\nlayout: default\ntitle: ${JSON.stringify(table.title)}\npermalink: ${tableUrl(table)}\ndescription: ${JSON.stringify(`${table.title}, ${source.editionLabel}. ${source.publisher}.`)}\n---\n<link rel="stylesheet" href="{{ '/assets/css/qds.css' | relative_url }}?v=20261105-ts1">\n<p><a href="/datasets/">Datasets</a> / <a href="/datasets/qds/">Quarterly statistics</a></p>\n<p class="meta">${escape(source.editionLabel)} edition · ${escape(table.subject)}</p>\n<p><a href="${dataUrl(table)}-timeseries.xlsx" download>Download Excel</a> · <a href="${dataUrl(table)}-timeseries.csv" download>Download CSV</a></p>\n<p class="small-note">${escape(table.units?`Source units: ${table.units}. `:'')}The edition is ${escape(source.editionLabel)}; individual series have different reporting dates. Historical rows and columns hidden in the supplied workbook are included.</p>\n${errorNote}\n${timeSeriesHTML(table,dataUrl(table))}\n<details class="qds-changes"><summary>Original published layout</summary><p><a href="${dataUrl(table)}.xlsx" download>Original Excel</a> · <a href="${dataUrl(table)}.csv" download>Original CSV</a> · <a href="${dataUrl(table)}-audit.csv" download>Source-cell audit (CSV)</a></p>\n<h2>Values</h2>\n${htmlGrid(table,1,percentStart<0?notesStart:percentStart,'Values')}\n${percentStart>=0?`<details class="qds-changes"><summary>Percentage changes from the source workbook</summary>${htmlGrid(table,percentStart,notesStart,'Percentage changes')}</details>`:''}\n</details>\n<h2>Source and notes</h2>\n<p>${escape(source.publisher)}. <em>${escape(source.sourceTitle)}</em>, ${escape(source.editionLabel)}. <a href="${publisherUrl}">About the official publication</a>.</p>\n<ul>${[...new Set(notes)].map(n=>`<li>${escape(n)}</li>`).join('')}</ul>\n<p class="small-note"><span class="qds-grey-key" aria-hidden="true"></span> Grey cells are marked “Not available for updating” in the source. R = revised; e = estimate; ** = divisor is zero. Totals may differ because of rounding. Original headings, blanks and markers are retained.</p>\n<p class="small-note">Original-layout CSV uses displayed values, including percent signs; original-layout Excel retains numeric values and source number formats. Excel errors are retained as literal markers in both formats. Downloads are static snapshots.</p>\n<details><summary>Source details</summary><p class="small-note">Workbook: ${escape(source.sourceFile)}<br>Worksheet: ${escape(table.sheet)}<br>Source range: ${table.range}<br>SHA-256: <code class="qds-hash">${source.sha256}</code></p></details>\n<p class="qds-navigation">${index?`<a href="${tableUrl(source.tables[index-1])}">Previous table</a> · `:''}<a href="/datasets/qds/">All tables</a>${index<source.tables.length-1?` · <a href="${tableUrl(source.tables[index+1])}">Next table</a>`:''}</p>\n<script defer src="{{ '/assets/js/qds.js' | relative_url }}?v=20261105-ts1"></script>\n`;
  await fs.writeFile(path.join(pagesPath,`${edition}-${table.slug}.html`),content);
  summary.push({slug:table.slug,title:table.title,label:table.label,subject:table.subject,sheet:table.sheet,range:table.range,units:table.units,yearLabels:table.coverage,sourceErrorCount:table.errors.length,sourceErrors:table.errors,notAvailableForUpdating:table.unavailableCells,timeSeriesVersion:table.timeSeries.version,observations:table.timeSeries.records.length,excel:`${dataUrl(table)}-timeseries.xlsx`,csv:`${dataUrl(table)}-timeseries.csv`,originalExcel:`${dataUrl(table)}.xlsx`,originalCSV:`${dataUrl(table)}.csv`,audit:`${dataUrl(table)}-audit.csv`,page:tableUrl(table)});
  console.log(`${index+1}/${source.tables.length} ${table.slug}: ${nrows} rows, ${ncols} columns exported`);
}
const manifest={publisher:source.publisher,sourceTitle:source.sourceTitle,edition:source.editionLabel,sourceFile:source.sourceFile,sourceSha256:source.sha256,dataSha256:source.dataSha256,tables:summary};
await fs.writeFile(path.join(filesPath,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const subjects=[...new Set(summary.map(t=>t.subject))].sort();
const list=summary.map(t=>`<li class="qds-entry" data-subject="${escape(t.subject)}"><h2><a href="${t.page}">${escape(t.title)}</a></h2><p class="meta">${escape(t.subject)}${t.units?` · ${escape(t.units)}`:''} · Year labels: ${escape(t.yearLabels)}</p><p><a href="${t.page}">View table</a> · <a href="${t.excel}" download>Excel</a> · <a href="${t.csv}" download>CSV</a></p></li>`).join('\n');
const catalog=`---\nlayout: default\ntitle: Quarterly statistics for Bermuda\npermalink: /datasets/qds/\ndescription: Browse and download individual statistical tables from Bermuda's Quarterly Bulletin of Statistics, ${escape(source.editionLabel)}.\n---\n<link rel="stylesheet" href="{{ '/assets/css/qds.css' | relative_url }}?v=20261105-ts1">\n<p><a href="/datasets/">All datasets</a></p>\n<p>Browse the ${source.tables.length} tables from the Department of Statistics’ <em>Quarterly Bulletin of Statistics — Annex I</em>, ${escape(source.editionLabel)}. This is the source workbook for the quarterly digest of statistics supplied by email. Each table is presented as a long-format time series: date, series name, value and units. Filter observations online or download Excel and CSV files. The original published layouts remain available on each page.</p>\n<p class="small-note">This is an independently presented archive of the supplied ${escape(source.editionLabel)} edition, not a live official data feed. Some series end earlier than the edition date. Historical rows, revision flags, source notes and existing error markers are preserved. The two employment classifications are kept separate.</p>\n<div class="qds-controls" hidden><div><label for="qds-search">Find a table</label><input id="qds-search" type="search" placeholder="e.g. tourism, prices, employment" autocomplete="off"></div><div><label for="qds-subject">Subject</label><select id="qds-subject"><option value="">All subjects</option>${subjects.map(s=>`<option>${escape(s)}</option>`).join('')}</select></div></div>\n<p id="qds-count" class="meta" aria-live="polite">${source.tables.length} tables</p>\n<p id="qds-empty" hidden>No tables match your search. Try another term or select all subjects.</p>\n<ul class="qds-catalogue">${list}</ul>\n<h2>Source and download formats</h2>\n<p>Government of Bermuda, Department of Statistics. <em>Quarterly Bulletin of Statistics — Annex I</em>, ${escape(source.editionLabel)}. <a href="${publisherUrl}">Official publication information</a>. The workbook was supplied to this site’s author through the publication mailing list.</p>\n<p>Time-series downloads use one observation per row, with numeric values, frequency, measure, classification, index base and source references. Percentage changes are kept separate from levels. Original-layout downloads retain the published headings and notes. These extracts do not recalculate or repair the original workbook’s formulas. Grey source shading means “Not available for updating”; the corresponding cell references are listed in the download notes and <a href="/assets/datasets/qds/${edition}/manifest.json">table metadata</a>.</p>\n<p class="small-note">Table extracts and web presentation by Ywione Darrell. Statistical source attribution remains with the Department of Statistics and the agencies named in each table.</p>\n<script defer src="{{ '/assets/js/qds.js' | relative_url }}?v=20261105-ts1"></script>\n`;
await fs.writeFile(path.join(pagesPath,'index.html'),catalog);
console.log(`QDS catalogue and ${source.tables.length} table pages written.`);

await fs.mkdir(path.join(sitePath, '_datasets'), { recursive: true });
await fs.writeFile(path.join(sitePath, '_datasets/quarterly-statistics.md'), `---
title: "Quarterly statistics for Bermuda"
description: ${JSON.stringify(`The Department of Statistics’ Quarterly Bulletin of Statistics, Annex I, broken into ${source.tables.length} individual table views and Excel/CSV downloads.`)}
coverage: ${JSON.stringify(`${source.editionLabel} edition; historical coverage varies by table`)}
updated: ${JSON.stringify(source.importedOn || new Date().toISOString().slice(0,10))}
source_name: ${JSON.stringify(source.publisher)}
source_url: ${JSON.stringify(publisherUrl)}
---

[Browse the ${source.tables.length} tables](/datasets/qds/), search by subject, or download an individual table in Excel or CSV format. Time-series downloads contain date, series, value and units, with frequency and source flags. Original layouts and footnotes remain available for reference.
`);

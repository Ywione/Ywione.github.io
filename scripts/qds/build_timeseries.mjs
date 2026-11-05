import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const csv = row => row.map(v => {const s=String(v ?? ''); return /[",\n\r]/.test(s)?`"${s.replaceAll('"','""')}"`:s;}).join(',');
export async function exportTimeSeries(source, table, filesPath, reviewPath, pagesOnly) {
  const ts=table.timeSeries;
  if(!ts?.records.length) throw new Error(`${table.slug}: run timeseries.py before building`);
  const stem=path.join(filesPath,`${table.slug}-timeseries`);
  await fs.writeFile(stem+'.json',JSON.stringify({title:table.title,...ts})+'\n');
  await fs.writeFile(stem+'.csv','\uFEFF'+[ts.fields,...ts.records.map(r=>ts.fields.map(k=>r[k]))].map(csv).join('\r\n')+'\r\n');
  await fs.writeFile(path.join(filesPath,`${table.slug}-audit.csv`),'\uFEFF'+[['source_cell','source_value','reason','row_context'],...ts.audit.map(r=>[r.source_cell,r.source_value,r.reason,r.row_context])].map(csv).join('\r\n')+'\r\n');
  const only=process.argv.find(a=>a.startsWith('--only='))?.slice(7);
  if(pagesOnly || (only && only!==table.slug))return;
  const wb=Workbook.create(),sheet=wb.worksheets.add('Time series'),notes=wb.worksheets.add('Source notes');
  const rows=[ts.fields,...ts.records.map(r=>ts.fields.map(k=>k==='date'?(r[k]?new Date(r[k]+'T00:00:00Z'):null):r[k]))];
  const range=sheet.getRangeByIndexes(0,0,rows.length,ts.fields.length);
  range.values=rows;
  range.format={font:{name:'Arial',size:11,color:'#222222'},rowHeight:32,verticalAlignment:'center',wrapText:true};
  const widths=[14,58,18,32,25,22,32,40,45,42,22,12,36,28,16,22,26];
  widths.forEach((w,c)=>sheet.getRangeByIndexes(0,c,rows.length,1).format.columnWidth=w);
  sheet.getRange(`A2:A${rows.length}`).setNumberFormat('yyyy-mm-dd');
  sheet.getRange(`C2:C${rows.length}`).format.numberFormat=ts.records.map(r=>[r.units==='%'?'#,##0.00':r.units.startsWith('Index')?'#,##0.0':r.units.startsWith('$')?'#,##0.00':'#,##0']);
  sheet.getRange(`P2:P${rows.length}`).setNumberFormat('0.###############');
  sheet.getRange('A1:Q1').format={fill:'#E9EEF2',font:{bold:true},rowHeight:30};
  sheet.tables.add(`A1:Q${rows.length}`,true,'Observations');
  sheet.freezePanes.freezeRows(1);sheet.showGridLines=false;
  const notesRows=[table.title,`${source.publisher}. ${source.sourceTitle}, ${source.editionLabel}.`,
    `Workbook: ${source.sourceFile}. Worksheet: ${table.sheet}.`,
    `Original layout: https://ywione.github.io/assets/datasets/qds/${source.edition}/${table.slug}.xlsx`,
    `Audit of cells outside the time series: https://ywione.github.io/assets/datasets/qds/${source.edition}/${table.slug}-audit.csv`,
    ...ts.notes,...ts.sourceNotes];
  notesRows.forEach((s,r)=>{notes.mergeCells(`A${r+1}:F${r+1}`);notes.getCell(r,0).values=[[s]];notes.getRange(`A${r+1}:F${r+1}`).format.rowHeight=Math.max(32,Math.ceil(s.length/108)*17+12);});
  notes.getRange(`A1:F${notesRows.length}`).format.font={name:'Arial',size:11,color:'#222222'};
  notes.getRange(`A1:F${notesRows.length}`).format.wrapText=true;
  notes.getRange(`A1:F${notesRows.length}`).format.columnWidth=18;
  notes.getRange('A1:F1').format={fill:'#E9EEF2',font:{bold:true}};notes.showGridLines=false;
  wb.recalculate();
  const inspection=await wb.inspect({kind:'table',range:'Time series!A1:G5',include:'values,formulas',tableMaxRows:5,tableMaxCols:7,maxChars:3000});
  await fs.writeFile(path.join(reviewPath,`${table.slug}-timeseries-inspect.ndjson`),inspection.ndjson);
  for(const [name,range,suffix] of [['Time series','A1:F12','timeseries'],['Source notes',`A1:F${Math.min(notesRows.length,15)}`,'notes']]){
    const png=await wb.render({sheetName:name,range,scale:1,format:'png'});
    await fs.writeFile(path.join(reviewPath,`${table.slug}-${suffix}.png`),new Uint8Array(await png.arrayBuffer()));
  }
  const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(stem+'.xlsx');
  try{await fs.rename(stem+'.xlsx.inspect.ndjson',path.join(reviewPath,`${table.slug}-timeseries.xlsx.inspect.ndjson`));}catch(e){if(e.code!=='ENOENT')throw e;}
}

export function timeSeriesHTML(table, url) {
  const ts=table.timeSeries;
  const shown=ts.records.filter(r=>r.measure==='Value').slice().reverse().slice(0,100);
  const cells=r=>[r.date||r.period,r.series,r.value===null?r.source_marker||'—':Number(r.value.toPrecision(12)).toLocaleString('en-US',{maximumFractionDigits:8}),r.units,r.frequency,r.classification||r.index_base,r.status+(r.availability?'; '+r.availability:'')];
  return `<h2>Time series</h2>
<p>Each row is one observation: date, series, value and units. Dates mark the end of the reported period. Annual and quarterly observations are separate; hotel employment uses reference months.</p>
${ts.notes.slice(8).map(n=>`<p class="small-note">${esc(n)}</p>`).join('')}
<div class="qds-series" data-url="${url}-timeseries.json">
<div class="qds-series-controls" hidden>
${[['series','Series'],['year','Year'],['frequency','Frequency'],['measure','Measure'],['basis','Classification / index base']].map(([id,label])=>`<div><label for="ts-${id}">${label}</label><select id="ts-${id}"><option value="">All</option></select></div>`).join('')}
</div><p id="ts-count" class="meta" aria-live="polite">Latest ${shown.length} value observations. Download the full series below.</p>
<div class="qds-table-shell" tabindex="0" role="region" aria-label="Time-series observations; scroll for more columns"><table class="qds-grid qds-long"><caption class="sr-only">${esc(table.title)} time series</caption><thead><tr>${['Date','Series','Value','Units','Frequency','Classification / base','Status'].map(s=>`<th scope="col">${s}</th>`).join('')}</tr></thead><tbody id="ts-body">${shown.map(r=>`<tr>${cells(r).map((v,i)=>`<td${i===2?' class="qds-number"':''}>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
<div class="qds-pagination" hidden><button type="button" id="ts-prev">Previous</button> <span id="ts-page"></span> <button type="button" id="ts-next">Next</button></div>
<noscript><p>Enable JavaScript to filter and page through all observations, or use the complete downloads.</p></noscript></div>
<p><a href="${url}-timeseries.xlsx" download>Download time series (Excel)</a> · <a href="${url}-timeseries.csv" download>Download time series (CSV)</a></p>
<p class="small-note">Downloads include frequency, measure, classification, index base, revision flags and source cell references. Percentage changes are published values, not recalculated. Blank or error values are not replaced by zero. CSV percentage values are numeric: 5 means 5%.</p>`;
}

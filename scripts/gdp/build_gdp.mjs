import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const [site,review]=process.argv.slice(2);
if(!site||!review)throw new Error('Usage: build_gdp.mjs SITE REVIEW_DIRECTORY');
await fs.mkdir(review,{recursive:true});
for(const kind of ['annual','quarterly']){
 const stem=path.join(site,'assets/datasets/gdp',kind+'-timeseries');
 const data=JSON.parse(await fs.readFile(stem+'.json','utf8'));
 const wb=Workbook.create(), sheet=wb.worksheets.add('Time series'), notes=wb.worksheets.add('Source notes');
 const rows=[data.fields,...data.records.map(r=>data.fields.map(k=>k==='date'?new Date(r[k]+'T00:00:00Z'):r[k]))];
 sheet.getRangeByIndexes(0,0,rows.length,data.fields.length).values=rows;
 sheet.getRange(`A1:N${rows.length}`).format={font:{name:'Arial',size:11,color:'#222222'},rowHeight:44,wrapText:true,verticalAlignment:'center'};
 [14,50,20,22,14,14,22,20,33,32,26,55,22,16].forEach((w,c)=>sheet.getRangeByIndexes(0,c,rows.length,1).format.columnWidth=w);
 sheet.getRange(`A2:A${rows.length}`).setNumberFormat('yyyy-mm-dd');
 sheet.getRange(`C2:C${rows.length}`).setNumberFormat('#,##0.000000');
 sheet.getRange('A1:N1').format={fill:'#E9EEF2',font:{bold:true},rowHeight:32};
 sheet.tables.add(`A1:N${rows.length}`,true,'Observations');sheet.freezePanes.freezeRows(1);sheet.showGridLines=false;
 const noteRows=[data.title, data.description, 'Source: Government of Bermuda, Department of Statistics; supplied bermuda-'+kind+'-gdp.xlsx.',...data.notes];
 noteRows.forEach((s,r)=>{notes.mergeCells(`A${r+1}:F${r+1}`);notes.getCell(r,0).values=[[s]];notes.getRange(`A${r+1}:F${r+1}`).format.rowHeight=Math.max(36,Math.ceil(s.length/100)*18+14);});
 notes.getRange(`A1:F${noteRows.length}`).format.font={name:'Arial',size:11,color:'#222222'};
 notes.getRange(`A1:F${noteRows.length}`).format.wrapText=true;
 notes.getRange(`A1:F${noteRows.length}`).format.columnWidth=18;
 notes.getRange('A1:F1').format={fill:'#E9EEF2',font:{bold:true}};notes.showGridLines=false;
 wb.recalculate();
 const check=await wb.inspect({kind:'table',range:'Time series!A1:F5',include:'values,formulas',tableMaxRows:5,tableMaxCols:6,maxChars:3000});
 await fs.writeFile(path.join(review,kind+'-inspect.ndjson'),check.ndjson);
 for(const [name,range] of [['Time series','A1:F12'],['Source notes','A1:F10']]){
  const png=await wb.render({sheetName:name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(review,kind+'-'+name.replaceAll(' ','-')+'.png'),new Uint8Array(await png.arrayBuffer()));
 }
 await (await SpreadsheetFile.exportXlsx(wb)).save(stem+'.xlsx');
 try{await fs.rename(stem+'.xlsx.inspect.ndjson',path.join(review,kind+'-export.ndjson'));}catch(e){if(e.code!=='ENOENT')throw e;}
 console.log(kind+': '+data.records.length+' observations exported');
}

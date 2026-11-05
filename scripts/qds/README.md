# Quarterly statistics import

The website currently contains the Q1 2026 edition of the Department of Statistics' **Quarterly Bulletin of Statistics — Annex I**, supplied as `QBS Q1 2026 Final.xls`.

## Published files

- `qds/index.html`: searchable catalogue, published at `/datasets/qds/`.
- `qds/2026-q1-table-*.html`: individual table views.
- `assets/datasets/qds/2026-q1/`: 22 Excel files, 22 CSV files and a metadata manifest.
- `_datasets/quarterly-statistics.md`: entry on the main Datasets page.
- `assets/css/qds.css` and `assets/js/qds.js`: table scrolling, search, subject filters and year navigation.

## Regeneration

Run this import through Codex using its bundled Python and Node runtimes. The extractor requires `xlrd`; the workbook exporter requires `@oai/artifact-tool`. The verifier reads the exported files with `openpyxl` and creates review images using Pillow. Do not install dependencies into the bundled runtime directories.

1. Run `extract_qds.py SOURCE.xls EXTRACT.json` in a temporary directory. It reads the original `.xls` without modifying it.
2. Run `build_qds.mjs EXTRACT.json SITE_DIRECTORY REVIEW_DIRECTORY`. This exports the table downloads and creates the pages. The review directory receives spreadsheet previews and export inspection files.
3. Run `verify_qds.py EXTRACT.json SITE_DIRECTORY REVIEW_DIRECTORY`. Every meaningful source cell and numeric format is compared with the exported workbook. Existing Excel error markers must remain unchanged, and no new live formulas are allowed.
4. Review the spreadsheet previews, run the Jekyll build and `scripts/check_site.py`, and test catalogue search, subject selection, year jumps and scrolling in a browser.
5. Commit the generated files with the scripts. Keep the input `.xls`, extracted JSON, temporary dependencies and QA previews outside the published site.

The import is explicitly configured for the supplied Q1 2026 edition. For a new edition, review worksheet names, ordering, table definitions, classification changes and source notes before adapting the edition metadata. Do not silently append or combine revised vintages.

## Data handling

- The 22 statistical worksheets are kept separate. Table 15 assets/liabilities and the two Table 18 employment classifications are not combined.
- Trailing formatting-only cells are excluded. All historical populated rows and columns, including those hidden in the source, are retained. Whitespace-only source cells may serialize as blanks.
- Excel files retain the original numeric values, number formats, source rows and cell references. Extra notes identify the source, snapshot method and unavailable-for-updating cells. Formulas are replaced by their supplied cached values; no calculations are repaired or refreshed.
- CSV files preserve the original tabulated layout and **displayed** values, including percentages, headings and notes. They are not normalized long-form datasets. Commas, quotes and line breaks are CSV-escaped. The final rows record provenance and grey-shaded source-cell references.
- The source workbook contains pre-existing `#DIV/0!`, `#REF!` and `#VALUE!` cells. These are retained as literal markers, not converted to zero or mislabeled as missing observations.
- Grey shading in the source means “Not available for updating.” It is preserved in Excel and on the web, with the source coordinates listed in CSV notes and the manifest.
- Each table page distinguishes the **Q1 2026 edition** from the dates actually reported by individual series. Source footnotes, revision flags, units and agencies remain visible.

## Initial verification

The import from source SHA-256 `cf7a382e88d3919c4cf27d9f2a86172dceead05ef8c1df213b3bd6a1a7ebc436` produced 22 table extracts. Independent checks compared 38,828 populated source cells without a value mismatch. There are 798 pre-existing source error markers.

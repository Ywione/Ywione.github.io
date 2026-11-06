# GDP datasets

Imports only `bermuda-annual-gdp.xlsx` and `bermuda-quarterly-gdp.xlsx` from `/Users/ywionedarrell/Documents/Consulting/Data`. Other files in that folder are ignored. Source files are never modified.

Run `python3 scripts/gdp/import_gdp.py --site .` with openpyxl installed, then `node scripts/gdp/build_gdp.mjs . /tmp/gdp-review` with `@oai/artifact-tool` available. The Python importer reads the saved calculation results; recalculate and save source workbooks before refreshing. Review the generated notes, coverage and provenance before publication.

Run `python3 scripts/gdp/validate_gdp.py . /Users/ywionedarrell/Documents/Consulting/Data`, build Jekyll and run `python3 scripts/check_site.py`. The validation baseline is 163 annual and 200 quarterly observations for the supplied November 2026 compilation; update these expectations deliberately when new source periods arrive.

Dates are period ends. Missing cells are omitted, percentages converted from fractions to percent values, and price bases kept separate. The original compiled workbooks are included unchanged for source links, methodology and revision history. Annual calculated growth retains both current and prior-period source IDs. No scheduled GDP refresh is installed by these scripts.

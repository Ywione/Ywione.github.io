# Quarterly statistics updates

The QBS importer reads a dedicated, locally configured source folder. It selects only top-level regular files named like `QBS Q2 2026 Final.xls` or `QBS Q2 2026 Final.xlsx`. It does not scan subfolders, follow symlinks, read unrelated datasets, or modify source workbooks. `Final`, `Revised`, numbered `Rev`/`Revision`, and duplicate-copy suffixes are supported. Drafts and Excel lock files are ignored.

The quarter/year in the filename must agree with the workbook cover. Selection uses publication quarter, never filesystem modification time. Different workbooks for the same latest quarter require review; byte-identical copies are safe. Newly written files wait until copying has settled. An older file cannot roll back the site.

## Local configuration

The installation-specific `.qbs-local.json` is gitignored and not published. It contains:

- `source_directory`: the user's QBS folder.
- `runtime_directory`: the Codex bundled dependencies directory containing `python/` and `node/`.
- `artifact_marker`: the spreadsheet skill's `container_tools/mark_artifact_operation_started.mjs`.
- `timezone`: the timezone used for import dates.

Use the Codex workspace-dependencies tool if runtime or skill locations change. The bundled Python needs `xlrd` and `openpyxl`; extra Python packages belong in the ignored `.qbs-local/python/`, never in bundled dependency directories. Local configuration, runtime dependencies, source copies, extracts, staging releases and review images stay outside the published repository.

## Check and prepare

From the repository root:

```sh
python3 scripts/qds/refresh_qbs.py --check
python3 scripts/qds/refresh_qbs.py --prepare
```

`--check` reports `unchanged`, `available`, or `needs_attention`. A source file hash detects new inputs. For a re-saved copy of the current edition, a second comparison of all extracted table values, formatting, definitions and metadata avoids a redundant release. No new edition is inferred from file modification time.

`--prepare` is a no-op for unchanged content. For a changed release it requires a clean checkout, creates an isolated `.qbs-local/release-*/site/`, preserves a private source copy, verifies the cover and contents mapping, and extracts all tables. XLSX formulas must contain saved results; missing cached results or unsupported source shading stop the import. Unknown table layouts or substantive title changes require review of `schema.json` and extraction mappings.

The maintained builder creates individual Excel/CSV downloads and table pages using the source edition, updates the catalogue and main dataset listing, and preserves previous edition directories. A revised copy of the same edition replaces that edition only; Git retains its published history. Every table keeps its source notes, revision markers and classifications. Displayed table numbering stays removed.

The preparation step marks spreadsheet authoring once, uses Artifact Tool for XLSX creation and rendering, and runs `verify_qds.py` to compare every populated source value and number format with the exported file. It writes `release.json` with the base commit and a checksum for every generated output. It does not publish anything or change the working website.

## Review, apply and publish

1. Inspect the prepared source metadata, differences from the current release, `review/verification.json`, and spreadsheet previews. Investigate source definition changes or unexpected revisions; do not silently merge classifications or repair original error markers.
2. Build Jekyll inside the prepared `site/` and run its `scripts/check_site.py`. Check representative table views and links when presentation or layout changed. Use the repository's existing build setup.
3. Apply the exact checked release:

   ```sh
   python3 scripts/qds/refresh_qbs.py --apply .qbs-local/release-EXAMPLE/release.json
   ```

   This checks that source, prepared outputs and repository head are unchanged, then copies only that edition's allowed outputs plus the catalogue and dataset listing. Prior editions and other website files are retained.
4. Publish the reviewed files together to `Ywione/Ywione.github.io`. Use the existing GitHub connector if command-line authentication is unavailable. Verify blob hashes and use the current expected head for the branch update; never force over another change. Do not upload local configuration, source workbooks, private extracts, dependencies or review images.
5. Confirm GitHub Pages deployment and public catalogue, table pages, Excel and CSV links. Synchronize the local checkout and source backup with the published commit.

The quarterly Codex check is responsible for orchestration and publishing. GitHub Pages cannot read the local source folder directly. The scheduled check needs this Mac and its local Codex environment to be available. If access, schema, source ambiguity or validation blocks an update, retain the currently published edition and report the specific issue.

## Data handling

- Preserve historical populated rows and columns, including those hidden in the source. Exclude only formatting-only trailing cells; whitespace-only cells may serialize as blanks.
- Keep separate tables for bank assets/liabilities and for the legacy and ISIC Rev. 4 employment classifications.
- Excel retains numeric values, source number formats and cell references. CSV retains the tabulated layout and displayed values, including percent signs. These original-layout files remain available alongside the primary long-format downloads.
- Use the source's saved formula results. Retain existing `#DIV/0!`, `#REF!` and `#VALUE!` markers literally, without treating them as zero.
- Preserve grey shading meaning “Not available for updating”; CSV notes and manifests record affected source coordinates.
- Distinguish the publication edition from the reporting dates actually present in each series. Do not infer current coverage from an edition date.

## Development checks

```sh
python3 -m unittest discover -s tests -p 'test_qbs_refresh.py'
```

The builder's `--pages-only` option updates pages, JSON and CSV using an already normalized source JSON file. It does not create Excel workbooks and must not be used to prepare a publication release. Never publish synthetic future-edition test output.

## Long-format time series

`timeseries.py` runs after extraction, before the builder. `timeseries-headers.json` guards the reviewed column mappings: changed headings stop publication for review. `build_timeseries.mjs` produces one observation per row in the primary Excel/CSV files and the JSON used for website filters. Each table also retains its original-layout Excel/CSV and a source-cell audit CSV.

The primary columns are date, series, value and units. Further columns retain period, frequency, measure, classification, index base, source markers, revision, availability, worksheet, cell, raw value and number format. Dates use period ends; annual dates do not claim a survey reference day. Hotel employment uses the published reference month. Percent-formatted source fractions are converted to numeric percentages. No levels, totals or growth rates are recalculated.

Missing year labels produce blank dates, and repeated observation keys are flagged as conflicting source periods. Never guess a year or choose among conflicts. Legacy and modern accommodation categories, overlapping CPI/retail bases, and employment classifications remain separate. Three identically labelled Hotels receipt columns retain their source-column identifiers. Unlabelled numeric cells and reference weights stay in the audit, not in an invented series.

`verify_timeseries.py` checks every exported Excel/CSV/JSON observation against its source cell and reconciles every numeric/error cell to either an observation or the audit. Review audit changes, missing dates and conflicts when preparing a new quarter. Website downloads and filters must be checked after deployment. The quarterly schedule and local source folder remain unchanged.

Run both source-selection and conversion regression checks:

```sh
python3 -m unittest discover -s tests -p 'test_qbs*.py'
```

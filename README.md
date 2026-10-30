# Ywione Darrell — personal website

A conventional academic Jekyll site with a profile sidebar, compact navigation and text-based pages, hosted on GitHub Pages: https://ywione.github.io.

## Update content

Edit `index.md`, `about.md`, `cv.md`, `research.md`, `datasets.md` or `writing.md` on GitHub and commit to `main`. GitHub Actions builds and deploys automatically. The CV page and downloadable PDF are based on the supplied CV. Research and dataset entries are added as they become available.

- **Add research:** copy `templates/research-entry.md` into `_research/your-paper.md`; update its title, date, status and abstract. Optional `pdf` and `code` links appear only when populated. Put PDFs in `assets/files/`.
- **Add a CV PDF:** upload `assets/files/cv.pdf`, then set `has_pdf: true` in `cv.md`.
- **Edit the bio/employer:** change `about.md` and `cv.md`.
- **Substack:** articles from `ywione.substack.com/feed` refresh on each deployment and daily at 06:17 UTC. Run “Build and deploy site” manually under Actions to refresh sooner. Failed fetches preserve cached data. GitHub may delay scheduled runs, and may disable schedules after 60 days without repository activity; re-enable the workflow under Actions if needed.
- **Theme:** defaults to the visitor’s system preference. The theme button saves a local choice. No analytics, third-party fonts or cookies are used by the site.

## GitHub Pages setup

Under **Settings → Pages**, set **Source** to **GitHub Actions**. The `pages.yml` workflow tests the feed parser, refreshes articles, builds Jekyll, checks internal links and deploys. Pull requests build and validate without deploying.

## Local preview

With a supported Ruby and Bundler installed:

```sh
bundle install
bundle exec jekyll serve
```

Then open http://localhost:4000. Verify with:

```sh
python3 -m unittest discover -s tests -v
bundle exec jekyll build
python3 scripts/check_site.py
```

The source summary and original ZIP are kept outside this repository. No sample papers or datasets are published as real work.

## Add a Bermuda dataset

1. Upload the Excel and CSV files to `assets/datasets/` on GitHub. Create the folder when uploading the first dataset. Use simple filenames, for example `bermuda-employment.xlsx` and `bermuda-employment.csv`.
2. Copy `templates/dataset-entry.md` into `_datasets/` with a descriptive filename, such as `_datasets/bermuda-employment.md`. Create this folder for the first entry.
3. Replace the title and description, fill in coverage, frequency, update date and source, then set `excel` and `csv` to the uploaded file paths. Leave a format blank if it is unavailable; its download link will be hidden.
4. Add any methodology, units, revisions or citation notes below the front matter. Optional `citation` and `license` fields can be used for a short citation and reuse terms.
5. Commit the files to `main`. The Datasets page updates automatically and lists entries alphabetically.

To update an existing dataset, replace its files and update its metadata. To remove a listing, delete its file from `_datasets/`.

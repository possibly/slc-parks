# SLC Parks CSV

This repo tracks a CSV export of City Cast Salt Lake's **Every Park SLC** map.
City Cast describes the project as a guide to Salt Lake County parks, including
amenities such as off-leash dog areas, playgrounds, splash pads, grills, courts,
and star ratings.

The scraper reads the public uMap data behind that page and writes a stable
`parks.csv` file for easier reuse than the raw map GeoJSON.

This follows Simon Willison's "git scraping" pattern: run a scraper on a schedule,
commit the data file when it changes, and use the git history as a lightweight
changelog over time.

## Usage

```bash
python scrape_slc_parks.py
```

GitHub Actions runs the scraper weekly and commits `parks.csv` if it changed.

## GitHub Pages

`index.html` is a no-build GitHub Pages front end for `parks.csv`. It loads the
CSV in the browser and adds search, city/rating filters, amenity filters, and a
CSV download link.

Pages is deployed by `.github/workflows/pages.yml` on every push to `main`.
Configure the repository's Pages source to **GitHub Actions**.

# michelin-map

**Every restaurant on the MICHELIN Guide, on one map you can open on your phone.**

A public scrape of `guide.michelin.com` — all 19,506 restaurants worldwide across every distinction (3-Star, 2-Star, 1-Star, Bib Gourmand, Green Star, and Selected/Plate) — packaged as CSVs and a KML file you can drop into Google My Maps in 30 seconds.

## What you get

- 📍 **Exact coordinates** for every restaurant (from Michelin's own JSON-LD, not a geocoding guess)
- 🔗 **Direct link** to the MICHELIN Guide page for each restaurant (tap on the pin → open the page on your phone)
- 🏷️ Distinction tier, cuisine, price band, year awarded, phone, address, description, reservations info, menu language, currencies + payment methods accepted, photo URL
- 🗂️ Split into per-tier layers so you can toggle 3-Stars vs everything else

Files live in [`outputs/`](outputs/):

| File | What it is |
| --- | --- |
| `michelin_all.csv` | Master spreadsheet, 24 columns, every restaurant |
| `gmaps_3-star.csv` … `gmaps_selected_partN.csv` | Per-tier CSVs sized for the Google My Maps 2,000-row-per-layer limit |
| `michelin.kml` | One-shot import — creates a folder per tier with colored pins and rich popups |

## 30-second setup: put it in Google My Maps

1. Go to [mymaps.google.com](https://www.google.com/maps/d/) → **Create a new map**
2. **Import** → drag in [`outputs/michelin.kml`](outputs/michelin.kml)
3. Done. Every tier is a separate layer with colored pins.
4. **View on phone:** Google Maps app → **You** → **Maps** → tap the map. Pins are tappable; the MICHELIN link opens in your browser.

If you'd rather build the map layer-by-layer, import each `gmaps_*.csv` separately and pick `lat`, `lng` as position columns.

## Fields

Every row includes: `name, tier, cuisine, price, star_rating, year_awarded, review_date, city, region, country, postal_code, street, address, lat, lng, phone, url, gmap_url, image, accepts_reservations, menu_language, currencies_accepted, payment_accepted, description`.

## Run it yourself

Requires Python 3.11+ and `curl_cffi`.

```bash
pip install curl_cffi

# Phase 1 — enumerate all restaurant URLs (~14 min, 407 list pages)
python scrape_michelin.py enumerate

# Or scope to a single country
python scrape_michelin.py enumerate --country france

# Phase 2 — fetch each restaurant's JSON-LD (2-3 hrs global, resumable)
python scrape_michelin.py fetch --workers 3 --delay 1.0

# Convert scraped JSONL to CSVs + KML
python build_outputs.py
```

The scraper is fully resumable — `data/restaurants.jsonl` is append-only, and re-running `fetch` picks up any URLs that aren't already done.

## How the scraper works

- The main list at `guide.michelin.com/gb/en/restaurants` is paginated (`/page/N`) with ~50 unique URLs per page across ~407 pages.
- Each restaurant page embeds a schema.org `Restaurant` JSON-LD `<script>` tag with everything above — no headless browser or JS execution needed.
- **Cloudflare bypass:** `curl_cffi` impersonating Safari 17 gets through. Chrome fingerprints are blocked; Safari is not.
- Rate limits are respected: 1.5–2s per list page, 3 concurrent workers with 1s per-request delay, exponential backoff on 202/challenge responses, and a single-threaded retry pass at the end for anything that failed the first time.

## Refreshing

Michelin updates rankings a few times per year. To refresh:

```bash
rm data/restaurants.jsonl data/urls.txt   # or keep to only fetch new URLs
python scrape_michelin.py enumerate
python scrape_michelin.py fetch
python build_outputs.py
```

## Data license

Code: MIT (see `LICENSE`).
Data: © MICHELIN, redistributed here for personal reference. If you build something on top, respect [MICHELIN's Terms of Use](https://guide.michelin.com/en/terms) and link back to the original guide.

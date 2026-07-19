# michelin-map

**Every restaurant on the MICHELIN Guide, on one map you can open on your phone.**

All 19,506 restaurants worldwide across every distinction — 3-Star, 2-Star, 1-Star, Bib Gourmand, Green Star, and Selected/Plate — as CSVs and a KML file you drop into Google My Maps in 30 seconds.

## What you get

- 📍 **Exact coordinates** for every restaurant
- 🔗 **Direct link** to the MICHELIN Guide page for each one (tap on the pin → opens on your phone)
- 🏷️ Distinction tier, cuisine, price band, year awarded, phone, address, description, reservations info, menu language, currencies + payment methods accepted, photo URL
- 🗂️ Split into per-tier layers so you can toggle 3-Stars vs everything else

Files live in [`outputs/`](outputs/):

| File | What it is |
| --- | --- |
| `michelin_all.csv` | Master spreadsheet, 24 columns, every restaurant |
| `gmaps_3-star.csv` … `gmaps_selected_partN.csv` | Per-tier CSVs sized for Google My Maps' 2,000-row-per-layer limit |
| `michelin.kml` | One-shot import — creates a folder per tier with colored pins and rich popups |

## 30-second setup: put it in Google My Maps

1. Go to [mymaps.google.com](https://www.google.com/maps/d/) → **Create a new map**
2. **Import** → drag in [`outputs/michelin.kml`](outputs/michelin.kml)
3. Done. Every tier is a separate layer with colored pins.
4. **View on phone:** Google Maps app → **You** → **Maps** → tap the map. Pins are tappable; the MICHELIN link opens in your browser.

Prefer to build the map layer-by-layer? Import each `gmaps_*.csv` separately and pick `lat`, `lng` as position columns.

## Fields

Every row includes:

`name`, `tier`, `cuisine`, `price`, `star_rating`, `year_awarded`, `review_date`, `city`, `region`, `country`, `postal_code`, `street`, `address`, `lat`, `lng`, `phone`, `url`, `gmap_url`, `image`, `accepts_reservations`, `menu_language`, `currencies_accepted`, `payment_accepted`, `description`

## License

Code: MIT (see `LICENSE`).
Data: © MICHELIN. Redistributed here for personal reference. If you build something on top, respect [MICHELIN's Terms of Use](https://guide.michelin.com/en/terms) and link back to the original guide.

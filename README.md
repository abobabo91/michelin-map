# michelin-map

**Every restaurant on the MICHELIN Guide, on one map you can open on your phone.**

All **19,505 restaurants worldwide** across every distinction, with exact coordinates and a link back to each restaurant's MICHELIN page.

| Tier | Count |
| --- | ---: |
| ⭐⭐⭐ 3 Star | 161 |
| ⭐⭐ 2 Star | 543 |
| ⭐ 1 Star | 3,172 |
| 🍽️ Bib Gourmand | 3,700 |
| 🥄 Selected / Plate | 11,929 |

Coverage: 52 countries. Top 5: France 3,054 · Italy 1,992 · USA 1,788 · Spain 1,328 · Germany 1,242.

## What you get

- 📍 **Exact coordinates** for every restaurant (from Michelin's own data, not a geocoding guess)
- 🔗 **Direct link** to the MICHELIN Guide page for each one (tap on the pin → opens on your phone)
- 🏷️ Distinction tier, cuisine, price band, year awarded, phone, address, description, reservations info, menu language, currencies + payment methods accepted, photo URL
- 🗂️ Colored pins per tier, toggleable as layers

## Fastest way: Google Earth (one file, everything)

Google Earth handles the full 19,505 pins in a single file.

1. Install **Google Earth** ([earth.google.com/web](https://earth.google.com/web/) — browser, no install; or the free desktop app; or the mobile app)
2. **File → Import → KML** and pick [`outputs/michelin.kml`](outputs/michelin.kml)
3. Done. Toggle tiers on/off in the sidebar, tap a pin to see the popup + link.

## Google My Maps (5 separate maps because of size limits)

Google My Maps caps you at 10,000 features per map and 5 MB per file, so the 19k pins have to be split into 5 maps. Each import creates one:

| File | Pins | Map to create |
| --- | ---: | --- |
| [`outputs/gmaps_kml_stars.kml`](outputs/gmaps_kml_stars.kml) | 3,876 | **MICHELIN Stars** |
| [`outputs/gmaps_kml_bib-gourmand.kml`](outputs/gmaps_kml_bib-gourmand.kml) | 3,700 | **Bib Gourmand** |
| [`outputs/gmaps_kml_selected_part1.kml`](outputs/gmaps_kml_selected_part1.kml) | 4,000 | **Selected (part 1)** |
| [`outputs/gmaps_kml_selected_part2.kml`](outputs/gmaps_kml_selected_part2.kml) | 4,000 | **Selected (part 2)** |
| [`outputs/gmaps_kml_selected_part3.kml`](outputs/gmaps_kml_selected_part3.kml) | 3,929 | **Selected (part 3)** |

For each: [mymaps.google.com](https://www.google.com/maps/d/) → **Create a new map** → **Import** → drop the file.
**On your phone:** Google Maps app → **You** → **Maps** → tap any imported map.

## Spreadsheet view

If you'd rather browse the whole list as a table, download [`outputs/michelin_all.csv`](outputs/michelin_all.csv) — 19,505 rows, 24 columns:

`name, tier, cuisine, price, star_rating, year_awarded, review_date, city, region, country, postal_code, street, address, lat, lng, phone, url, gmap_url, image, accepts_reservations, menu_language, currencies_accepted, payment_accepted, description`

Per-tier CSVs (`outputs/gmaps_<tier>.csv`) are also there if you want to import individual tiers into Google My Maps and pick `lat`/`lng` as position columns manually.

## License

Code: MIT (see [`LICENSE`](LICENSE)).
Data: © MICHELIN. Redistributed here for personal reference. If you build something on top, respect [MICHELIN's Terms of Use](https://guide.michelin.com/en/terms) and link back to the original guide.

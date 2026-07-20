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

Google Earth handles the full 19,505 pins in a single file, and it's on iOS/Android/desktop/web.

1. **Google Earth** — [earth.google.com/web](https://earth.google.com/web/) (browser, no install), or the free desktop / mobile apps
2. **Projects → New → Import KML file** → pick [`outputs/michelin.kml`](outputs/michelin.kml)
3. Done. Toggle tiers on/off in the sidebar, tap a pin to see the popup + link.

## Google My Maps — one map per region

Google My Maps caps you at 10,000 features and 5 MB per map, so the 19k pins are pre-split into regional KMLs. Each one imports cleanly into one map.

| Region | File | Pins |
| --- | --- | ---: |
| France & Monaco | [`outputs/gmaps_kml_france-monaco.kml`](outputs/gmaps_kml_france-monaco.kml) | 3,070 |
| Italy & Malta | [`outputs/gmaps_kml_italy-malta.kml`](outputs/gmaps_kml_italy-malta.kml) | 2,039 |
| Iberia (Spain, Portugal, Andorra) | [`outputs/gmaps_kml_iberia.kml`](outputs/gmaps_kml_iberia.kml) | 1,540 |
| UK & Ireland | [`outputs/gmaps_kml_uk-ireland.kml`](outputs/gmaps_kml_uk-ireland.kml) | 1,241 |
| DACH (Germany, Austria, Switzerland, Liechtenstein) | [`outputs/gmaps_kml_dach.kml`](outputs/gmaps_kml_dach.kml) | 2,201 |
| Benelux (Belgium, Netherlands, Luxembourg) | [`outputs/gmaps_kml_benelux.kml`](outputs/gmaps_kml_benelux.kml) | 1,258 |
| Rest of Europe (Nordics, Baltics, Central & Eastern, Balkans, Greece, Turkey) | [`outputs/gmaps_kml_europe-rest.kml`](outputs/gmaps_kml_europe-rest.kml) | 1,150 |
| Asia, Middle East & New Zealand | [`outputs/gmaps_kml_asia-mideast.kml`](outputs/gmaps_kml_asia-mideast.kml) | 4,463 |
| Americas (USA, Canada, Mexico, Brazil, Argentina) | [`outputs/gmaps_kml_americas.kml`](outputs/gmaps_kml_americas.kml) | 2,543 |

For each: [mymaps.google.com](https://www.google.com/maps/d/) → **Create a new map** → **Import** → drop the file. Inside each region the pins are grouped by tier (3-Star, 2-Star, 1-Star, Bib Gourmand, Selected) so you can toggle them independently.

**On your phone:** Google Maps app → **You** → **Maps** → tap any imported map. Pins are tappable; the MICHELIN link opens in your browser.

## Spreadsheet view

If you'd rather browse the whole list as a table, download [`outputs/michelin_all.csv`](outputs/michelin_all.csv) — 19,505 rows, 24 columns:

`name, tier, cuisine, price, star_rating, year_awarded, review_date, city, region, country, postal_code, street, address, lat, lng, phone, url, gmap_url, image, accepts_reservations, menu_language, currencies_accepted, payment_accepted, description`

Per-tier CSVs (`outputs/gmaps_<tier>.csv`) are also there if you want to import individual tiers instead of individual regions.

## License

Code: MIT (see [`LICENSE`](LICENSE)).
Data: © MICHELIN. Redistributed here for personal reference. If you build something on top, respect [MICHELIN's Terms of Use](https://guide.michelin.com/en/terms) and link back to the original guide.

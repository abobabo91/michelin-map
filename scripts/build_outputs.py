"""
Convert data/restaurants.jsonl into user-facing outputs:

- outputs/michelin_all.csv          Master spreadsheet, all fields, all tiers.
- outputs/gmaps_3-star.csv          Per-tier CSVs sized for Google My Maps
- outputs/gmaps_2-star.csv          import (each stays under the 2,000 rows /
- outputs/gmaps_1-star.csv          layer limit; if a tier exceeds 2k, it is
- outputs/gmaps_bib-gourmand.csv    split into multiple parts).
- outputs/gmaps_selected_partN.csv
- outputs/michelin.kml              Single KML: pins categorized by <Folder>
                                    (Google My Maps import).

Run after scraper is done:
    python build_outputs.py
"""

import csv
import json
import re
from collections import defaultdict, Counter
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "data" / "restaurants.jsonl"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

GMAPS_LAYER_CAP = 2000

TIER_ORDER = ["3 Star", "2 Star", "1 Star", "Bib Gourmand", "Selected", "Green Star"]
TIER_COLORS = {
    "3 Star": "ff0000ff",       # red
    "2 Star": "ff0080ff",       # orange
    "1 Star": "ff00d7ff",       # gold
    "Bib Gourmand": "ff00a5ff", # amber-ish
    "Selected": "ff787878",     # gray
    "Green Star": "ff00ff00",   # green
}


def tier_from_award(award) -> str:
    """Normalize Michelin's various 'award' strings/objects to a compact tier label."""
    if not award:
        return "Selected"
    s = award.get("awardFor", "") if isinstance(award, dict) else str(award)
    s_low = s.lower()
    if "three star" in s_low or "3 star" in s_low or "three michelin" in s_low:
        return "3 Star"
    if "two star" in s_low or "2 star" in s_low or "two michelin" in s_low:
        return "2 Star"
    if "one star" in s_low or "1 star" in s_low or "one michelin" in s_low:
        return "1 Star"
    if "bib gourmand" in s_low:
        return "Bib Gourmand"
    if "green star" in s_low:
        return "Green Star"
    if "selected" in s_low or "good cooking" in s_low or "plate" in s_low:
        return "Selected"
    return "Selected"


def get(obj, *keys, default=""):
    for k in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k, default if k == keys[-1] else {})
    return obj if obj else default


def flatten(rec: dict) -> dict:
    addr = rec.get("address", {}) or {}
    award = rec.get("award") or {}
    tier = tier_from_award(award)

    lat = rec.get("latitude")
    lng = rec.get("longitude")

    address_parts = [
        addr.get("streetAddress"),
        addr.get("addressLocality"),
        addr.get("addressRegion"),
        addr.get("postalCode"),
        addr.get("addressCountry"),
    ]
    address_full = ", ".join(p for p in address_parts if p)

    description = get(rec, "review", "description") or ""
    description = re.sub(r"\s+", " ", description).strip()

    year_awarded = ""
    if isinstance(award, dict):
        year_awarded = str(award.get("dateAwarded") or "")

    review_date = get(rec, "review", "datePublished") or ""

    image = rec.get("image") or ""
    if isinstance(image, list):
        image = image[0] if image else ""

    return {
        "name": rec.get("name", "").strip(),
        "tier": tier,
        "cuisine": rec.get("servesCuisine", "") or "",
        "price": rec.get("priceRange", "") or "",
        "star_rating": rec.get("starRating", "") or "",
        "year_awarded": year_awarded,
        "review_date": review_date,
        "city": addr.get("addressLocality", ""),
        "region": addr.get("addressRegion", ""),
        "country": addr.get("addressCountry", ""),
        "postal_code": addr.get("postalCode", ""),
        "street": addr.get("streetAddress", ""),
        "address": address_full,
        "lat": lat,
        "lng": lng,
        "phone": rec.get("telephone", "") or "",
        "url": rec.get("url") or rec.get("_source_url", ""),
        "gmap_url": rec.get("hasMap", "") or "",
        "image": image,
        "accepts_reservations": rec.get("acceptsReservations", "") or "",
        "menu_language": rec.get("knowsLanguage", "") or "",
        "currencies_accepted": rec.get("currenciesAccepted", "") or "",
        "payment_accepted": rec.get("paymentAccepted", "") or "",
        "description": description,
    }


def load_all() -> list[dict]:
    if not JSONL.exists():
        raise SystemExit(f"Missing {JSONL}. Run scrape_michelin.py first.")
    rows = []
    seen = set()
    with JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            flat = flatten(rec)
            key = flat["url"] or f"{flat['name']}|{flat['lat']}|{flat['lng']}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(flat)
    return rows


# ---------- Outputs ----------

def write_master_csv(rows: list[dict]) -> None:
    path = OUT / "michelin_all.csv"
    fields = [
        "name", "tier", "cuisine", "price", "star_rating", "year_awarded", "review_date",
        "city", "region", "country", "postal_code", "street", "address",
        "lat", "lng", "phone", "url", "gmap_url", "image",
        "accepts_reservations", "menu_language", "currencies_accepted", "payment_accepted",
        "description",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"[csv] {path.name}: {len(rows)} rows")


def write_gmaps_csvs(by_tier: dict[str, list[dict]]) -> None:
    """One CSV per tier (or per 2000-row chunk if tier > 2000).

    Google My Maps CSV import expects: name + address OR lat/lng columns.
    We include everything; the user picks lat/lng as location cols on import.
    """
    fields = ["name", "tier", "cuisine", "price", "year_awarded", "city", "country",
              "address", "lat", "lng", "phone", "url", "image",
              "accepts_reservations", "description"]
    for tier in TIER_ORDER:
        rows = by_tier.get(tier, [])
        if not rows:
            continue
        chunks = [rows[i:i + GMAPS_LAYER_CAP] for i in range(0, len(rows), GMAPS_LAYER_CAP)]
        for idx, chunk in enumerate(chunks, 1):
            suffix = f"_part{idx}" if len(chunks) > 1 else ""
            slug = tier.lower().replace(" ", "-")
            path = OUT / f"gmaps_{slug}{suffix}.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for r in chunk:
                    w.writerow({k: r.get(k, "") for k in fields})
            print(f"[gmaps] {path.name}: {len(chunk)} rows")


def write_kml(by_tier: dict[str, list[dict]]) -> None:
    """Single KML with one <Folder> per tier — a colored pin style each.

    Google My Maps supports KML import; folders become layers.
    """
    path = OUT / "michelin.kml"
    with path.open("w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
        f.write("<Document>\n")
        f.write("<name>MICHELIN Guide restaurants</name>\n")
        for tier, color in TIER_COLORS.items():
            f.write(f'<Style id="s-{tier.replace(" ", "-")}">\n')
            f.write("  <IconStyle>\n")
            f.write(f"    <color>{color}</color><scale>1.0</scale>\n")
            f.write('    <Icon><href>http://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href></Icon>\n')
            f.write("  </IconStyle>\n")
            f.write("</Style>\n")
        for tier in TIER_ORDER:
            rows = by_tier.get(tier, [])
            if not rows:
                continue
            f.write(f"<Folder><name>{escape(tier)} ({len(rows)})</name>\n")
            for r in rows:
                try:
                    lat = float(r["lat"]); lng = float(r["lng"])
                except (TypeError, ValueError):
                    continue
                name = escape(r["name"] or "(unnamed)")
                city = escape(r.get("city", ""))
                country = escape(r.get("country", ""))
                cuisine = escape(r.get("cuisine", ""))
                price = escape(r.get("price", ""))
                url = escape(r.get("url", ""))
                phone = escape(r.get("phone", ""))
                year = escape(str(r.get("year_awarded", "")))
                reserv = escape(r.get("accepts_reservations", ""))
                image = escape(r.get("image", ""))
                short_desc = escape((r.get("description") or "")[:220])

                img_html = f"<img src='{image}' width='240'><br>" if image else ""
                year_html = f" &middot; awarded {year}" if year else ""
                phone_html = f"<br>{phone}" if phone else ""
                reserv_html = f"<br>Reservations: {reserv}" if reserv else ""
                desc = (
                    f"<![CDATA[{img_html}"
                    f"<b>{tier}</b>{year_html} &middot; {cuisine} &middot; {price}<br>"
                    f"{city}, {country}"
                    f"{phone_html}{reserv_html}<br>"
                    f"<a href='{url}'>MICHELIN Guide page</a><br><br>"
                    f"<i>{short_desc}</i>]]>"
                )
                f.write("<Placemark>\n")
                f.write(f"  <name>{name}</name>\n")
                f.write(f'  <styleUrl>#s-{tier.replace(" ", "-")}</styleUrl>\n')
                f.write(f"  <description>{desc}</description>\n")
                f.write(f"  <Point><coordinates>{lng},{lat},0</coordinates></Point>\n")
                f.write("</Placemark>\n")
            f.write("</Folder>\n")
        f.write("</Document></kml>\n")
    print(f"[kml] {path.name}")


def main() -> None:
    rows = load_all()
    print(f"[load] {len(rows)} unique restaurants")

    tiers = Counter(r["tier"] for r in rows)
    countries = Counter(r["country"] for r in rows)
    missing_coords = sum(1 for r in rows if not r["lat"] or not r["lng"])
    print("[stats] tiers:", dict(tiers))
    print(f"[stats] countries: {len(countries)} distinct — top 10: "
          f"{countries.most_common(10)}")
    print(f"[stats] missing coordinates: {missing_coords}")

    by_tier: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_tier[r["tier"]].append(r)

    write_master_csv(rows)
    write_gmaps_csvs(by_tier)
    write_kml(by_tier)


if __name__ == "__main__":
    main()

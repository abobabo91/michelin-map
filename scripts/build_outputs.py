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


def _placemark(tier: str, r: dict) -> str:
    try:
        lat = float(r["lat"]); lng = float(r["lng"])
    except (TypeError, ValueError):
        return ""
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
    return (
        "<Placemark>\n"
        f"  <name>{name}</name>\n"
        f'  <styleUrl>#s-{tier.replace(" ", "-")}</styleUrl>\n'
        f"  <description>{desc}</description>\n"
        f"  <Point><coordinates>{lng},{lat},0</coordinates></Point>\n"
        "</Placemark>\n"
    )


def _write_kml(path: Path, doc_name: str, tier_folders: list[tuple[str, list[dict]]]) -> None:
    """Write a KML with one <Folder> per (tier_label, rows) tuple.

    tier_label is the human-readable folder label ("1 Star", "1 Star (part 1)", …).
    The styling <styleUrl> derives from the first token, so parts share the same pin color.
    """
    with path.open("w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
        f.write(f"<Document>\n<name>{escape(doc_name)}</name>\n")
        for base_tier, color in TIER_COLORS.items():
            f.write(f'<Style id="s-{base_tier.replace(" ", "-")}">\n')
            f.write("  <IconStyle>\n")
            f.write(f"    <color>{color}</color><scale>1.0</scale>\n")
            f.write('    <Icon><href>http://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href></Icon>\n')
            f.write("  </IconStyle>\n")
            f.write("</Style>\n")
        for folder_label, rows in tier_folders:
            base_tier = folder_label.split(" (")[0]  # "1 Star (part 1)" -> "1 Star"
            f.write(f"<Folder><name>{escape(folder_label)} ({len(rows)})</name>\n")
            for r in rows:
                f.write(_placemark(base_tier, r))
            f.write("</Folder>\n")
        f.write("</Document></kml>\n")
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"[kml] {path.name}: {sum(len(rs) for _, rs in tier_folders)} pins, {size_mb:.1f} MB")


def _folders_from(by_tier: dict[str, list[dict]], tiers: list[str], layer_cap: int) -> list[tuple[str, list[dict]]]:
    """Split each tier into <=layer_cap layers, in TIER_ORDER, skipping empties."""
    folders: list[tuple[str, list[dict]]] = []
    for tier in tiers:
        rows = by_tier.get(tier, [])
        if not rows:
            continue
        if len(rows) <= layer_cap:
            folders.append((tier, rows))
        else:
            for i, start in enumerate(range(0, len(rows), layer_cap), 1):
                folders.append((f"{tier} (part {i})", rows[start:start + layer_cap]))
    return folders


def write_kmls(by_tier: dict[str, list[dict]]) -> None:
    """Emit:
    - michelin.kml                  everything, single file (Google Earth, GIS)
    - gmaps_kml_stars.kml           3+2+1 stars — fits one Google My Maps
    - gmaps_kml_bib-gourmand.kml    Bib Gourmand only
    - gmaps_kml_selected_partN.kml  Selected, split so each < ~5 MB / < 10k features
    """
    # Master (unrestricted).
    all_folders = _folders_from(by_tier, TIER_ORDER, layer_cap=2000)
    _write_kml(OUT / "michelin.kml", "MICHELIN Guide — all restaurants", all_folders)

    # Stars (3+2+1) — 3,876 total, easily under Google My Maps' 10k features / 5 MB.
    stars_folders = _folders_from(by_tier, ["3 Star", "2 Star", "1 Star"], layer_cap=2000)
    _write_kml(OUT / "gmaps_kml_stars.kml", "MICHELIN Stars", stars_folders)

    # Bib Gourmand alone — ~3.7k, one map with 2 layers.
    bib_folders = _folders_from(by_tier, ["Bib Gourmand"], layer_cap=2000)
    if bib_folders:
        _write_kml(OUT / "gmaps_kml_bib-gourmand.kml", "MICHELIN Bib Gourmand", bib_folders)

    # Selected tier — huge. Split into ~4k / map so each stays under 5 MB and
    # under 10k features. Layers still capped at 2000.
    selected = by_tier.get("Selected", [])
    MAP_CAP = 4000  # per file, before layer split
    parts = [selected[i:i + MAP_CAP] for i in range(0, len(selected), MAP_CAP)]
    for i, chunk in enumerate(parts, 1):
        pseudo = {"Selected": chunk}
        chunk_folders = _folders_from(pseudo, ["Selected"], layer_cap=2000)
        _write_kml(
            OUT / f"gmaps_kml_selected_part{i}.kml",
            f"MICHELIN Selected (part {i}/{len(parts)})",
            chunk_folders,
        )


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
    write_kmls(by_tier)


if __name__ == "__main__":
    main()

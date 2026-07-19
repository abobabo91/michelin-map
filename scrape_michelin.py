"""
Scrape the entire MICHELIN Guide restaurant catalog.

Phase 1: enumerate restaurant URLs from paginated global list.
Phase 2: fetch each restaurant page, extract JSON-LD (name, lat/lng, tier, cuisine, address, ...).

Resumable — reads/writes progress files under ./data/ .

Usage:
    python scrape_michelin.py enumerate                       # global (407 pages)
    python scrape_michelin.py enumerate --country singapore-region
    python scrape_michelin.py fetch                           # fetch every URL in urls.txt
    python scrape_michelin.py fetch --limit N
"""

import argparse
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from curl_cffi import requests

# Unbuffered stdout so progress lines show up live under `tee`.
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

BASE = "https://guide.michelin.com"
LIST_URL = f"{BASE}/gb/en/restaurants"
IMPERSONATE = "safari17_0"

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

URLS_FILE = DATA / "urls.txt"
JSONL_FILE = DATA / "restaurants.jsonl"
FAILED_FILE = DATA / "failed.txt"

REST_HREF_RE = re.compile(r'href="(/gb/en/[^"]+/restaurant/[^"?#]+)"')
LDJSON_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)
PAGE_NUM_RE = re.compile(r'href="/gb/en/[^"]*restaurants/page/(\d+)"')


def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def get(session: requests.Session, url: str, tries: int = 6) -> str | None:
    """GET with retry + Cloudflare-challenge backoff. Returns HTML text or None.

    We only accept 200 with a plausibly-sized body. 202/challenge pages are ~2 KB.
    Backoff is exponential + jittered so retries don't sync up when many workers
    hit a wall at once.
    """
    for attempt in range(tries):
        try:
            r = session.get(url, impersonate=IMPERSONATE, timeout=30)
            if r.status_code == 200 and len(r.text) > 3000:
                return r.text
            wait = min(60, 4 * (2 ** attempt)) + random.uniform(0, 2)
            time.sleep(wait)
        except Exception as e:
            wait = min(60, 5 * (2 ** attempt)) + random.uniform(0, 2)
            print(f"    ! {url}: {type(e).__name__}: {e} — sleep {wait:.1f}s", flush=True)
            time.sleep(wait)
    return None


# ---------- Phase 1: enumerate ----------

def find_last_page(html: str) -> int:
    """Look at /gb/en/restaurants for pagination href numbers, return max."""
    nums = [int(n) for n in PAGE_NUM_RE.findall(html)]
    return max(nums) if nums else 1


def urls_on_page(html: str) -> set[str]:
    hrefs = REST_HREF_RE.findall(html)
    return {BASE + h for h in hrefs}


def enumerate_all(country: str | None = None, urls_out: Path | None = None) -> None:
    session = new_session()
    root = f"{BASE}/gb/en/{country}/restaurants" if country else LIST_URL
    out = urls_out or URLS_FILE
    # In country mode, only accept URLs whose path starts with that country slug —
    # list pages also include "you might also like" cards from elsewhere.
    country_prefix = f"/gb/en/{country}/" if country else None
    print(f"[enumerate] loading {root} ...")
    html = get(session, root)
    if not html:
        raise SystemExit("Could not load initial list page — Cloudflare?")
    last = find_last_page(html)
    print(f"[enumerate] last page = {last}")

    def keep(u: str) -> bool:
        return not country_prefix or country_prefix in u

    all_urls: set[str] = {u for u in urls_on_page(html) if keep(u)}
    print(f"[enumerate] page 1: cumulative {len(all_urls)} unique", flush=True)
    failed_pages: list[int] = []

    for n in range(2, last + 1):
        page_url = f"{root}/page/{n}"
        html = get(session, page_url)
        if not html:
            print(f"[enumerate] page {n}: FAILED — will retry at end", flush=True)
            failed_pages.append(n)
            time.sleep(5)  # extra cool-down after a failure
            continue
        page_urls = {u for u in urls_on_page(html) if keep(u)}
        all_urls |= page_urls
        if n % 5 == 0 or n == last:
            print(f"[enumerate] page {n}/{last}: cumulative {len(all_urls)} unique", flush=True)
        if n % 25 == 0:
            out.write_text("\n".join(sorted(all_urls)), encoding="utf-8")
        # 1.5s ± jitter to stay under Cloudflare's rate ceiling.
        time.sleep(1.5 + random.uniform(0, 0.7))

    # Retry pass — one more crack at pages that 202'd.
    if failed_pages:
        print(f"[enumerate] retrying {len(failed_pages)} failed page(s) with longer sleep", flush=True)
        time.sleep(10)
        session = new_session()
        for n in failed_pages[:]:
            html = get(session, f"{root}/page/{n}", tries=8)
            if html:
                page_urls = {u for u in urls_on_page(html) if keep(u)}
                all_urls |= page_urls
                failed_pages.remove(n)
                print(f"[enumerate] retry page {n}: cumulative {len(all_urls)} unique", flush=True)
            else:
                print(f"[enumerate] retry page {n}: STILL FAILED", flush=True)
            time.sleep(4 + random.uniform(0, 2))

    out.write_text("\n".join(sorted(all_urls)), encoding="utf-8")
    if failed_pages:
        (out.parent / "enumerate_failed_pages.txt").write_text(
            "\n".join(map(str, failed_pages)), encoding="utf-8"
        )
    print(
        f"[enumerate] DONE — {len(all_urls)} unique URLs, "
        f"{len(failed_pages)} page(s) unrecoverable -> {out}",
        flush=True,
    )


# ---------- Phase 2: fetch details ----------

def load_completed() -> set[str]:
    if not JSONL_FILE.exists():
        return set()
    done: set[str] = set()
    with JSONL_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if u := obj.get("_source_url"):
                    done.add(u)
            except Exception:
                pass
    return done


def fetch_one(url: str, per_request_delay: float = 0.0) -> dict | None:
    # Small per-worker jitter so all N workers don't hit Michelin in lockstep.
    if per_request_delay > 0:
        time.sleep(per_request_delay + random.uniform(0, per_request_delay))
    session = new_session()
    html = get(session, url)
    if not html:
        return None
    m = LDJSON_RE.search(html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None
    data["_source_url"] = url
    return data


def fetch_details(limit: int | None, workers: int, per_request_delay: float) -> None:
    if not URLS_FILE.exists():
        raise SystemExit(f"No URL file. Run: python {sys.argv[0]} enumerate first.")
    urls = [u for u in URLS_FILE.read_text(encoding="utf-8").splitlines() if u.strip()]
    completed = load_completed()
    pending = [u for u in urls if u not in completed]
    if limit is not None:
        pending = pending[:limit]
    print(
        f"[fetch] {len(urls)} total, {len(completed)} already done, "
        f"{len(pending)} to fetch — {workers} workers, {per_request_delay:.1f}s per-req delay",
        flush=True,
    )

    failed: list[str] = []
    ok = 0
    t0 = time.time()

    with JSONL_FILE.open("a", encoding="utf-8") as jf:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_one, u, per_request_delay): u for u in pending}
            for i, fut in enumerate(as_completed(futs), 1):
                url = futs[fut]
                try:
                    obj = fut.result()
                except Exception as e:
                    obj = None
                    print(f"    [{i}] EXC {url}: {e}", flush=True)
                if obj is None:
                    failed.append(url)
                else:
                    jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    ok += 1
                if i % 50 == 0:
                    jf.flush()
                    dt = time.time() - t0
                    rate = i / dt if dt else 0
                    remain = (len(pending) - i) / rate if rate else 0
                    print(
                        f"[fetch] {i}/{len(pending)} — ok={ok} fail={len(failed)} "
                        f"— {rate:.2f}/s — ETA {remain/60:.1f} min",
                        flush=True,
                    )

    # Retry pass — failed URLs get a second chance with a fresh single-threaded pass,
    # slower cadence, more tries per URL.
    if failed:
        print(f"[fetch] retrying {len(failed)} failed URL(s) single-threaded", flush=True)
        still_failed: list[str] = []
        with JSONL_FILE.open("a", encoding="utf-8") as jf:
            for i, u in enumerate(failed, 1):
                obj = fetch_one(u, per_request_delay=0.0)
                if obj is None:
                    # Try once more with a longer delay
                    time.sleep(8)
                    obj = fetch_one(u, per_request_delay=0.0)
                if obj is None:
                    still_failed.append(u)
                else:
                    jf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    ok += 1
                if i % 25 == 0:
                    jf.flush()
                    print(f"[fetch/retry] {i}/{len(failed)} — recovered {len(failed)-len(still_failed)-max(0,len(failed)-i)}, still-failing {len(still_failed)}", flush=True)
                time.sleep(2 + random.uniform(0, 2))
        failed = still_failed

    if failed:
        FAILED_FILE.write_text("\n".join(failed), encoding="utf-8")
        print(f"[fetch] {len(failed)} unrecoverable -> {FAILED_FILE}", flush=True)
    print(f"[fetch] DONE — {ok} ok, {len(failed)} failed, {time.time()-t0:.0f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enumerate")
    e.add_argument("--country", type=str, default=None,
                   help="Country slug (e.g. singapore-region, japan, france). Omit = global.")
    f = sub.add_parser("fetch")
    f.add_argument("--limit", type=int, default=None)
    f.add_argument("--workers", type=int, default=3,
                   help="Concurrent workers. Lower = less likely to trip Cloudflare. Default 3.")
    f.add_argument("--delay", type=float, default=1.0,
                   help="Per-request base delay per worker (jittered up to 2x). Default 1.0s.")
    args = ap.parse_args()

    if args.cmd == "enumerate":
        enumerate_all(country=args.country)
    elif args.cmd == "fetch":
        fetch_details(args.limit, args.workers, args.delay)


if __name__ == "__main__":
    main()

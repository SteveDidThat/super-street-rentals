#!/usr/bin/env python3
"""
Super Street Rentals - auction listing ingester (prototype, READ-ONLY).

Pulls PUBLIC listing data (no login, no bidding, no purchasing) from sources that
served public pages during research on 2026-10-18:
  * Bring a Trailer  - /auctions/ page embeds `auctionsCurrentInitialData` JSON
  * PCARMARKET       - /auctions server-rendered cards (end time is relative -> approx)
  * IAA (iaai.com)   - /Vehiclelisting/<Make> and /Vehiclelisting/RentalRides/<Make>
                       public SEO listing pages (first page only; bids require login)
Blocked / not used: Copart (Incapsula 403), Cars & Bids (signed API, JS-only),
eBay Motors (robots + use the official Browse API instead), Manheim/ADESA/ACV (dealer login).

Outputs (paths relative to this file):
  exotic_listings.csv/.json, rental_listings.csv/.json, feed.json, site/feed.json

Be polite: 1-2 s between requests, identify yourself, respect robots.txt, and get
written permission / a partner feed before using this commercially (see data_pipeline_plan.md).
Usage:  python3 fetch_listings.py [--out DIR]
"""
import csv, html, json, os, re, sys, time, argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import urllib.request

ET = ZoneInfo("America/New_York")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124 Safari/537.36 SuperStreetRentals-research/0.1")
DELAY = 1.5

EXOTIC_RE = re.compile(
    r"Ferrari|Lamborghini|McLaren|Aston Martin|Rolls-Royce|Bentley|Bugatti|Pagani|Koenigsegg|"
    r"Lotus|Ford GT\b|Viper|NSX|Lexus LFA|\bLFA\b|MC20|Maserati GranTurismo|Audi R8|\bR8\b|GT-R|GTR\b|"
    r"Z06|ZR1|Corvette E-Ray|SLS AMG|AMG GT|Mercedes-AMG GT|SL ?65|Carrera GT|\b918\b|"
    r"Porsche 911 (Turbo|GT2|GT3|GT)|Porsche 911 .*(Turbo|GT2|GT3)|\bGT2 RS|\bGT3|Cayman GT4|Spyder RS|Turbo S|\b930\b|"
    r"Shelby (GT500|Super Snake|GT350)", re.I)
NON_CAR_RE = re.compile(r"wheels|seats|luggage|manual|engine\b|display model|arcade|go-kart|"
                        r"memorabilia|parts|\bOEM\b|PCCB|\bset\b|literature|watch|poster|sign\b|model car|tool kit", re.I)
RENTAL_TEXT_RE = re.compile(r"\bHertz\b|\bSixt\b|\bAvis\b|Enterprise Rent|Budget Rent|"
                            r"rental (car|fleet|company|unit|program)|ex-rental|former rental|\bGT-H\b|GT350H|Dream Collection|Rent-A-Racer", re.I)
SPORTY_RE = re.compile(r"\bM[2345]\b|\bM[2-8]\d\d|M60I|M50I|\bAMG\b|\bC ?63|\bE ?63|MUSTANG|CAMARO|CORVETTE|CHARGER|"
                       r"CHALLENGER|PORSCHE|CAYMAN|BOXSTER|911|G70|GV60 PERFORMANCE|\bRS ?\d|\bS[45] |CT[45]-?V|"
                       r"RANGE ROVER|DEFENDER|SUPRA|GR86|WRX|GOLF R|GTI|MACAN|SHELBY|GT500|SCAT|HELLCAT|ROADSTER|CONVERTIBLE|"
                       r"BRONCO|WRANGLER RUBICON|TESLA MODEL S|LUCID|ESCALADE|GLS|X6|X7|740I|COUPE", re.I)
TZ_OFF = {"EDT": -4, "EST": -5, "CDT": -5, "CST": -6, "MDT": -6, "MST": -7, "PDT": -7, "PST": -8,
          "AKDT": -8, "AKST": -9, "HST": -10, "AST": -4, "ADT": -3}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")

def now_utc():
    return datetime.now(timezone.utc)

def iso_et(dt):
    return dt.astimezone(ET).strftime("%Y-%m-%d %I:%M %p ET") if dt else ""

def parse_ymm(title):
    t = html.unescape(title)
    m = re.search(r"\b(19[0-9]{2}|20[0-3][0-9])(?:\.5)?\s+([A-Za-z][\w\-]*(?:\s(?:Martin|Royce|Benz|Rover|Romeo))?)\s+(.+)", t)
    if not m:
        return None, None, None
    return int(m.group(1)), m.group(2).title() if m.group(2).isupper() else m.group(2), m.group(3).strip()

def miles_from_title(t):
    m = re.search(r"([\d,\.]+)(k?)-Mile", t)
    if m:
        n = float(m.group(1).replace(",", ""))
        return int(n * 1000) if m.group(2) else int(n)
    m = re.search(r"([\d,\.]+)(k?)-Kilometer", t)
    if m:
        n = float(m.group(1).replace(",", ""))
        return f"{int(n*1000) if m.group(2) else int(n)} km"
    return None

def rec(**kw):
    base = dict(id="", source="", category="", title="", year=None, make=None, model=None,
                current_bid=None, current_bid_text="", currency="USD", bid_count=None,
                end_time_utc="", end_time_et="", end_time_is_approx=False, location="",
                mileage=None, damage="", title_status="", rental_evidence="", sporty=None,
                image_url="", url="", access="", fetched_at_et="", notes="")
    base.update(kw)
    return base

# ---------------------------------------------------------------- Bring a Trailer
def fetch_bat():
    h = get("https://bringatrailer.com/auctions/")
    key = "auctionsCurrentInitialData = "
    i = h.find(key)
    if i < 0:
        raise RuntimeError("BaT: embedded JSON not found (page layout changed)")
    data, _ = json.JSONDecoder().raw_decode(h[i + len(key):])
    out = []
    for x in data.get("items", []):
        title = html.unescape(x.get("title", ""))
        if not x.get("year") or NON_CAR_RE.search(title):
            continue
        excerpt = html.unescape(x.get("excerpt") or "")
        is_exotic = bool(EXOTIC_RE.search(title))
        rental_hit = RENTAL_TEXT_RE.search(title + " " + excerpt)
        if not (is_exotic or rental_hit):
            continue
        end = datetime.fromtimestamp(int(x["timestamp_end"]), timezone.utc) if x.get("timestamp_end") else None
        y, mk, mo = parse_ymm(title)
        base = dict(id=f"bat-{x.get('id')}", source="Bring a Trailer", title=title, year=y, make=mk, model=mo,
                    current_bid=x.get("current_bid"), current_bid_text=html.unescape(x.get("current_bid_formatted") or ""),
                    currency=x.get("currency") or "USD", end_time_utc=end.isoformat() if end else "", end_time_et=iso_et(end),
                    location=x.get("country") or "", mileage=miles_from_title(title),
                    image_url=x.get("thumbnail_url") or "", url=x.get("url") or "",
                    access="Public (free BaT account + credit card on file to bid; 5% buyer fee, $250 min / $7,500 max)",
                    notes=("No Reserve. " if x.get("noreserve") else "") + "Location detail on listing page.")
        if is_exotic:
            out.append(rec(category="exotic", **base))
        if rental_hit:
            out.append(rec(category="rental", rental_evidence=f"BaT listing text mentions: '{rental_hit.group(0)}' (verify on listing)",
                           sporty=True, **{**base, "id": base["id"] + "-r"}))
    return out

# ---------------------------------------------------------------- PCARMARKET
def parse_rel(s):
    m = re.match(r"(\d+)D (\d+)H (\d+)M", s.strip())
    return timedelta(days=int(m.group(1)), hours=int(m.group(2)), minutes=int(m.group(3))) if m else None

def fetch_pcar():
    h = get("https://www.pcarmarket.com/auctions")
    fetched = now_utc()
    out = []
    for u, b in re.findall(r'<li><a href="(/auction/[^"]+)"[^>]*>(.*?)</a></li>', h, re.S):
        img = re.search(r'<img[^>]*src="([^"]+)"', b)
        t = re.sub(r"<svg.*?</svg>", "", b, flags=re.S)
        parts = [html.unescape(p).strip() for p in re.sub(r"<[^>]+>", "|", t).split("|") if p.strip()]
        try:
            bid = parts[parts.index("Current bid") + 1]
            title = parts[parts.index("Current bid") + 2]
            loc = parts[parts.index("Current bid") + 3]
        except (ValueError, IndexError):
            continue
        bids = next((p for p in parts if p.endswith("Bids") or p.endswith("Bid")), "")
        rels = [p for p in parts if re.match(r"\d+D \d+H \d+M", p)]
        delta = next((parse_rel(r) for r in reversed(rels) if parse_rel(r) and parse_rel(r).total_seconds() > 0), None)
        end = fetched + delta if delta else None
        if NON_CAR_RE.search(title) or not EXOTIC_RE.search(title + " " + u):
            continue
        y, mk, mo = parse_ymm(title)
        out.append(rec(id="pcar-" + u.rsplit("/", 1)[-1], source="PCARMARKET", category="exotic", title=title,
                       year=y, make=mk, model=mo, current_bid=float(re.sub(r"[^\d.]", "", bid) or 0) or None,
                       current_bid_text=bid, bid_count=int(re.sub(r"\D", "", bids) or 0) if bids else None,
                       end_time_utc=end.isoformat() if end else "", end_time_et=iso_et(end), end_time_is_approx=True,
                       location=loc, mileage=miles_from_title(title), image_url=html.unescape(img.group(1)) if img else "",
                       url="https://www.pcarmarket.com" + u,
                       access="Public (free account + card verification to bid; buyer's fee per PCARMARKET terms)",
                       notes="End time computed from 'Ends in' countdown at fetch time (+/- 1 min)."))
    return out

# ---------------------------------------------------------------- IAA
IAA_EXOTIC_MAKES = ["Ferrari", "Lamborghini", "McLaren", "Aston%20Martin", "Bentley", "Rolls-Royce",
                    "Lotus", "Porsche", "Maserati"]
IAA_RENTAL_MAKES = ["", "Chevrolet", "Ford", "Dodge", "BMW", "Mercedes-Benz", "Land%20Rover", "Genesis", "Tesla"]

def parse_iaa_date(s, ref):
    m = re.search(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\w{3}) (\d{1,2}), (\d{1,2}):(\d{2})(am|pm) ([A-Z]{2,4})", s)
    if not m:
        return None
    mon = datetime.strptime(m.group(2), "%b").month
    hr = int(m.group(4)) % 12 + (12 if m.group(6) == "pm" else 0)
    off = TZ_OFF.get(m.group(7), -5)
    yr = ref.year + (1 if mon < ref.month - 6 else 0)
    return datetime(yr, mon, int(m.group(3)), hr, int(m.group(5)), tzinfo=timezone(timedelta(hours=off)))

def parse_iaa_page(h, category, ref):
    out = []
    starts = [m.start() for m in re.finditer(r'<h4[^>]*><a href="/VehicleDetail/', h)]
    for k, s in enumerate(starts):
        blk = h[s: starts[k + 1] if k + 1 < len(starts) else s + 20000]
        pre = h[max(0, s - 2500): s]
        vid = re.search(r'/VehicleDetail/([^"]+)"', blk).group(1)
        title = html.unescape(re.search(r'>([^<]+)</a>', blk).group(1)).strip()
        title = re.sub(r"\s+", " ", title)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", blk))
        cells = [c.strip() for c in txt.split("|") if c.strip()]
        def attr(lbl):
            m = re.search(r'title="' + re.escape(lbl) + r':\s*([^"]*)"', blk)
            return html.unescape(m.group(1)).strip() if m else ""
        odo = re.search(r"([\d,]+) mi\b", txt)
        loc = next((c for c in cells if re.match(r"^[A-Z][\w .'/&\-]+ \([A-Za-z .]+\)$", c)), "")
        acv_i = max([i for i, c in enumerate(cells) if c == "ACV:"] or [0])
        tail = cells[acv_i:]
        dates = [parse_iaa_date(c, ref) for c in tail if parse_iaa_date(c, ref)]
        end = dates[0] if dates else None
        unassigned = any("Auction Not Assigned" in c for c in tail)
        buy_now = next((c for c in tail if c.startswith("Buy Now")), "")
        acv = next((cells[i + 1] for i, c in enumerate(cells) if c == "ACV:" and i + 1 < len(cells)), "")
        img = ["https://vis.iaai.com/resizer?imageKeys=" + vid + "~SID~I1&width=400&height=300"]
        y, mk, mo = parse_ymm(title)
        sporty = bool(SPORTY_RE.search(title))
        out.append(rec(id="iaa-" + vid.replace("~", "-"), source="IAA (Insurance Auto Auctions)", category=category,
                       title=title.title(), year=y, make=mk, model=mo, current_bid=None,
                       current_bid_text=(buy_now + " / " if buy_now else "") + ("Auction date not yet assigned" if unassigned and not end else "Pre-bid open - live bid visible to registered IAA buyers only"),
                       end_time_utc=end.astimezone(timezone.utc).isoformat() if end else "",
                       end_time_et=iso_et(end), location=loc, mileage=int(odo.group(1).replace(",", "")) if odo else None,
                       damage=attr("Primary Damage"), title_status=attr("Title/Sale Doc"),
                       rental_evidence="Listed in IAA 'Rental Vehicles' (RentalRides) category" if category == "rental" else "",
                       sporty=sporty if category == "rental" else None,
                       image_url=html.unescape(img[-1]) if img else "",
                       url="https://www.iaai.com/VehicleDetail/" + vid,
                       access="IAA buyer account; most lots need a dealer license or a registered broker (e.g. a licensed IAA broker) for public buyers",
                       notes=("End time = scheduled IAA live-auction start for the lot. " if end else "Upcoming: IAA has not assigned a sale date yet. ")
                             + (f"IAA ACV (actual cash value est.): {acv}. " if acv and acv != "$0 USD" else "")
                             + ("Odometer shows 1 = likely exempt/unknown. " if odo and odo.group(1) == "1" else "")))
    return out

def fetch_iaa():
    ref = now_utc()
    out, seen = [], set()
    for mk in IAA_EXOTIC_MAKES:
        for r in parse_iaa_page(get(f"https://www.iaai.com/Vehiclelisting/{mk}"), "exotic", ref):
            if mk in ("Porsche", "Maserati") and not EXOTIC_RE.search("Porsche " + r["title"] if mk == "Porsche" else r["title"]):
                if not re.search(r"911|GT3|GT2|TURBO|CAYMAN GT4|MC20|GRANTURISMO", r["title"], re.I):
                    continue
            if r["id"] not in seen:
                seen.add(r["id"]); out.append(r)
        time.sleep(DELAY)
    for mk in IAA_RENTAL_MAKES:
        path = "RentalRides" + ("/" + mk if mk else "")
        for r in parse_iaa_page(get(f"https://www.iaai.com/Vehiclelisting/{path}"), "rental", ref):
            if r["id"] not in seen:
                seen.add(r["id"]); out.append(r)
        time.sleep(DELAY)
    return out

# ---------------------------------------------------------------- main
FIELDS = list(rec().keys())

def write(rows, base, outdir):
    with open(os.path.join(outdir, base + ".json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    with open(os.path.join(outdir, base + ".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--site", default=None, help="site dir to write feed.json into (default OUT/site)")
    a = ap.parse_args()
    site = a.site or os.path.join(a.out, "site")
    rows, status = [], {}
    for name, fn in [("bringatrailer", fetch_bat), ("pcarmarket", fetch_pcar), ("iaa", fetch_iaa)]:
        try:
            r = fn(); rows += r; status[name] = {"ok": True, "count": len(r)}
        except Exception as e:  # keep going if one source breaks
            status[name] = {"ok": False, "error": str(e)[:300]}
        time.sleep(DELAY)
    for name, why in {"copart": "Incapsula bot protection (HTTP 403). Use Copart broker/member data access or a licensed data partner.",
                      "carsandbids": "JS app; API requires signed session token. Ask C&B for a partner/affiliate feed.",
                      "ebay_motors": "robots.txt prohibits scraping; use official eBay Browse API (free developer key)."}.items():
        status[name] = {"ok": False, "skipped": why}
    nowu = now_utc()
    stamp = iso_et(nowu)
    keep = []
    for r in rows:
        r["fetched_at_et"] = stamp
        if r["end_time_utc"]:
            if datetime.fromisoformat(r["end_time_utc"]) < nowu:  # already ended
                continue
        keep.append(r)
    keep.sort(key=lambda r: r["end_time_utc"] or "9999")
    exotic = [r for r in keep if r["category"] == "exotic"]
    rental = sorted([r for r in keep if r["category"] == "rental"], key=lambda r: (not r["sporty"], r["end_time_utc"] or "9999"))
    os.makedirs(site, exist_ok=True)
    write(exotic, "exotic_listings", a.out)
    write(rental, "rental_listings", a.out)
    feed = {"generated_at_utc": nowu.isoformat(), "generated_at_et": stamp, "sources": status,
            "disclaimer": "Listings are aggregated from third-party public auction pages for information only. "
                          "Super Street Rentals is an independent broker, not affiliated with these auction sites. "
                          "Bids/end times change constantly - always confirm on the source listing.",
            "counts": {"exotic": len(exotic), "rental": len(rental)},
            "listings": exotic + rental}
    for p in (os.path.join(a.out, "feed.json"), os.path.join(site, "feed.json")):
        with open(p, "w") as f:
            json.dump(feed, f, indent=1, default=str)
    print(json.dumps({"counts": feed["counts"], "sources": status}, indent=1))

if __name__ == "__main__":
    main()

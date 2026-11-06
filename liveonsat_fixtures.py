#!/usr/bin/env python3
"""liveonsat_fixtures.py - real start times for sports our other sources don't cover (6 Nov 2026).

Reads a few of liveonsat.com's sport pages (rugby union, rugby league, Aussie rules, boxing / fighting) a few times a day and writes
liveonsat_fixtures.json: [{sport, comp, a, b, start (UTC), stan}].
A second set of pages - football (UK / Ireland, UEFA, the big leagues, MLS, women's, international) - goes to liveonsat_football.json,
with each match's list of channels, for the reference page fixtures.html (6 Nov 2026). That file is NOT read by event_epg.py. event_epg.py reads that file as the last place to look for a match's
real kick-off (Stan, Peacock, Paramount+, Soccer PPV streams carry the time the STREAM opens, which is 10-55 minutes before it).

* The page shows its times in a time zone of its own choosing (the runner got America/Chicago; a browser in New York got New York) and
  marks the selected one in a list - read every run and converted to UTC; no marker = that page is skipped.
* One request per page, 4 seconds apart, a browser-like User-Agent; a small hobby site, so nothing more.
* A page that fails (or suddenly yields nothing where it had data) keeps its previous fixtures. Nothing found at all = the file is not touched.
* Fixtures older than 12 hours are dropped.

    python3 liveonsat_fixtures.py            # -> liveonsat_fixtures.json + liveonsat_football.json (fixed names)
"""
import html, json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OUT = "liveonsat_fixtures.json"
OUT_FOOTBALL = "liveonsat_football.json"
BASE = "https://liveonsat.com/"
PAGES = {"Rugby Union": "x-rugby-union.php", "Rugby League": "x-rugby-league.php", "Aussie Rules": "x-aussie-rules.php",
         "Boxing / Fighting": "x-boxing-mma.php"}
FOOTBALL_PAGES = {
    "English Premier League": "uk-england-premier-league.php", "English ex-Premier League": "uk-england-ex-premiership.php",
    "UK cup competitions": "uk-cup-competitions-all.php", "Scotland": "uk-scotland-premiership.php",
    "Ireland / Wales": "uk-wales-ireland-all-football.php",
    "UEFA Champions League": "club-uefa-champions-league.php", "UEFA Europa League": "club-uefa-europa-league.php",
    "UEFA Conference League": "club-uefa-europa-conference-league.php",
    "Germany Bundesliga": "europe-germany-bundesliga1.php", "Italy Serie A": "europe-italy-serie-a.php",
    "Spain La Liga": "europe-spain-laliga.php", "France": "europe-france-all-football.php",
    "International": "international-all-football.php", "MLS": "americas-mls.php", "Women's football": "womens-televised-football.php",
}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15 Version/17.0 Safari/605.1.15",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-GB,en;q=0.9"}
DAY = re.compile(r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (\d{1,2})(?:st|nd|rd|th) (\w+)$")
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                      "October", "November", "December"], 1)}
FIXTURE = re.compile(r"^(.{2,70}?) v (.{2,70})$")
ST = re.compile(r"^ST:\s*(\d{1,2}):(\d{2})$")


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        print(f"  {url}: {e}")
        return 0, ""


def tokens(page):
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    page = re.sub(r"(?i)</?(td|tr|p|br|div|li|h\d|table|a|span|b|strong)[^>]*>", "\n", page)
    page = re.sub(r"<[^>]+>", " ", page)
    out = []
    for line in html.unescape(page).split("\n"):
        t = re.sub(r"\s+", " ", line).strip()
        if t:
            out.append(t)
    return out


def zone_of(page):
    c = re.findall(r"selected[^>]*>\s*\(GMT\s*[+-]\d\d:\d\d\)\s*([A-Za-z_]+/[A-Za-z_/]+)", page)
    c += re.findall(r"\*\s*\(GMT\s*[+-]\d\d:\d\d\)\s*([A-Za-z_]+/[A-Za-z_/]+)", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    for name in c:
        try:
            return ZoneInfo(name), name
        except Exception:
            continue
    return None, None


def clean_channel(t):
    """"Premier Sports 2 Ireland HD [$/geo/R] 📺" -> "Premier Sports 2 Ireland HD" (the flags in brackets and the TV emoji go)"""
    t = re.sub(r"\s*\[[^\]]*\]|\s*\([^)]*geo/R[^)]*\)|📺", "", t)
    return re.sub(r"\s+", " ", t).strip(" |")


def parse(page, tz, now, with_channels=False):
    toks = tokens(page)
    date, out, cur = None, [], None
    for i, t in enumerate(toks):
        m = DAY.match(t)
        if m and m.group(2) in MONTHS:
            mo = MONTHS[m.group(2)]
            year = now.year + (1 if mo < now.month - 6 else 0)           # a January date read in December
            date = (year, mo, int(m.group(1)))
            cur = None
            continue
        m = ST.match(t)
        if m and date:
            a = b = comp = ""
            for back in range(1, 7):
                f = FIXTURE.match(toks[i - back]) if i - back >= 0 else None
                if f:
                    a, b = f.group(1).strip(), f.group(2).strip()
                    comp = toks[i - back - 1] if i - back - 1 >= 0 else ""
                    break
            try:
                start = datetime(*date, int(m.group(1)), int(m.group(2)), tzinfo=tz).astimezone(timezone.utc)
            except ValueError:
                cur = None
                continue
            cur = {"comp": comp, "a": a, "b": b, "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "stan": False}
            if with_channels:
                cur["ch"] = []
            out.append(cur)
            continue
        if cur is None:
            continue
        if "Stan Sport" in t:
            cur["stan"] = True
        if with_channels:
            # a fixture's channel list ends where the next fixture begins: its competition line is followed at once by its "A v B" line
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if FIXTURE.match(t) or FIXTURE.match(nxt):
                cur = None
                continue
            name = clean_channel(t)
            if name and len(name) < 60 and name not in cur["ch"] and not name.startswith("(GMT") and name not in ("|", "---"):
                cur["ch"].append(name)
    return [f for f in out if f["a"] and f["b"]]


def read_pages(pages, out_path, with_channels, now):
    """fetch `pages` once each (4 s apart), keep a failing page's earlier fixtures, write out_path. Returns the fixture count."""
    old = {}
    try:
        with open(out_path, encoding="utf-8") as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        pass
    old_by_sport = {}
    for f in old.get("fixtures", []):
        old_by_sport.setdefault(f["sport"], []).append(f)
    info, fixtures = {}, []
    for sport, path in pages.items():
        status, body = fetch(BASE + path)
        tz, zname = zone_of(body) if status == 200 else (None, None)
        got = parse(body, tz, now, with_channels) if tz else []
        for f in got:
            f["sport"] = sport
        prev = old_by_sport.get(sport, [])
        if status != 200 or not tz or (not got and len(prev) > 5):
            why = f"HTTP {status}" if status != 200 else ("no time zone marker" if not tz else "found nothing (had data) - parser change?")
            print(f"  {sport}: {why} - keeping {len(prev)} earlier fixture(s)")
            fixtures += prev
            info[sport] = {"status": status, "kept": len(prev)}
        else:
            extra = "" if with_channels else f" ({sum(1 for g in got if g['stan'])} on Stan Sport)"
            print(f"  {sport}: HTTP 200, zone {zname}, {len(got)} fixtures{extra}")
            if not got and body:
                print("    no fixtures parsed - first text pieces:", [t for t in tokens(body) if len(t) < 90][:40])
            fixtures += got
            info[sport] = {"status": 200, "zone": zname, "count": len(got)}
        time.sleep(4)
    cutoff = (now - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fixtures = [f for f in fixtures if f["start"] >= cutoff]
    if with_channels:                       # the same match is on several pages: one entry, all channels
        merged = {}
        for f in fixtures:
            key = (re.sub(r"\W+", "", f["a"].lower()), re.sub(r"\W+", "", f["b"].lower()), f["start"])
            if key in merged:
                for c in f.get("ch", []):
                    if c not in merged[key]["ch"]:
                        merged[key]["ch"].append(c)
            else:
                merged[key] = dict(f)
        fixtures = list(merged.values())
        for f in fixtures:
            f["ch"].sort(key=str.lower)
    fixtures.sort(key=lambda f: f["start"])
    if not fixtures and not old.get("fixtures"):
        print(f"  nothing found - {out_path} not written")
        return 0
    data = {"fetched": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "pages": info, "fixtures": fixtures}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=None if with_channels else 1, separators=(",", ":") if with_channels else None)
    print(f"  wrote {out_path}: {len(fixtures)} fixtures")
    return len(fixtures)


def main():
    now = datetime.now(timezone.utc)
    read_pages(PAGES, OUT, False, now)
    read_pages(FOOTBALL_PAGES, OUT_FOOTBALL, True, now)
    return 0


if __name__ == "__main__":
    sys.exit(main())

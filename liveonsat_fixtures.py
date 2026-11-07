#!/usr/bin/env python3
"""liveonsat_fixtures.py - real start times for sports our other sources don't cover (6 Nov 2026).

Reads a few of liveonsat.com's sport pages (rugby union, rugby league, Aussie rules, boxing / fighting) a few times a day and writes
liveonsat_fixtures.json: [{sport, comp, a, b, start (UTC), stan}].
A second set of pages - ALL football, one request per day of liveonsat.com's "2day.php" - goes into the SAME file under the key
"football": {fetched, pages, fixtures} with each match's list of channels, for the reference page fixtures.html (6 Nov 2026). It travels in
liveonsat_fixtures.json so the existing workflow commits it; event_epg.py reads only "fixtures" and ignores "football". event_epg.py reads that file as the last place to look for a match's
real kick-off (Stan, Peacock, Paramount+, Soccer PPV streams carry the time the STREAM opens, which is 10-55 minutes before it).

* The page shows its times in a time zone of its own choosing (the runner got America/Chicago; a browser in New York got New York) and
  marks the selected one in a list - read every run and converted to UTC; no marker = that page is skipped.
* One request per page, 4 seconds apart, a browser-like User-Agent; a small hobby site, so nothing more.
* A page that fails (or suddenly yields nothing where it had data) keeps its previous fixtures. Nothing found at all = the file is not touched.
* Fixtures older than 12 hours are dropped.

    python3 liveonsat_fixtures.py            # -> liveonsat_fixtures.json (fixed name)
"""
import html, json, re, sys, time, urllib.request, urllib.error
from html.parser import HTMLParser
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OUT = "liveonsat_fixtures.json"
BASE = "https://liveonsat.com/"
PAGES = {"Rugby Union": "x-rugby-union.php", "Rugby League": "x-rugby-league.php", "Aussie Rules": "x-aussie-rules.php",
         "Boxing / Fighting": "x-boxing-mma.php"}
FOOTBALL_DAYS_BACK, FOOTBALL_DAYS_AHEAD = 0, 6      # football reference: one request per day of liveonsat.com's all-football "2day.php"


def football_pages(now):
    """{label: path}: 2day.php for each day from yesterday to 6 days ahead (the page's own time zone cuts the days a few hours
    from UK ones; yesterday's page comes back empty, so it starts with today). All football - every competition."""
    base = now.astimezone(ZoneInfo("America/Chicago")).date()
    out = {}
    for n in range(-FOOTBALL_DAYS_BACK, FOOTBALL_DAYS_AHEAD + 1):
        d = base + timedelta(days=n)
        out[f"Football {d.isoformat()}"] = (f"2day.php?start_dd={d:%d}&start_mm={d:%m}&start_yyyy={d:%Y}"
                                            f"&end_dd={d:%d}&end_mm={d:%m}&end_yyyy={d:%Y}")
    return out


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


_JUNK = re.compile(
    r"^(?:encryption|freq|pos|satellite|symbol|LiveOnSat\.com|Download APP|0|0\.000|0\.0°|-|\d+(?:\.\d+)?\s?[HV]|\d+(?:\.\d+)?°-?[ew]?|"
    r"\d{4,5}\s*-?\s*\d/\d+|\d+(?:\.\d+)?\s*[LR]|\d+(?:\.\d+)?\s*-|Satellite Feeds)$|^\*|"
    r"(?i:\b(?:Astra|Eutelsat|Hotbird|Intelsat|Hispasat|Hellas Sat|Turksat|Measat|Koreasat|KazSat|Eshail|AzerSpace|Telstar|Thor [567]|"
    r"Express (?:AMU|AT|AM)\d*|ABS \d+[A-Z]?|BulgariaSat|Exset|Bulcrypt|Seca|Nilesat|Yamal|Arabsat|Badr|Thaicom|AsiaSat|Optus|Insat|Amos|"
    r"MonacoSat|Express AMU|Dror 1|VideoGuard|Irdeto|Conax|NagraVision|Nagra|Viaccess|Cryptoworks|Mediaguard|Verimatrix|Biss|"
    r"TrophyAccess|Tongfang|MPEG-4|Free To Air|FTA)\b)")
POSTPONED = re.compile(r"(?i)p-?o-?s-?t-?p-?o-?n-?e-?d|\bcancel+ed\b|\babandoned\b")


class PageParser(HTMLParser):
    """liveonsat.com's own markup (seen in the raw HTML on 7 Nov 2026):
      <span class=comp_head>English Premier League - Week 10</span>
      <div class=fLeft style="width:270px..">Arsenal v Hull City</div>
      <div class="fLeft_time_live dynamic-time" data-timestamp="1794063600"> ST: 09:00 </div>     (UNIX time, UTC - no zone guessing)
      <a class=chan_live_not_free onmouseover="return overlib('<table>..satellite details..</table>',CAPTION,'..')">Arena M1 HD </a>
    The satellite table sits inside the link's onmouseover ATTRIBUTE, so a text-only reading mistook it for channels; this reads the
    link text. Channels are kept only for the group whose ST is the match's first start (delayed / repeat groups are ignored)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fixtures, self.comp, self.cur = [], "", None
        self.cap, self.buf, self.ts, self.group_ts = None, "", None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        style = a.get("style") or ""
        if tag == "span" and "comp_head" in cls:
            self.cap, self.buf = "comp", ""
        elif tag == "div" and "fLeft" in cls and "width:270px" in style.replace(" ", ""):
            self.cap, self.buf = "teams", ""
        elif tag == "div" and "dynamic-time" in cls:
            self.cap, self.buf, self.ts = "st", "", a.get("data-timestamp")
        elif tag == "a" and any(c.startswith("chan_") for c in cls):
            self.cap, self.buf = "chan", ""

    def handle_data(self, data):
        if self.cap:
            self.buf += data
        if self.cur is not None:
            self.cur["_text"] += " " + data

    def handle_endtag(self, tag):
        want = {"comp": "span", "teams": "div", "st": "div", "chan": "a"}.get(self.cap)
        if not want or tag != want:
            return
        text = re.sub(r"\s+", " ", self.buf).strip()
        cap, self.cap = self.cap, None
        if cap == "comp":
            self.comp = text
        elif cap == "teams":
            m = re.match(r"^(.+?)\s+v\s+(.+)$", text)
            if m:
                self.cur = {"comp": self.comp, "a": m.group(1).strip(), "b": m.group(2).strip(), "start": None, "stan": False,
                            "ch": [], "_ts": None, "_text": ""}
                self.fixtures.append(self.cur)
            else:
                self.cur = None
        elif cap == "st":
            self.group_ts = None
            if self.cur is not None and text.startswith("ST:") and (self.ts or "").isdigit():
                self.group_ts = int(self.ts)
                if self.cur["_ts"] is None:
                    self.cur["_ts"] = self.group_ts
                    self.cur["start"] = datetime.fromtimestamp(self.group_ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif cap == "chan" and self.cur is not None and self.group_ts is not None and self.group_ts == self.cur["_ts"]:
            name = clean_channel(text)
            if name and "Stan Sport" in name:
                self.cur["stan"] = True
            if name and name not in self.cur["ch"]:
                self.cur["ch"].append(name)


def parse_html(page, with_channels):
    """fixtures from the page's own markup; [] if it isn't in that shape"""
    pp = PageParser()
    try:
        pp.feed(page)
        pp.close()
    except Exception as e:                                    # a malformed page must not stop the run
        print(f"  HTML parse problem: {e}")
    out = []
    for f in pp.fixtures:
        if not f["start"] or POSTPONED.search(f["_text"]):
            continue
        g = {"comp": f["comp"], "a": f["a"], "b": f["b"], "start": f["start"], "stan": f["stan"]}
        if with_channels:
            g["ch"] = f["ch"]
        out.append(g)
    return out


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
            if POSTPONED.search(t):
                cur["postponed"] = True
                continue
            name = clean_channel(t)
            if (name and 2 < len(name) < 60 and name not in cur["ch"] and not name.startswith("(GMT")
                    and name not in ("|", "---") and not _JUNK.search(name) and not DAY.match(name)):
                cur["ch"].append(name)
    return [f for f in out if f["a"] and f["b"] and not f.get("postponed")]


def read_pages(pages, old_fixtures, with_channels, now):
    """fetch `pages` once each (4 s apart); a failing page keeps its earlier fixtures (old_fixtures). Returns (fixtures, info)."""
    old_by_sport = {}
    for f in old_fixtures:
        old_by_sport.setdefault(f["sport"], []).append(f)
    info, fixtures = {}, []
    for sport, path in pages.items():
        status, body = fetch(BASE + path)
        tz, zname = zone_of(body) if status == 200 else (None, None)
        got = parse_html(body, with_channels) if status == 200 else []
        how = "timestamps"
        if not got and tz:                                    # the old text reading, only if the page's markup ever changes
            got, how = parse(body, tz, now, with_channels), f"text, zone {zname}"
        for f in got:
            f["sport"] = sport
        prev = old_by_sport.get(sport, [])
        if status != 200 or (not got and len(prev) > 5):
            why = f"HTTP {status}" if status != 200 else "found nothing (had data) - parser change?"
            print(f"  {sport}: {why} - keeping {len(prev)} earlier fixture(s)")
            fixtures += prev
            info[sport] = {"status": status, "kept": len(prev)}
        else:
            extra = "" if with_channels else f" ({sum(1 for g in got if g['stan'])} on Stan Sport)"
            print(f"  {sport}: HTTP 200, {how}, {len(got)} fixtures{extra}")
            if not got and body:
                print("    no fixtures parsed - first text pieces:", [t for t in tokens(body) if len(t) < 90][:40])
            fixtures += got
            info[sport] = {"status": 200, "read": how, "count": len(got)}
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
    return fixtures, info


def main():
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    old = {}
    try:
        with open(OUT, encoding="utf-8") as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        pass
    fixtures, pages = read_pages(PAGES, old.get("fixtures", []), False, now)
    football, fpages = read_pages(football_pages(now), (old.get("football") or {}).get("fixtures", []), True, now)
    if not fixtures and not football and not old:
        print("  nothing found - file not written")
        return 0
    data = {"fetched": stamp, "pages": pages, "fixtures": fixtures,
            "football": {"fetched": stamp, "pages": fpages, "fixtures": football}}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"  wrote {OUT}: {len(fixtures)} rugby / fighting fixtures and {len(football)} football fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())

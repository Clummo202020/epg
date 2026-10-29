#!/usr/bin/env python3
"""
USA_epg.py - XMLTV guide of the main US channels (network, cable, news, kids, premium,
Spanish-language and sports), taken from TV Passport's public listings:

    https://www.tvpassport.com/tv-listings/stations/<station>/<YYYY-MM-DD>

One page per channel per day. Each programme is a <div class="list-group-item"> whose
data-* attributes hold the start (data-st, in the page's timezone - America/New_York unless the
page selects another), the length in minutes (data-duration), title (data-showName), episode
title, description, categories (data-showType), year, rating, and live/new/repeat flags.

Channel IDs are US.<Name> (US.ESPN, US.FS1, US.CNN ...). The list is CHANNELS below: to add a
channel, find its station path on tvpassport.com (the part after /stations/, e.g.
"espn/594") and add a line. Feeds are the Eastern (East Coast) ones; NBC/CBS/ABC/FOX/CW are
the New York stations.

Live sport is titled "LIVE: ..." (no 🔴, like the SPORT guide) and gets the "Live" category.
A second guide of Canadian sports channels (TSN, Sportsnet ...; IDs CA.<Name>,
list CA_CHANNELS) is written to CANADA_epg.xml.gz in the same run.

Times in the file are UK time. The guide runs from midnight today (UK) to the end of the last
day TV Passport has listings for (found on each run, up to MAX_DAYS_AHEAD).

Run:  python3 USA_epg.py            (or --days-ahead 5 to fix the number of days)
"""
import argparse
import gzip
import html
import http.cookiejar
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape, quoteattr
from zoneinfo import ZoneInfo

BASE = "https://www.tvpassport.com/tv-listings/stations/{}/{}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
UK = ZoneInfo("Europe/London")
ET = ZoneInfo("America/New_York")
MAX_DAYS_AHEAD = 7   # upper limit (was 14 until 28 Oct 2026 - cut to a week); the run checks TV Passport has them
PROBE_CHANNELS = ["cnn/70", "espn/594", "hbo--eastern-feed/614"]   # used to find that limit
WORKERS = 4          # pages fetched at once - kept low to be polite
LIVE_PREFIX = "LIVE: "
# Red ball (28 Oct 2026) on these channels' live sports EVENTS only - a game/match/draw, not studio
# shows ("Hockey Central Tonight", "MLB Central", "NHL Now" keep plain "LIVE: "). They are the
# channels the user's Sportsnet UHD streams are linked to (the HD streams share the IDs).
RED_BALL_CHANNELS = {"CA.SportsnetOne", "CA.Sportsnet360",
                     "US.CBSSportsNetwork", "US.CBSSportsGolazo"}     # (29 Oct 2026: CBS Sports channels)
RED_BALL_PREFIX = "🔴 LIVE: "
# General (non-sports) channels (29 Oct 2026): only live sports EVENTS get a tag there, always the red
# ball; everything else - studio shows ("Football Night in America", "Big Ten Countdown"), and anything
# TV Passport files under Sports that isn't sport ("Saturday Night Live") - is never LIVE.
GENERAL_CHANNELS = {"US.NBC", "US.USANetwork", "US.CBS", "US.FOX", "US.ABC"}
MATCHUP_RE = re.compile(r"\S\s+(at|vs?\.?|v)\s+\S", re.I)          # "Buffalo Sabres at San Jose Sharks"
EVENT_WORDS_RE = re.compile(r"(?i)\b(draw \d+|game \d+|round \d+|(semi|quarter)-?finals?|finals?|"
                            r"grand prix|grand slam|qualifying|race \d*|championships?|cup|tournament)\b")
STUDIO_RE = re.compile(r"(?i)\b(central(?! american)|tonight|now|pre-?game|post-?game|show|insider|coverage|preview|"
                       r"recap|highlights|in 30|countdown|today|report|daily|best|top \d+|plays of)\b")


def is_event(p):
    """True for a game/match/draw (not a studio show) - used for the red ball."""
    if STUDIO_RE.search(p["title"]):
        return False
    return bool(MATCHUP_RE.search(f'{p["title"]} | {p["sub"] or ""}')     # "UFC Fight Night: A vs. B" too
                or EVENT_WORDS_RE.search(f'{p["title"]} {p["sub"]}'))
# TV Passport flags studio shows as live too (SportsCenter, Get Up, MLB Tonight ...). Live sport
# with one of these categories is not an event, so it doesn't get "LIVE:".
NOT_EVENT_CATEGORIES = {"talk show", "news", "anthology", "magazine", "newsmagazine",
                        "news magazine", "interview", "documentary", "instructional",
                        "fishing", "outdoors", "hunting", "special", "awards"}

# (channel ID, display name, TV Passport station path)
CHANNELS = [
    # Networks (New York stations) and PBS
    ("US.NBC", "NBC (WNBC New York)", "nbc-wnbc-new-york-ny/1767"),
    ("US.CBS", "CBS (WCBS New York)", "cbs-wcbs-new-york-ny/1766"),
    ("US.ABC", "ABC (WABC New York)", "abc-wabc-new-york-ny/1769"),
    ("US.FOX", "FOX (WNYW New York)", "fox-wnyw-new-york-ny/1638"),
    ("US.CW", "CW (WPIX New York)", "wpix-new-york-superstation/63"),
    ("US.PBS", "PBS", "pbs--network-hd--eastern/4259"),
    # Sports
    ("US.ESPN", "ESPN", "espn/594"),
    ("US.ESPN2", "ESPN2", "espn2/650"),
    ("US.ESPNU", "ESPNU", "espn-u/3331"),
    ("US.ESPNews", "ESPNews", "espn-news/1527"),
    ("US.ESPNDeportes", "ESPN Deportes", "espn-deportes/2108"),
    ("US.SECNetwork", "SEC Network", "sec-network/13711"),
    ("US.ACCNetwork", "ACC Network", "acc-network/33964"),
    ("US.BigTenNetwork", "Big Ten Network", "big-ten-network/4499"),
    ("US.FS1", "FS1", "fox-sports-1/668"),
    ("US.FS2", "FS2", "fox-sports-2/2114"),
    ("US.FoxDeportes", "Fox Deportes", "fox-deportes/1827"),
    ("US.CBSSportsNetwork", "CBS Sports Network", "cbs-sports-network-usa/3115"),
    ("US.NFLNetwork", "NFL Network", "nfl-network/3349"),
    ("US.NFLRedZone", "NFL RedZone", "nfl-redzone/6921"),
    ("US.NBATV", "NBA TV", "nba-tv-usa/3116"),
    ("US.MLBNetwork", "MLB Network", "mlb-network/6178"),
    ("US.NHLNetwork", "NHL Network", "nhl-network-usa/14156"),
    ("US.GolfChannel", "Golf Channel", "golf-channel-usa/193"),
    ("US.TennisChannel", "Tennis Channel", "the-tennis-channel/2269"),
    ("US.beINSports", "beIN Sports USA", "bein-sport-usa/10853"),
    ("US.TUDN", "TUDN", "tudn/11145"),
    ("US.Willow", "Willow Cricket", "willow-cricket/15964"),
    ("US.OutdoorChannel", "Outdoor Channel", "outdoor-channel-us/1086"),
    # Entertainment
    ("US.TNT", "TNT", "tnt--eastern-feed/347"),
    ("US.TBS", "TBS", "tbs--east/61"),
    ("US.truTV", "truTV", "trutv-usa--eastern/333"),
    ("US.USANetwork", "USA Network", "usa-network--east-feed/640"),
    ("US.FX", "FX", "fx-networks-east-coast/652"),
    ("US.FXX", "FXX", "fxx-usa--eastern/1952"),
    ("US.FXM", "FX Movie Channel", "fx-movie-channel/1308"),
    ("US.AMC", "AMC", "amc--eastern-feed/177"),
    ("US.AandE", "A&E", "ae-us--eastern-feed/2"),
    ("US.History", "History", "history-channel-us--eastern-feed/621"),
    ("US.Discovery", "Discovery Channel", "discovery-channel-us--eastern-feed/649"),
    ("US.TLC", "TLC", "tlc-usa--eastern/5005"),
    ("US.HGTV", "HGTV", "hgtv-usa--eastern-feed/623"),
    ("US.FoodNetwork", "Food Network", "food-network-usa--eastern-feed/1054"),
    ("US.TravelChannel", "Travel Channel", "travel-us--east/662"),
    ("US.Bravo", "Bravo", "bravo-usa--eastern-feed/646"),
    ("US.E", "E!", "e-entertainment-usa--eastern-feed/617"),
    ("US.Syfy", "Syfy", "syfy--eastern-feed/596"),
    ("US.ParamountNetwork", "Paramount Network", "paramount-network-usa--eastern-feed/1030"),
    ("US.ComedyCentral", "Comedy Central", "comedy-central-us--eastern-feed/647"),
    ("US.MTV", "MTV", "mtv-usa--eastern-feed/656"),
    ("US.VH1", "VH1", "vh1--eastern-feed/663"),
    ("US.BET", "BET", "bet--eastern-feed/323"),
    ("US.CMT", "CMT", "cmt-us--eastern-feed/1076"),
    ("US.TVLand", "TV Land", "tv-land--eastern/1252"),
    ("US.Lifetime", "Lifetime", "lifetime-network-us--eastern-feed/654"),
    ("US.LMN", "Lifetime Movies", "lifetime-movies--east/1333"),
    ("US.Hallmark", "Hallmark Channel", "hallmark--eastern-feed/1052"),
    ("US.HallmarkMystery", "Hallmark Mystery", "hallmark-mystery--eastern/4453"),
    ("US.Freeform", "Freeform", "freeform--east-feed/1011"),
    ("US.OWN", "OWN", "oprah-winfrey-network-usa-eastern/1159"),
    ("US.NatGeo", "National Geographic", "national-geographic-us--eastern/657"),
    ("US.NatGeoWild", "Nat Geo Wild", "national-geographic-wild/7537"),
    ("US.AnimalPlanet", "Animal Planet", "animal-planet-us--east/645"),
    ("US.ID", "Investigation Discovery", "investigation-discovery-usa--eastern/2090"),
    ("US.Smithsonian", "Smithsonian Channel", "smithsonian-channel-usa/4679"),
    ("US.Science", "Science", "science/1960"),
    # Kids
    ("US.Nickelodeon", "Nickelodeon", "nickelodeon-usa--east-feed/658"),
    ("US.DisneyChannel", "Disney Channel", "disney--eastern-feed/595"),
    ("US.DisneyJunior", "Disney Junior", "disney-junior-usa--east/6867"),
    ("US.DisneyXD", "Disney XD", "disney-xd-usa--eastern-feed/1053"),
    ("US.CartoonNetwork", "Cartoon Network", "cartoon-network-usa--eastern-feed/661"),
    ("US.AdultSwim", "Adult Swim", "adult-swim--east/607"),
    # News and weather
    ("US.CNN", "CNN", "cnn/70"),
    ("US.CNNInternational", "CNN International", "cnn-international-north-america/3008"),
    ("US.FoxNews", "Fox News", "fox-news/1083"),
    ("US.MSNOW", "MS NOW", "msnbc-usa/655"),
    ("US.CNBC", "CNBC", "cnbc-usa/201"),
    ("US.FoxBusiness", "Fox Business", "fox-business/4656"),
    ("US.HLN", "HLN", "hln/425"),
    ("US.NewsNation", "NewsNation", "newsnation--eastern-feed/65"),
    ("US.WeatherChannel", "The Weather Channel", "the-weather-channel/1526"),
    # Premium
    ("US.HBO", "HBO", "hbo--eastern-feed/614"),
    ("US.Showtime", "Paramount+ with Showtime", "paramount-with-showtime--eastern-feed/665"),
    ("US.Starz", "Starz", "starz1--east/55"),
    ("US.Cinemax", "Cinemax", "cinemax--eastern-hd/3567"),
    # Spanish-language
    ("US.Univision", "Univision", "univision--eastern-feed/1305"),
    ("US.Telemundo", "Telemundo", "telemundo--eastern-feed/1521"),
    ("US.Galavision", "Galavisión", "galavision--eastern-feed/1894"),
]

# Canadian sports - a separate guide, CANADA_epg.xml.gz (English-language channels only).
# A 4th item (e.g. "fr") would set a channel's language; the default is "en".
CA_CHANNELS = [
    ("CA.TSN1", "TSN1", "tsn1/11"),
    ("CA.TSN2", "TSN2", "tsn2/4294"),
    ("CA.TSN3", "TSN3", "tsn3/13719"),
    ("CA.TSN4", "TSN4", "tsn4/279"),
    ("CA.TSN5", "TSN5", "tsn5/278"),
    ("CA.SportsnetOntario", "Sportsnet Ontario", "sportsnet-ontario/254"),
    ("CA.SportsnetEast", "Sportsnet East", "sportsnet-east/255"),
    ("CA.SportsnetWest", "Sportsnet West", "sportsnet-west/252"),
    ("CA.SportsnetPacific", "Sportsnet Pacific", "sportsnet-pacific/314"),
    ("CA.SportsnetOne", "Sportsnet One", "sportsnet-one/8249"),
    ("CA.Sportsnet360", "Sportsnet 360", "sportsnet-360/336"),
    ("CA.SportsnetWorld", "Sportsnet World", "sportsnet-world/4442"),
    ("CA.SportsnetFlames", "Sportsnet Flames", "sportsnet-flames/8489"),
    ("CA.SportsnetOilers", "Sportsnet Oilers", "sportsnet-oilers/8492"),
    ("CA.SportsnetCanucks", "Sportsnet Canucks", "sportsnet-canucks/8628"),
    ("CA.OneSoccer", "OneSoccer", "one-soccer/37452"),
    ("CA.NBATVCanada", "NBA TV Canada", "nba-tv-canada/1150"),
    ("CA.NFLNetwork", "NFL Network Canada", "nfl-network--canada/37557"),
    ("CA.MLBNetwork", "MLB Network Canada", "mlb-network-canada/32974"),
    ("CA.GolfChannel", "Golf Channel Canada", "golf-channel-canada/9900"),
    ("CA.beINSports", "beIN Sports Canada", "bein-sport-canada/13246"),
    ("CA.FightNetwork", "Fight Network", "fight-network-canada/3433"),
]

# output file -> its channels
# CBS Sports Golazo Network (added 29 Oct 2026) is a free streaming channel - not on TV Passport. Its
# listings come from Pluto TV's guide as published by i.mjh.nz (matthuisman's GitHub repo; Pluto's own
# API needs a session). Pluto marks EVERY programme live, so that flag is ignored: a programme is live
# when it is a match ("Saprissa vs. CD LA Firpo"), at least PLUTO_MATCH_MINUTES long, not a highlights/
# re-air show ("90 in 60"), and the first airing of that match in the listings (later ones are re-airs).
# Pluto lists only about a day ahead; the twice-daily runs and PlaylistLabs' appending keep it filled.
PLUTO_GUIDE = "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/us.xml.gz"
PLUTO_CHANNELS = {"US.CBSSportsGolazo": "63a0e33a45264d000850ed7e"}    # our ID -> Pluto channel id
PLUTO_MATCH_MINUTES = 100
PLUTO_NOT_LIVE = re.compile(r"(?i)\b(\d+ in \d+|highlights?|replay|re-?airs?|rewind|classic|encore|"
                            r"best of|condensed|extended|recap|review|preview|show)\b")
CHANNELS.append(("US.CBSSportsGolazo", "CBS Sports Golazo", "pluto"))

GUIDES = {"USA_epg.xml.gz": CHANNELS, "CANADA_epg.xml.gz": CA_CHANNELS}

ITEM = re.compile(r'<div\s[^>]*class="list-group-item"[^>]*>', re.S)
ATTR = re.compile(r'data-([A-Za-z_]+)="([^"]*)"')
TZ_SELECTED = re.compile(r'<option\s+value="([A-Za-z_]+/[A-Za-z_]+)"\s+selected', re.I)

_cookies = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookies))


def fetch(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with _opener.open(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            err = e
            if getattr(e, "code", None) == 404:
                break
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(err)


def flag(v):
    return (v or "").strip().lower() not in ("", "0", "false", "n", "no")


def rating(r):
    r = (r or "").strip()
    return "TV-" + r[2:] if re.fullmatch(r"TV[A-Z0-9]+", r) else r


def parse_page(page):
    """[{start, stop, title, sub, desc, cats, year, rating, live, new}] from one day's page."""
    m = TZ_SELECTED.search(page)
    try:
        tz = ZoneInfo(m.group(1)) if m else ET
    except Exception:
        tz = ET
    progs = []
    for tag in ITEM.findall(page):
        a = {k.lower(): html.unescape(v).strip() for k, v in ATTR.findall(tag)}
        try:
            start = datetime.strptime(a["st"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            dur = int(a.get("duration") or 0)
        except (KeyError, ValueError):
            continue
        title = a.get("showname") or a.get("showtitle") or ""
        sub = a.get("episodetitle") or ""
        if title in ("Movie", "Cinéma") and sub:
            title, sub = sub, ""
        if not title:
            continue
        cats = [c.strip() for c in (a.get("showtype") or "").split(",") if c.strip()]
        progs.append({
            "start": start.astimezone(timezone.utc),
            "stop": (start + timedelta(minutes=dur)).astimezone(timezone.utc) if dur > 0 else None,
            "title": title, "sub": sub if sub != title else "",
            "desc": a.get("description") or "", "cats": cats,
            "year": a.get("year") or "", "rating": rating(a.get("rating")),
            "live": flag(a.get("live")), "new": flag(a.get("new_show")),
        })
    return progs


def fetch_pluto():
    """{our id: [programmes]} for PLUTO_CHANNELS from the i.mjh.nz Pluto TV guide."""
    import xml.etree.ElementTree as XT
    out = {cid: [] for cid in PLUTO_CHANNELS}
    try:
        req = urllib.request.Request(PLUTO_GUIDE, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=60) as r:
            root = XT.fromstring(gzip.decompress(r.read()))
    except Exception as e:
        print(f"  WARNING: Pluto TV guide not available ({e})")
        return out
    ours = {v: k for k, v in PLUTO_CHANNELS.items()}

    def when(v):
        return datetime.strptime(v, "%Y%m%d%H%M%S %z").astimezone(timezone.utc)

    for el in root.iter("programme"):
        cid = ours.get(el.get("channel"))
        if not cid:
            continue
        try:
            start, stop = when(el.get("start")), when(el.get("stop"))
        except (TypeError, ValueError):
            continue
        out[cid].append({"start": start, "stop": stop, "title": (el.findtext("title") or "").strip(),
                         "sub": (el.findtext("sub-title") or "").strip(),
                         "desc": (el.findtext("desc") or "").strip(),
                         "cats": [c.text.strip() for c in el.findall("category") if c.text and c.text.strip()],
                         "year": "", "rating": "", "live": False, "new": False})
    for cid, progs in out.items():
        progs.sort(key=lambda p: p["start"])
        seen = set()
        for p in progs:
            match = (p["sub"] if MATCHUP_RE.search(p["sub"]) else p["title"]) if \
                MATCHUP_RE.search(f'{p["title"]} | {p["sub"]}') else ""
            key = re.sub(r"\W+", " ", match.lower()).strip()
            p["live"] = bool(match and key not in seen
                             and p["stop"] - p["start"] >= timedelta(minutes=PLUTO_MATCH_MINUTES)
                             and not PLUTO_NOT_LIVE.search(f'{p["title"]} {p["sub"]} {p["desc"]}'))
            if key:
                seen.add(key)
        print(f"  Pluto TV {cid}: {len(progs)} programmes, {sum(p['live'] for p in progs)} live match(es)"
              + (f", to {progs[-1]['stop'].astimezone(UK):%a %d %b %H:%M} UK" if progs else ""))
    return out


def grab(job):
    cid, path, day = job
    url = BASE.format(path, day.strftime("%Y-%m-%d"))
    try:
        return cid, day, parse_page(fetch(url)), None
    except Exception as e:
        return cid, day, [], e


def tidy(progs, first, last):
    """Sort, drop duplicates, give each programme a stop time, keep those between first-last."""
    by_start = {}
    for p in progs:
        by_start.setdefault(p["start"], p)
    out = sorted(by_start.values(), key=lambda p: p["start"])
    for i, p in enumerate(out):
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        if p["stop"] is None or (nxt and p["stop"] > nxt):
            p["stop"] = nxt or p["start"] + timedelta(minutes=30)
    return [p for p in out if p["stop"] > p["start"] and p["stop"] > first and p["start"] < last]


def find_days_ahead(today):
    """How many days ahead TV Passport has listings: checks a few big channels day by day
    and stops at the first day none of them has."""
    ahead = 0
    for d in range(1, MAX_DAYS_AHEAD + 1):
        day = (today + timedelta(days=d)).strftime("%Y-%m-%d")
        found = False
        for path in PROBE_CHANNELS:
            try:
                if parse_page(fetch(BASE.format(path, day))):
                    found = True
                    break
            except Exception:
                continue
        if not found:
            break
        ahead = d
    print(f"TV Passport has listings up to {ahead} days ahead "
          f"({today + timedelta(days=ahead):%a %d %b})")
    return ahead


def xmltv_time(dt):
    return dt.astimezone(UK).strftime("%Y%m%d%H%M%S %z")


def write(path, channels, guide):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<tv generator-info-name="USA_epg.py" source-info-name="TV Passport">']
    for cid, name, *_ in channels:
        lines.append(f'  <channel id={quoteattr(cid)}>\n'
                     f'    <display-name>{escape(name)}</display-name>\n  </channel>')
    count = 0
    for cid, _, _, *rest in channels:
        lang = rest[0] if rest else "en"
        for p in guide.get(cid, []):
            low = {c.lower() for c in p["cats"]}
            sport = any(c.startswith("sports") for c in low)
            live = p["live"] and sport and not (low & NOT_EVENT_CATEGORIES)
            if cid in GENERAL_CHANNELS:
                live = live and is_event(p)
            prefix = RED_BALL_PREFIX if ((cid in RED_BALL_CHANNELS or cid in GENERAL_CHANNELS)
                                         and is_event(p)) else LIVE_PREFIX
            title = (prefix + p["title"]) if live else p["title"]
            cats = p["cats"] + (["Live"] if live else [])
            out = [f'  <programme start="{xmltv_time(p["start"])}" stop="{xmltv_time(p["stop"])}" '
                   f'channel={quoteattr(cid)}>',
                   f'    <title lang="{lang}">{escape(title)}</title>']
            if p["sub"]:
                out.append(f'    <sub-title lang="{lang}">{escape(p["sub"])}</sub-title>')
            if p["desc"]:
                out.append(f'    <desc lang="{lang}">{escape(p["desc"])}</desc>')
            if re.fullmatch(r"\d{4}", p["year"]):
                out.append(f'    <date>{p["year"]}</date>')
            seen = set()
            for c in cats:
                if c.lower() not in seen:
                    seen.add(c.lower())
                    out.append(f'    <category lang="{lang}">{escape(c)}</category>')
            if p["new"] and not live:
                out.append('    <new />')
            if p["rating"]:
                out.append(f'    <rating system="MPA"><value>{escape(p["rating"])}</value></rating>')
            out.append('  </programme>')
            lines.append("\n".join(out))
            count += 1
    lines.append('</tv>\n')
    data = "\n".join(lines).encode("utf-8")
    if path.endswith(".gz"):
        with gzip.GzipFile(path, "wb", mtime=0) as f:     # mtime=0: no change = no commit
            f.write(data)
    else:
        with open(path, "wb") as f:
            f.write(data)
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-ahead", type=int, default=None,
                    help="fixed number of days ahead (default: as many as TV Passport has)")
    args = ap.parse_args()

    # The guide runs from midnight today (UK) to the end of the last day TV Passport lists.
    # TV Passport pages are US dates, so the US day before is fetched too (UK early hours =
    # the US evening before).
    uk_today = datetime.now(UK).date()
    if args.days_ahead is None:
        args.days_ahead = find_days_ahead(uk_today)
    first = datetime(uk_today.year, uk_today.month, uk_today.day, tzinfo=UK)
    last_day = uk_today + timedelta(days=args.days_ahead + 1)
    last = datetime(last_day.year, last_day.month, last_day.day, tzinfo=UK)
    days = [uk_today + timedelta(days=d) for d in range(-1, args.days_ahead + 1)]
    every = [c for chans in GUIDES.values() for c in chans]
    jobs = [(c[0], c[2], d) for c in every for d in days if c[2] != "pluto"]
    print(f"Fetching {len(every)} channels x {len(days)} days ({len(jobs)} pages) ...")

    raw, failed, empty = {}, [], {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, (cid, day, progs, err) in enumerate(pool.map(grab, jobs), 1):
            raw.setdefault(cid, []).extend(progs)
            if err:
                failed.append(f"{cid} {day} ({err})")
            elif not progs:
                empty[cid] = empty.get(cid, 0) + 1
            if i % 50 == 0:
                print(f"  {i}/{len(jobs)} pages")

    raw.update(fetch_pluto())                       # CBS Sports Golazo (Pluto TV)
    guide = {cid: tidy(p, first, last) for cid, p in raw.items()}
    ends = {cid: v[-1]["stop"] for cid, v in guide.items() if v}
    if ends:
        latest = max(ends.values())
        print(f"  Listings run to {latest.astimezone(UK):%a %d %b %H:%M} UK time "
              f"(asked for up to {last - timedelta(minutes=1):%a %d %b %H:%M})")
        short = sorted(cid for cid, e in ends.items() if e < latest - timedelta(days=1))
        if short:
            print(f"  NOTE: {len(short)} channels have shorter listings (TV Passport gives them "
                  f"less): {', '.join(short)}")
    for msg in failed[:15]:
        print(f"  WARNING: failed {msg}")
    if len(failed) > 15:
        print(f"  ... and {len(failed) - 15} more failed pages")
    blank = [c[0] for c in every if not guide.get(c[0])]
    if blank:
        print(f"  WARNING: no programmes for {len(blank)} channels: {', '.join(blank)}")
    if sum(len(v) for v in guide.values()) == 0:
        print("ERROR: no programmes at all - TV Passport may be blocking or has changed. "
              "Not writing the file.")
        sys.exit(1)
    for path, chans in GUIDES.items():
        n = write(path, chans, guide)
        print(f"Wrote {path}: {len(chans)} channels, {n} programmes")


if __name__ == "__main__":
    main()

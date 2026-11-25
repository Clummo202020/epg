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
                     "US.CBSSportsNetwork", "US.CBSSportsGolazo", "CARIB.ESPN", "CARIB.ESPN2",
                     "US.beINSports", *[f"US.beINSports{n}" for n in range(3, 9)],     # (29 Oct 2026: CBS Sports channels)
                     # 29 Oct 2026 (late): FOX and ESPN channels, and TSN 1-5
                     "US.FS1", "US.FS2", "US.FoxSoccerPlus", "US.ESPN", "US.ESPN2", "US.ESPNU",
                     *[f"CA.TSN{n}" for n in range(1, 6)], "CA.ATNCricketPlus"}
RED_BALL_PREFIX = "🔴 LIVE: "
# General (non-sports) channels (29 Oct 2026): only live sports EVENTS get a tag there, always the red
# ball; everything else - studio shows ("Football Night in America", "Big Ten Countdown"), and anything
# TV Passport files under Sports that isn't sport ("Saturday Night Live") - is never LIVE.
GENERAL_CHANNELS = {"US.NBC", "US.USANetwork", "US.CBS", "US.FOX", "US.ABC", "US.NBCChicago"}
# 18 Nov 2026 (user): "Premier League Goal Rush" on Premier League TV is treated like the other Goal Rush sources - always live, with the red ball
# ("🔴 LIVE: Premier League Goal Rush"). TV Passport doesn't flag it live.
GOAL_RUSH_CHANNELS = {"US.PremierLeagueTV2"}
GOAL_RUSH_RE = re.compile(r"(?i)\bgoal rush\b")
# 20 Nov 2026 (user): Willow Cricket's live cricket gets the red ball too. Its titles are "Test Cricket", "Abu Dhabi T10 Cricket" - no "v" or
# "cup" for is_event() to see - so on this channel every live programme is an event except the Review / Preview / Highlights style ones.
CRICKET_EVENT_CHANNELS = {"US.Willow", "US.Willow2.5rda"}
CRICKET_STUDIO_RE = re.compile(r"(?i)\b(review|preview|highlights?|filler|show|magazine|studio|report|round-?up|best of|classic|archive|replay)\b")
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
    ("US.NBCChicago", "NBC (WMAQ Chicago)", "nbc-wmaq-chicago-il-hd/6492"),      # 29 Oct 2026 (Central time feed)
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
    ("US.PremierLeagueTV2", "Premier League TV", "premier-league-tv/37457"),   # 30 Oct 2026 (iptv-org's TV Passport list)
    ("US.FoxSoccerPlus", "FOX Soccer Plus", "fox-soccer-plus/7538"),            # 29 Oct 2026 (HD page: fox-soccer-plus-hd/11551)
    ("US.FoxDeportes", "Fox Deportes", "fox-deportes/1827"),
    ("US.CBSSportsNetwork", "CBS Sports Network", "cbs-sports-network-usa/3115"),
    # Caribbean (29 Oct 2026) - TV Passport lists both; live events get the red ball
    ("CARIB.ESPN", "ESPN Caribbean", "espn-caribbean/8135"),
    ("CARIB.ESPN2", "ESPN2 Caribbean", "espn2--caribbean/32923"),
    ("US.NFLNetwork", "NFL Network", "nfl-network/3349"),
    ("US.NFLRedZone", "NFL RedZone", "nfl-redzone/6921"),
    ("US.NBATV", "NBA TV", "nba-tv-usa/3116"),
    ("US.MLBNetwork", "MLB Network", "mlb-network/6178"),
    ("US.NHLNetwork", "NHL Network", "nhl-network-usa/14156"),
    ("US.GolfChannel", "Golf Channel", "golf-channel-usa/193"),
    ("US.TennisChannel", "Tennis Channel", "the-tennis-channel/2269"),
    ("US.beINSports", "beIN Sports USA", "bein-sport-usa/10853"),
    # beIN SPORTS 3-8 USA (29 Oct 2026) - extra match channels, often blank between events
    *[(f"US.beINSports{n}", f"beIN Sports {n} USA", f"bein-sports-{n}/{37179 + n}") for n in range(3, 9)],
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
    ("CA.ATNCricketPlus", "ATN Cricket Plus", "atn--cricket-plus/13695"),   # 30 Oct 2026 (TV Passport)
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
    ("CA.CTVMontreal", "CTV", "ctv-montreal-cfcf-qc/50"),      # 17 Nov 2026 (NFL, Super Bowl - the English CTV feed; user found the station)
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
# Other free streaming channels from i.mjh.nz guides (29 Oct 2026): our ID -> (guide, channel id ending).
# Listings only - never LIVE (Billiard TV shows dated replays: "Final: A vs. B from July 10, 2026").
MJH_PLAIN = {"US.BilliardTV": ("https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/Plex/gb.xml.gz",
                               "6334a8e48a7b2a349d903b8c"),
             # GolfPass (30 Oct 2026): NBC's golf channel, free on Plex/Pluto/Samsung/Roku - Plex US has most listings
             "US.GolfPass": ("https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/Plex/us.xml.gz",
                             "5fc706038aba71002d8b7c8e")}
# Roku's guide (25 Nov 2026, user: "a better source than Pluto TV"): the same channel on Roku lists about 3 days (61 programmes against Pluto's
# ~16 hours / 16 programmes), same descriptions. Used when it reaches further than Pluto; Pluto stays as the fallback. Roku titles read
# "UEFA Champions League: Slavia Praha vs Villarreal CF" - split into title "Slavia Praha vs Villarreal CF" + sub-title "UEFA Champions League".
ROKU_GUIDE = "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/Roku/all.xml.gz"
ROKU_CHANNELS = {"US.CBSSportsGolazo": "b18a1af4fa8b5c58acd43dbc2cf5cc9f"}
_ROKU_COMP_MATCH = re.compile(r"^(?P<comp>[^:]{3,60}):\s+(?P<match>\S.*?\s(?:vs?\.?|v)\s\S.*)$", re.I)
PLUTO_MATCH_MINUTES = 100
PLUTO_NOT_LIVE = re.compile(r"(?i)\b(\d+ in \d+|highlights?|replay|re-?airs?|rewind|classic|encore|"
                            r"best of|condensed|extended|recap|review|preview|show)\b")
CHANNELS.append(("US.CBSSportsGolazo", "CBS Sports Golazo", "pluto"))
CHANNELS.append(("US.Willow2.5rda", "Willow 2 Cricket", "pluto"))      # 20 Nov 2026: not on TV Passport - listings from Willow's own feed (fetch_willow)
CHANNELS.append(("US.BilliardTV", "Billiard TV", "pluto"))
CHANNELS.append(("US.GolfPass", "GolfPass", "pluto"))

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
    try:                                             # Roku: longer look-ahead for the same channel (kept only when it reaches further)
        req = urllib.request.Request(ROKU_GUIDE, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=90) as r:
            rroot = XT.fromstring(gzip.decompress(r.read()))
        rours = {v: k for k, v in ROKU_CHANNELS.items()}
        rprogs = {cid: [] for cid in ROKU_CHANNELS}
        for el in rroot.iter("programme"):
            cid = rours.get(el.get("channel"))
            if not cid:
                continue
            try:
                start, stop = when(el.get("start")), when(el.get("stop"))
            except (TypeError, ValueError):
                continue
            title, sub = (el.findtext("title") or "").strip(), (el.findtext("sub-title") or "").strip()
            m = _ROKU_COMP_MATCH.match(title)
            if m and not sub:
                title, sub = m.group("match").strip(), m.group("comp").strip()
            rprogs[cid].append({"start": start, "stop": stop, "title": title, "sub": sub, "desc": (el.findtext("desc") or "").strip(),
                                "cats": [c.text.strip() for c in el.findall("category") if c.text and c.text.strip()],
                                "year": "", "rating": "", "live": False, "new": False})
        for cid, rp in rprogs.items():
            if rp and (not out[cid] or max(p["stop"] for p in rp) > max(p["stop"] for p in out[cid])):
                filler = {p["title"]: p["desc"] for p in out[cid] if p["desc"]}      # Roku leaves some descriptions empty ("Champions League Matchday")
                for p in rp:
                    if not p["desc"] and p["title"] in filler:
                        p["desc"] = filler[p["title"]]
                print(f"  Roku {cid}: {len(rp)} programmes to {max(p['stop'] for p in rp).astimezone(UK):%a %d %b %H:%M} UK "
                      f"(Pluto had {len(out[cid])}) - Roku listings used")
                out[cid] = rp
    except Exception as e:
        print(f"  Roku guide not available ({e}) - Pluto listings used")
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
        if cid == "US.CBSSportsGolazo":
            golazo_enrich(progs)
        print(f"  Pluto TV {cid}: {len(progs)} programmes, {sum(p['live'] for p in progs)} live match(es)"
              + (f", to {progs[-1]['stop'].astimezone(UK):%a %d %b %H:%M} UK" if progs else ""))
    return out


# CBS Sports Golazo live matches (25 Nov 2026, user: "a bit sparse on info" - Pluto only gives "From Fortuna Arena in Prague."): the stage
# ("League Phase, Matchday 5") and where else to watch ("This match is available on TNT Sports 5, ... and Sony Sports 1.") are taken from
# our own football guide's block for the same match. Matched by kick-off (within 30 minutes) and the teams' names; nothing found = the
# Pluto text stays as it is.
FOOTBALL_GUIDE = "https://raw.githubusercontent.com/Clummo202020/epg/main/football_epg.xml"
_NAME_STOP = {"club", "city", "united", "utd", "town", "real", "athletic", "sporting", "west", "east", "north", "south", "albion", "rovers",
              "wanderers", "county", "forest", "athletico", "atletico", "inter", "dynamo", "football", "women", "womens", "hotspur", "wednesday"}
_STAGE_RE = re.compile(r"(?i)matchweek|\bMW\s?\d|round|phase|group|final|\bleg\b|matchday|play-?offs?|week \d")


def _name_words(text):
    import unicodedata
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return {w for w in re.findall(r"[a-z0-9]{4,}", t) if w not in _NAME_STOP}


def _sides(match):
    parts = re.split(r"\s+(?:vs?\.?|v|at)\s+", match, maxsplit=1, flags=re.I)
    return parts if len(parts) == 2 else None


def golazo_enrich(progs):
    """Adds stage + other channels to the description of each live Golazo match, from football_epg.xml. Never raises."""
    live = [p for p in progs if p.get("live")]
    if not live:
        return
    try:
        import xml.etree.ElementTree as XT
        root = XT.fromstring(fetch(FOOTBALL_GUIDE).encode("utf-8"))
    except Exception as e:
        print(f"  Golazo: football guide not available ({e}) - Pluto descriptions kept")
        return
    cands = []
    for el in root.iter("programme"):
        title = (el.findtext("title") or "")
        if "LIVE:" not in title:
            continue
        sd = _sides(re.sub(r"^.*?LIVE:\s*", "", title))
        if not sd:
            continue
        try:
            st = datetime.strptime(el.get("start"), "%Y%m%d%H%M%S %z").astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        cands.append((st, _name_words(sd[0]), _name_words(sd[1]), (el.findtext("desc") or "")))
    done = 0
    for p in live:
        m = p["title"] if MATCHUP_RE.search(p["title"]) else p["sub"]
        sd = _sides(m or "")
        if not sd:
            continue
        a, b = _name_words(sd[0]), _name_words(sd[1])
        best = None
        for st, ca, cb, desc in cands:
            if abs(st - p["start"]) > timedelta(minutes=20) or "available on" not in desc:
                continue
            straight, crossed = bool(a & ca) + bool(b & cb), bool(a & cb) + bool(b & ca)
            score = max(straight, crossed)
            if score >= 1 and (best is None or score > best[0]):
                best = (score, desc)
        if not best:
            continue
        desc = best[1]
        head = desc.split(" | ")[0]
        # the stage is the LAST sentence of the head ("LIVE from St. Mary's Stadium. Championship (Matchweek 18)." - a venue may hold full stops)
        last = re.split(r"(?<=\.)\s+", head.strip())[-1] if head.strip() else ""
        stage = last if _STAGE_RE.search(last) and not last.lower().startswith("live from") else ""
        stage = re.sub(r"\bMW\s?(\d+)", r"Matchday \1", stage)
        tail = desc.split(" | ", 1)[-1]
        chans = []
        # "This match is available on A, B and C."  and / or  "It is on D and E too." (the football guide's two sentence forms)
        for mm in re.finditer(r"(?:available on|It is on) (.+?)(?: too)?\.(?=\s|$)", tail, re.S):
            for c in re.split(r",\s*|\s+and\s+", mm.group(1)):
                c = c.strip()
                if c and "golazo" not in c.lower() and c not in chans:
                    chans.append(c)
        bits = [stage if stage and stage.endswith(".") else (stage + "." if stage else ""), p["desc"].strip()]
        if chans:
            joined = chans[0] if len(chans) == 1 else ", ".join(chans[:-1]) + " and " + chans[-1]
            bits.append(f"This match is available on {joined}.")
        new = " ".join(x for x in bits if x)
        if new and new != p["desc"]:
            p["desc"] = new
            done += 1
    print(f"  Golazo: {done} of {len(live)} live match(es) enriched from the football guide")


# Willow (20 Nov 2026, user): Willow and Willow 2 listings straight from Willow's own schedule page (cricket.willow.tv), which loads them from two
# feeds - datafeedAssoc.php = Willow, datafeedAssocExtra.php = Willow 2 - 8 days at a time. Each programme has a title, start / end, a Live flag
# and a BroadCastDay. The CLOCK the times are in depends on who asks: the user's browser (London) got times 1 hour ahead of UTC, the GitHub runner
# (US) got times 7 hours earlier than that. So the clock is worked out on every run from the BroadCastDay field: the broadcast day always rolls
# over at 00:00 UTC (the browser's feed shows it at 01:00 = UTC+1, checked 20 Nov against what Willow was showing: "Heat v Thunder" highlights
# listed at 21:30-22:00 were on at 20:52 UTC). The first programme of each new BroadCastDay is where the day rolls over; its clock time is the
# feed's offset from UTC. Not clear (fewer than 4 days / under 80% agreeing / not a multiple of 30 minutes) = the feed is NOT used: Willow keeps
# its TV Passport listings and Willow 2 gets the standard "no schedule" blocks. WILLOW_FEED_TZ is the value the site's own page sends (5.5).
WILLOW_FEED_BASE = "https://epgadmindev.willow.tv/php/"
WILLOW_FEEDS = {"US.Willow": "datafeedAssoc.php?method=list", "US.Willow2.5rda": "datafeedAssocExtra.php"}
WILLOW_FEED_TZ = "5.5"
WILLOW_CAT = ["Sports", "Cricket"]
WILLOW_TRIES = 5
WILLOW_RETRY_WAIT = 8             # seconds, times the attempt number
PUBLISHED_GUIDE = "https://raw.githubusercontent.com/Clummo202020/epg/main/USA_epg.xml.gz"
WILLOW_STALE_OK = {"US.Willow2.5rda"}   # channels with no other source: if the feed fails, the last published listings (still to come) are kept
WILLOW_DAY_ROLLS_AT_UTC_MIN = 0          # the broadcast day starts at 00:00 UTC
_WILLOW_LEAD = re.compile(r"^\s*(?:Continued Event from yesterday,\s*)?(?:LIVE\s*[-\u2013:]\s*)?", re.I)
_WILLOW_STUDIO = re.compile(r"(?i)\b(preview|review)\s*$")


def _willow_time(text):
    """"11/20/2026 0:0" -> naive datetime (the feed's own clock), or None."""
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{1,2})\s*", text or "")
    if not m:
        return None
    mo, d, y, hh, mm = (int(x) for x in m.groups())
    try:
        return datetime(y, mo, d, hh, mm)
    except ValueError:
        return None


def willow_clock_offset(entries):
    """Minutes the feed's clock is ahead of UTC (negative = behind), from where BroadCastDay changes; None if not clear.
    entries = [(naive start, BroadCastDay string)] in feed order."""
    from collections import Counter
    votes = Counter()
    days = [(st, bd) for st, bd in entries if st and bd]
    for (_, a), (st, b) in zip(days, days[1:]):
        if a != b:
            votes[st.hour * 60 + st.minute] += 1
    total = sum(votes.values())
    if total < 4:
        return None
    mins, top = votes.most_common(1)[0]
    if top / total < 0.8:
        return None
    off = (mins - WILLOW_DAY_ROLLS_AT_UTC_MIN + 720) % 1440 - 720
    return off if off % 30 == 0 else None


def willow_text(raw_title):
    """Feed title -> (title, sub, desc, studio). "LIVE - WBBL 2026 - Strikers vs Renegades - 28th Match, Preview" ->
    ("Cricket. Strikers v Renegades", "WBBL 2026", "WBBL 2026: Strikers v Renegades - 28th Match, Preview.", True);
    "New Zealand vs India - 1st Test, Day 2, Lunch Break" -> ("Cricket. 1st Test: New Zealand v India", "Day 2, Lunch Break", ...)."""
    t = re.sub(r"\s+", " ", _WILLOW_LEAD.sub("", raw_title or "")).strip(" ,")
    t = _WILLOW_LEAD.sub("", t).strip(" ,")            # "Continued Event from yesterday, LIVE - ..."
    parts = [x.strip() for x in re.split(r"\s+-\s+", t) if x.strip()]
    studio = bool(_WILLOW_STUDIO.search(t))
    fix = next((i for i, x in enumerate(parts) if VS_RE.search(f" {x} ")), None)
    if fix is None:                                       # "Super Over Podcast - S2, Episode 15", "Cricket Filler"
        title = parts[0] if parts else t
        sub = ", ".join(parts[1:]) if len(parts) > 1 else ""
        return title, sub, (f"{title}. {sub}." if sub else ""), studio
    a, b = (x.strip() for x in VS_RE.split(f" {parts[fix]} ", maxsplit=1))
    fixture = f"{a} v {b}"
    series = " - ".join(parts[:fix])
    tail = " - ".join(parts[fix + 1:])
    if series:
        title, sub = f"Cricket. {fixture}", series
        kind = re.search(r"(?i)(?:^|,)\s*(highlights|preview|review)\s*$", tail)
        if kind:                                          # say so in the sub-title: "WBBL 2026, Highlights"
            sub = f"{series}, {kind.group(1).capitalize()}"
        desc = f"{series}: {fixture}" + (f" - {tail}." if tail else ".")
    else:
        rnd, _, rest = tail.partition(",")
        title = f"Cricket. {rnd.strip()}: {fixture}" if rnd.strip() else f"Cricket. {fixture}"
        sub = rest.strip()
        desc = f"{fixture}" + (f" - {tail}." if tail else ".")
    return title, sub, desc, studio


def willow_from_published(cid):
    """Listings still to come for `cid` from the guide published last run (used only when the feed failed and the channel has no
    other source). Entries are turned back into plain programmes: "🔴 LIVE: Cricket. A v B" -> live, title "Cricket. A v B"."""
    import xml.etree.ElementTree as XT
    try:
        req = urllib.request.Request(PUBLISHED_GUIDE, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=60) as r:
            root = XT.fromstring(gzip.decompress(r.read()))
    except Exception as e:
        print(f"  WARNING: last published guide not available for {cid} ({e})")
        return []
    now = datetime.now(timezone.utc)
    progs = []
    for el in root.iter("programme"):
        if el.get("channel") != cid:
            continue
        try:
            start = datetime.strptime(el.get("start"), "%Y%m%d%H%M%S %z").astimezone(timezone.utc)
            stop = datetime.strptime(el.get("stop"), "%Y%m%d%H%M%S %z").astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        if stop <= now:
            continue
        title = (el.findtext("title") or "").strip()
        if title.startswith(("Willow 2 Cricket", "Willow Cricket")) and "No schedule" in (el.findtext("sub-title") or ""):
            return []                                                   # the standard blocks - not real listings
        m = re.match(r"^(🔴\s*)?LIVE:\s*", title)
        live = bool(m)
        studio = bool(m) and not m.group(1)                              # live without the red ball = a Preview / Review
        title = title[m.end():] if m else title
        progs.append({"start": start, "stop": stop, "title": title, "sub": (el.findtext("sub-title") or "").strip(),
                      "desc": (el.findtext("desc") or "").strip(),
                      "cats": [c.text.strip() for c in el.findall("category") if c.text and c.text.strip() and c.text.strip() != "Live"] or list(WILLOW_CAT),
                      "year": "", "rating": "", "live": live, "new": False, "studio": studio, "raw": ""})
    progs.sort(key=lambda p: p["start"])
    return progs


def fetch_willow(uk_today):
    """{our id: [programmes]} for WILLOW_FEEDS (nothing for a channel whose feed could not be read or whose clock is unclear)."""
    import json
    from urllib.parse import urlencode
    out = {}
    body = urlencode({"showdate": f"{uk_today.month}/{uk_today.day}/{uk_today.year}", "viewtype": "week",
                      "timezone": WILLOW_FEED_TZ, "group_by_week": "1", "qty": "8"}).encode()
    for cid, path in WILLOW_FEEDS.items():
        try:
            req = urllib.request.Request(WILLOW_FEED_BASE + path, data=body, method="POST",
                                         headers={"User-Agent": HEADERS["User-Agent"], "Origin": "https://cricket.willow.tv",
                                                  "Referer": "https://cricket.willow.tv/",
                                                  "Content-Type": "application/x-www-form-urlencoded", "Accept": "*/*"})
            data, err = None, None
            for attempt in range(WILLOW_TRIES):               # the feed's server is a "dev" one and gives the odd HTTP 500
                try:
                    with urllib.request.urlopen(req, timeout=40) as r:
                        data = json.loads(r.read().decode("utf-8", "replace"))
                    break
                except Exception as e:
                    err = e
                    if attempt + 1 < WILLOW_TRIES:
                        time.sleep(WILLOW_RETRY_WAIT * (attempt + 1))
            if data is None:
                raise err
            events = [e for day in (data.get("events") or []) for e in (day.get("todaySchedule") or [])]
            off = willow_clock_offset([(_willow_time(e.get("BroadCastStartDate")), e.get("BroadCastDay")) for e in events])
            if off is None:
                raise ValueError("can't tell what clock the feed's times are in")
            shift = timedelta(minutes=off)
            print(f"  Willow feed {cid}: clock is {off / 60:+g}h from UTC")
            progs = []
            for e in events:
                start, stop = _willow_time(e.get("BroadCastStartDate")), _willow_time(e.get("BroadCastEndDate"))
                raw = e.get("Title") or ""
                if not start or not stop or stop <= start or not raw.strip():
                    continue
                start = (start - shift).replace(tzinfo=timezone.utc)
                stop = (stop - shift).replace(tzinfo=timezone.utc)
                title, sub, desc, studio = willow_text(raw)
                live = str(e.get("Live")) == "1" or bool(re.match(r"\s*(?:Continued Event from yesterday,\s*)?LIVE\b", raw, re.I))
                key = _WILLOW_LEAD.sub("", raw).strip(" ,")
                cont = progs[-1] if progs else None
                if cont and cont["raw"] == key and cont["stop"] >= start - timedelta(minutes=1):
                    cont["stop"] = max(cont["stop"], stop)            # an event that runs past midnight is listed twice
                    continue
                progs.append({"start": start, "stop": stop, "title": title, "sub": sub, "desc": desc, "cats": list(WILLOW_CAT),
                              "year": "", "rating": "", "live": live, "new": False, "studio": studio, "raw": key})
            if not progs:
                raise ValueError("no programmes in the feed")
            out[cid] = progs
            print(f"  Willow feed {cid}: {len(progs)} programmes, {sum(p['live'] for p in progs)} live"
                  f", {progs[0]['start'].astimezone(UK):%a %d %b %H:%M} to {progs[-1]['stop'].astimezone(UK):%a %d %b %H:%M} UK")
        except Exception as ex:
            print(f"  WARNING: Willow feed for {cid} not used ({ex}) - TV Passport listings / standard blocks instead")
            if cid in WILLOW_STALE_OK:
                old = willow_from_published(cid)
                if old:
                    out[cid] = old
                    print(f"  Willow feed {cid}: kept the {len(old)} listings still to come from the last published guide")
    return out


def fetch_mjh_plain():
    """{our id: [programmes]} for MJH_PLAIN (never live)."""
    import xml.etree.ElementTree as XT
    out, cache = {cid: [] for cid in MJH_PLAIN}, {}

    def when(v):
        return datetime.strptime(v, "%Y%m%d%H%M%S %z").astimezone(timezone.utc)

    for cid, (url, chan) in MJH_PLAIN.items():
        if url not in cache:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
                with urllib.request.urlopen(req, timeout=60) as r:
                    cache[url] = XT.fromstring(gzip.decompress(r.read()))
            except Exception as e:
                print(f"  WARNING: {url} not available ({e})")
                cache[url] = None
        root = cache[url]
        if root is None:
            continue
        for el in root.iter("programme"):
            if not (el.get("channel") or "").endswith(chan):
                continue
            try:
                start, stop = when(el.get("start")), when(el.get("stop"))
            except (TypeError, ValueError):
                continue
            out[cid].append({"start": start, "stop": stop, "title": (el.findtext("title") or "").strip(),
                             "sub": (el.findtext("sub-title") or "").strip(),
                             "desc": (el.findtext("desc") or "").strip(),
                             "cats": [c.text.strip() for c in el.findall("category") if c.text and c.text.strip()]
                                     or ["Sports"], "year": "", "rating": "", "live": False, "new": False})
        out[cid].sort(key=lambda p: p["start"])
        print(f"  {cid}: {len(out[cid])} programmes (i.mjh.nz)")
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


# Channels with nothing listed (3 Nov 2026): TV Passport / i.mjh.nz sometimes have no listings for a channel (Billiard TV had
# 30 programmes one day and none the next). Such a channel gets the same standard "no schedule" blocks as in SPORT_epg.py, so the
# row never reads "No information". 2-hour blocks for 24 hours only: when listings come back they are not hidden for long.
EMPTY_SUB = "No schedule available at this time."
EMPTY_DESC = ("{name}: no programmes are listed for this channel at the moment. The schedule will appear here when the "
              "broadcaster publishes it (some channels only run during events).")
EMPTY_BLOCK_HOURS = 2
EMPTY_HOURS = 24


def empty_blocks(name, now=None):
    now = (now or datetime.now(UK)).replace(minute=0, second=0, microsecond=0)
    t = now - timedelta(hours=now.hour % EMPTY_BLOCK_HOURS)
    end = t + timedelta(hours=EMPTY_HOURS)
    blocks = []
    while t < end:
        blocks.append({"start": t, "stop": t + timedelta(hours=EMPTY_BLOCK_HOURS), "title": name, "sub": EMPTY_SUB,
                       "desc": EMPTY_DESC.format(name=name), "cats": ["Sports"], "year": "", "rating": "",
                       "live": False, "new": False})
        t += timedelta(hours=EMPTY_BLOCK_HOURS)
    return blocks


def xmltv_time(dt):
    return dt.astimezone(UK).strftime("%Y%m%d%H%M%S %z")


# 12-hour clock (lower case, no space, minutes dropped on the hour: 12:30am, 3pm, 5:45pm) in every title, secondary title and description (6 Nov 2026, user request: "across the board"; the same
# code is in SPORT_epg.py, football_epg.py, scottish_epg.py, event_epg.py, USA_epg.py, TEAMS_epg.py and GENERAL_epg.py). Applied LAST,
# where each programme is written, so nothing that parses the 24-hour text earlier is affected. Every time these scripts put into
# text is UK time (Europe/London) already - see the audit in the handover.
def _clock_part(h, m):
    """12-hour clock, lower case, no space, minutes dropped on the hour: 12:30am, 3pm, 5:45pm"""
    return f"{(h % 12) or 12}{(':%02d' % m) if m else ''}{'am' if h < 12 else 'pm'}"


CLOCK_24H = re.compile(r"(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])(?!\s?[AaPp]\.?[Mm])(?!\.\d)")
CLOCK_SHORT = re.compile(r"(?<![\w:.])(\d{1,2})(?:[:.]([0-5]\d))?\s?([AaPp])(?:\.[Mm]\.|[Mm])(?!\w)")


def clock12(text):
    """EVERY clock time in a title / secondary title / description -> 12-hour with AM / PM (6 Nov 2026, user request, whole Sport
    guide; applied last, in add_programme, so nothing that parses the 24-hour text is affected): "19:00" -> "7pm", "00:15" ->
    "12:15am", "9:00 PM" / "3.30pm" style -> "9pm" / "3:30pm". Skipped: lap times ("1:23.456"), h:mm:ss, anything already "7:45 PM"."""
    t = CLOCK_24H.sub(lambda m: _clock_part(int(m.group(1)), int(m.group(2))), text or "")

    def short(m):
        h = int(m.group(1))
        if not 1 <= h <= 12:
            return m.group(0)
        mm = m.group(2)
        return f"{h}{(':' + mm) if mm and mm != '00' else ''}{'am' if m.group(3).lower() == 'a' else 'pm'}"
    return CLOCK_SHORT.sub(short, t)


# 20 Nov 2026 (user): a soccer fixture goes in the title, the competition in the sub-title, like the football guide:
# title "Bundesliga Soccer" + sub "Bayern Munich vs. 1. FC Köln" -> "Bayern Munich vs FC Cologne" + "Bundesliga".
SOCCER_TITLE_RE = re.compile(r"^(?P<comp>.{3,40}?)\s+Soccer$", re.I)
VS_RE = re.compile(r"\s+(?:vs?\.?|v)\s+", re.I)


def soccer_fixture(title, sub):
    m = SOCCER_TITLE_RE.match((title or "").strip())
    sub = (sub or "").strip()
    fixture = VS_RE.sub(" vs ", sub)
    if m and len(VS_RE.split(sub)) == 2 and len(sub) <= 70:      # exactly one "A vs. B" (not a sentence or two fixtures)
        return fixture, m.group("comp").strip()
    return title, sub


# 20 Nov 2026 (user, Willow): title "International League T20 Cricket" + sub "Desert Vipers vs. MI Emirates" read as one long line.
# A "<competition> Cricket" title with a single "A vs. B" sub-title becomes title "Cricket. Desert Vipers v MI Emirates", sub "International League T20".
CRICKET_TITLE_RE = re.compile(r"^(?P<comp>.{3,50}?)\s+Cricket$", re.I)


def cricket_fixture(title, sub):
    m = CRICKET_TITLE_RE.match((title or "").strip())
    sub = (sub or "").strip()
    sides = VS_RE.split(sub)
    if m and len(sides) == 2 and len(sub) <= 70 and all(x.strip() for x in sides):
        comp = re.sub(r"\bleague\b", "League", m.group("comp").strip())
        return f"Cricket. {sides[0].strip()} v {sides[1].strip()}", comp
    return title, sub


CRICKET_COMP_RE = re.compile(r"(?i)\b(Abu Dhabi T10(?: League)?)\b")
ASIA_CUP_RE = re.compile(r"(?i)\b(ACC Men['\u2019]s (?:U19 )?Asia Cup|Asia Cup)( Rising(?: Stars)?)?\s*$")

# 20 Nov 2026 (user): every listing gets its sport at the start of the title unless the title already says it -
# "🔴 LIVE: Tennis. ATP Finals", "🔴 LIVE: Cricket. WBBL Hobart Hurricanes v Sydney Thunder", "NBA" -> "Basketball. NBA ...".
# The sport is worked out from the title + sub-title (competition names / abbreviations), first matching rule wins.
# NOT done for football (the clubs and leagues are obvious and nearly every listing is football) or motorsport / horse racing
# (the series names say it). To add a sport or a competition, add it to SPORT_RULES; SPORT_SAID says which words in the
# title already name the sport.
SPORT_RULES = [
    ("Tennis", r"\bATP\b|\bWTA\b|Wimbledon|Roland[- ]Garros|French Open|Australian Open|Davis Cup|Billie Jean King|(?i:\bBJK Cup)|Laver Cup|\bNitto\b|Next Gen Finals|Hopman Cup|United Cup|Stockholm Open"),
    ("Cricket", r"^(?:Test|ODIs?|T20Is?)(?:\s-|\s*$)|\b(?:T20I?|T10|ODIs?|IPL|WBBL|WPL|PSL|CPL|SA20|ILT20|MLC|LPL|BPL|ICC|Ashes|The Hundred|Big Bash|Sheffield Shield|Ranji Trophy|County Championship|Vitality Blast|Metro Bank One.Day Cup|Nepal Premier League|Indian Premier League|Syed Mushtaq Ali|Champions Trophy|Extraaa Innings|Cricbuzz|Lords Of England|Vijay Hazare)\b|\b\d(?:st|nd|rd|th) (?:Test|ODI|T20I?)\b"),
    ("Rugby League", r"\bNRLW?\b|State of Origin|\bRLWC\d*\b|Challenge Cup Final"),
    ("Rugby Union", r"Six Nations|Rugby Championship|\bURC\b|United Rugby|Top 14|Pro D2|Super Rugby|Gallagher (?:PREM|Premiership)|\bPREM\b|\bPWR\b|Premiership Rugby|Champions Cup|Autumn Nations|Nations Series|Bunnings NPC|Currie Cup|Lions Tour"),
    ("Golf", r"\b(?:PGA|LPGA|LIV Golf|DP World Tour|Ryder Cup|Solheim Cup|Presidents Cup|Korn Ferry|Race to Dubai|Q-School|USPGA|Asian Tour|Rolex Grand Final)\b|Open Championship|Augusta National"),
    ("Basketball", r"\b(?:NBA|WNBA|NBL|WNBL|FIBA|EuroLeague|EuroCup|NCAAB|G League|East Asia Super League|Liga ACB)\b|March Madness"),
    ("American Football", r"\b(?:NFL|NCAAF|CFL|CFP|CFB)\b|Super Bowl|Pro Football Talk|Football Night In America|College GameDay"),
    ("Ice Hockey", r"\b(?:NHL|KHL|AHL|EIHL|IIHF|SHL)\b|Stanley Cup"),
    ("Baseball", r"\b(?:MLB|NPB|KBO)\b|World Series(?! of)"),
    ("Australian Rules", r"\bAFLW?\b"),
    ("Darts", r"\bPDC\b|World Matchplay"),
    ("Snooker", r"\bWST(?::| Tour| Snooker)|Crucible|Champion of Champions|In The Frame"),
    ("MMA", r"\b(?:UFC|PFL|KSW|Oktagon|Bellator)\b|The Ultimate Fighter|Total Combat|ONE Championship|ONE Fight Night|ONE Friday Fights|Cage Warriors"),
    ("Boxing", r"Matchroom|Queensberry|Top Rank|\bGolden Boy\b|\bKOTV\b"),
    ("Wrestling", r"\b(?:WWE|AEW|TNA)\b|SmackDown|WrestleMania"),
    ("Cycling", r"\bUCI\b|Tour de France|Giro d.Italia|La Vuelta|Paris-Roubaix|Tour Down Under|Arctic Race of Norway|Colocross"),
    ("Athletics", r"Diamond League"),
    ("Volleyball", r"\b(?:VNL|CEV)\b|SuperLega|Volleyball Nations"),
    ("Sailing", r"\bSailGP\b|America.s Cup|Vend[ée]e Globe"),
    ("Show Jumping", r"\bLongines\b|Global Champions|\bGCL\b|\bLGCT\b|\bFEI\b|Jumping World Cup|Show Jumping|Grand Prix Jumping"),
    ("Badminton", r"\bBWF\b|Thomas (?:&|and) Uber"),
    ("Biathlon", r"\bIBU\b"),
    ("Swimming", r"Aquatics|\bFINA\b"),
    ("Handball", r"\bEHF\b"),
]
SPORT_RULES = [(n, re.compile(rx, re.I)) for n, rx in SPORT_RULES]
SPORT_SAID = {
    "Tennis": r"t[eé]nn?is", "Cricket": r"cricket", "Rugby League": r"rugby", "Rugby Union": r"rugby", "Golf": r"golf",
    "Basketball": r"basket|baloncesto|pallacanestro|basquet", "American Football": r"american football|college football|football am[eé]ricain|futebol americano",
    "Ice Hockey": r"hockey", "Baseball": r"baseball|b[eé]isbol|beisebol", "Australian Rules": r"aussie rules|australian rules",
    "Darts": r"darts", "Snooker": r"snooker", "MMA": r"\bmma\b|martial arts", "Boxing": r"\bbox(?:ing|e|eo|en)\b",
    "Wrestling": r"wrestl|lucha", "Cycling": r"cycl|ciclismo|cyclisme|radsport", "Athletics": r"athletic|atletica|athl[eé]tisme",
    "Volleyball": r"volley|voleibol", "Sailing": r"sail", "Show Jumping": r"jumping|equestri|horse riding|riding:|ridebane|ecuestre|reiten|hípica|hippique", "Badminton": r"badminton", "Biathlon": r"biathl", "Swimming": r"swim|nuoto|natation", "Netball": r"netball", "Handball": r"handball|balonmano",
}
SPORT_SAID = {k: re.compile(v, re.I) for k, v in SPORT_SAID.items()}
LIVE_LEAD_RE = re.compile(r"^((?:🔴\s*)?(?:LIVE[:,]\s*)?)")


# Fixtures ("A v B", "A vs B") with no recognisable competition: if the description names exactly one sport, that is the sport
# ("New Zealand vs India" + "...cricket...", "Atlanta v Boston" + "...golf...").
FIXTURE_RE = re.compile(r"\S\s(?:v|vs\.?)\s\S")
DESC_SPORT = {"Cricket": r"cricket|\bwickets?\b", "Tennis": r"(?<!table )tennis", "Basketball": r"basketball", "American Football": r"american football|\bNFL\b|college football",
              "Ice Hockey": r"ice hockey|\bNHL\b", "Baseball": r"baseball|\bMLB\b", "Golf": r"\bgolf", "Rugby League": r"rugby league", "Handball": r"handball", "Volleyball": r"volleyball", "Netball": r"netball",
              "Australian Rules": r"\bAFL\b|aussie rules|australian rules"}
DESC_SPORT = {k: re.compile(v, re.I) for k, v in DESC_SPORT.items()}


# Names that are never anything but this sport, whatever the title looks like (checked against the description too).
DESC_STRONG = {"Show Jumping": re.compile(r"(?i)show[- ]jumping"),
               "Rugby Union": re.compile(r"(?i)PREM Rugby|Gallagher PREM|Premiership Women.s Rugby|Premiership Rugby|Rugby Union")}


def add_sport(title, sub, cid="", desc=""):
    if not title:
        return title
    m = LIVE_LEAD_RE.match(title)
    body = title[m.end():]
    hay = f"{body} {sub or ''}"
    sport = None
    for name, rx in SPORT_RULES:
        if rx.search(hay):
            sport = name
            break
    if sport is None and desc:
        if not re.search(r"(?i)pentathlon|triathlon|racing|^This is\b", hay):
            sport = next((n for n, rx in DESC_STRONG.items() if rx.search(desc[:400])), None)
    if sport is None and desc and FIXTURE_RE.search(body):
        found = [n for n, rx in DESC_SPORT.items() if rx.search(desc[:400])]
        if len(found) == 1:
            sport = found[0]
    if sport is None and not (CRICKET_COMP_RE.search(hay) or (ASIA_CUP_RE.search(hay) and re.search(r"(?i)ACC|Rising", hay))):
        return title
    sport = sport or "Cricket"
    if SPORT_SAID[sport].search(body) or body.lower().startswith(sport.lower()):
        return title
    return f"{m.group(1)}{sport}. {body}"




def fix_team_names(text):
    """Köln is always Cologne ("1. FC Köln" -> "FC Cologne"); Bayern is Munich, never München / Munchen."""
    if not text:
        return text
    text = re.sub(r"\b1\.\s*FC K(?:ö|o|oe)ln\b", "FC Cologne", text)
    text = re.sub(r"\bK(?:ö|oe)ln\b", "Cologne", text)
    return re.sub(r"\bM(?:ü|u|ue)nchen\b", "Munich", text)


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
            goal_rush = cid in GOAL_RUSH_CHANNELS and bool(GOAL_RUSH_RE.search(p["title"]))
            if goal_rush:
                live = True
            cricket_event = cid in CRICKET_EVENT_CHANNELS and not p.get("studio") and not CRICKET_STUDIO_RE.search(p["title"])
            prefix = RED_BALL_PREFIX if (goal_rush or cricket_event or ((cid in RED_BALL_CHANNELS or cid in GENERAL_CHANNELS)
                                                                         and is_event(p))) else LIVE_PREFIX
            ptitle, psub, pdesc = cricket_fixture(*soccer_fixture(p["title"], p["sub"])) + (p["desc"],)
            ptitle, psub, pdesc = (fix_team_names(x) for x in (ptitle, psub, pdesc))
            ptitle = add_sport(ptitle, psub, cid, pdesc)
            title = (prefix + ptitle) if live else ptitle
            cats = p["cats"] + (["Live"] if live else [])
            out = [f'  <programme start="{xmltv_time(p["start"])}" stop="{xmltv_time(p["stop"])}" '
                   f'channel={quoteattr(cid)}>',
                   f'    <title lang="{lang}">{escape(clock12(title))}</title>']
            if psub:
                out.append(f'    <sub-title lang="{lang}">{escape(clock12(psub))}</sub-title>')
            if pdesc:
                out.append(f'    <desc lang="{lang}">{escape(clock12(pdesc))}</desc>')
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
    raw.update(fetch_mjh_plain())                   # Billiard TV (Plex)
    raw.update(fetch_willow(uk_today))              # Willow + Willow 2 (Willow's own schedule feed); a failed feed changes nothing
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
    names = {c[0]: c[1] for c in every}
    for cid in blank:                                # nothing listed: the standard "no schedule" blocks
        guide[cid] = empty_blocks(names[cid])
    if blank:
        print(f"  Standard 'no schedule' blocks added for {len(blank)} channel(s)")
    for path, chans in GUIDES.items():
        n = write(path, chans, guide)
        print(f"Wrote {path}: {len(chans)} channels, {n} programmes")


if __name__ == "__main__":
    main()

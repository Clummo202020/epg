#!/usr/bin/env python3
"""
football_epg.py - XMLTV guide of football fixtures for IPTV event channels.

One file covers everything that used to be split across two scripts:
  * English clubs (top four tiers): every competition they play in
  * Non-English clubs: UEFA Champions League, Europa League and Conference League
  * Spanish clubs: La Liga (Real.Madrid.LaLiga, Barcelona.LaLiga ...)

Data comes from ESPN's public (unofficial, key-free) site API.

What this script does, and why (lessons from getting it working on MyTV Online
and PlaylistLabs):

  * FIXED CHANNEL IDS AND FILE NAME (default).  Channels are <club>.<competition>,
    e.g. Brentford.Prem, Arsenal.ChampsLge, and the output always overwrites
    OUTPUT_NAME below - the file name used on GitHub - so the raw link never
    changes.  PlaylistLabs re-reads that link and ADDS new programmes after the
    latest one it holds for each channel id; channels stay linked for good.
  * It never changes programmes it already holds, so when a kick-off time moves
    use --run-ids once: ids become <club>.<competition>Run<n> (Brentford.PremRun3),
    brand new to PlaylistLabs, so it takes the whole file; relink to those ids.
    The last run number is kept in football_epg_run.json next to this script.
    (--suffix N forces a run number.)  --unique gives a new file name each run.
  * FILLER PROGRAMMES.  Between now and each kick-off the channel shows
    "Brentford v Liverpool (Sat 17 Oct, 15:00)" with the match details,
    so the guide never says "No Information" before the match.  Filler is cut
    into blocks of at most 2 hours (on clock boundaries): PlaylistLabs skips
    programmes that run much longer than a normal 2-hour event.
    (--filler-hours changes the block length; 0 = one block per gap.)
  * STANDARD XMLTV HEADER (with the usual DOCTYPE line, as in the files that
    PlaylistLabs accepted with filler intact), UTF-8, every programme has a title,
    sub-title, description and categories. The file is re-read after writing to
    prove it parses.
  * All times are Europe/London (GMT/BST offsets written into each time).

Usage:
    python3 football_epg.py                 # next 10 days -> OUTPUT_NAME (fixed ids, overwrites)
    python3 football_epg.py --days 30       # next 30 days
    python3 football_epg.py --days 0        # rest of the season (to 30 June)
    python3 football_epg.py --run-ids       # fresh ids (Brentford.PremRun3) when kick-off times change
    python3 football_epg.py --suffix 12     # run ids with run 12 forced; later runs go on from it
    python3 football_epg.py --unique        # new file name each run: football_epg_<date-time>_<random>.xml
    python3 football_epg.py --english-only  # skip non-English clubs' UEFA channels
    python3 football_epg.py --channel-list channels.csv   # also write id,name list

Only the Python standard library is needed (the optional `certifi` package is
used for SSL certificates if installed). On Windows: pip install tzdata
"""

import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
LONDON = ZoneInfo("Europe/London")
HEADERS = {"User-Agent": "Mozilla/5.0 (football_epg.py)"}

# display name -> (ESPN league slug, channel-id competition part)
COMPETITIONS = {
    "Premier League":         ("eng.1", "Prem"),
    "Championship":           ("eng.2", "Championship"),
    "League One":             ("eng.3", "League1"),
    "League Two":             ("eng.4", "League2"),
    "FA Cup":                 ("eng.fa", "FACup"),
    "Carabao Cup":            ("eng.league_cup", "Carabao"),
    "UEFA Champions League":  ("uefa.champions", "ChampsLge"),
    "UEFA Europa League":     ("uefa.europa", "Europa"),
    "UEFA Conference League": ("uefa.europa.conf", "ConfLeague"),
    "La Liga":                ("esp.1", "LaLiga"),
}

# Leagues that define "English clubs".
ENGLISH_LEAGUES = ["Premier League", "Championship", "League One", "League Two"]

# Competitions in which non-English clubs also get channels.
UEFA_COMPETITIONS = ["UEFA Champions League", "UEFA Europa League", "UEFA Conference League"]

# Foreign leagues in which every club gets a channel (--english-only skips them).
OTHER_LEAGUES = ["La Liga"]

# Fixtures with these statuses have no reliable kick-off and are skipped.
SKIP_STATUSES = {"STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_CANCELLED",
                 "STATUS_ABANDONED", "STATUS_FORFEIT"}

# Club name tidy-ups, used in channel names, channel ids and match titles.
# Changing these changes channel ids, so leave them alone once mapped.
NAME_RULES = [
    (r"^AFC Bournemouth$", "Bournemouth"),
    (r"^Wolverhampton Wanderers$", "Wolves"),
    (r"^Milton Keynes Dons$", "MK Dons"),
    (r"^Feyenoord Rotterdam$", "Feyenoord"),
    (r"\bUnited\b", "Utd"),
]

RUN_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "football_epg_run.json")


def load_last_run():
    try:
        with open(RUN_STATE_FILE, encoding="utf-8") as f:
            return int(json.load(f)["last_run"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_last_run(n):
    try:
        with open(RUN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_run": n}, f)
    except OSError as e:
        print(f"WARNING: could not save run number to {RUN_STATE_FILE}: {e}")
OUTPUT_NAME = "football_epg.xml"   # the file name on GitHub

# Premier League Goal Rush channel: one programme for every slot where at least
# GOAL_RUSH_MIN Premier League matches kick off at the same time (e.g. Sat 15:00).
GOAL_RUSH = True                   # False = leave the channel out
GOAL_RUSH_ID = "GoalRush2.id"
GOAL_RUSH_COMP = "Premier League"
GOAL_RUSH_MIN = 2
# Channels to name at the end of each Goal Rush description, e.g.
# ["Hub Premier 1 (Singapore)", "Sky Sport 8 (New Zealand)"]; empty = none
GOAL_RUSH_ON = []

# The Goal Rush "main game" is whichever slot match these channels show live,
# read from the SPORT guide (the local file in the repo, else the GitHub copy).
GOAL_RUSH_MAIN_FROM = ["HK.NowSportsPLTV", "SG.HubPremier1", "NZ.SkySport8NZ"]   # first match wins
GOAL_RUSH_GUIDE_FILE = "SPORT_epg.xml.gz"
GOAL_RUSH_GUIDE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/SPORT_epg.xml.gz"
# PlaylistLabs never rewrites programmes it already holds, so a Goal Rush slot is
# held back until its main game is known; a slot whose main game still isn't
# listed this close to kick-off is published without one.
GOAL_RUSH_WAIT_DAYS = 2

# One general channel for every UEFA match: a programme for each kick-off time,
# listing all the Champions / Europa / Conference League matches starting then.
UEFA_CHANNEL = True                # False = leave the channel out
UEFA_CHANNEL_ID = "UEFA.comps"
UEFA_CHANNEL_NAME = "UEFA Competitions"
UEFA_CHANNEL_TITLE = "Streams are live at match time only."
# Generic (all-sport) streaming services: plain 2-hour blocks with the same
# title and description, not tied to any fixtures. (id, name, title, description)
DUMMY_CHANNELS = [
    ("peacock.us", "Peacock", "Stream is live at event time only.",
     "Peacock, live sports streaming."),
    ("stan.au", "Stan Sport", "Stream is live at event time only.",
     "Stan Sport, live sports streaming."),
    ("paramountplus.us", "Paramount+", "Stream is live at event time only.",
     "Paramount+, live sports streaming."),
    ("hbomax.uk", "HBO Max", "Stream is live at event time only.",
     "HBO Max, live sports streaming."),
    ("sportsnetplus.ca", "Sportsnet+", "Stream is live at event time only.",
     "Sportsnet+, live sports streaming."),
    ("tsnplus.ca", "TSN+", "Stream is live at event time only.",
     "TSN+, live sports streaming."),
    ("tod.qa", "TOD", "Stream is live at event time only.",
     "TOD, live sports streaming."),
    ("skysports+.uk", "Sky Sports+", "Live at event time only.",
     "Skysports+ is a streaming service. No programme guide is available. "
     "You will need to scroll through the channels to see what's on where."),
    ("aussie.rules", "Aussie Rules", "Stream is live at event time only",
     "Aussie Rules footy from the Australian Football League (AFL)."),
    ("darts.uk", "Darts", "Stream is live at event time only.",
     "Live darts events from around the world."),
    ("espn+.us", "ESPN+", "Stream is live at event time only.",
     "Live sports from ESPN+ in the USA"),
    ("f1drivers.uk", "F1 Drivers", "Stream is live at event time only.",
     "Formula 1 driver onboard cameras, live during race weekends."),
    ("f1.uk", "Formula 1", "Stream is live at event time only",
     "Live F1 Grand Prix events and races."),
    ("gaelic.sports", "Gaelic Sports", "Stream is live at event time only.",
     "Gaelic Football, Hurling and Camogie. Live from Ireland."),
    ("replay.uk", "Game Replays", "Replays",
     "See INFO channel for schedules."),
    ("mls.na", "MLS", "Stream is live at match time only.",
     "Major League Soccer from North America."),
    ("nrl.aus", "NRL", "Stream is live at event time only.",
     "Rugby League action from Australia"),
    ("ppv.events", "PPV Events", "Stream is live at event time only.",
     "Live Pay Per View events from around the world."),
    ("rugby.union", "Rugby Union", "Stream is live at event time only.",
     "Live Rugby from around the world."),
    ("rugby.league", "Super League Rugby", "Stream is live at event time only.",
     "Action from the Bet Fred Super League."),
    ("usaevents.us", "USA Events", "Stream is live at event time only.",
     "Various live events streamed for American TV."),
    ("canadalive.ca", "Canada Events", "Stream is live at event time only.",
     "Various live events streamed for Canadian TV."),
    ("dazn.live", "DAZN", "Stream is live at event time only.",
     "DAZN, live sports streaming."),
    ("nfl.usa", "NFL", "Stream is live at event time only.",
     "Live American football from the NFL."),
    ("mlb.usa", "MLB", "Stream is live at event time only.",
     "Live baseball from the MLB."),
    ("nba.usa", "NBA", "Stream is live at event time only.",
     "Live basketball from the NBA."),
    ("nhl.usa", "NHL", "Stream is live at event time only.",
     "Live ice hockey from the NHL."),
    ("tennis.live", "Tennis", "Stream is live at event time only.",
     "Live tennis from around the world."),
    ("boxing.live", "Boxing", "Stream is live at event time only.",
     "Live boxing from around the world."),
]
DUMMY_HOURS = 2          # block length
DUMMY_DAYS = 10          # how far ahead the blocks run

UEFA_CHANNEL_DESC = ("Matches that fall under the UEFA umbrella.\n\n"
                     "Club competitions: Champions League, Europa League, "
                     "Conference League, and Super Cup.")
FILLER_HOURS = 2          # longest filler block in hours (0 = one block per gap)
DOCTYPE = True            # write the standard XMLTV DOCTYPE line
COUNTDOWN = False         # add "- kick-off in 2d 23h" to each filler block
FILLER_STYLE = "plain"    # "plain": "Brentford v Liverpool (Sat 17 Oct, 15:00)"
                          # "next":  "Next: Brentford v Liverpool - Sat 17 Oct, 15:00"


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ssl_context()


class NoData(Exception):
    """ESPN answered 400/404 (bad slug or no data for that request)."""
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


def get_json(url, params=None, retries=3):
    """Parsed JSON, or None (with a warning) if ESPN can't be reached after a few tries,
    so one failed request leaves a gap instead of stopping the whole run."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                raise NoData(e.code)
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = str(getattr(e, "reason", e))
        time.sleep(1.5 * (attempt + 1))
    print(f"  WARNING: could not fetch {url}: {last_err} - skipped", file=sys.stderr)
    return None


# --------------------------------------------------------------------------
# ESPN data
# --------------------------------------------------------------------------
def fetch_english_clubs():
    """{team_id: name} for every club in the top four English tiers."""
    clubs = {}
    for comp in ENGLISH_LEAGUES:
        slug = COMPETITIONS[comp][0]
        print(f"Fetching clubs: {comp} ...")
        try:
            data = get_json(f"{ESPN_BASE}/{slug}/teams", {"limit": 100})
            teams = data["sports"][0]["leagues"][0]["teams"] if data else []
        except NoData:
            print(f"  WARNING: no team list for {slug}")
            continue
        except (KeyError, IndexError, TypeError):
            teams = []
        for t in teams:
            team = t.get("team") or {}
            if team.get("id"):
                clubs[str(team["id"])] = short_name(team.get("displayName") or team.get("name"))
        print(f"  {len(teams)} clubs")
    return clubs


def fetch_events(start, end):
    """{competition: [event, ...]}. ESPN wants one request per day."""
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    out = {}
    for comp, (slug, _) in COMPETITIONS.items():
        print(f"Fetching fixtures: {comp} ...")
        try:
            get_json(f"{ESPN_BASE}/{slug}/scoreboard", {"dates": f"{start:%Y%m%d}"})
        except NoData as e:
            print(f"  WARNING: ESPN rejected '{slug}' (HTTP {e.code}) - skipping")
            out[comp] = []
            continue

        def grab(day):
            try:
                data = get_json(f"{ESPN_BASE}/{slug}/scoreboard", {"dates": f"{day:%Y%m%d}"})
            except NoData:
                return []
            return (data or {}).get("events") or []

        events, seen = [], set()
        with ThreadPoolExecutor(max_workers=8) as pool:
            for day_events in pool.map(grab, days):
                for ev in day_events:
                    if ev.get("id") not in seen:
                        seen.add(ev.get("id"))
                        events.append(ev)
        print(f"  {len(events)} fixtures")
        out[comp] = events
    return out


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def utd(text):
    """'United' -> 'Utd' anywhere in free text (venues, round notes ...)."""
    return re.sub(r"\bUnited\b", "Utd", text, flags=re.I) if text else text


def short_name(name):
    if not name:
        return name
    for pattern, repl in NAME_RULES:
        name = re.sub(pattern, repl, name, flags=re.I)
    return name


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", ".", text).strip(".")


def parse_espn_time(s):
    """ESPN dates look like '2026-10-17T14:00Z' (UTC)."""
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def xmltv_time(dt):
    return dt.astimezone(LONDON).strftime("%Y%m%d%H%M%S %z")


# --------------------------------------------------------------------------
# Matches and channels
# --------------------------------------------------------------------------
def collect_matches(events_by_comp, match_minutes):
    matches, seen = [], set()
    for comp_name, events in events_by_comp.items():
        for ev in events:
            comp = (ev.get("competitions") or [{}])[0]
            status = ((ev.get("status") or {}).get("type") or {}).get("name", "")
            if status in SKIP_STATUSES or not ev.get("date") or ev.get("id") in seen:
                continue
            sides = {c.get("homeAway"): c for c in comp.get("competitors", [])}
            if "home" not in sides or "away" not in sides:
                continue
            seen.add(ev.get("id"))
            h, a = sides["home"].get("team") or {}, sides["away"].get("team") or {}
            title = f"{short_name(h.get('displayName'))} v {short_name(a.get('displayName'))}"
            start = parse_espn_time(ev["date"])
            ko = start.astimezone(LONDON)

            notes = [n.get("headline") for n in comp.get("notes", []) if n.get("headline")]
            sub = utd(comp_name + (f" - {notes[0]}" if notes else ""))

            tbc = comp.get("timeValid") is False             # ESPN's time is only a placeholder
            desc = [f"{title}."]    # the competition is in the secondary title
            venue = comp.get("venue") or {}
            if venue.get("fullName"):
                city = (venue.get("address") or {}).get("city")
                desc.append(f"{venue['fullName']}{', ' + city if city else ''}.")
            desc.append("Kick-off time to be confirmed." if tbc else f"Kick-off: {ko:%H:%M}.")

            matches.append({
                "comp": comp_name, "title": title, "sub": sub, "desc": utd(" ".join(desc)),
                "start": start, "stop": start + timedelta(minutes=match_minutes),
                "when": f"{ko:%a %d %b}, {'TBC' if tbc else f'{ko:%H:%M}'}",
                "teams": [h, a], "tbc": tbc,
            })
    return matches


def load_main_game_listings():
    """[(start, stop, text)] for the GOAL_RUSH_MAIN_FROM channels in the SPORT guide."""
    import gzip
    raw = None
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), GOAL_RUSH_GUIDE_FILE)
    try:
        if os.path.exists(local):
            with open(local, "rb") as f:
                raw = f.read()
        else:
            req = urllib.request.Request(GOAL_RUSH_GUIDE_URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                raw = resp.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        root = ET.fromstring(raw)
    except Exception as e:          # no guide = no main game, never a failed run
        print(f"  WARNING: Goal Rush main game: could not read the SPORT guide ({e})")
        return []
    wanted = set(GOAL_RUSH_MAIN_FROM)
    out = []
    for p in root.iter("programme"):
        if p.get("channel") not in wanted:
            continue
        try:
            start = datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
            stop = datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        except (TypeError, ValueError):
            continue
        text = " ".join((e.text or "") for e in p if e.tag in ("title", "sub-title", "desc"))
        out.append((GOAL_RUSH_MAIN_FROM.index(p.get("channel")), start, stop, text))
    out.sort(key=lambda r: r[0])                 # channel priority order
    return [(a, b, t) for _, a, b, t in out]


TEAM_ALIASES = {
    "manchester utd": ["man utd", "man united", "manchester united"],
    "manchester city": ["man city"],
    "tottenham hotspur": ["spurs", "tottenham"],
    "wolves": ["wolverhampton"],
    "nottingham forest": ["nott'm forest", "notts forest", "forest"],
    "brighton & hove albion": ["brighton"],
    "crystal palace": ["palace"],
    "aston villa": ["villa"],
    "west ham utd": ["west ham"],
    "newcastle utd": ["newcastle"],
    "leeds utd": ["leeds"],
    "sheffield utd": ["sheffield united", "sheff utd"],
}
AMBIGUOUS_FIRST_WORDS = {"manchester", "west", "sheffield", "nottingham", "aston", "crystal",
                         "queens", "afc", "fc", "real", "athletic"}


def _norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9'&]+", " ", text.replace(" and ", " & ")) + " "


def _aliases(name):
    n = _norm(name).strip()
    names = {n, n.replace(" utd", " united"), n.replace("&", "and")}
    names.update(TEAM_ALIASES.get(n, []))
    first = n.split()[0] if n else ""
    if first and first not in AMBIGUOUS_FIRST_WORDS and len(first) > 3:
        names.add(first)
    return [_norm(a) for a in names if a]


def find_main_game(ms, listings):
    """The slot match a GOAL_RUSH_MAIN_FROM channel shows live at kick-off, or None."""
    ko = ms[0]["start"]
    on_air = [t for a, b, t in listings
              if a <= ko + timedelta(minutes=20) and b >= ko + timedelta(minutes=30)]
    for text in on_air:
        txt = _norm(text)
        for m in ms:
            h, a = (short_name(t.get("displayName")) for t in m["teams"])
            if any(x in txt for x in _aliases(h)) and any(x in txt for x in _aliases(a)):
                return m
    return None


def slot_channel(matches, comps, chan_id, name, title, desc, live_title=None):
    """A general "streams are live at match time" channel: the same title and
    description throughout, split at the kick-off times of every match in
    `comps` (one block per kick-off time, never overlapping); match blocks get
    live_title if given. No secondary title."""
    slots = {}
    for m in matches:
        if m["comp"] in comps and not m.get("tbc"):
            slots.setdefault(m["start"], []).append(m)
    starts = sorted(slots)
    shows = []
    for i, start in enumerate(starts):
        ms = slots[start]
        ko = start.astimezone(LONDON)
        label = ms[0]["comp"] if len({m["comp"] for m in ms}) == 1 else name
        stop = max(m["stop"] for m in ms)
        if i + 1 < len(starts):
            stop = min(stop, starts[i + 1])          # never overlap the next kick-off
        shows.append({
            "comp": label, "title": label, "sub": "", "desc": desc,
            "start": start, "stop": stop,
            "when": f"{ko:%a %d %b}, {ko:%H:%M}", "teams": [], "tbc": False,
            "fixed_title": title, "fixed_desc": desc,
            "filler_sub": "", "live_sub": "",          # no secondary title
            "live_title": live_title or title,         # match blocks only
        })
    return (chan_id, name, None, shows)


def uefa_channel(matches, suffix):
    return slot_channel(matches, UEFA_COMPETITIONS, f"{UEFA_CHANNEL_ID}{suffix}",
                        UEFA_CHANNEL_NAME, UEFA_CHANNEL_TITLE, UEFA_CHANNEL_DESC,
                        live_title=f"🔴 LIVE – {UEFA_CHANNEL_TITLE}")


def dummy_channel(chan_id, name, title, desc):
    """A generic channel: back-to-back DUMMY_HOURS blocks, same title and
    description, no secondary title, not tied to any fixtures."""
    now = datetime.now(LONDON)
    t = now.replace(minute=0, second=0, microsecond=0)
    t -= timedelta(hours=t.hour % DUMMY_HOURS)          # align to 00:00, 02:00 ...
    end = t + timedelta(days=DUMMY_DAYS)
    shows = []
    while t < end:
        stop = t + timedelta(hours=DUMMY_HOURS)
        shows.append({
            "comp": "Sports", "title": title, "sub": "", "desc": desc,
            "start": t.astimezone(timezone.utc), "stop": stop.astimezone(timezone.utc),
            "when": "", "teams": [], "tbc": False, "live_sub": "", "not_live": True,
        })
        t = stop
    return (chan_id, name, None, shows)


def goal_rush_channel(matches, suffix):
    """A 'Premier League Goal Rush' channel: one programme for every time slot in
    which at least GOAL_RUSH_MIN Premier League matches kick off together
    (usually Saturday 15:00), listing the matches in that slot."""
    on_air = ""
    if GOAL_RUSH_ON:
        names = GOAL_RUSH_ON[0] if len(GOAL_RUSH_ON) == 1 else \
            ", ".join(GOAL_RUSH_ON[:-1]) + " and " + GOAL_RUSH_ON[-1]
        on_air = f" On {names}."
    slots = {}
    for m in matches:
        if m["comp"] == GOAL_RUSH_COMP and not m.get("tbc"):
            slots.setdefault(m["start"], []).append(m)
    listings = load_main_game_listings() if GOAL_RUSH_MAIN_FROM else []
    hold_from = datetime.now(timezone.utc) + timedelta(days=GOAL_RUSH_WAIT_DAYS)
    shows = []
    for start, ms in sorted(slots.items()):
        if len(ms) < GOAL_RUSH_MIN:
            continue
        ko = start.astimezone(LONDON)
        main = find_main_game(ms, listings) if listings else None
        if main is None and GOAL_RUSH_MAIN_FROM and start > hold_from:
            print(f"  Goal Rush {ko:%a %d %b %H:%M}: main game not listed yet - held back")
            break                       # later slots wait too, so nothing is skipped
        if main:
            others = sorted(m["title"] for m in ms if m is not main)
            print(f"  Goal Rush {ko:%a %d %b %H:%M}: main game {main['title']}")
            desc = (f"Goal Rush. Main game: {main['title']}, with updates and "
                    f"goal flashes from {', '.join(others)}.")
        else:
            games = ", ".join(sorted(m["title"] for m in ms))
            desc = f"Goal Rush: live action from {len(ms)} matches - {games}."
        shows.append({
            "comp": GOAL_RUSH_COMP, "title": "Goal Rush", "sub": GOAL_RUSH_COMP,
            "desc": desc + on_air,
            "start": start, "stop": max(m["stop"] for m in ms),
            "when": f"{ko:%a %d %b}, {ko:%H:%M}", "teams": [], "tbc": False,
            "filler_prefix": "Coming up",
            "filler_sub": f"⏭ Goal Rush {ko:%a} {ko.day} {ko:%b}",
            "live_sub": "🔴 LIVE: Goal Rush",
        })
    return (f"{GOAL_RUSH_ID}{suffix}", "Goal Rush", None, shows)   # kept even if empty


def build_channels(matches, english, suffix, english_only):
    """[(channel_id, display_name, logo, [matches])], sorted by name."""
    names, logos = dict(english), {}
    for m in matches:
        for t in m["teams"]:
            tid = str(t.get("id", ""))
            if tid:
                names.setdefault(tid, short_name(t.get("displayName")) or f"Team {tid}")
                logos.setdefault(tid, t.get("logo"))

    # Unique id base per club (Brentford, Real.Madrid, ...)
    bases, used = {}, set()
    for tid, name in sorted(names.items(), key=lambda kv: kv[1] or ""):
        base = slugify(name or "") or f"team{tid}"
        if base in used:
            base = f"{base}.{tid}"
        used.add(base)
        bases[tid] = base

    grouped = {}
    for m in matches:
        for t in m["teams"]:
            tid = str(t.get("id", ""))
            if not tid:
                continue
            if tid in english or (not english_only and m["comp"] in UEFA_COMPETITIONS + OTHER_LEAGUES):
                grouped.setdefault((tid, m["comp"]), []).append(m)

    channels = []
    for (tid, comp), ms in grouped.items():
        ext = COMPETITIONS[comp][1]
        channels.append((f"{bases[tid]}.{ext}{suffix}", f"{names[tid]} {comp}",
                         logos.get(tid), sorted(ms, key=lambda m: m["start"])))
    if UEFA_CHANNEL and not english_only:
        channels.append(uefa_channel(matches, suffix))
    for cid, cname, ctitle, cdesc in DUMMY_CHANNELS:
        channels.append(dummy_channel(f"{cid}{suffix}", cname, ctitle, cdesc))
    if GOAL_RUSH:
        gr = goal_rush_channel(matches, suffix)
        if gr:
            channels.append(gr)
    channels.sort(key=lambda c: c[1])
    return channels


# --------------------------------------------------------------------------
# XMLTV
# --------------------------------------------------------------------------
def add_programme(tv, chan_id, start, stop, title, sub, desc, comp, live=False):
    p = ET.SubElement(tv, "programme", {
        "start": xmltv_time(start), "stop": xmltv_time(stop), "channel": chan_id})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:                                   # "" = no secondary title (UEFA.comps)
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    cats = ("Sports",) if comp == "Sports" else ("Sports", "Football", comp)   # generic: Sports only
    for cat in cats + (("Live",) if live else ()):
        ET.SubElement(p, "category", {"lang": "en"}).text = cat


def countdown(delta):
    """timedelta -> '2d 6h', '5h', '45m'."""
    mins = max(int(delta.total_seconds() // 60), 0)
    d, rem = divmod(mins, 24 * 60)
    h, m = divmod(rem, 60)
    if d:
        return f"{d}d {h}h" if h else f"{d}d"
    if h:
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{m}m"


def filler_blocks(start, stop):
    """[start, stop) as one piece, or split on FILLER_HOURS clock boundaries."""
    if not FILLER_HOURS:
        if start < stop:
            yield start, stop
        return
    cur = start
    while cur < stop:
        local = cur.astimezone(LONDON).replace(minute=0, second=0, microsecond=0)
        boundary = local + timedelta(hours=FILLER_HOURS - local.hour % FILLER_HOURS)
        nxt = min(boundary.astimezone(timezone.utc), stop)
        if nxt <= cur:                      # safety net around clock changes
            nxt = min(cur + timedelta(hours=1), stop)
        yield cur, nxt
        cur = nxt


def build_xmltv(channels, filler):
    tv = ET.Element("tv", {"generator-info-name": "football_epg.py",
                           "source-info-name": "ESPN"})
    for chan_id, name, logo, _ in channels:
        c = ET.SubElement(tv, "channel", {"id": chan_id})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = name
        if logo:
            ET.SubElement(c, "icon", {"src": logo})

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    count = 0
    for chan_id, _, _, ms in channels:
        last_stop = None
        for m in ms:
            start, stop = m["start"], m["stop"]
            if last_stop and start < last_stop:       # overlapping fixtures
                start = last_stop
                if stop <= start:
                    continue
            if filler:
                for a, b in filler_blocks(last_stop or now, start):
                    if FILLER_STYLE == "next":
                        f_title = f"Next: {m['title']} - {m['when']}"
                        f_desc = f"Coming up: {m['desc']}"
                    else:
                        f_title = f"{m['title']} ({m['when']})"
                        f_desc = f"{m.get('filler_prefix', 'Next Match')}: {m['desc']}"   # Goal Rush: "Coming up"
                    if "fixed_title" in m:        # UEFA.id: same title/description throughout
                        f_title, f_desc = m["fixed_title"], m["fixed_desc"]
                    if COUNTDOWN:    # optional "- kick-off in 2d 23h" per block
                        f_title += f" - kick-off in {countdown(start - a)}"
                    add_programme(tv, chan_id, a, b, f_title,
                                  m.get("filler_sub", f"⏭ Next Match: {m['sub']}"), f_desc, m["comp"])
                    count += 1
            # the match itself: "🔴 LIVE: Premier League" (filler blocks say "⏭ Next Match: Premier League")
            add_programme(tv, chan_id, start, stop, m.get("live_title", m.get("fixed_title", m["title"])),
                          m.get("live_sub", f"🔴 LIVE: {m['sub']}"), m.get("fixed_desc", m["desc"]),
                          m["comp"], live=not m.get("not_live"))
            count += 1
            last_stop = stop
    return tv, count


def write_xml(tv, path):
    ET.indent(tv, space="  ")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        if DOCTYPE:
            f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(ET.tostring(tv, encoding="unicode") + "\n")
    root = ET.parse(path).getroot()          # prove the file is valid XMLTV
    if root.tag != "tv":
        sys.exit(f"ERROR: {path} did not write correctly")


def unique_path(path):
    folder, name = os.path.split(path)
    stem, ext = os.path.splitext(name)
    while True:
        stamp = datetime.now(LONDON).strftime("%Y%m%d-%H%M%S")
        candidate = os.path.join(folder, f"{stem}_{stamp}_{uuid.uuid4().hex[:6]}{ext}")
        if not os.path.exists(candidate):
            return candidate


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="XMLTV guide of football fixtures from ESPN.")
    ap.add_argument("--out", default=OUTPUT_NAME,
                    help="base output name (default football_epg.xml)")
    ap.add_argument("--unique", action="store_true",
                    help="add date-time and a random code to the file name instead of overwriting")
    ap.add_argument("--fixed-name", action="store_true", help=argparse.SUPPRESS)  # old flag, now default
    ap.add_argument("--from", dest="start", help="start date YYYY-MM-DD (default today)")
    ap.add_argument("--days", type=int, default=10,
                    help="days to cover including today (default 10; 0 = to 30 June)")
    ap.add_argument("--minutes", type=int, default=120, help="match length (default 120)")
    ap.add_argument("--suffix", type=int, default=None,
                    help="run ids with this run number forced (12 -> Brentford.PremRun12); later runs continue from it")
    ap.add_argument("--run-ids", action="store_true",
                    help="fresh ids with a run number (Brentford.PremRun3), e.g. when kick-off times change")
    ap.add_argument("--fixed-ids", action="store_true", help=argparse.SUPPRESS)   # old flag, now default
    ap.add_argument("--english-only", action="store_true",
                    help="only English clubs' channels (no non-English UEFA clubs)")
    ap.add_argument("--no-filler", action="store_true",
                    help="no 'Next: ...' programmes before each match")
    ap.add_argument("--filler-hours", type=int, default=2, choices=[0, 1, 2, 3, 4, 6, 8, 12],
                    help="longest filler block in hours (default 2, as PlaylistLabs skips "
                         "long programmes; 0 = one block per gap)")
    ap.add_argument("--filler-style", choices=["plain", "next"], default="plain",
                    help="filler titles: plain = 'Brentford v Liverpool (Sat 17 Oct, 15:00)' "
                         "(default), next = 'Next: Brentford v Liverpool - Sat 17 Oct, 15:00'")
    ap.add_argument("--countdown", action="store_true",
                    help="add '- kick-off in 2d 23h' to each filler block's title")
    ap.add_argument("--no-doctype", action="store_true",
                    help="leave out the <!DOCTYPE tv SYSTEM \"xmltv.dtd\"> line")
    ap.add_argument("--channel-list", metavar="CSV",
                    help="also write a list of channel ids and names to this CSV file")
    args = ap.parse_args()
    global FILLER_HOURS, DOCTYPE, FILLER_STYLE, COUNTDOWN
    COUNTDOWN = args.countdown
    FILLER_STYLE = args.filler_style
    FILLER_HOURS = args.filler_hours
    DOCTYPE = not args.no_doctype

    today = datetime.now(LONDON).date()
    start = date.fromisoformat(args.start) if args.start else today
    end = (start + timedelta(days=args.days - 1) if args.days
           else date(start.year + (1 if start.month >= 7 else 0), 6, 30))
    print(f"Fixtures from {start} to {end} (Europe/London)\n")

    english = fetch_english_clubs()
    if not english:
        sys.exit("No English clubs found - ESPN may be unreachable or changed its API.")
    events = fetch_events(start, end)
    matches = collect_matches(events, args.minutes)
    if not (args.run_ids or args.suffix is not None):
        run_no, suffix = None, ""
    else:
        run_no = args.suffix if args.suffix is not None else load_last_run() + 1
        suffix = f"Run{run_no}"
    channels = build_channels(matches, english, suffix, args.english_only)
    if not channels:
        sys.exit("No fixtures found in this date range - try a longer --days.")

    tv, count = build_xmltv(channels, filler=not args.no_filler)
    if args.unique:
        out_path = unique_path("football_epg.xml" if args.out == OUTPUT_NAME else args.out)
    else:
        out_path = args.out
    write_xml(tv, out_path)
    if run_no is not None:
        save_last_run(run_no)

    if args.channel_list:
        with open(args.channel_list, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["channel_id", "name", "matches"])
            for chan_id, name, _, ms in channels:
                w.writerow([chan_id, name, "; ".join(f"{m['title']} ({m['when']})" for m in ms)])
        print(f"Channel list: {args.channel_list}")

    print(f"\nWrote {out_path}: {len(channels)} channels, {count} programmes")
    print(f"Example channel id: {channels[0][0]}"
          + (f"  (link channels to ids ending in Run{run_no})" if run_no is not None else ""))


if __name__ == "__main__":
    main()

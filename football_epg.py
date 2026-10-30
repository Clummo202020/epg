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
    "UEFA Nations League":    ("uefa.nations", "NationsLge"),   # used only by the Sky Sports+ streams channel
}

# Leagues that define "English clubs".
ENGLISH_LEAGUES = ["Premier League", "Championship", "League One", "League Two"]

# Competitions in which non-English clubs also get channels.
UEFA_COMPETITIONS = ["UEFA Champions League", "UEFA Europa League", "UEFA Conference League"]

# Foreign leagues in which every club gets a channel (--english-only skips them).
OTHER_LEAGUES = ["La Liga"]

# Cup rounds / UEFA stages (ESPN doesn't say which round or matchday a match is in). Each entry is the
# first UK date of a round; a match gets the latest round that started on or before its
# date, so a postponed tie keeps its round until the next one starts. Dates are the
# confirmed 2026-27 round dates (EFL / The FA) - ADD NEXT SEASON'S IN SUMMER 2027; outside
# a table the secondary title is just the cup name (and the log says so).
CUP_ROUNDS = {
    "Carabao Cup": [                     # EFL: w/c dates, so start the Saturday before
        ("2026-07-25", "Preliminary Round"),
        ("2026-08-06", "1st Round"),
        ("2026-08-22", "2nd Round"),
        ("2026-09-05", "3rd Round"),
        ("2026-10-24", "4th Round"),
        ("2026-12-12", "Quarter-final"),
        ("2027-01-09", "Semi-final, 1st Leg"),
        ("2027-01-30", "Semi-final, 2nd Leg"),
        ("2027-03-20", "Final"),
        ("2027-03-28", None),            # season over
    ],
    "FA Cup": [                          # The FA: round Saturdays, start the Thursday before
        ("2026-10-15", "4th Qualifying Round"),
        ("2026-11-05", "1st Round"),
        ("2026-12-03", "2nd Round"),
        ("2027-01-07", "3rd Round"),
        ("2027-02-11", "4th Round"),
        ("2027-03-04", "5th Round"),
        ("2027-04-01", "Quarter-final"),
        ("2027-04-22", "Semi-final"),
        ("2027-05-20", "Final"),
        ("2027-05-29", None),            # season over
    ],
    "UEFA Champions League": [           # UEFA: start the Saturday before each matchday week
        # (MD7 date not published in my sources - any UCL match between MD6 and MD8 is MD7)
        ("2026-09-05", "Matchday 1"),
        ("2026-10-10", "Matchday 2"),
        ("2026-10-17", "Matchday 3"),
        ("2026-10-31", "Matchday 4"),
        ("2026-11-21", "Matchday 5"),
        ("2026-12-05", "Matchday 6"),
        ("2027-01-16", "Matchday 7"),
        ("2027-01-24", "Matchday 8"),
        ("2027-02-13", "Knockout Play-off, 1st Leg"),
        ("2027-02-20", "Knockout Play-off, 2nd Leg"),
        ("2027-03-06", "Round of 16, 1st Leg"),
        ("2027-03-13", "Round of 16, 2nd Leg"),
        ("2027-04-03", "Quarter-final, 1st Leg"),
        ("2027-04-10", "Quarter-final, 2nd Leg"),
        ("2027-04-24", "Semi-final, 1st Leg"),
        ("2027-05-01", "Semi-final, 2nd Leg"),
        ("2027-05-29", "Final"),
        ("2027-06-08", None),
    ],
    "UEFA Europa League": [
        ("2026-09-12", "Matchday 1"),
        ("2026-10-10", "Matchday 2"),
        ("2026-10-17", "Matchday 3"),
        ("2026-10-31", "Matchday 4"),
        ("2026-11-21", "Matchday 5"),
        ("2026-12-05", "Matchday 6"),
        ("2027-01-16", "Matchday 7"),
        ("2027-01-24", "Matchday 8"),
        ("2027-02-13", "Knockout Play-off, 1st Leg"),
        ("2027-02-20", "Knockout Play-off, 2nd Leg"),
        ("2027-03-06", "Round of 16, 1st Leg"),
        ("2027-03-13", "Round of 16, 2nd Leg"),
        ("2027-04-03", "Quarter-final, 1st Leg"),
        ("2027-04-10", "Quarter-final, 2nd Leg"),
        ("2027-04-24", "Semi-final, 1st Leg"),
        ("2027-05-01", "Semi-final, 2nd Leg"),
        ("2027-05-22", "Final"),
        ("2027-06-01", None),
    ],
    "UEFA Conference League": [
        # (semi-final dates assumed = Europa League's: 29 Apr / 6 May 2027)
        ("2026-10-10", "Matchday 1"),
        ("2026-10-17", "Matchday 2"),
        ("2026-10-31", "Matchday 3"),
        ("2026-11-21", "Matchday 4"),
        ("2026-12-05", "Matchday 5"),
        ("2026-12-12", "Matchday 6"),
        ("2027-02-13", "Knockout Play-off, 1st Leg"),
        ("2027-02-20", "Knockout Play-off, 2nd Leg"),
        ("2027-03-06", "Round of 16, 1st Leg"),
        ("2027-03-13", "Round of 16, 2nd Leg"),
        ("2027-04-03", "Quarter-final, 1st Leg"),
        ("2027-04-10", "Quarter-final, 2nd Leg"),
        ("2027-04-24", "Semi-final, 1st Leg"),
        ("2027-05-01", "Semi-final, 2nd Leg"),
        ("2027-05-29", "Final"),
        ("2027-06-08", None),
    ],
}


def cup_round(comp_name, day):
    """The round of a domestic cup match on this UK date, or None if not known."""
    table = CUP_ROUNDS.get(comp_name)
    if not table:
        return None
    found = None
    for start, name in table:
        if day >= date.fromisoformat(start):
            found = name
    if found is None:
        print(f"  WARNING: no {comp_name} round for {day} - update CUP_ROUNDS")
    return found


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

# Club match blocks go LIVE this many minutes before kick-off (0 = at kick-off)
MATCH_EARLY_MINUTES = 10

# Premier League Goal Rush channel: one programme for every slot where at least
# GOAL_RUSH_MIN Premier League matches kick off at the same time (e.g. Sat 15:00).
GOAL_RUSH = True                   # False = leave the channel out
GOAL_RUSH_ID = "GoalRush2.id"
GOAL_RUSH_COMP = "Premier League"
GOAL_RUSH_MIN = 2
GOAL_RUSH_EARLY_MINUTES = 10       # Goal Rush goes LIVE this many minutes before kick-off
# Channels to name at the end of each Goal Rush description, e.g.
# ["Hub Premier 1 (Singapore)", "Sky Sport 8 (New Zealand)"]; empty = none
GOAL_RUSH_ON = []

# The Goal Rush "main game" is whichever slot match these channels show live,
# read from the SPORT guide (the local file in the repo, else the GitHub copy).
GOAL_RUSH_MAIN_FROM = ["HK.NowSportsPLTV", "SG.HubPremier1", "NZ.SkySport8NZ"]   # first match wins
GOAL_RUSH_GUIDE_FILE = "SPORT_epg.xml.gz"
GOAL_RUSH_GUIDE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/SPORT_epg.xml.gz"
# PlaylistLabs never rewrites programmes it already holds, and broadcasters can
# change the main game late (25 Oct 2026: Liverpool v Brighton became Man Utd v
# Bournemouth the evening before). So the main game is only named from matchday:
#  - before matchday the channel runs "Coming up" blocks with a generic description
#    (no main game) up to GOAL_RUSH_REVEAL_HOUR on matchday, and nothing after that;
#  - the first run on matchday (04:41 UTC) adds the rest of that day's blocks and the
#    LIVE show with the main game, read from the SPORT guide at that moment.
# A slot whose main game still isn't listed on matchday keeps the generic description.
GOAL_RUSH_REVEAL_HOUR = 8          # UK time on matchday when the main-game blocks start

# One general channel for every UEFA match: a programme for each kick-off time,
# listing all the Champions / Europa / Conference League matches starting then.
UEFA_CHANNEL = True                # False = leave the channel out
UEFA_CHANNEL_ID = "UEFA.comps"
UEFA_CHANNEL_NAME = "UEFA Competitions"
UEFA_CHANNEL_TITLE = "Streams are live at match time only."
# With no UEFA kick-offs in range (between matchdays) the channel gets plain blocks this far
# ahead instead of nothing. Kept short: PlaylistLabs only adds after the last programme it
# holds, so the next matchday's live blocks must be able to follow on a later run.
UEFA_IDLE_HOURS = 24
# Generic (all-sport) streaming services: plain 2-hour blocks with the same
# title and description, not tied to any fixtures. (id, name, title, description)
DUMMY_CHANNELS = [
    ("peacock.liveUSA", "Peacock", "Stream is live at event time only.",
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
    # Azam Sports 1-4 (Tanzania, 29 Oct 2026): no programme guide anywhere, so plain blocks with a description
    *[(f"azamsports{n}.tz", f"Azam Sports {n}", "Stream is live at event time only.",
       f"Azam Sports {n} from Azam TV, Tanzania. Tanzanian and East African football, "
       f"other local sport and, at times, live English football. No programme guide is available.")
      for n in range(1, 5)],
    # Sportsnet World Extra 1-4 (Canada, 30 Oct 2026): overflow channels with no guide anywhere
    *[(f"sportsnetworldextra{n}.ca", f"Sportsnet World Extra {n}", "Stream is live at event time only.",
       f"Sportsnet World Extra {n} (Canada): extra Sportsnet World channel for international football and "
       f"rugby matches that don't fit on the main channel. No programme guide is available.")
      for n in range(1, 5)],
    # Cricbuzz / STARZPLAY Cricbuzz (30 Oct 2026): streaming-only cricket channels, no guide anywhere
    ("cricbuzz.live", "Cricbuzz", "Stream is live at event time only.",
     "Cricbuzz: live international and franchise cricket when a match is on. No programme guide is available."),
    *[(f"starzplaycricbuzz{n}.live", f"STARZPLAY Cricbuzz {n}", "Stream is live at event time only.",
       f"STARZPLAY Cricbuzz {n}: live cricket (internationals, PSL, ILT20 and more) when a match is on. "
       f"No programme guide is available.") for n in (1, 2)],
    # STARZPLAY Sports 1 and 3 (MENA, 30 Oct 2026; the provider labels them AD Sports Premium): no guide anywhere -
    # STARZPLAY Sports 2 has a listing in the SPORT guide as AE.ADSportsPremium
    *[(f"starzplaysports{n}.ae", f"STARZPLAY Sports {n}", "Stream is live at event time only.",
       f"STARZPLAY Sports {n} (Middle East): Serie A, UFC, cricket and more, live and replays. "
       f"No programme guide is available.") for n in (1, 3)],
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
            rnd = cup_round(comp_name, ko.date())       # e.g. "Carabao Cup 4th Round"
            if rnd:
                sub = f"{comp_name} {rnd}"
            else:
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


_SPORT_GUIDE = []                    # parsed SPORT guide, read once per run ([root] or [None])


def _sport_guide_root():
    """The SPORT guide (local copy in the repo, else GitHub) as an XML root, or None."""
    import gzip
    if _SPORT_GUIDE:
        return _SPORT_GUIDE[0]
    root = None
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
    except Exception as e:          # no guide = no main game / no filtering, never a failed run
        print(f"  WARNING: could not read the SPORT guide ({e})")
    _SPORT_GUIDE.append(root)
    return root


def load_guide_listings(channel_ids):
    """[(channel, start, stop, text)] for these channels in the SPORT guide, in the order given."""
    root = _sport_guide_root()
    if root is None:
        return []
    order = {c: i for i, c in enumerate(channel_ids)}
    out = []
    for p in root.iter("programme"):
        if p.get("channel") not in order:
            continue
        try:
            start = datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
            stop = datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        except (TypeError, ValueError):
            continue
        text = " ".join((e.text or "") for e in p if e.tag in ("title", "sub-title", "desc"))
        out.append((p.get("channel"), start, stop, text))
    out.sort(key=lambda r: order[r[0]])           # channel priority order
    return out


def load_main_game_listings():
    """[(start, stop, text)] for the GOAL_RUSH_MAIN_FROM channels in the SPORT guide."""
    return [(a, b, t) for _, a, b, t in load_guide_listings(GOAL_RUSH_MAIN_FROM)]


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
    "sheffield wednesday": ["sheff wed", "sheffield wed"],
    "west bromwich albion": ["west brom"],
    "queens park rangers": ["qpr"],
    "milton keynes dons": ["mk dons"],
}
AMBIGUOUS_FIRST_WORDS = {"manchester", "west", "sheffield", "nottingham", "aston", "crystal",
                         "queens", "afc", "fc", "real", "athletic", "bristol"}


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


def slot_channel(matches, comps, chan_id, name, title, desc, live_title=None, early_minutes=0):
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
        early = timedelta(minutes=early_minutes)     # go LIVE a little before kick-off
        if i + 1 < len(starts):
            stop = min(stop, starts[i + 1] - early)  # never overlap the next slot
        shows.append({
            "comp": label, "title": label, "sub": "", "desc": desc,
            "start": start - early, "stop": stop,
            "when": f"{ko:%a %d %b}, {ko:%H:%M}", "teams": [], "tbc": False,
            "fixed_title": title, "fixed_desc": desc,
            "filler_sub": "", "live_sub": "",          # no secondary title
            "live_title": live_title or title,         # match blocks only
        })
    return (chan_id, name, None, shows)


def uefa_channel(matches, suffix):
    chan = slot_channel(matches, UEFA_COMPETITIONS, f"{UEFA_CHANNEL_ID}{suffix}",
                        UEFA_CHANNEL_NAME, UEFA_CHANNEL_TITLE, UEFA_CHANNEL_DESC,
                        live_title=f"🔴 LIVE – {UEFA_CHANNEL_TITLE}",
                        early_minutes=MATCH_EARLY_MINUTES)
    if chan[3]:
        return chan
    # No UEFA kick-offs in range: UEFA_IDLE_HOURS of plain blocks so the channel isn't empty
    now = datetime.now(LONDON)
    t = now.replace(minute=0, second=0, microsecond=0)
    t -= timedelta(hours=t.hour % DUMMY_HOURS)          # align to 00:00, 02:00 ...
    shows = []
    while t < now + timedelta(hours=UEFA_IDLE_HOURS):
        stop = t + timedelta(hours=DUMMY_HOURS)
        shows.append({
            "comp": UEFA_CHANNEL_NAME, "title": UEFA_CHANNEL_TITLE, "sub": "",
            "desc": UEFA_CHANNEL_DESC, "start": t.astimezone(timezone.utc),
            "stop": stop.astimezone(timezone.utc), "when": "", "teams": [], "tbc": False,
            "live_sub": "", "not_live": True,
        })
        t = stop
    return (chan[0], chan[1], chan[2], shows)


# Sky Sports+ (30 Oct 2026): ONE guide channel for all the user's Sky Sports+ 1-40 streams (they share it).
# Blocks at every EFL / Carabao Cup kick-off time that Sky Sports+ can show in the UK (not Saturday 14:45-17:15 -
# the 3pm blackout; Sky's deal streams every EFL match outside it, the main-channel picks on Sky Sports itself), each listing that slot's matches; the time before a slot says what's coming up.
# 30 Oct 2026 (evening): matches listed on a main Sky Sports UK channel in the SPORT guide (SKYPLUS_MAIN_CHANNELS)
# are left out, and kick-offs that overlap (Fri 19:45 + 20:00) share ONE block, so an earlier match no longer
# disappears from the guide when a later kick-off starts (Newport v Chesterfield, Fri 30 Oct).
SKYPLUS_CHANNEL = True
SKYPLUS_ID = "SkySportsPlus2.live"   # was SkySportsPlus.live (30 Oct: new id so PlaylistLabs loads the fixed blocks)
SKYPLUS_NAME = "Sky Sports+ streams"
SKYPLUS_COMPS = ["Championship", "League One", "League Two", "Carabao Cup", "UEFA Nations League"]
SKYPLUS_EFL = ["Championship", "League One", "League Two", "Carabao Cup"]
STREAMS_SHORT = {"UEFA Nations League": "Nations League",    # shorter names in titles/descriptions
                 "UEFA Champions League": "Champions League"}
# Nations League (30 Oct 2026): the streams show the bigger matches, so only League A ties (both teams below,
# the 2026-27 League A) are listed - minus the home nations (England/Wales on ITV/BBC, not Sky). Update the
# list for each new Nations League season (League A changes with promotion/relegation).
SKYPLUS_NL_TEAMS = {"portugal", "spain", "france", "germany", "italy", "netherlands", "denmark", "croatia",
                    "serbia", "belgium", "england", "norway", "wales", "czechia", "czech republic", "greece",
                    "turkiye", "turkey"}
SKYPLUS_NL_SKIP = {"england", "wales", "scotland", "northern ireland"}
SKYPLUS_MAIN_CHANNELS = [            # SPORT guide ids; a match live on any of these is not on the streams
    "UK.SkySportsMainEvent", "UK.SkySportsFootball", "UK.SkySportsPremierLeague", "UK.SkySportsAction",
    "UK.SkySportsMix", "UK.SkySportsPlus", "UK.SkySportsCricket", "UK.SkySportsGolf",
    "UK.SkySportsTennis", "UK.SkySportsF1", "UK.SkySportsNFL", "UK.SkySportsRacing", "UK.SkySportsBoxOffice",
    "UK.SkySportsMainEvent4K", "UK.SkySportsF14K", "UK.SkySportsUHD1", "UK.SkySportsUHD2",
]
SKYPLUS_IDLE = ("Sky Sports+ streams carry every EFL match not shown on the main Sky Sports channels "
                "(Championship, League One, League Two and the Carabao Cup), plus international football, tennis, darts, "
                "golf, NFL and more. Each event is on its own stream - scroll the Sky Sports+ channels "
                "to find it. No Saturday 3pm football in the UK.")


def on_main_sky(m, listings):
    """The main Sky Sports channel showing match m live (from the SPORT guide), or None."""
    ko = m["start"]
    h, a = (short_name(t.get("displayName")) for t in m["teams"])
    ha, aa = _aliases(h), _aliases(a)
    for ch, s, e, text in listings:
        if s <= ko + timedelta(minutes=15) and e >= ko + timedelta(minutes=30):   # on air at kick-off
            txt = _norm(text)
            if any(x in txt for x in ha) and any(x in txt for x in aa):
                return ch
    return None


def skyplus_channel(matches):
    """(id, name, None, shows) for the Sky Sports+ streams, or None when no slots."""
    listings = load_guide_listings(SKYPLUS_MAIN_CHANNELS)
    if not listings:
        print("  Sky Sports+: no main Sky Sports listings in the SPORT guide - no matches left out")
    else:
        last = max(e for _, _, e, _ in listings).astimezone(LONDON)
        print(f"  Sky Sports+: main Sky Sports listings up to {last:%a %d %b %H:%M}")
    kept = []
    for m in matches:
        if m["comp"] not in SKYPLUS_COMPS or m.get("tbc"):
            continue
        if m["comp"] == "UEFA Nations League":
            sides = {_norm(short_name(t.get("displayName"))).strip() for t in m["teams"]}
            if not sides <= SKYPLUS_NL_TEAMS or sides & SKYPLUS_NL_SKIP:
                continue                               # not a League A tie, or a home nation (ITV/BBC)
        ko = m["start"].astimezone(LONDON)
        hm = ko.hour * 60 + ko.minute
        if ko.weekday() == 5 and 14 * 60 + 45 <= hm < 17 * 60 + 15:
            continue                                   # Saturday 14:45-17:15 UK blackout
        ch = on_main_sky(m, listings) if listings else None
        if ch:
            print(f"  Sky Sports+: {m['title']} ({ko:%a %d %b %H:%M}) is on {ch} - left out")
            continue
        kept.append(m)

    return streams_channel(kept, SKYPLUS_ID, SKYPLUS_NAME, "Sky Sports+", "the Sky Sports+ streams",
                           SKYPLUS_COMPS, SKYPLUS_IDLE, efl_label=True)


def streams_channel(kept, chan_id, name, label, where, comps_order, idle, efl_label=False):
    """(id, name, None, shows) for a shared event-streams channel (Sky Sports+, Setanta), or None.
    One block per kick-off time; kick-offs that overlap share ONE block (so an earlier match doesn't vanish when
    a later one starts); the time before a block says what's coming up."""
    early = timedelta(minutes=MATCH_EARLY_MINUTES)
    groups = []
    for m in sorted(kept, key=lambda m: m["start"]):
        if groups and m["start"] - early < max(x["stop"] for x in groups[-1]):
            groups[-1].append(m)
        else:
            groups.append([m])

    shows = []
    for i, ms in enumerate(groups):
        start = min(m["start"] for m in ms)
        ko = start.astimezone(LONDON)
        kos = sorted({m["start"] for m in ms})
        parts = []
        for k in kos:
            at = [m for m in ms if m["start"] == k]
            comps = []
            for c in comps_order:
                games = sorted(m["title"] for m in at if m["comp"] == c)
                if games:
                    comps.append(f"{STREAMS_SHORT.get(c, c)}: " + ", ".join(games))
            parts.append((k, ". ".join(comps)))
        n = len(ms)
        if len(kos) == 1:
            desc = (f"{ko:%a %d %b}, {ko:%H:%M} kick-off{'s' if n != 1 else ''} on {where} - "
                    + parts[0][1] + ".\n\n" + idle)
        else:
            desc = (f"{ko:%a %d %b} on {where} - "
                    + " ".join(f"{k.astimezone(LONDON):%H:%M}: {txt}." for k, txt in parts)
                    + "\n\n" + idle)
        cs = {m["comp"] for m in ms}
        what = (STREAMS_SHORT.get(ms[0]["comp"], ms[0]["comp"]) if len(cs) == 1
                else "EFL" if efl_label and cs <= set(SKYPLUS_EFL) else "Football")
        count = f"{n} match{'es' if n != 1 else ''}"
        stop = max(m["stop"] for m in ms)
        if i + 1 < len(groups):
            stop = min(stop, min(m["start"] for m in groups[i + 1]) - early)
        shows.append({
            "comp": what, "title": what, "sub": "", "desc": desc,
            "start": start - early, "stop": stop, "when": f"{ko:%a %d %b}, {ko:%H:%M}", "teams": [], "tbc": False,
            "fixed_title": f"{label} - next: {what}, {ko:%a %H:%M} ({count})",
            "fixed_desc": desc, "filler_sub": "", "live_sub": "",
            "live_title": f"🔴 LIVE - {label}: {what} ({count})",
        })
    return (chan_id, name, None, shows) if shows else None


# Setanta Sports (30 Oct 2026): ONE guide channel for the user's "Setanta | Event 1-40" streams (group "Setanta
# Sports PPV"), built like the Sky Sports+ one: a block at every Premier League / Champions League kick-off, listing
# that slot's matches. Setanta is not a UK service, so there is no 3pm blackout and nothing is left out. Add more
# competitions from COMPETITIONS to SETANTA_COMPS if wanted (e.g. "UEFA Europa League", "La Liga").
SETANTA_CHANNEL = True
SETANTA_ID = "SetantaSports.live"
SETANTA_NAME = "Setanta Sports streams"
SETANTA_COMPS = ["Premier League", "UEFA Champions League"]
SETANTA_IDLE = ("Setanta Sports event streams carry Premier League and UEFA Champions League football, plus "
                "other European football, UFC, NBA, NHL, tennis and motorsport. Each event is on its own stream - "
                "scroll the Setanta channels to find it.")


def setanta_channel(matches):
    """(id, name, None, shows) for the Setanta Sports streams, or None when no matches."""
    kept = [m for m in matches if m["comp"] in SETANTA_COMPS and not m.get("tbc")]
    return streams_channel(kept, SETANTA_ID, SETANTA_NAME, "Setanta", "the Setanta Sports streams",
                           SETANTA_COMPS, SETANTA_IDLE)


# Formula 1 (30 Oct 2026): f1.uk and f1drivers.uk from OpenF1's session list (the SPORT guide already uses it)
# instead of plain placeholder blocks. Each session (Practice 1-3, Sprint Qualifying, Sprint, Qualifying, Race)
# is a block, "🔴 LIVE - F1 Mexico: Race", starting when the coverage starts (race 70 min early, like the
# streams' own "NEXT | MEXICO: RACE | 18:50" names; other sessions 15 min); the time before says what's next.
# The description lists the whole weekend in UK time. No OpenF1 data -> the old plain blocks.
OPENF1_SESSIONS = "https://api.openf1.org/v1/sessions?year={year}"
F1_CHANNELS = [("Formula1.live", "Formula 1", "Formula 1"),      # new id 30 Oct 2026 (user's request)
               ("f1.uk", "Formula 1", "Formula 1"), ("f1drivers.uk", "F1 Drivers", "F1 driver onboards"),
               ("F1Drivers.live", "F1 Drivers", "F1 driver onboards")]   # new id 30 Oct 2026 (PlaylistLabs caches old ids)
# Season schedule first from Jolpica (the Ergast successor - fixed timetable, always available); OpenF1 only as a
# backup, because OpenF1 refuses free requests while a session is live (30 Oct 2026: the run during FP1 got nothing).
JOLPICA_SEASON = "https://api.jolpi.ca/ergast/f1/{year}.json"
JOLPICA_SESSIONS = [("FirstPractice", "Practice 1", 60), ("SecondPractice", "Practice 2", 60),
                    ("ThirdPractice", "Practice 3", 60), ("SprintQualifying", "Sprint Qualifying", 45),
                    ("SprintShootout", "Sprint Qualifying", 45), ("Sprint", "Sprint", 45),
                    ("Qualifying", "Qualifying", 60), ("Race", "Race", 120)]


def jolpica_sessions(years):
    """OpenF1-shaped session dicts from Jolpica's season schedule."""
    out = []
    for year in years:
        try:
            data = get_json(JOLPICA_SEASON.format(year=year))
        except NoData:
            data = None
        races = (((data or {}).get("MRData") or {}).get("RaceTable") or {}).get("Races") or []
        for r in races:
            loc = ((r.get("Circuit") or {}).get("Location") or {})
            gp = str(r.get("raceName") or "").replace(" Grand Prix", "").strip()
            for key, name, mins in JOLPICA_SESSIONS:
                x = r if key == "Race" else r.get(key)
                if not isinstance(x, dict) or not x.get("date") or not x.get("time"):
                    continue
                start = _iso(f"{x['date']}T{x['time']}")
                if not start:
                    continue
                out.append({"session_name": name, "date_start": start.isoformat(),
                            "date_end": (start + timedelta(minutes=mins)).isoformat(),
                            "country_name": "", "location": gp, "meeting_key": f"{year}-{r.get('round')}",
                            "circuit_short_name": str((r.get("Circuit") or {}).get("circuitName") or loc.get("locality") or "")})
    return out
F1_EARLY = {"Race": 70}                 # minutes of build-up before the session; others F1_EARLY_DEFAULT
F1_EARLY_DEFAULT = 15
F1_PLACE_BY_LOCATION = {"United States", "Italy", "Spain"}   # countries with two races: use the city
F1_SHORT = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3", "Sprint Qualifying": "Sprint Quali",
            "Sprint": "Sprint", "Qualifying": "Quali", "Race": "Race"}


def _iso(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def f1_channels(days):
    """[(id, name, None, shows)] for F1_CHANNELS from OpenF1, or [] when there's no data."""
    now = datetime.now(timezone.utc)
    years = sorted({now.year, (now + timedelta(days=days)).year})
    sess = jolpica_sessions(years)
    src = "Jolpica"
    if not sess:
        src = "OpenF1"
        for year in years:
            try:
                data = get_json(OPENF1_SESSIONS.format(year=year))
            except NoData:
                data = None
            sess += data if isinstance(data, list) else []
    rows = []
    for x in sess:
        start, stop = _iso(x.get("date_start")), _iso(x.get("date_end"))
        name = str(x.get("session_name") or "").strip()
        if not start or not name:
            continue
        stop = stop if stop and stop > start else start + timedelta(hours=2)
        country = str(x.get("country_name") or "").strip()
        place = str(x.get("location") or "").strip()
        gp = place if (country in F1_PLACE_BY_LOCATION or not country) else country
        rows.append({"start": start, "stop": stop, "name": name, "gp": gp or "Grand Prix",
                     "meeting": x.get("meeting_key"), "circuit": str(x.get("circuit_short_name") or "").strip()})
    rows = [r for r in rows if r["stop"] > now - timedelta(hours=6) and r["start"] < now + timedelta(days=days)]
    if not rows:
        print(f"  F1: no {src} sessions in range - plain blocks")
        return []
    rows.sort(key=lambda r: r["start"])
    by_meeting = {}
    for r in rows:
        by_meeting.setdefault(r["meeting"], []).append(r)
    out = []
    for cid, cname, what in F1_CHANNELS:
        shows = []
        for i, r in enumerate(rows):
            weekend = by_meeting.get(r["meeting"], [r])
            plan = ", ".join(f"{F1_SHORT.get(w['name'], w['name'])} {w['start'].astimezone(LONDON):%a %H:%M}"
                             for w in weekend)
            uk = r["start"].astimezone(LONDON)
            word = "Lights out" if r["name"] in ("Race", "Sprint") else "Session starts"
            desc = (f"{what}: {r['gp']} {r['name']}" + (f" ({r['circuit']})" if r["circuit"] else "")
                    + f". {word}: {uk:%a %d %b %H:%M} UK.\n\nThis weekend (UK time): {plan}.")
            early = timedelta(minutes=F1_EARLY.get(r["name"], F1_EARLY_DEFAULT))
            start, stop = r["start"] - early, r["stop"]
            if i + 1 < len(rows):
                nxt = rows[i + 1]["start"] - timedelta(minutes=F1_EARLY.get(rows[i + 1]["name"], F1_EARLY_DEFAULT))
                stop = min(stop, nxt)
            if shows and start < shows[-1]["stop"]:
                start = shows[-1]["stop"]
            if stop <= start:
                continue
            shows.append({
                "comp": "Formula 1", "title": "Formula 1", "sub": "", "desc": desc,
                "start": start, "stop": stop, "when": f"{uk:%a %d %b}, {uk:%H:%M}", "teams": [], "tbc": False,
                "fixed_title": f"F1 - next: {r['gp']} {r['name']}, {uk:%a %H:%M}",
                "fixed_desc": desc, "filler_sub": "", "live_sub": "",
                "live_title": f"🔴 LIVE - F1 {r['gp']}: {r['name']}",
            })
        out.append((cid, cname, None, shows))
    print(f"  F1: {len(rows)} sessions from {src}")
    return out


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


def goal_rush_channel(matches, suffix, now=None):
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
    today_uk = (now or datetime.now(timezone.utc)).astimezone(LONDON).date()
    shows = []
    for start, ms in sorted(slots.items()):
        if len(ms) < GOAL_RUSH_MIN:
            continue
        ko = start.astimezone(LONDON)
        live_start = start - timedelta(minutes=GOAL_RUSH_EARLY_MINUTES)   # show starts before kick-off
        reveal = datetime(ko.year, ko.month, ko.day, GOAL_RUSH_REVEAL_HOUR,
                          tzinfo=LONDON).astimezone(timezone.utc)
        reveal = min(reveal, live_start)
        games = ", ".join(sorted(m["title"] for m in ms))
        generic = f"Goal Rush. Live action from {len(ms)} matches: {games}.{on_air}"
        show = {
            "comp": GOAL_RUSH_COMP, "title": "Goal Rush", "sub": GOAL_RUSH_COMP,
            "desc": generic, "generic_desc": generic, "reveal": reveal,
            "start": live_start,
            "stop": max(m["stop"] for m in ms),
            "when": f"{ko:%a %d %b}, {ko:%H:%M}", "teams": [], "tbc": False,
            "filler_prefix": f"Coming up {ko:%A}",      # "Coming up Saturday: Goal Rush. ..."
            "filler_sub": f"⏭ Goal Rush {ko:%a} {ko.day} {ko:%b}",
            "live_sub": GOAL_RUSH_COMP,                  # secondary title: Premier League
            "live_title": "🔴 LIVE: Goal Rush",         # title of the show itself
        }
        if today_uk < ko.date():
            # not matchday yet: generic "Coming up" blocks up to the reveal time, then
            # nothing - so PlaylistLabs can still add the main-game blocks on matchday
            print(f"  Goal Rush {ko:%a %d %b %H:%M}: before matchday - generic blocks until "
                  f"{reveal.astimezone(LONDON):%a %H:%M}, main game named on the day")
            show.update({"start": reveal, "stop": reveal, "filler_only": True})
            shows.append(show)
            break                       # later slots wait too, so nothing is skipped
        main = find_main_game(ms, listings) if listings else None
        if main:
            others = sorted(m["title"] for m in ms if m is not main)
            print(f"  Goal Rush {ko:%a %d %b %H:%M}: main game {main['title']}")
            show["desc"] = (f"Goal Rush. Main game: {main['title']}, with updates and "
                            f"goal flashes from {', '.join(others)}.{on_air}")
        else:
            print(f"  Goal Rush {ko:%a %d %b %H:%M}: main game not listed - generic description")
        shows.append(show)
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
    f1 = f1_channels(DUMMY_DAYS)
    for cid, cname, logo, shows in f1:
        channels.append((f"{cid}{suffix}", cname, logo, shows))
    if not f1:                                         # OpenF1 down: the old placeholder blocks, same ids
        for fid in ("Formula1.live", "f1.uk"):
            channels.append(dummy_channel(f"{fid}{suffix}", "Formula 1", "Stream is live at event time only.",
                                          "Live F1 Grand Prix events and races."))
        for fid in ("F1Drivers.live", "f1drivers.uk"):
            channels.append(dummy_channel(f"{fid}{suffix}", "F1 Drivers", "Stream is live at event time only.",
                                          "Formula 1 driver onboard cameras, live during race weekends."))
    if SKYPLUS_CHANNEL:
        sp = skyplus_channel(matches)
        if sp:
            channels.append((f"{sp[0]}{suffix}",) + sp[1:])
        else:                                          # no EFL in range: plain blocks, same id
            channels.append(dummy_channel(f"{SKYPLUS_ID}{suffix}", SKYPLUS_NAME,
                                          "Live at event time only.", SKYPLUS_IDLE))
    if SETANTA_CHANNEL:
        st = setanta_channel(matches)
        if st:
            channels.append((f"{st[0]}{suffix}",) + st[1:])
        else:                                          # no matches in range: plain blocks, same id
            channels.append(dummy_channel(f"{SETANTA_ID}{suffix}", SETANTA_NAME,
                                          "Live at event time only.", SETANTA_IDLE))
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
            if m.get("teams"):                         # club matches go LIVE a little before kick-off
                start -= timedelta(minutes=MATCH_EARLY_MINUTES)
            if last_stop and start < last_stop:       # overlapping fixtures
                start = last_stop
                if stop <= start:
                    continue
            if filler:
                cuts = [last_stop or now]
                rv = m.get("reveal")             # Goal Rush: generic text before the reveal time
                if rv and cuts[0] < rv < start:
                    cuts.append(rv)
                cuts.append(start)
                pieces = [blk for i in range(len(cuts) - 1)
                          for blk in filler_blocks(cuts[i], cuts[i + 1])]
                for a, b in pieces:
                    d = m["generic_desc"] if rv and a < rv else m["desc"]
                    if FILLER_STYLE == "next":
                        f_title = f"Next: {m['title']} - {m['when']}"
                        f_desc = f"Coming up: {d}"
                    else:
                        f_title = f"{m['title']} ({m['when']})"
                        f_desc = f"{m.get('filler_prefix', 'Next Match')}: {d}"   # Goal Rush: "Coming up"
                    if "fixed_title" in m:        # UEFA.id: same title/description throughout
                        f_title, f_desc = m["fixed_title"], m["fixed_desc"]
                    if COUNTDOWN:    # optional "- kick-off in 2d 23h" per block
                        f_title += f" - kick-off in {countdown(start - a)}"
                    add_programme(tv, chan_id, a, b, f_title,
                                  m.get("filler_sub", f"⏭ Next Match: {m['sub']}"), f_desc, m["comp"])
                    count += 1
            if m.get("filler_only"):                  # Goal Rush before matchday: no show yet
                last_stop = start
                continue
            # the match itself: title "🔴 LIVE: A v B", secondary title "Premier League"
            live_title = m.get("live_title") or (f"🔴 LIVE: {m['title']}" if m.get("teams")
                                                 else m.get("fixed_title", m["title"]))
            add_programme(tv, chan_id, start, stop, live_title,
                          m.get("live_sub", m["sub"]), m.get("fixed_desc", m["desc"]),   # 🔴 is in the title
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

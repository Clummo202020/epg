#!/usr/bin/env python3
"""
event_epg.py - XMLTV guide built from the event times in your IPTV stream names.

Event streams are named with their start time, e.g.
    US (Peacock 003) | Celtics vs. Pistons (2026-10-20 14:50:05)
    AU (STAN 08) | Manchester City v AEK Athens  UEFA Champions League ... (2026-10-21 05:55:15)
    End | College Swimming League - Match 3 | College Swimming League | 2026-10-03 | 00:30 (GMT) | 8K EXCLUSIVE | GB: DAZN PPV 5
    (Apple) (MLS) 001 | Montréal vs. Nashville (2026-10-24 13:25:00)        (US Eastern time)
    NFL  | 13 - SNF 8:20pm Chiefs at Seahawks        (US Eastern time, date from ESPN's NFL schedule)
    NHL | 04 - 7pm Rangers at Senators               (US Eastern time, date from ESPN's NHL schedule)
    Charlotte Hornets vs Miami Heat  @ Oct 24 6:00 PM :NBA  01      (US Eastern time)
    MLB 01 : Rays x Guardians start:2026-10-18 22:08:00 stop:2026-10-19 05:21:20
    MLB 13 | Baltimore vs Tampa Bay @ Aug 14 7:00 PM

Each stream "slot" (US (Peacock 003), AU (STAN 08), GB: DAZN PPV 5 ...) becomes a guide
channel - Peacock003.us, STAN08.au, DAZNPPV5.gb - showing:
    * "Coming up" blocks until the event starts
    * the event itself (EVENT_HOURS long), titled "🔴 LIVE: <event>", with the
      competition (when the name gives one) as the secondary title
Times are converted to UK time. Names with no date/time get no channel.

The guide stops when the event ends: PlaylistLabs only adds programmes after the
last one it holds, so nothing is listed past the event and the slot's next event
can be added on a later run.

The playlist link usually contains your provider login, so it is never stored in
the repository: the workflow passes it in from a GitHub Secret (PLAYLIST_URL).

Usage:
    PLAYLIST_URL=... python3 event_epg.py       # download the playlist, write events_epg.xml
    python3 event_epg.py --m3u playlist.m3u     # use a local file instead
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import unicodedata
from difflib import SequenceMatcher
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
OUTPUT_NAME = "events_epg.xml"
LONDON = ZoneInfo("Europe/London")
EVENT_HOURS = 3            # how long each event is listed for
BLOCK_HOURS = 2            # "Coming up" block length before the event
PAST_EVENT_HOURS = 2       # an event that has ended keeps its slot for this long (its LIVE
                           # block is followed straight away by ENDED_FILLER_HOURS of
                           # "This event has now finished" blocks, so there's no gap)
MAX_DAYS_AHEAD = 2         # events further ahead than this get filler until they come into range
FILLER_TITLE = "Stream is live at event time only."
FILLER_DESC = "The next event on this stream will be listed nearer the time."
# Shown on a slot whose event is over (or that is empty) until its stream name changes to a new event;
# the new event's real titles/descriptions then replace it automatically.
OFFLINE_TITLE = "Channel is offline"   # only used if a stream has no name at all
# Finished/empty slots are titled with the stream's own name (25 Oct 2026), e.g.
# "US (Paramount 009) | Motherwell vs. Heart of Midlothian (2026-10-25 09:00:00)".


def offline_title(ev):
    """Title for the blocks of a finished or empty slot: the actual stream name."""
    return (ev.get("name") or "").strip() or OFFLINE_TITLE
OFFLINE_DESC = "This channel is offline. The next event will be listed when the stream is updated."
# Description used instead when the slot's last event has finished (an empty slot keeps OFFLINE_DESC)
FINISHED_DESC = "This event has now finished. The next event will be listed when the stream is updated."

# Time zone of the times in names that start with a country code, e.g. "US (Peacock 003) | ..."
COUNTRY_TZ = {
    "US": "America/New_York",
    "CA": "America/Toronto",
    "AU": "Australia/Sydney",
    "NZ": "Pacific/Auckland",
    "UK": "Europe/London",
    "GB": "Europe/London",
    "IE": "Europe/Dublin",
}
# Time zone written in the name, e.g. "00:30 (GMT)"
ABBREV_TZ = {
    "GMT": "UTC", "UTC": "UTC", "BST": "Europe/London", "UK": "Europe/London",
    "ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York",
    "PT": "America/Los_Angeles", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
    "AEST": "Australia/Sydney", "AEDT": "Australia/Sydney", "CET": "Europe/Paris",
    "CEST": "Europe/Paris",
}
# Status words some providers put first ("End | ...", "Live | ...", "Upcoming | ...")
STATUS_WORDS = {"end", "ended", "live", "upcoming", "next", "soon", "finished", "off"}

HEADERS = {"User-Agent": "Mozilla/5.0 (event_epg.py)"}

# Competitions recognised in event names (longest first wins), used as the secondary title
COMPETITIONS = [
    "UEFA Champions League", "UEFA Europa League", "UEFA Conference League", "UEFA Super Cup",
    "UEFA Youth League", "Champions League", "Europa League", "Conference League",
    "Concacaf Champions Cup", "Concacaf Nations League", "Copa Libertadores", "Copa Sudamericana",
    "Premier League", "English Football League", "EFL Championship", "EFL League One",
    "EFL League Two", "Carabao Cup", "FA Cup", "Scottish Premiership", "La Liga", "LaLiga",
    "Serie A", "Bundesliga", "Ligue 1", "Eredivisie", "Liga MX", "MLS", "NWSL", "WSL",
    "NFL", "NBA", "WNBA", "NHL", "MLB", "NCAA", "College Football", "College Basketball",
    "UFC", "PFL", "Boxing", "WWE", "Formula 1", "F1", "MotoGP", "NASCAR", "IndyCar",
    "PGA Tour", "LPGA", "DP World Tour", "Ryder Cup", "ATP", "WTA", "Grand Slam",
    "Six Nations", "Super Rugby", "NRL", "AFL", "Big Ten", "SEC", "ACC", "Big 12",
]
_COMP_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in
                      sorted(COMPETITIONS, key=len, reverse=True)) + r")\b", re.I)
_COMP_CANON = {c.lower(): c for c in COMPETITIONS}


def competition(*texts):
    """The first known competition named in the texts, or ""."""
    for t in texts:
        m = _COMP_RE.search(t or "")
        if m:
            return _COMP_CANON[m.group(1).lower()]
    return ""

# "US (Peacock 003) | Title (2026-10-20 14:50:05)"
SLOT_FIRST = re.compile(
    r"^\s*(?P<cc>[A-Z]{2})\s*\((?P<slot>[^)]*)\)\s*\|\s*(?P<title>.*?)\s*"
    r"\((?P<date>\d{4}-\d{2}-\d{2})[ T](?P<time>\d{1,2}:\d{2})(?::\d{2})?\)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# "UEFA | 28 - Universitatea Craiova vs Getafe 20:00 pm" - kick-off time (UK) only, no date
KICKOFF_ONLY = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z0-9+ ]*?)\s*\|\s*(?P<num>\d+)\s*-\s*(?P<title>.+?)"
                          r"\s+(?P<h>\d{1,2})[:.](?P<m>\d{2})\s*(?P<ap>[ap]\.?m\.?)?\s*$", re.I)
KICKOFF_EARLY_MINUTES = 10     # these streams go LIVE this many minutes before kick-off
# "UEFA | 08 -" - a slot with nothing on it yet (shows filler)
EMPTY_SLOT = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z0-9+ ]*?)\s*\|\s*(?P<num>\d+)\s*-?\s*$")
# Names like "UEFA | 01 - Como vs Manchester United 17:45 pm" carry no date, so the date is
# taken from the football guide (football_epg.xml, in the repo): the fixture with the same
# teams and kick-off. A name whose match is no longer in the football guide is over.
FOOTBALL_GUIDE_FILE = "football_epg.xml"
FOOTBALL_GUIDE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/football_epg.xml"
# Names with these labels ("UEFA | 01 - ...") are only matched to fixtures in competitions whose
# name starts with the same word, so a finished UEFA tie can't latch onto a later league match
# of one of its teams (e.g. "Lillestrom vs Real Sociedad" -> Athletic Club v Real Sociedad).
SAME_COMP_LABELS = {"uefa"}
HORIZON_HOURS = 24             # the guide only lists this far ahead (see add_programme).
                               # 4 h until 25 Oct 2026, then 12 h, then 24 h: PlaylistLabs refreshes
                               # each external EPG roughly once a day, in a rolling queue with no fixed
                               # time (plus manual "Force Refresh"), and only appends after what it
                               # holds - so the data must last until the next fetch. The user does one
                               # manual refresh a day; the automatic one is the backup.
                               # Trade-off: a listing is fixed up to this long before it airs, so when
                               # a slot moves to a new event the old listing can linger that long.
PIECE_HOURS = 2                # programmes are written in pieces of at most this length
                               # (1 h until 25 Oct 2026; 2 h with the 24-h horizon keeps the file
                               # about the size it was - PlaylistLabs may fail on very large files)
ENDED_FILLER_HOURS = HORIZON_HOURS   # a finished/empty slot shows "Channel is offline" for this
                               # long (was 2 h; raised with the horizon so these don't go blank)
# Name sections that are labels, not event information ("8K EXCLUSIVE", "4K", "HD" ...)
JUNK_RE = re.compile(r"(?i)\s*((8K|4K|UHD|FHD|HD|SD)\s*)?(EXCLUSIVE|ONLY)?\s*|\s*(8K|4K|UHD|FHD|HD|SD)\s*")
# "Wed 21 Oct 19:00 EDT (US)" - date and time in one field, no year
DAYTIME_RE = re.compile(r"^(?:[A-Za-z]{3}\s+)?(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{1,2}:\d{2})"
                        r"(?:\s+([A-Z]{2,5}))?(?:\s*\([A-Z]{2}\))?$")
TIME_RE = re.compile(r"^(\d{1,2}:\d{2})(?::\d{2})?\s*(?:\((\w+)\))?$")
# MLS streams (names start "(Apple) (MLS)"). Their times are US Eastern (checked against real kick-offs); the guide
# shows them in UK time like every other stream.
MLS_TZ = "America/New_York"
# "(Apple) (MLS) 001 | Montréal vs. Nashville (2026-10-24 13:25:00)"  -> AppleMLS001.us
# NFL and NHL slots: "NFL  | 02 - 9:30am Steelers at Saints", "NFL  | 13 - SNF 8:20pm Chiefs at
# Seahawks", "NHL | 04 - 7pm Rangers at Senators", "NHL LIVE| 17 - ...".
# The names carry no date and their times are US Eastern; the date is taken from ESPN's
# schedule (the game with the same two teams nearest to now). A game no longer on the schedule
# is over. Each slot keeps the ID of its empty version: "NFL | 02 -" and a game on slot 02 are
# both NFL2.uk; "NHL LIVE| 17 -" is NHLLIVE17.uk.
NFL_SLOT = re.compile(r"^\s*(?P<label>NFL|NHL(?:\s*LIVE)?)\s*\|\s*(?P<num>\d+)\s*-\s*(?P<rest>\S.*?)\s*$", re.I)
# label word -> (ESPN schedule, LIVE block hours)
US_LEAGUES = {"NFL": ("football/nfl", 3.5), "NHL": ("hockey/nhl", 3)}
NFL_TIME = re.compile(r"\b(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\b\.?", re.I)
NFL_TZ = "America/New_York"
NFL_EVENT_HOURS = 3.5          # NFL games usually run 3 h 10 - 3 h 30
NFL_SHOWS = {"SNF": "Sunday Night Football", "TNF": "Thursday Night Football",
             "MNF": "Monday Night Football"}
NFL_SHOW_DAY = {"SNF": 6, "TNF": 3, "MNF": 0}     # weekday (Mon=0) - used only without ESPN
# One request per day (?dates=YYYYMMDD), the same way football_epg.py reads ESPN - a date
# range in one request is rejected (HTTP 400).
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{}/scoreboard?dates={}"
NFL_ESPN = "football/nfl"
# NBA streams: "Charlotte Hornets vs Miami Heat  @ Oct 24 6:00 PM :NBA  01" (US Eastern) -> NBA1.uk.
# Only names ending ":NBA <number>" are read (the same layout with ":MLS 01" stays ignored).
NBA_AT = re.compile(
    r"^\s*(?P<title>.+?)\s*@\s*(?P<mon>[A-Za-z]{3})[a-z]*\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+"
    r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\.?\s*:\s*NBA\s*(?P<num>\d+)\s*$", re.I)
NBA_TZ = "America/New_York"
NBA_ESPN = "basketball/nba"
NBA_EVENT_HOURS = 3
# MLB streams, two styles:
#   "MLB 01 : Rays x Guardians start:2026-10-18 22:08:00 stop:2026-10-19 05:21:20"  (MLB_START_TZ)
#   "MLB 13 | Baltimore vs Tampa Bay @ Aug 14 7:00 PM"                              (US Eastern)
# Both give slot IDs MLB1.uk, MLB13.uk ... When ESPN's MLB schedule has the same two teams
# within MLB_MATCH_HOURS of the name's time, ESPN's first-pitch time is used instead (this also
# corrects the time if MLB_START_TZ is wrong - the log prints a check line for each).
MLB_START = re.compile(
    r"^\s*MLB\s*(?P<num>\d+)\s*:\s*(?P<title>.+?)\s+start:\s*(?P<date>\d{4}-\d{2}-\d{2})[ T]"
    r"(?P<time>\d{1,2}:\d{2})(?::\d{2})?(?:\s+stop:\s*\S+(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)?\s*$", re.I)
MLB_AT = re.compile(
    r"^\s*MLB\s*(?P<num>\d+)\s*\|\s*(?P<title>.+?)\s*@\s*(?P<mon>[A-Za-z]{3})[a-z]*\.?\s+(?P<day>\d{1,2})"
    r"(?:st|nd|rd|th)?,?\s+(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\.?\s*$", re.I)
MLB_EMPTY = re.compile(r"^\s*MLB\s*(?P<num>\d+)\s*[:|\-]?\s*$", re.I)
MLB_START_TZ = "UTC"           # "start:" times look like UTC (01:00 = 9 pm ET); check the log
MLB_AT_TZ = "America/New_York"
MLB_ESPN = "baseball/mlb"
MLB_EVENT_HOURS = 3.5          # allows for extra innings
MLB_EARLY_MINUTES = 10         # LIVE this long before first pitch
MLB_MATCH_HOURS = 18
# PDC darts streams (the Boxing group was removed from the playlist and from this script):
#   "PDC Board 02 : Title | Day 3 - Evening Session Watch live ... start:2026-10-18 18:00:00
#    stop:2026-10-18 23:00:00"                         (UK time)          -> PDCBoard2.uk
#   "PDC event 01 : Title | Session Watch live ..."    (no time)          -> PDCEvent1.uk
# An event with no time gets UNTIMED_HOURS of blocks with its name (no LIVE block, as the time
# isn't known). SEEN_FILE records when each name was first seen (used for TOD "Live" names).
PDC = re.compile(r"^\s*PDC\s*(?P<kind>[A-Za-z]+)?\s*(?P<num>\d+)\s*[:|\-]?\s*(?P<rest>.*?)\s*$", re.I)
START_STOP = re.compile(r"\s*start:\s*(?P<d1>\d{4}-\d{2}-\d{2})[ T](?P<t1>\d{1,2}:\d{2})(?::\d{2})?"
                        r"(?:\s*stop:\s*(?P<d2>\d{4}-\d{2}-\d{2})[ T](?P<t2>\d{1,2}:\d{2})(?::\d{2})?)?\s*$", re.I)
INFO_START = re.compile(r"\s(?=(?:Watch|Follow|Catch|Join|Don't|Live coverage|Coverage|See)\b)")
DARTS_TZ = "Europe/London"
DARTS_EVENT_HOURS = 5
UNTIMED_HOURS = 12
SEEN_FILE = "events_seen.json"
MLS_APPLE = re.compile(
    r"^\s*\((?P<prov>[^)]+)\)\s*\((?P<label>[^)]+)\)\s*(?P<num>\d+)\s*\|\s*(?P<title>.*?)\s*"
    r"\((?P<date>\d{4}-\d{2}-\d{2})[ T](?P<time>\d{1,2}:\d{2})(?::\d{2})?\)\s*$")


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "", text)


# Groups whose slot numbers repeat across regions ("CA: SOCCER PPV 198" and "US: SOCCER PPV 198"):
# their IDs also start with the region code, so the two can't be mixed up when linking
# (CASOCCERPPV198.ca, USSOCCERPPV198.us).
REGION_PREFIX_GROUPS = {"SOCCERPPV"}


def pipe_slot_id(cc, label):
    """ID for a "CC: SLOT LABEL" stream ("GB: DAZN PPV 5" -> DAZNPPV5.gb)."""
    base = slug(label)
    if re.sub(r"\d+$", "", base).upper() in REGION_PREFIX_GROUPS:
        base = cc.strip().upper() + base
    return f"{base}.{cc.strip().lower()}"


_FIXTURES = None


def _team_key(name):
    """First significant word of a team name, for loose matching ("Manchester Utd" ->
    "manchester", "AFC Bournemouth" -> "bournemouth")."""
    words = re.sub(r"[^a-z0-9 ]+", " ", unicodedata.normalize("NFKD", name or "")
                   .encode("ascii", "ignore").decode().lower()).split()
    skip = {"fc", "afc", "cf", "sc", "ac", "as", "ss", "sk", "fk", "nk", "the", "real", "club",
            "sporting", "athletic", "atletico", "inter", "dynamo", "dinamo", "olympique", "rc"}
    for w in words:
        if w not in skip and len(w) > 2:
            return w
    return words[0] if words else ""


def load_fixtures():
    """[(home_key, away_key, home, away, kick-off datetime UK, competition)] from the
    football guide, or None."""
    global _FIXTURES
    if _FIXTURES is not None:
        return _FIXTURES or None
    raw = None
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), FOOTBALL_GUIDE_FILE)
    try:
        if os.path.exists(local):
            with open(local, "rb") as f:
                raw = f.read()
        else:
            req = urllib.request.Request(FOOTBALL_GUIDE_URL, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"  WARNING: football guide not available for dating fixtures ({e})")
        _FIXTURES = []
        return None
    out = set()
    for p in root.iter("programme"):
        t = (p.findtext("title") or "")
        m = re.match(r"^(?:🔴 LIVE: )?(.+?) v (.+?) \((?:\w{3}) (\d{1,2}) (\w{3}), (\d{1,2}):(\d{2})\)$", t)
        if not m:
            continue
        year = int((p.get("start") or "2000")[:4])
        try:
            ko = datetime.strptime(f"{m[3]} {m[4]} {year} {m[5]}:{m[6]}", "%d %b %Y %H:%M") \
                .replace(tzinfo=LONDON)
        except ValueError:
            continue
        cats = [c.text or "" for c in p.findall("category")]
        comp = cats[2] if len(cats) > 2 else ""          # Sports, Football, <competition>
        out.add((_team_key(m[1]), _team_key(m[2]), m[1].strip(), m[2].strip(), ko, comp))
    _FIXTURES = sorted(out, key=lambda r: r[4])
    return _FIXTURES or None


_ESPN_GAMES = {}         # sport path -> games, or "failed"


def load_espn_games(sport, label):
    """[(home names, away names, start UTC)] from ESPN's schedule for `sport` ("football/nfl",
    "baseball/mlb"), 4 days back to 10 days ahead, or None if it can't be read."""
    if sport in _ESPN_GAMES:
        got = _ESPN_GAMES[sport]
        return got if got != "failed" else None
    today = datetime.now(ZoneInfo("America/New_York")).date()
    days = [today + timedelta(days=d) for d in range(-4, 11)]

    def grab(day):
        url = ESPN_SCOREBOARD.format(sport, day.strftime("%Y%m%d"))
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode("utf-8")).get("events") or []
            except Exception as e:
                err = e
                time.sleep(1.5 * (attempt + 1))
        print(f"  WARNING: {label} schedule for {day} not available ({err})")
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(grab, days))
    if all(r is None for r in results):
        print(f"  WARNING: {label} schedule not available - times taken from the stream names")
        _ESPN_GAMES[sport] = "failed"
        return None
    games, seen = [], set()
    for ev in (e for day in results if day for e in day):
        try:
            if ev.get("id") in seen:
                continue
            seen.add(ev.get("id"))
            ko = datetime.strptime(ev["date"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
            sides = []
            for c in ev["competitions"][0]["competitors"]:
                t = c.get("team", {})
                sides.append({_norm(t.get(k, "")) for k in
                              ("name", "displayName", "shortDisplayName", "location", "abbreviation")}
                             - {""})
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if len(sides) == 2:
            games.append((sides[0], sides[1], ko))
    print(f"  {label} schedule: {len(games)} games")
    _ESPN_GAMES[sport] = games
    return games


def _team_match(name, aliases):
    n = _norm(name)
    return bool(n) and any(n == a or n in a.split() or (len(n) > 3 and n in a) for a in aliases)


def slot_kickoff(league, title, h, mi, show):
    """Start (UTC) of the NFL/NHL game in `title` ("Steelers at Saints") at h:mi US Eastern.
    The date comes from ESPN's schedule; False = not on the schedule (game over)."""
    tz = ZoneInfo(NFL_TZ)
    now = datetime.now(timezone.utc)
    sides = re.split(r"\s+(?:at|vs?\.?|@)\s+", title, maxsplit=1, flags=re.I)
    games = load_espn_games(US_LEAGUES[league][0], league)
    if games is not None and len(sides) == 2:
        hits = [ko for a, b, ko in games
                if (_team_match(sides[0], a) and _team_match(sides[1], b)) or
                   (_team_match(sides[0], b) and _team_match(sides[1], a))]
        if not hits:
            return False
        ko = min(hits, key=lambda k: abs(k - now))
        if h is None:
            return ko
        local = ko.astimezone(tz)               # ESPN's date, the stream name's time
        return local.replace(hour=h, minute=mi).astimezone(timezone.utc)
    if games is not None or h is None:
        return None
    if league != "NFL":          # no schedule: games are listed on the day, so today (US Eastern)
        d = now.astimezone(tz).date()
        return datetime(d.year, d.month, d.day, h, mi, tzinfo=tz).astimezone(timezone.utc)
    # No schedule: the next game day (Sunday, or the day the SNF/TNF/MNF label gives)
    day = NFL_SHOW_DAY.get(show, 6)
    d = now.astimezone(tz).date() - timedelta(days=1)
    for _ in range(9):
        cand = datetime(d.year, d.month, d.day, h, mi, tzinfo=tz)
        if cand.weekday() == day and \
                cand + timedelta(hours=NFL_EVENT_HOURS + PAST_EVENT_HOURS) >= now:
            return cand.astimezone(timezone.utc)
        d += timedelta(days=1)
    return None


_MLB_CHECKS = 0


def month_day_time(mon, day, h, mi, ap, tz):
    """"Oct 24", 6:00 PM in `tz` -> datetime in the year nearest today, or None."""
    h = int(h) % 12 + (12 if ap.lower() == "p" else 0)
    now_l = datetime.now(tz)
    best = None
    for year in (now_l.year, now_l.year - 1, now_l.year + 1):
        try:
            cand = datetime.strptime(f"{int(day)} {mon[:3]} {year}", "%d %b %Y") \
                .replace(hour=h, minute=int(mi or 0), tzinfo=tz)
        except ValueError:
            continue
        if best is None or abs(cand - now_l) < abs(best - now_l):
            best = cand
    return best


def espn_start(sport, label, title, approx):
    """ESPN's start (UTC) for `title` ("Rays vs Guardians") near `approx`, else `approx`."""
    global _MLB_CHECKS
    sides = re.split(r"\s+(?:x|vs?\.?|at|@)\s+", title, maxsplit=1, flags=re.I)
    games = load_espn_games(sport, label) if len(sides) == 2 else None
    if not games:
        return approx
    hits = [ko for a, b, ko in games
            if ((_team_match(sides[0], a) and _team_match(sides[1], b)) or
                (_team_match(sides[0], b) and _team_match(sides[1], a)))
            and abs(ko - approx) <= timedelta(hours=MLB_MATCH_HOURS)]
    if not hits:
        return approx
    ko = min(hits, key=lambda k: abs(k - approx))
    if _MLB_CHECKS < 5:
        _MLB_CHECKS += 1
        print(f"  {label} time check: {title}: name {approx:%d %b %H:%M} UTC, "
              f"ESPN start {ko:%d %b %H:%M} UTC")
    return ko


def _norm(name):
    return re.sub(r"[^a-z0-9 ]+", " ", unicodedata.normalize("NFKD", name or "")
                  .encode("ascii", "ignore").decode().lower()).strip()


def fixture_date(title, h, mi, now, label=""):
    """Kick-off (UK) of the fixture named in `title` at h:mi, from the football guide.
    Returns a datetime, False if the guide is loaded but has no such fixture (match over),
    or None if the football guide isn't available. A label in SAME_COMP_LABELS ("UEFA")
    limits the search to that competition's fixtures."""
    fx = load_fixtures()
    if fx is None:
        return None
    sides = re.split(r"\s+(?:vs?\.?|-)\s+", title, maxsplit=1, flags=re.I)
    if len(sides) != 2:
        return None
    def similar(a_key, a_name, b_key, b_name):
        """Same team, allowing for small spelling slips ("Araenal" = "Arsenal")."""
        if a_key and a_key == b_key:
            return True
        return (SequenceMatcher(None, a_key, b_key).ratio() >= 0.8 or
                SequenceMatcher(None, _norm(a_name), _norm(b_name)).ratio() >= 0.8)

    hk, ak = _team_key(sides[0]), _team_key(sides[1])
    both, one = [], []
    word = label.strip().split()[0].lower() if label.strip() else ""
    for fh, fa, fhn, fan, ko, comp in fx:
        if word in SAME_COMP_LABELS and not comp.lower().startswith(word):
            continue                  # e.g. a UEFA stream never matches a league fixture
        h_ok = similar(hk, sides[0], fh, fhn) or similar(hk, sides[0], fa, fan)
        a_ok = similar(ak, sides[1], fa, fan) or similar(ak, sides[1], fh, fhn)
        if h_ok and a_ok:
            both.append(ko)
        elif (h_ok or a_ok) and (ko.hour, ko.minute) == (h, mi):
            one.append(ko)            # one team matches and the kick-off time agrees
    hits = both or one
    if not hits:
        return False
    same_time = [ko for ko in hits if (ko.hour, ko.minute) == (h, mi)] or hits
    return min(same_time, key=lambda ko: abs(ko - now))


# TOD (beIN, Middle East) streams:
#   "Next | Austin Round - Reverse Grid Race || Arabic | F1 Academy | 24-10-2026 | 22:35 (GMT) |
#    8K EXCLUSIVE | MENA: AR PPV 27"                                  -> ARPPV27.mena
#   "Live | Zambia vs France || Arabic | FIFA U-17 Women's WC | 8K EXCLUSIVE | MENA: AR PPV 20"
#   "End | Arsenal vs Everton || English | ... | 24-10-2026 | 13:40 (GMT) | ... | MENA: AR PPV 9"
# Status first: "End" = over; "Live" with no time = live since the name was first seen
# (SEEN_FILE). The language goes in the description, not the title.
TOD_SLOT = re.compile(r"^(?P<cc>[A-Z]{3,5}):\s*(?P<label>\S.*)$")
TOD_DATE = re.compile(r"^(?:(?P<d>\d{1,2})-(?P<m>\d{1,2})-(?P<y>\d{4})|(?P<y2>\d{4})-(?P<m2>\d{2})-(?P<d2>\d{2}))$")
# Placeholder text on an empty slot ("NO EVENT STREAMING NOW -") - shown as "Channel is offline"
NO_EVENT = re.compile(r"(?i)^\W*(no\s+(live\s+)?(event|events|stream|streams|match|game)s?\b|offline\b|"
                      r"coming\s+soon\W*$|tba\W*$|tbc\W*$)")
TOD_TZ = "Asia/Qatar"          # used only if the name gives a time without "(GMT)" etc.
LANGUAGES = {"arabic", "english", "french", "spanish", "turkish", "persian", "urdu", "hindi",
             "multi", "multilanguage", "multi-language", "portuguese", "german", "italian"}

_SEEN, _SEEN_USED = None, {}


def first_seen(slot_id, name):
    """When this stream name was first seen on this slot (UTC), from SEEN_FILE."""
    global _SEEN
    if _SEEN is None:
        try:
            with open(SEEN_FILE, encoding="utf-8") as f:
                _SEEN = json.load(f)
        except (OSError, ValueError):
            _SEEN = {}
    rec = _SEEN.get(slot_id)
    if rec and rec.get("name") == name:
        seen = datetime.fromisoformat(rec["seen"])
    else:
        seen = datetime.now(timezone.utc).replace(microsecond=0)
    _SEEN_USED[slot_id] = {"name": name, "seen": seen.isoformat()}
    return seen


def save_seen():
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(_SEEN_USED.items())), f, indent=1, ensure_ascii=False)


def _nice_title(t):
    t = re.sub(r"\s+", " ", t).strip(" -|:@")
    if re.sub(r"\b(?:vs?|v)\b\.?", "", t).isupper():
        t = t.title()
    return re.sub(r"\b(V|Vs|VS)\b\.?", lambda m: m.group(1).lower(), t)


def parse_tod(name):
    parts = [p.strip() for p in name.split("|")]
    if len(parts) < 3:
        return None
    sm = TOD_SLOT.match(parts[-1])
    if not sm:
        return None
    cc, label = sm["cc"], sm["label"].strip()
    slot_id, slot_name = pipe_slot_id(cc, label), f"{cc}: {label}"
    status = parts[0].lower() if parts[0].lower() in STATUS_WORDS else ""
    date = time_ = zone = None
    text, langs = [], []
    for p in parts[1 if status else 0:-1]:
        if not p or JUNK_RE.fullmatch(p):
            continue
        dm, tm = TOD_DATE.match(p), TIME_RE.match(p)
        if dm:
            date = (int(dm["y"] or dm["y2"]), int(dm["m"] or dm["m2"]), int(dm["d"] or dm["d2"]))
        elif tm:
            time_ = tm.group(1)
            zone = ABBREV_TZ.get((tm.group(2) or "").upper())
        elif p.lower() in LANGUAGES:
            langs.append(p.capitalize())
        else:
            text.append(p)
    text = [t for t in text if not NO_EVENT.match(t)]
    if not text:                                     # nothing on the slot ("NO EVENT STREAMING NOW -")
        return {"name": name, "slot_id": slot_id, "slot_name": slot_name, "title": "",
                "extra": "", "comp": "", "start": datetime.now(timezone.utc) - timedelta(days=1)}
    title = text[0]
    comp = text[1] if len(text) > 1 else competition(title)
    extra = ". ".join(t for t in [*text[2:], f"{', '.join(langs)} commentary" if langs else ""] if t)
    ev = {"name": name, "slot_id": slot_id, "slot_name": slot_name, "title": title,
          "extra": extra, "comp": comp or "", "start": None}
    now = datetime.now(timezone.utc)
    if status in ("end", "ended", "finished", "off"):
        ev["start"] = now - timedelta(days=2)            # the name says it's over
    elif date and time_:
        h, mi = map(int, time_.split(":"))
        ev["start"] = datetime(*date, h, mi, tzinfo=ZoneInfo(zone or TOD_TZ)).astimezone(timezone.utc)
    elif status == "live":
        ev["start"] = first_seen(slot_id, name).replace(minute=0, second=0)   # live since we
                                                         # first saw this name (from the hour)
    else:
        ev["untimed"] = True
        ev["start"] = now
    return ev


def parse_darts(name):
    p = PDC.match(name)
    if not p:
        return None
    m = p
    num = int(m["num"])
    kind = (p["kind"] or "").capitalize()
    slot_id, slot_name, comp, hours, tz = f"PDC{kind}{num}.uk", f"PDC {kind} {num}".replace("  ", " "), \
        "PDC Darts", DARTS_EVENT_HOURS, ZoneInfo(DARTS_TZ)
    rest = m["rest"]
    if not rest:                                     # empty slot
        return {"name": name, "slot_id": slot_id, "slot_name": slot_name, "title": "",
                "extra": "", "comp": "", "start": datetime.now(timezone.utc) - timedelta(days=1)}
    start = None
    ss = START_STOP.search(rest)
    if ss:                                           # start:/stop: given (UK time)
        start = datetime.strptime(f"{ss['d1']} {ss['t1']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        if ss["d2"]:
            stop = datetime.strptime(f"{ss['d2']} {ss['t2']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            if timedelta(hours=1) <= stop - start <= timedelta(hours=14):
                hours = (stop - start).total_seconds() / 3600
        start = start.astimezone(timezone.utc)
        rest = rest[:ss.start()]
    extra, info = "", ""
    title, _, after = rest.partition("|")
    title = _nice_title(title)
    after = after.strip()
    if after:
        parts = INFO_START.split(after, maxsplit=1)
        extra = parts[0].strip(" -|")
        info = parts[1].strip() if len(parts) > 1 else ""
        if info and info[-1] not in ".!?":
            info += "…"
    if not title:
        return None
    ev = {"name": name, "slot_id": slot_id, "slot_name": slot_name, "title": title,
          "extra": extra, "info": info, "comp": comp, "hours": hours}
    if start is None:
        ev["untimed"] = True
        ev["start"] = datetime.now(timezone.utc)
    else:
        ev["start"] = start
    return ev


# Empty slots in the other groups (shown as "Channel is offline", same ID as when filled):
EMPTY_COUNTRY_SLOT = re.compile(r"^\s*(?P<cc>[A-Z]{2})\s*\((?P<slot>[^)]*\d[^)]*)\)\s*(?:\|\s*(?P<rest>.*?))?\s*$")
EMPTY_APPLE = re.compile(r"^\s*\((?P<prov>[^)]+)\)\s*\((?P<label>[^)]+)\)\s*(?P<num>\d+)\s*(?:\|\s*(?P<rest>.*?))?\s*$")
EMPTY_NBA = re.compile(r"^\W*NBA\s*(?P<num>\d+)\s*$", re.I)
PIPE_SLOT = re.compile(r"^(?P<cc>[A-Z]{2,5}):\s*(?P<label>\S.*)$")


def _empty_slot(name, slot_id, slot_name):
    return {"name": name, "slot_id": slot_id, "slot_name": slot_name, "title": "", "extra": "",
            "comp": "", "start": datetime.now(timezone.utc) - timedelta(days=1)}


def _placeholder(text):
    """True for nothing / "NO EVENT STREAMING NOW -" / "8K EXCLUSIVE" / a status word only."""
    t = (text or "").strip(" -|:")
    return not t or bool(NO_EVENT.match(t)) or bool(JUNK_RE.fullmatch(t)) or t.lower() in STATUS_WORDS


def empty_slot(name):
    """The slot of a stream with no event on it, in any group's naming style, else None."""
    m = EMPTY_COUNTRY_SLOT.match(name)               # US (Peacock 099)  /  AU (STAN 40) | No event
    if m and _placeholder(m["rest"]):
        return _empty_slot(name, f"{slug(m['slot'])}.{m['cc'].lower()}", f"{m['cc']} ({m['slot']})")
    m = EMPTY_APPLE.match(name)                      # (Apple) (MLS) 049 |
    if m and _placeholder(m["rest"]):
        label = m["label"].strip()
        return _empty_slot(name, f"{slug(m['prov'] + label)}{m['num']}.us",
                           f"({m['prov'].strip()}) ({label}) {m['num']}")
    m = EMPTY_NBA.match(name)                        # NBA 05
    if m:
        return _empty_slot(name, f"NBA{int(m['num'])}.uk", f"NBA {int(m['num'])}")
    parts = [p.strip() for p in name.split("|")]     # NO EVENT STREAMING NOW - | 8K EXCLUSIVE | GB: DAZN PPV 9
    if len(parts) >= 2:
        sm = PIPE_SLOT.match(parts[-1])
        if sm and all(_placeholder(p) for p in parts[:-1]):
            label = sm["label"].strip()
            return _empty_slot(name, pipe_slot_id(sm['cc'], label), f"{sm['cc']}: {label}")
    return None


def parse_name(name):
    """{slot_id, slot_name, title, extra, start (UTC)} for an event name, else None."""
    name = re.sub(r"\s+", " ", name or "").strip()
    ev = _parse_name(name)
    if ev is None:
        return empty_slot(name)
    if ev.get("title") and NO_EVENT.match(ev["title"]):    # "No Event (2026-10-24 20:00)" etc.
        return _empty_slot(name, ev["slot_id"], ev["slot_name"])
    if ev and ev.get("title"):       # "• Chelsea v Tottenham" (Stan's second feed) -> no bullet
        ev["title"] = re.sub(r"^[\s•·*\-–]+", "", ev["title"]).strip()
    return ev


def _parse_name(name):
    name = re.sub(r"\s+", " ", name or "").strip()

    fd = parse_darts(name) or parse_tod(name)
    if fd:
        return fd

    mlb = MLB_START.match(name) or MLB_AT.match(name)
    if mlb:                                          # MLB 01 : A x B start:... / MLB 13 | A vs B @ Aug 14 7:00 PM
        title = re.sub(r"\s+x\s+", " vs ", mlb["title"].strip(), flags=re.I)
        if "date" in mlb.groupdict():
            approx = datetime.strptime(f"{mlb['date']} {mlb['time']}", "%Y-%m-%d %H:%M") \
                .replace(tzinfo=ZoneInfo(MLB_START_TZ))
        else:
            approx = month_day_time(mlb["mon"], mlb["day"], mlb["h"], mlb["m"], mlb["ap"],
                                    ZoneInfo(MLB_AT_TZ))
            if approx is None:
                return None
        start = espn_start(MLB_ESPN, "MLB", title, approx.astimezone(timezone.utc))
        num = int(mlb["num"])
        return {"name": name, "slot_id": f"MLB{num}.uk", "slot_name": f"MLB {num}",
                "title": title, "extra": "", "comp": "MLB", "hours": MLB_EVENT_HOURS,
                "early": MLB_EARLY_MINUTES, "start": start}
    b = NBA_AT.match(name)                           # A vs B @ Oct 24 6:00 PM :NBA 01 (US Eastern)
    if b:
        title = re.sub(r"\s+", " ", b["title"]).strip()
        approx = month_day_time(b["mon"], b["day"], b["h"], b["m"], b["ap"], ZoneInfo(NBA_TZ))
        if approx is None:
            return None
        start = espn_start(NBA_ESPN, "NBA", title, approx.astimezone(timezone.utc))
        num = int(b["num"])
        return {"name": name, "slot_id": f"NBA{num}.uk", "slot_name": f"NBA {num}",
                "title": title, "extra": "", "comp": "NBA", "hours": NBA_EVENT_HOURS,
                "start": start}
    me = MLB_EMPTY.match(name)                       # "MLB 05" with nothing on it
    if me:
        num = int(me["num"])
        return {"name": name, "slot_id": f"MLB{num}.uk", "slot_name": f"MLB {num}", "title": "",
                "extra": "", "comp": "", "start": datetime.now(timezone.utc) - timedelta(days=1)}

    e = EMPTY_SLOT.match(name)                       # "UEFA | 08 -": no match on this slot yet
    if e:
        label = e["label"].strip()
        return {"name": name, "slot_id": f"{slug(label)}{int(e['num'])}.uk",
                "slot_name": f"{label} | {int(e['num'])}", "title": "", "extra": "", "comp": "",
                "start": datetime.now(timezone.utc) - timedelta(days=1)}   # -> filler only

    n = NFL_SLOT.match(name)                         # NFL | 02 - 9:30am Steelers at Saints (ET)
    if n:                                            # (and NHL | 04 - 7pm Rangers at Senators)
        rest = n["rest"]
        show = next((w for w in NFL_SHOWS if re.search(rf"\b{w}\b", rest)), "")
        t = NFL_TIME.search(rest)
        h = mi = None
        if t:
            h, mi = int(t["h"]) % 12, int(t["m"] or 0)
            if t["ap"].lower() == "p":
                h += 12
            rest = rest[:t.start()] + " " + rest[t.end():]
        if show:
            rest = re.sub(rf"\b{show}\b", " ", rest)
        title = re.sub(r"\s+", " ", rest).strip(" -|:")
        league = "NHL" if n["label"].upper().startswith("NHL") else "NFL"
        if league != "NFL":
            show = ""
        start = slot_kickoff(league, title, h, mi, show)
        if start is None:
            return None
        if start is False:                            # no longer on the schedule: it's over
            start = datetime.now(timezone.utc) - timedelta(days=2)
        num = int(n["num"])
        label = re.sub(r"\s+", " ", n["label"].upper())
        return {"name": name, "slot_id": f"{slug(label)}{num}.uk", "slot_name": f"{label} | {num}",
                "title": title, "extra": NFL_SHOWS.get(show, ""), "comp": league,
                "hours": US_LEAGUES[league][1], "start": start}

    k = KICKOFF_ONLY.match(name)                     # UEFA | 28 - A vs B 20:00 pm (UK, today)
    if k:
        h, mi, ap = int(k["h"]), int(k["m"]), (k["ap"] or "").lower()
        if ap.startswith("p") and h < 12:
            h += 12
        elif ap.startswith("a") and h == 12:
            h = 0
        now = datetime.now(LONDON)
        found = fixture_date(k["title"].strip(), h, mi, now, k["label"])
        if found:                                     # date from the football guide
            local = found
        elif found is False:                          # match no longer listed: it's over
            # dated 2 days back so it always counts as finished (1 day back made a late
            # kick-off look like last night's game just after midnight, showing a false LIVE)
            local = now.replace(hour=h, minute=mi, second=0, microsecond=0) - timedelta(days=2)
        else:                                         # no football guide: assume today/tomorrow
            local = now.replace(hour=h, minute=mi, second=0, microsecond=0)
            if local + timedelta(hours=EVENT_HOURS + PAST_EVENT_HOURS) < now:
                local += timedelta(days=1)
        label = k["label"].strip()
        return {"name": name, "slot_id": f"{slug(label)}{int(k['num'])}.uk",
                "slot_name": f"{label} | {int(k['num'])}",
                "title": k["title"].strip(), "extra": "",
                "comp": competition(k["title"]) or label,
                "early": KICKOFF_EARLY_MINUTES,
                "start": local.astimezone(timezone.utc)}

    a = MLS_APPLE.match(name)                        # (Apple) (MLS) 001 | A vs. B (date time)
    if a:
        local = datetime.strptime(f"{a['date']} {a['time']}", "%Y-%m-%d %H:%M") \
            .replace(tzinfo=ZoneInfo(MLS_TZ))
        label = a["label"].strip()
        return {"name": name, "slot_id": f"{slug(a['prov'] + label)}{a['num']}.us",
                "slot_name": f"({a['prov'].strip()}) ({label}) {a['num']}",
                "title": a["title"].strip(), "extra": "",
                "comp": competition(a["title"], label) or label,
                "start": local.astimezone(timezone.utc)}

    m = SLOT_FIRST.match(name)                       # US (Peacock 003) | ... (date time)
    if m:
        tz = ZoneInfo(COUNTRY_TZ.get(m["cc"], "Europe/London"))
        local = datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        return {"name": name, "slot_id": f"{slug(m['slot'])}.{m['cc'].lower()}",
                "slot_name": f"{m['cc']} ({m['slot']})",
                "title": m["title"].strip(), "extra": "", "comp": competition(m["title"]),
                "start": local.astimezone(timezone.utc)}

    parts = [p.strip() for p in name.split("|")]     # End | Title | Comp | date | time (TZ) | ... | GB: SLOT
    if len(parts) >= 4:
        di = next((i for i, p in enumerate(parts) if DATE_RE.match(p)), None)
        ti = next((i for i, p in enumerate(parts) if TIME_RE.match(p)), None)
        slot = next((p for p in reversed(parts) if re.match(r"^[A-Z]{2}:\s*\S", p)), None)
        dti = next((i for i, p in enumerate(parts) if DAYTIME_RE.match(p)), None)
        if (di is None or ti is None) and dti is not None and slot:      # HBO Max style
            dm = DAYTIME_RE.match(parts[dti])
            cc, slot_label = slot.split(":", 1)
            zone = ABBREV_TZ.get((dm.group(4) or "").upper()) or COUNTRY_TZ.get(cc, "Europe/London")
            tz = ZoneInfo(zone)
            now = datetime.now(tz)
            local = None
            for year in (now.year, now.year + 1, now.year - 1):   # the year closest to today
                try:
                    cand = datetime.strptime(f"{dm.group(1)} {dm.group(2)} {year} {dm.group(3)}",
                                             "%d %b %Y %H:%M").replace(tzinfo=tz)
                except ValueError:
                    continue
                if local is None or abs(cand - now) < abs(local - now):
                    local = cand
            if local is not None:
                text = [p for i, p in enumerate(parts) if i != dti and p != slot]
                if text and text[0].lower() in STATUS_WORDS:
                    text = text[1:]
                text = [t for t in text if not JUNK_RE.fullmatch(t)]
                title = text[0] if text else slot_label.strip()
                extra = ". ".join(t for t in text[1:] if t)
                return {"name": name, "slot_id": pipe_slot_id(cc, slot_label),
                        "slot_name": f"{cc}: {slot_label.strip()}",
                        "title": title, "extra": extra, "comp": competition(title, extra),
                        "start": local.astimezone(timezone.utc)}
        if di is not None and ti is not None and slot:
            tm = TIME_RE.match(parts[ti])
            cc, slot_label = slot.split(":", 1)
            zone = ABBREV_TZ.get((tm.group(2) or "").upper()) or COUNTRY_TZ.get(cc, "Europe/London")
            local = datetime.strptime(f"{parts[di]} {tm.group(1)}", "%Y-%m-%d %H:%M") \
                .replace(tzinfo=ZoneInfo(zone))
            text = [p for i, p in enumerate(parts) if i not in (di, ti) and p != slot]
            if text and text[0].lower() in STATUS_WORDS:
                text = text[1:]
            text = [t for t in text if not JUNK_RE.fullmatch(t)]
            title = text[0] if text else slot_label.strip()
            extra = ". ".join(t for t in text[1:] if t)
            comp = text[1] if len(text) > 1 and not re.search(r"\b(8K|4K|HD|UHD|EXCLUSIVE)\b", text[1]) else ""
            return {"name": name, "slot_id": pipe_slot_id(cc, slot_label),
                    "slot_name": f"{cc}: {slot_label.strip()}",
                    "title": title, "extra": extra, "comp": comp or competition(title, extra),
                    "start": local.astimezone(timezone.utc)}
    return None


def read_playlist(args):
    if args.m3u:
        with open(args.m3u, encoding="utf-8", errors="replace") as f:
            return f.read()
    url = os.environ.get("PLAYLIST_URL", "").strip()
    if not url:
        sys.exit("No playlist: set the PLAYLIST_URL secret, or use --m3u FILE.")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", errors="replace")


def stream_names(text):
    """Display names of every #EXTINF line: tvg-name, else the text after the comma that ends
    the attributes (names can contain commas themselves, e.g. "St. Catharines, Ontario")."""
    for line in text.splitlines():
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-name="([^"]*)"', line)
            if m:
                yield m.group(1).strip()
                continue
            bare = re.sub(r'\s[\w-]+="[^"]*"', "", line)
            yield (bare.split(",", 1)[1] if "," in bare else bare).strip()


def uk(dt):
    return dt.astimezone(LONDON)


def xmltv_time(dt):
    return uk(dt).strftime("%Y%m%d%H%M%S %z")


_HORIZON = None    # set by build(): nothing is written that starts after this


def add_programme(tv, cid, start, stop, title, sub, desc, live=False):
    """Writes the programme in pieces of at most PIECE_HOURS, and only the pieces that start
    before the horizon (now + HORIZON_HOURS). PlaylistLabs never replaces a programme it has
    loaded, so when the provider moves a slot to a new event, the old listing can only linger
    until the end of what it already holds - at most HORIZON_HOURS."""
    t = start
    while t < stop:
        if _HORIZON is not None and t >= _HORIZON:
            break
        b = min(t + timedelta(hours=PIECE_HOURS), stop)
        p = ET.SubElement(tv, "programme", {"start": xmltv_time(t), "stop": xmltv_time(b),
                                            "channel": cid})
        ET.SubElement(p, "title", {"lang": "en"}).text = title
        if sub:
            ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
        if desc:
            ET.SubElement(p, "desc", {"lang": "en"}).text = desc
        ET.SubElement(p, "category", {"lang": "en"}).text = "Sports"
        if live:
            ET.SubElement(p, "category", {"lang": "en"}).text = "Live"
        t = b


def build(events, now):
    global _HORIZON
    _HORIZON = now + timedelta(hours=HORIZON_HOURS)
    tv = ET.Element("tv", {"generator-info-name": "event_epg.py"})
    by_slot, ended = {}, {}
    untimed = {}
    for ev in events:                       # one event per slot: the next one still to finish
        if ev.get("untimed"):
            untimed.setdefault(ev["slot_id"], ev)
            continue
        end = ev["start"] + timedelta(hours=ev.get("hours", EVENT_HOURS))
        if end + timedelta(hours=PAST_EVENT_HOURS) < now:
            ended.setdefault(ev["slot_id"], ev)
            continue
        cur = by_slot.get(ev["slot_id"])
        if cur is None or ev["start"] < cur["start"]:
            by_slot[ev["slot_id"]] = ev
    untimed = {sid: ev for sid, ev in untimed.items() if sid not in by_slot}
    ended = {sid: ev for sid, ev in ended.items() if sid not in by_slot and sid not in untimed}
    for sid in sorted(untimed):
        c = ET.SubElement(tv, "channel", {"id": sid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = untimed[sid]["name"]
        ET.SubElement(c, "display-name", {"lang": "en"}).text = untimed[sid]["slot_name"]
    for sid in sorted(set(by_slot) | set(ended)):
        if sid in ended:          # event over, nothing new yet: a channel with short filler
            c = ET.SubElement(tv, "channel", {"id": sid})
            ET.SubElement(c, "display-name", {"lang": "en"}).text = ended[sid]["name"]
            ET.SubElement(c, "display-name", {"lang": "en"}).text = ended[sid]["slot_name"]
            continue
        c = ET.SubElement(tv, "channel", {"id": sid})
        # the full stream name first, so PlaylistLabs' automatic search can match it exactly
        ET.SubElement(c, "display-name", {"lang": "en"}).text = by_slot[sid]["name"]
        ET.SubElement(c, "display-name", {"lang": "en"}).text = by_slot[sid]["slot_name"]
    count = 0
    for sid in sorted(by_slot):
        ev = by_slot[sid]
        kickoff = ev["start"]
        start = kickoff - timedelta(minutes=ev.get("early", 0))   # LIVE a little early where set
        end = kickoff + timedelta(hours=ev.get("hours", EVENT_HOURS))
        when = f"{uk(kickoff):%a} {uk(kickoff).day} {uk(kickoff):%b}, {uk(kickoff):%H:%M}"
        desc = f"{ev['title']}." + (f" {ev['extra']}." if ev["extra"] else "") + \
               f" Starts {when} UK time." + (f" {ev['info']}" if ev.get("info") else "")
        in_range = start <= now + timedelta(days=MAX_DAYS_AHEAD)
        # Out of range: generic filler only up to the range limit, so the event's own
        # "Coming up" blocks can still be added after it on a later run.
        stop_at = start if in_range else now + timedelta(days=MAX_DAYS_AHEAD)
        t = now.replace(minute=0, second=0, microsecond=0)
        t -= timedelta(hours=uk(t).hour % BLOCK_HOURS)
        while t < stop_at:
            b = min(t + timedelta(hours=BLOCK_HOURS), stop_at)
            if in_range:                                   # "Coming up" blocks
                add_programme(tv, sid, t, b, f"{ev['title']} ({when})",
                              f"⏭ Coming up {uk(kickoff):%a} {uk(kickoff).day} {uk(kickoff):%b}",
                              f"Coming up: {desc}")
            else:                                          # filler until the event is in range
                add_programme(tv, sid, t, b, FILLER_TITLE, None, FILLER_DESC)
            count += 1
            t = b
        if in_range:
            add_programme(tv, sid, start, end, f"🔴 LIVE: {ev['title']}",
                          ev.get("comp") or None, desc, live=True)  # secondary title: the competition
            count += 1
            # Straight after LIVE: "finished" blocks, so there's no gap with nothing listed.
            # Kept to ENDED_FILLER_HOURS, as PlaylistLabs only adds programmes after the last
            # one it holds - the slot's next event must be able to follow on.
            t = end
            while t < end + timedelta(hours=ENDED_FILLER_HOURS):
                b = min(t + timedelta(hours=BLOCK_HOURS), end + timedelta(hours=ENDED_FILLER_HOURS))
                add_programme(tv, sid, t, b, offline_title(ev), None, FINISHED_DESC)
                count += 1
                t = b
    t0 = now.replace(minute=0, second=0, microsecond=0)
    t0 -= timedelta(hours=uk(t0).hour % BLOCK_HOURS)
    for sid in sorted(untimed):  # event named but no time given: its name, no LIVE block
        ev = untimed[sid]
        desc = f"{ev['title']}." + (f" {ev['extra']}." if ev["extra"] else "") + \
               " The start time isn't given in the stream name." + \
               (f" {ev['info']}" if ev.get("info") else "")
        t = t0
        while t < now + timedelta(hours=UNTIMED_HOURS):
            b = t + timedelta(hours=BLOCK_HOURS)
            add_programme(tv, sid, t, b, ev["title"], ev.get("comp") or None, desc)
            count += 1
            t = b
    for sid in sorted(ended):    # kept short, so the slot's next event can follow it
        # a finished event says so; an empty slot ("UEFA | 08 -", no title) just says offline
        desc = FINISHED_DESC if ended[sid]["title"] else OFFLINE_DESC
        t = t0
        while t < now + timedelta(hours=ENDED_FILLER_HOURS):
            b = t + timedelta(hours=BLOCK_HOURS)
            add_programme(tv, sid, t, b, offline_title(ended[sid]), None, desc)
            count += 1
            t = b
    count = len(tv.findall("programme"))
    return tv, len(by_slot) + len(ended) + len(untimed), count


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--m3u", help="read this playlist file instead of PLAYLIST_URL")
    ap.add_argument("--out", default=OUTPUT_NAME)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    names = list(stream_names(read_playlist(args)))
    events = [e for e in (parse_name(n) for n in names) if e]
    print(f"{len(names)} streams in the playlist, {len(events)} with an event time")
    tv, chans, progs = build(events, now)
    save_seen()
    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(args.out, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {args.out}: {chans} channels, {progs} programmes")


if __name__ == "__main__":
    main()

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
    PLAYLIST_URL=... [PLAYLIST_URL_2=...] python3 event_epg.py   # download the playlist(s), write events_epg.xml
    python3 event_epg.py --m3u a.m3u [b.m3u]                      # use local files instead
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
# Longer LIVE blocks for events that run longer (added 27 Oct 2026) - used only when the
# stream's group doesn't set its own length (NFL, NBA, MLB, darts do). First match wins, so
# cricket comes before the "Day N" rule (a Test's "Day 3" gets 8 h, not 10).
#   cricket: a Test or ODI (~7-8 h a day), a T20 (~3.5 h)
#   all-day sessions: "Day 2", "Day #2", "Court 1", "Centre Court" (tennis order of play etc.)
LONG_EVENTS = [
    (re.compile(r"(?i)\b(ODI|one[- ]day|\d+(st|nd|rd|th)\s+test|test\s+match|tests?\b.*\bvs?\b)"), 8),
    (re.compile(r"(?i)\bT20I?\b"), 4),
    (re.compile(r"(?i)\bday\s*#?\s*\d+\b|\bcourt\b"), 10),
]


def event_hours(ev):
    """LIVE block length for `ev`: its own "hours", else LONG_EVENTS, else EVENT_HOURS."""
    if ev.get("hours"):
        return ev["hours"]
    text = " ".join(str(ev.get(k) or "") for k in ("title", "extra", "comp"))
    for pattern, hours in LONG_EVENTS:
        if pattern.search(text):
            return hours
    return EVENT_HOURS
BLOCK_HOURS = 2            # "Coming up" block length before the event
PAST_EVENT_HOURS = 2       # an event that has ended keeps its slot for this long (its LIVE
                           # block is followed straight away by ENDED_FILLER_HOURS of
                           # "This event has now finished" blocks, so there's no gap)
MAX_DAYS_AHEAD = 2         # events further ahead than this get filler until they come into range
FILLER_TITLE = "Stream is live at event time only."
FILLER_DESC = "The next event on this stream will be listed nearer the time."
# Shown on a slot whose event is over (or that is empty) until its stream name changes to a new event;
# the new event's real titles/descriptions then replace it automatically.
# 8 Nov 2026 (user): everything that has ended - a finished event or an empty slot - reads the same generic listing; the
# stream's own name in the playlist already shows the event, so the description no longer repeats it.
GENERIC_TITLE = "No streams available at this time"
GENERIC_DESC = "No streams available at this time. Check back later."
OFFLINE_TITLE = GENERIC_TITLE          # only used if a stream has no name at all
# 4 Nov 2026 (user): every EMPTY slot - whatever the provider calls it ("NO EVENT STREAMING NOW - | 8K EXCLUSIVE |
# CA: SOCCER PPV 100", "US (Peacock 099)", "AU (STAN 40) | No event streaming", "MLB 10 :", "UEFA | 08 -" ...) - gets
# this title, and a FINISHED event shows just its own name (see offline_title). The channel display-name is
# unchanged, so PlaylistLabs linking is not affected.
NO_EVENT_TITLE = GENERIC_TITLE         # was "No event streaming now" until 8 Nov 2026
# Finished/empty slots are titled with the stream's own name (25 Oct 2026), e.g.
# "US (Paramount 009) | Motherwell vs. Heart of Midlothian (2026-10-25 09:00:00)".


def offline_title(ev):
    """Title for the blocks of a finished or empty slot: the actual stream name, without a
    leading provider status word ("LIVE | Saint Peter's vs. Marist | ..." -> "Saint Peter's vs.
    Marist | ..."), so a finished slot doesn't look live in the guide (changed 28 Oct 2026)."""
    if not ev.get("offline_name"):             # 4 Nov 2026 (user): never the provider's raw stream name -
        # an empty slot gets NO_EVENT_TITLE, a finished event just its own name (no "US (Peacock 002) |" /
        # "| 8K EXCLUSIVE | US: MAX PPV 1" / "(2026-11-03 08:05:00)" around it). PPV EVENT slots (offline_name,
        # with the UK time) keep their format.
        return (ev.get("title") or "").strip() or NO_EVENT_TITLE
    name = (ev.get("offline_name") or ev.get("name") or "").strip()
    head, sep, rest = name.partition("|")
    if sep and head.strip().lower() in STATUS_WORDS and rest.strip():
        name = rest.strip()
    return name or OFFLINE_TITLE
OFFLINE_DESC = GENERIC_DESC            # was "This channel is offline. The next event will be listed when the stream is updated."
# Description used instead when the slot's last event has finished (an empty slot keeps OFFLINE_DESC)
FINISHED_DESC = GENERIC_DESC           # was "<event> has now finished. The next event will be listed when the stream is updated." until 8 Nov 2026
# 7 Nov 2026 (user): the blocks of a FINISHED event no longer repeat the event's name (\"Hong Kong: Day 6 WTA 250\" kept showing in the grid until
# the stream changed): the TITLE says it has finished, the name moves to the description. An empty slot is unchanged (\"No event streaming now\").
FINISHED_TITLE = "This event has now finished"   # 8 Nov 2026 briefly generic; restored 9 Nov (user): finished = this title + the generic description, an EMPTY slot = the generic title


def finished_desc(ev):
    return FINISHED_DESC       # 8 Nov 2026 (user): the generic text only - the event's name is already in the stream's name

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
KICKOFF_EARLY_MINUTES = 0      # these streams go LIVE this many minutes before kick-off (10 until 6 Nov 2026; the user: streams are not live before the kick-off)
# Paramount+ and Peacock (6 Nov 2026, user): their streams are NOT live until about the kick-off - there is no pre-roll; the provider can only
# link what is playing to the listed match once it is playing. So the LIVE block of these two groups starts AT the real kick-off (the
# stream time in the name is only when the stream opens), and the "Next up: LIVE" block runs up to it. 0 = at the kick-off; a negative number
# (e.g. -2) would start it that many minutes AFTER the kick-off.
PROVIDER_EARLY_MINUTES = 0
# "UEFA | 08 -" - a slot with nothing on it yet (shows filler)
EMPTY_SLOT = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z0-9+ ]*?)\s*\|\s*(?P<num>\d+)\s*-?\s*$")
# Names like "UEFA | 01 - Como vs Manchester United 17:45 pm" carry no date, so the date is
# taken from the football guide (football_epg.xml, in the repo): the fixture with the same
# teams and kick-off. A name whose match is no longer in the football guide is over.
FOOTBALL_GUIDE_FILE = "football_epg.xml"
FOOTBALL_GUIDE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/football_epg.xml"
# The Scottish guide is read as well (28 Oct 2026), for Scottish matches on Paramount+ / Soccer PPV.
SCOTTISH_GUIDE_FILE = "scottish_epg.xml"
SCOTTISH_GUIDE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/scottish_epg.xml"
# Slot groups whose stream-name time is when the STREAM starts, not the kick-off (28 Oct 2026):
# Paramount+ opens its streams 10-60 min early ("Liverpool vs. Chelsea (15:00 ET)" = 19:00 UK for a
# 19:45/20:00 kick-off). For these, real_start() looks up the real kick-off and the competition with
# its round, like the Soccer PPV slots. Peacock added 28 Oct 2026 (its Premier League streams open
# ~10 min early: "Hull City v. Ipswich Town (10:50 ET)" for a 15:00 UK kick-off).
REAL_START_GROUPS = ("paramount", "peacock", "stan")   # "stan" added 6 Nov 2026: Stan's stream time is ~30 min before kick-off (user: "Stan 04 times are out")
TEAM_SHORT_NAMES = [(r"(?i)^\s*spurs\s*$", "Tottenham Hotspur"), (r"(?i)^\s*wolves\s*$", "Wolverhampton"),
                    (r"(?i)\bnott'?m\.?\s+forest\b", "Nottingham Forest"),
                    (r"(?i)^\s*forest\s*$", "Nottingham Forest"), (r"(?i)^\s*palace\s*$", "Crystal Palace"),
                    (r"(?i)\bsheff\.?\s+(utd|united|wed|wednesday)\b", r"Sheffield \1"),
                    (r"(?i)\bqpr\b", "Queens Park Rangers"), (r"(?i)\bwest brom\b", "West Bromwich")]
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
# Slots that get a different match within a day (Peacock, Paramount+): their finished/empty blocks
# only run this far ahead (1 Nov 2026), so a slot that switches to a new event isn't stuck behind
# up to 24 h of old "finished" blocks PlaylistLabs already holds (Peacock 003 showed Bournemouth v.
# Leeds until 04:00 the next day for Liverpool v. Arsenal). Trade-off: these rows go blank this long
# after the last refresh. Slots are matched by id prefix, like REAL_START_GROUPS.
SHORT_ENDED_GROUPS = ("paramount", "peacock")
SHORT_ENDED_HOURS = HORIZON_HOURS   # 8 Nov 2026 (user: Peacock / Paramount+ rows "No information available"): was 4 h, so
                               # the rows went blank 4 h after PlaylistLabs' last fetch. Since 7-8 Nov a refresh REPLACES
                               # the blocks that are in the new file, so the old "stuck behind finished blocks" worry is
                               # gone. Set 4 to go back.
def ended_filler_hours(slot_id):
    return SHORT_ENDED_HOURS if slot_id.lower().startswith(SHORT_ENDED_GROUPS) else ENDED_FILLER_HOURS
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
# 7 Nov 2026: the provider also names NHL slots "NHL 01: 7pm Mammoth @ Canadiens" (colon, no dash, "@") - 10 of tonight's 12 slots had no channel
# ("EPG data not available" in PlaylistLabs); same ids (NHL1.uk ...). Same fields as NFL_SLOT.
NFL_SLOT_COLON = re.compile(r"^\s*(?P<label>NFL|NHL(?:\s*LIVE)?)\s*(?P<num>\d+)\s*:\s*(?P<rest>\S.*?)\s*$", re.I)
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
# Paramount+ streams in the provider's other layout (4 Nov 2026, user): "UEFA Champions League: Slavia Praha vs Arsenal
# @ Nov 4 2:00 PM :Paramount+  05" -> Paramount005.us (the same ids as "US (Paramount 005) | ... (date time)"). These names
# were ignored, so a row with that name had no listing of its own and was linked by hand to the other layout's id - whose
# name for slot 5 was a stale September 2025 match. The time in them is US Central (2:00 PM = 15:00 ET = 20:00 UK, one
# hour before the other layout's Eastern time); a match is moved to its real kick-off by real_start() as for the other
# layout. If both layouts name the same slot, the event still to be played wins over a finished one (build()).
PARAMOUNT_AT = re.compile(
    r"^\s*(?:(?P<comp>[^:@]+?)\s*:\s*)?(?P<title>[^@]+?)\s*@\s*(?P<mon>[A-Za-z]{3})[a-z]*\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+"
    r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\.?\s*:\s*Paramount\+?\s*(?P<num>\d+)\s*$", re.I)
PARAMOUNT_AT_TZ = "America/Chicago"
NBA_ESPN = "basketball/nba"
NBA_EVENT_HOURS = 3
# MLB streams, two styles:
#   "MLB 01 : Rays x Guardians start:2026-10-18 22:08:00 stop:2026-10-19 05:21:20"  (MLB_START_TZ; "|" instead of ":" also accepted, 8 Nov 2026)
#   "MLB 13 | Baltimore vs Tampa Bay @ Aug 14 7:00 PM"                              (US Eastern)
# Both give slot IDs MLB1.uk, MLB13.uk ... When ESPN's MLB schedule has the same two teams
# within MLB_MATCH_HOURS of the name's time, ESPN's first-pitch time is used instead (this also
# corrects the time if MLB_START_TZ is wrong - the log prints a check line for each).
MLB_START = re.compile(
    r"^\s*MLB\s*(?P<num>\d+)\s*[:|]\s*(?P<title>.+?)\s+start:\s*(?P<date>\d{4}-\d{2}-\d{2})[ T]"
    r"(?P<time>\d{1,2}:\d{2})(?::\d{2})?(?:\s+stop:\s*\S+(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)?\s*$", re.I)
MLB_AT = re.compile(
    r"^\s*MLB\s*(?P<num>\d+)\s*\|\s*(?P<title>.+?)\s*@\s*(?P<mon>[A-Za-z]{3})[a-z]*\.?\s+(?P<day>\d{1,2})"
    r"(?:st|nd|rd|th)?,?\s+(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\.?\s*$", re.I)
MLB_EMPTY = re.compile(r"^\s*MLB\s*(?P<num>\d+)\s*[:|\-]?\s*$", re.I)
MLB_START_TZ = "UTC"           # "start:" times look like UTC (01:00 = 9 pm ET); check the log
MLB_AT_TZ = "America/New_York"
MLB_ESPN = "baseball/mlb"
MLB_EVENT_HOURS = 3.5          # allows for extra innings
MLB_EARLY_MINUTES = 0          # LIVE this long before first pitch (10 until 6 Nov 2026)
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

# "PPV Events" group (30 Oct 2026): "PPV EVENT 01: Trophy Cup at Tulare Thunderbowl (10.30 8:30 PM ET)" - month.day and
# a US time with its zone -> PPVEVENT1.us (two rows with the same name share the id). An empty slot ("PPV EVENT 07",
# "PPV EVENT 07: No Event") keeps the same id and shows filler.
PPV_EVENT = re.compile(
    r"^\s*PPV\s*EVENT\s*(?P<num>\d+)\s*[:|\-]?\s*(?P<title>.+?)\s*\(\s*(?P<mo>\d{1,2})[./-](?P<d>\d{1,2})"
    r"(?:[./-]\d{2,4})?,?\s+(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\.?\s*(?P<tz>[A-Z]{2,3})?\s*\)\s*$", re.I)
PPV_EMPTY = re.compile(r"^\s*PPV\s*EVENT\s*(?P<num>\d+)\s*[:|\-]?\s*(?P<rest>.*?)\s*$", re.I)
PPV_TZ = {"ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York",
          "CT": "America/Chicago", "CST": "America/Chicago", "CDT": "America/Chicago",
          "MT": "America/Denver", "MST": "America/Denver", "MDT": "America/Denver",
          "PT": "America/Los_Angeles", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
          "GMT": "Europe/London", "BST": "Europe/London", "UK": "Europe/London"}
PPV_DEFAULT_TZ = "America/New_York"     # when the name gives no zone


# How long a PPV Event is listed as LIVE (31 Oct 2026). The name's time is when the broadcast STARTS, and a
# fight card runs far longer than the generic 3 h (Canelo v Mbilli: card from 17:00, still on the undercard at
# 20:52, yet the guide said "finished" at 20:00). First match wins; err on the long side - a LIVE block that
# runs on a little is better than "finished" while the stream is live.
PPV_HOURS = [
    (re.compile(r"(?i)press\s*conference|post[- ]?fight|weigh[- ]?in|face[- ]?off"), 2),
    (re.compile(r"(?i)\bprelims?\b|\bearly\b"), 4),
    (re.compile(r"(?i)\b(UFC|FN|MMA|PFL|Bellator|OKTAGON|Open\s*FC|KSW|ONE|Cage\s*Warriors|Fight\s*Night)\b"), 5),
    (re.compile(r"(?i)\bvs?\.?\s"), 10),         # a boxing card: undercard, then the main event (Canelo v Mbilli:
                                                  # broadcast from 17:00, main event expected ~01:00 UK)
]
PPV_DEFAULT_HOURS = 4                                # motorsport, anything else


def ppv_hours(title):
    for pattern, hours in PPV_HOURS:
        if pattern.search(title):
            return hours
    return PPV_DEFAULT_HOURS


def parse_ppv_event(name):
    """"PPV EVENT 01: Title (10.30 8:30 PM ET)" -> event, "PPV EVENT 07" -> empty slot, else None."""
    p = PPV_EVENT.match(name)
    if p:
        num = int(p["num"])
        tz = ZoneInfo(PPV_TZ.get((p["tz"] or "").upper(), PPV_DEFAULT_TZ))
        h = int(p["h"]) % 12 + (12 if p["ap"].lower() == "p" else 0)
        now_l = datetime.now(tz)
        local = None
        for year in (now_l.year, now_l.year - 1, now_l.year + 1):     # the year nearest today
            try:
                cand = datetime(year, int(p["mo"]), int(p["d"]), h, int(p["m"] or 0), tzinfo=tz)
            except ValueError:
                continue
            if local is None or abs(cand - now_l) < abs(local - now_l):
                local = cand
        if local is None:
            return None
        title = p["title"].strip(" -|:")
        uk_start = local.astimezone(LONDON)
        # 31 Oct 2026: finished blocks used the raw stream name, so they still showed the US time
        # ("10.31 5:00 PM ET"). The name shown in the guide now carries the London time instead.
        shown = f"PPV EVENT {num:02d}: {title} ({uk_start:%a} {uk_start.day} {uk_start:%b}, {uk_start:%H:%M})"
        return {"name": name, "offline_name": shown,
                "slot_id": f"PPVEVENT{num}.us", "slot_name": f"PPV EVENT {num:02d}",
                "title": title, "extra": "", "comp": competition(title) or "PPV Event",
                "hours": ppv_hours(title), "start": local.astimezone(timezone.utc)}
    e = PPV_EMPTY.match(name)
    if e and _placeholder(e["rest"]):
        num = int(e["num"])
        return _empty_slot(name, f"PPVEVENT{num}.us", f"PPV EVENT {num:02d}")
    return None


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "", text)


# Groups whose slot numbers repeat across regions ("CA: SOCCER PPV 198" and "US: SOCCER PPV 198"):
# their IDs also start with the region code, so the two can't be mixed up when linking
# (CASOCCERPPV198.ca, USSOCCERPPV198.us).
REGION_PREFIX_GROUPS = {"SOCCERPPV"}
def add_channel(tv, sid, ev):
    """<channel> with the full stream name first (so PlaylistLabs' automatic search can match
    an empty slot's name exactly) and the slot name second."""
    c = ET.SubElement(tv, "channel", {"id": sid})
    ET.SubElement(c, "display-name", {"lang": "en"}).text = ev["name"]
    ET.SubElement(c, "display-name", {"lang": "en"}).text = ev["slot_name"]
    return c


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
    words = re.sub(r"[^a-z0-9 ]+", " ", unicodedata.normalize("NFKD", (name or "").replace("ß", "ss"))
                   .encode("ascii", "ignore").decode().lower()).split()
    skip = {"fc", "afc", "cf", "sc", "ac", "as", "ss", "sk", "fk", "nk", "the", "real", "club",
            "sporting", "athletic", "atletico", "inter", "dynamo", "dinamo", "olympique", "rc"}
    for w in words:
        if w not in skip and len(w) > 2:
            return w
    return words[0] if words else ""


def parse_clock(text):
    """(hour, minute) from "15:00", "3:00 PM", "3pm" or "3:30pm" (6 Nov 2026: the guides changed to a 12-hour clock), else None"""
    t = (text or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", t)
    if m:
        return int(m[1]), int(m[2])
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s?([AaPp])[Mm]$", t)
    if m:
        return int(m[1]) % 12 + (12 if m[3].lower() == "p" else 0), int(m[2] or 0)
    return None


def load_fixtures():
    """[(home_key, away_key, home, away, kick-off datetime UK, competition)] from the
    football guide, or None."""
    global _FIXTURES
    if _FIXTURES is not None:
        return _FIXTURES or None
    roots = []
    for fname, url, label in ((FOOTBALL_GUIDE_FILE, FOOTBALL_GUIDE_URL, "football"),
                              (SCOTTISH_GUIDE_FILE, SCOTTISH_GUIDE_URL, "Scottish")):
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        try:
            if os.path.exists(local):
                with open(local, "rb") as f:
                    raw = f.read()
            else:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=60) as r:
                    raw = r.read()
            roots.append(ET.fromstring(raw))
        except Exception as e:
            print(f"  WARNING: {label} guide not available for dating fixtures ({e})")
    if not roots:
        _FIXTURES = []
        return None
    out = set()
    for p in (p for root in roots for p in root.iter("programme")):
        t = (p.findtext("title") or "")
        # the football / Scottish guides write the time as "15:00" (until 6 Nov 2026), "3:00 PM" (12-hour, 6 Nov) or "3pm" / "3:30pm" (the
        # current style: lower case, no space, minutes dropped on the hour): all three are read
        m = re.match(r"^(?:🔴 LIVE: )?(.+?) v (.+?) \((?:\w{3}) (\d{1,2}) (\w{3}), ([^()]+)\)$", t)
        if m:
            hm = parse_clock(m[5])
            if hm is None:
                continue
            year = int((p.get("start") or "2000")[:4])
            try:
                ko = datetime.strptime(f"{m[3]} {m[4]} {year} {hm[0]:02d}:{hm[1]:02d}", "%d %b %Y %H:%M") \
                    .replace(tzinfo=LONDON)
            except ValueError:
                continue
            home, away = m[1], m[2]
        else:
            # Once a match has kicked off its blocks are "🔴 LIVE: A v B" with no date and time in the title, so the fixture used to
            # vanish from this list and the events guide fell back to the stream-name time (Paramount+ Raith Rovers v Dunfermline,
            # 6 Nov 2026: real 19:30, name 20:25, and the LIVE start flipped from run to run). The LIVE block starts AT the kick-off
            # (football / Scottish MATCH_EARLY_MINUTES = 0), so its start is the kick-off.
            m = re.match(r"^🔴 LIVE: (.+?) v (.+)$", t)
            if not m or "(" in t:
                continue
            try:
                ko = datetime.strptime(p.get("start") or "", "%Y%m%d%H%M%S %z").astimezone(LONDON)
            except ValueError:
                continue
            home, away = m[1], m[2]
        cats = [c.text or "" for c in p.findall("category")]
        comp = cats[2] if len(cats) > 2 else ""          # Sports, Football, <competition>
        nxt = re.match(r"^(?:⏭\s*)?Next (?:Match|Up):\s*(.+)$", p.findtext("sub-title") or "")
        if nxt and nxt[1].lower().startswith(comp.lower()):
            comp = nxt[1].strip()                        # with the round: "Carabao Cup 4th Round"
        out.add((_team_key(home), _team_key(away), home.strip(), away.strip(), ko, comp))
    _FIXTURES = sorted(out, key=lambda r: r[4])
    return _FIXTURES or None


_ESPN_GAMES = {}         # sport path -> games, or "failed"


def load_espn_games(sport, label, quiet=False):
    """[(home names, away names, start UTC)] from ESPN's schedule for `sport` ("football/nfl",
    "baseball/mlb"), 4 days back to 10 days ahead, or None if it can't be read.
    quiet=True skips the per-day warnings (only the one "not available" line is printed)."""
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
        if not quiet:
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


# Local city names in stream names -> the English names ESPN uses ("Köln" = ESPN's "Cologne").
# Accents are already removed when this is applied. Add pairs here if a team doesn't match.
ENGLISH_NAMES = {"koln": "cologne", "munchen": "munich", "nurnberg": "nuremberg",
                 "monchengladbach": "gladbach"}


def _side_match(name, aliases):
    """_team_match, or the team's main word ("Walsall FC" -> "walsall") is a word of one of
    ESPN's names for it - for football, where stream names add "FC", "SC" etc. Also tries
    the English city name (ENGLISH_NAMES)."""
    english = " ".join(ENGLISH_NAMES.get(w, w) for w in _norm(name).split())
    for n in {name, english}:
        if _team_match(n, aliases):
            return True
        k = _team_key(n)
        if len(k) > 3 and any(k in a.split() for a in aliases):
            return True
    return False


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
    return re.sub(r"[^a-z0-9 ]+", " ", unicodedata.normalize("NFKD", (name or "").replace("ß", "ss"))
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


# Soccer PPV names ("Next | Walsall FC vs. Salford City FC | all | 26-10-2026 | 20:52 (GMT) |
# ... | CA: SOCCER PPV 11") give a time that isn't the kick-off (that match started 20:00).
# So for these, the real start is looked up: the football guide first, then ESPN's schedules for
# the football competitions in ESPN_FOOTBALL, then ESPN's NFL, NBA, NHL and MLB schedules -
# same two teams within REAL_START_HOURS of the name's time.
REAL_START_HOURS = 12
# Football competitions NOT in the football guide, looked up on ESPN for Soccer PPV slots
# (added 27 Oct 2026): ESPN league path -> name used as the secondary title. Matches go LIVE
# KICKOFF_EARLY_MINUTES early, like the football guide. Each league is read at most once a run
# (15 small requests) and only when a Soccer PPV name isn't in the football guide. To add a
# competition, add its ESPN path here (e.g. "soccer/esp.copa_del_rey": "Copa del Rey").
ESPN_FOOTBALL = {
    "soccer/ger.1": "Bundesliga",
    "soccer/ger.dfb_pokal": "DFB-Pokal",
    "soccer/ita.1": "Serie A",
    "soccer/fra.1": "Ligue 1",
    "soccer/ned.1": "Eredivisie",
    "soccer/ita.coppa_italia": "Coppa Italia",                 # (28 Oct 2026, for Paramount+)
    "soccer/uefa.wchampions": "UEFA Women's Champions League",
}


# LiveOnSat fixtures (6 Nov 2026): rugby union / league, Aussie rules, boxing and fighting - sports the football guide and ESPN don't give us.
# liveonsat_fixtures.py (own workflow, every 6 hours) writes liveonsat_fixtures.json with UTC start times; Stan's stream-name times were
# 10-55 minutes before the real start (Ireland v Argentina: name 20:00, kick-off 20:10; Scotland v New Zealand: 13:15 vs 14:10).
LIVEONSAT_FILE = "liveonsat_fixtures.json"
LIVEONSAT_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/liveonsat_fixtures.json"
_LOS = None


_LOS_STOP = {"the", "club", "and", "fc", "cf", "sc", "ac", "afc", "bsc", "fk", "sk", "bk", "if", "cd", "ca", "sd", "ud", "rc"}


def _words(text):
    """the meaningful words of a team name (lower case, no accents, no FC / CF ...), for matching the two sources"""
    return frozenset(w for w in _norm(text).split() if len(w) >= 3 and w not in _LOS_STOP)


def load_liveonsat():
    """[(home words, away words, start UTC, competition)] from liveonsat_fixtures.json - the rugby / fighting list AND the football list
    (7 Nov 2026) - or [] (never raises)."""
    global _LOS
    if _LOS is not None:
        return _LOS
    _LOS = []
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), LIVEONSAT_FILE)
    try:
        if os.path.exists(local):
            with open(local, "rb") as f:
                raw = f.read()
        else:
            with urllib.request.urlopen(urllib.request.Request(LIVEONSAT_URL, headers=HEADERS), timeout=30) as r:
                raw = r.read()
        data = json.loads(raw.decode("utf-8"))
        fetched = datetime.strptime(data.get("fetched", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched > timedelta(hours=48):
            print(f"  WARNING: LiveOnSat fixtures are {fetched:%d %b %H:%M} UTC - older than 48 h (its workflow may have stopped)")
        for f in list(data.get("fixtures", [])) + list((data.get("football") or {}).get("fixtures", [])):
            start = datetime.strptime(f["start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            comp = re.sub(r"\s+-\s+.*$", "", f.get("comp") or "").strip()
            a, b = _words(f["a"]), _words(f["b"])
            if a and b:
                _LOS.append((a, b, start, comp))
    except Exception as e:
        print(f"  LiveOnSat fixtures not available ({e}) - stream times are used as they are")
        _LOS = []
    return _LOS


def liveonsat_start(sides, approx):
    """(start UTC, competition) of the LiveOnSat fixture whose two teams are the two `sides` (the second side may carry trailing
    competition words) within REAL_START_HOURS of `approx`, else None. A side matches a team when its words are all in the team's name
    or the team's words are all in the side (\"Dallas\" = \"FC Dallas\", \"Minnesota\" = \"Minnesota United\")."""
    def match(side, team):
        w = _words(side)
        return bool(w) and (w <= team or team <= w)
    best = None
    for a, b, ko, comp in load_liveonsat():
        if abs(ko - approx) > timedelta(hours=REAL_START_HOURS):
            continue
        if (match(sides[0], a) and match(sides[1], b)) or (match(sides[0], b) and match(sides[1], a)):
            if best is None or abs(ko - approx) < abs(best[0] - approx):
                best = (ko, comp)
    return best


# Kick-off cross-check (7 Nov 2026, user: LiveOnSat was to be used for CHECKING kick-off times): when our own sources (football guide /
# ESPN) and LiveOnSat both know a match, differences of 5 min or more are logged and counted; summary in events_seen.json "_timing".check
_CHECK = {"compared": 0, "differ": {}}


def _note_check(title, ours, theirs, label):
    key = _norm(title)
    if key in _CHECK.get("seen", set()):
        return
    _CHECK.setdefault("seen", set()).add(key)
    _CHECK["compared"] += 1
    if abs(ours - theirs) >= timedelta(minutes=5):
        _CHECK["differ"][key] = {"match": title, "ours": ours.strftime("%Y-%m-%dT%H:%MZ"), "liveonsat": theirs.strftime("%Y-%m-%dT%H:%MZ"), "source": label}
        print(f"  Kick-off check: {title}: {label} {ours:%d %b %H:%M} UTC but LiveOnSat {theirs:%d %b %H:%M} UTC")


WOMENS_TITLE = re.compile(r"\b(WSL|NWSL|Women|Womens|Women's|Feminin\w*|Femenino|Frauen|Liga F|Damallsvenskan|Toppserien)\b|\(W\)", re.I)


def _title_sides(title):
    sides = re.split(r"\s+(?:vs?\.?|at|@|x|-)\s+", title, maxsplit=1, flags=re.I)
    if len(sides) != 2:
        return None
    # Short names used by Paramount+ / Peacock -> the football guide's names
    sides = [re.sub(r"(?i)\bman\.?\s+(?=(city|united|utd)\b)", "Manchester ", x) for x in sides]
    for pat, full in TEAM_SHORT_NAMES:
        sides = [re.sub(pat, full, x) for x in sides]
    return sides


def real_start(title, approx, quiet=False):
    """(start UTC, early minutes, competition) of the match in `title` near `approx`, else None: our football guide / ESPN first, then
    LiveOnSat (rugby, Aussie rules, boxing and - since 7 Nov - football from every country); LiveOnSat also cross-checks the first two."""
    sides = _title_sides(title)
    if sides is None:
        return None
    # A women's match (\"Aston Villa v Manchester United WSL 2026/27\") must not be matched to the same two clubs' MEN's fixture later that
    # day (7 Nov 2026: Stan 42 got the 16:30 Premier League kick-off instead of the 12:00 WSL one) - our guides and ESPN only hold the men's
    # games, so for these only LiveOnSat is asked.
    women = bool(WOMENS_TITLE.search(title))
    res = None if women else _real_start_ours(title, sides, approx, quiet)
    los = liveonsat_start(sides, res[0] if res else approx)
    if res:
        if los:
            _note_check(title, res[0], los[0], res[2] or "our guide")
        return res
    if los:
        if not quiet:
            print(f"  Start from LiveOnSat: {title}: name {approx:%d %b %H:%M} UTC, {los[1] or '?'} {los[0]:%d %b %H:%M} UTC")
        return los[0], PROVIDER_EARLY_MINUTES, los[1]
    return None


def _real_start_ours(title, sides, approx, quiet=False):
    """the football guide, ESPN football, then NFL / NBA / NHL / MLB (the part of real_start that needs no LiveOnSat)"""
    fx = load_fixtures() or []
    best = None
    for fh, fa, fhn, fan, ko, comp in fx:
        def same(side, key, nm):
            k = _team_key(side)
            return bool(k) and (k == key or SequenceMatcher(None, k, key).ratio() >= 0.85 or
                                SequenceMatcher(None, _norm(side), _norm(nm)).ratio() >= 0.8)
        if ((same(sides[0], fh, fhn) and same(sides[1], fa, fan)) or
                (same(sides[0], fa, fan) and same(sides[1], fh, fhn))):
            k = ko.astimezone(timezone.utc)
            if abs(k - approx) <= timedelta(hours=REAL_START_HOURS) and \
                    (best is None or abs(k - approx) < abs(best[0] - approx)):
                best = (k, comp)
    if best:
        return best[0], KICKOFF_EARLY_MINUTES, best[1]
    for sport, label in ESPN_FOOTBALL.items():      # other football competitions on ESPN
        games = load_espn_games(sport, label, quiet=True) or []
        for a, b, ko in games:
            if ((_side_match(sides[0], a) and _side_match(sides[1], b)) or
                    (_side_match(sides[0], b) and _side_match(sides[1], a))) and \
                    abs(ko - approx) <= timedelta(hours=REAL_START_HOURS) and \
                    (best is None or abs(ko - approx) < abs(best[0] - approx)):
                best = (ko, label)
    if best:
        print(f"  Kick-off from ESPN: {title}: name {approx:%d %b %H:%M} UTC, "
              f"{best[1]} {best[0]:%d %b %H:%M} UTC")
        return best[0], KICKOFF_EARLY_MINUTES, best[1]
    for sport, label in ((NFL_ESPN, "NFL"), (NBA_ESPN, "NBA"), (US_LEAGUES["NHL"][0], "NHL"),
                         (MLB_ESPN, "MLB")):
        games = load_espn_games(sport, label) or []
        hits = [ko for a, b, ko in games
                if ((_team_match(sides[0], a) and _team_match(sides[1], b)) or
                    (_team_match(sides[0], b) and _team_match(sides[1], a)))
                and abs(ko - approx) <= timedelta(hours=REAL_START_HOURS)]
        if hits:
            return min(hits, key=lambda k: abs(k - approx)), 0, label
    return None


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


# Timing statistics (7 Nov 2026): for every stream whose title is "A v B", how far the time in the stream NAME is from the real start
# (name time minus real start, minutes: negative = the stream opens EARLY, positive = late). Taken per provider group from the slot id
# (STAN, Peacock, Paramount, TSN, DAZNPPV ...). Groups in REAL_START_GROUPS / the Soccer PPV layouts have their start moved ("applied");
# the others are only MEASURED (real_start called quietly, nothing changed) - so guide_health can say which group is out and by how much.
# Saved under "_timing" in events_seen.json (this run's streams only: ~24 h ahead).
_TIMING = {}


def note_timing(slot_id, title, approx, real, applied):
    if not re.search(r"\s(?:vs?\.?|at|@)\s", title or "", flags=re.I):
        return                                        # not a two-sided match: nothing to compare
    m = re.match(r"[A-Za-z+]+", slot_id or "")
    g = _TIMING.setdefault(m.group(0) if m else "?", {"d": [], "missed": 0, "applied": False})
    g["applied"] = g["applied"] or applied
    if real is None:
        g["missed"] += 1
    else:
        g["d"].append(round((approx - real).total_seconds() / 60))


def measure_unapplied(events):
    """real_start() for every two-sided stream that was not looked up already - measured only, the event is not changed"""
    for ev in events:
        if ev.get("_timed"):
            continue
        rs = real_start(ev["title"], ev["start"], quiet=True)
        note_timing(ev["slot_id"], ev["title"], ev["start"], rs[0] if rs else None, False)


def timing_summary(now):
    import statistics
    out = {}
    for g, v in sorted(_TIMING.items()):
        d = v["d"]
        out[g] = {"n": len(d), "missed": v["missed"], "applied": v["applied"]}
        if d:
            out[g].update({"median": round(statistics.median(d)), "min": min(d), "max": max(d)})
    chk = {"compared": _CHECK["compared"], "differ": len(_CHECK["differ"]), "examples": list(_CHECK["differ"].values())[:8]}
    return {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "groups": out, "check": chk}


def save_seen(now=None):
    data = dict(sorted(_SEEN_USED.items()))
    data["_timing"] = timing_summary(now or datetime.now(timezone.utc))
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def _nice_title(t):
    t = re.sub(r"\s+", " ", t).strip(" -|:@")
    if re.sub(r"\b(?:vs?|v)\b\.?", "", t).isupper():
        t = t.title()
    return re.sub(r"\b(V|Vs|VS)\b\.?", lambda m: m.group(1).lower(), t)


def parse_tod(name, any_region=False):
    """any_region=True also takes 2-letter regions ("CA: SOCCER PPV 1") - used only as a last
    resort, after the DAZN-style parser, so "GB: DAZN PPV 5" names are read as before."""
    parts = [p.strip() for p in name.split("|")]
    if len(parts) < 3:
        return None
    sm = (PIPE_SLOT if any_region else TOD_SLOT).match(parts[-1])
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
        elif p.lower() == "all":                     # "all" (all languages/regions) - nothing to show
            continue
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
    named = None
    if date and time_:
        h, mi = map(int, time_.split(":"))
        named = datetime(*date, h, mi, tzinfo=ZoneInfo(zone or COUNTRY_TZ.get(cc, TOD_TZ))) \
            .astimezone(timezone.utc)
    if status in ("end", "ended", "finished", "off") and (named is None or named <= now):
        ev["start"] = now - timedelta(days=2)            # the name says it's over
    elif named:
        # "End" on a name whose time is still ahead is ignored (27 Oct 2026: the provider put
        # "End" on that evening's DFB-Pokal ties hours before kick-off) - listed as upcoming.
        if status in ("end", "ended", "finished", "off"):
            print(f"  Early \"End\" ignored (time still ahead): {name}")
        ev["start"] = named
        if any_region:                               # Soccer PPV: the name's time isn't the kick-off
            rs = real_start(title, ev["start"])
            note_timing(ev["slot_id"], title, ev["start"], rs[0] if rs else None, True)
            ev["_timed"] = True
            if rs:
                ev["start"], ev["early"] = rs[0], rs[1]
                if not ev["comp"] and rs[2]:
                    ev["comp"] = rs[2]
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


# ALL CAPS event names -> normal case (4 Nov 2026, user). ESPN+ and MAX write most titles in capitals ("KENT STATE VS.
# APP STATE (QUARTERFINALS)", "AARON HILL - ZHAO XINTONG"). Only a title that is (almost) all capitals is touched;
# acronyms (KEEP_CAPS), roman numerals, single letters, words touching digits (F1, U19) and 1-3 letter state codes
# in brackets ("XAVIER (LA)") stay as they are. Add a word to KEEP_CAPS if a name comes out as "Ucf" / "Xyz";
# CAPS_SPECIAL gives a word its own spelling.
KEEP_CAPS = set("""
UFC NBA NFL NHL MLB MLS WNBA NCAA UEFA FIFA FA EFL EPL WWE AEW ATP WTA PGA LPGA LIV DP IPL ICC ODI GP MMA PFL BKFC
DAZN ESPN BBC CNN BT TNT TV HD UHD PPV VAR USA UK UAE EU UCL XTRA RB PSV LASK SSC RCD SL KAA KV FK SK BK FC SC AC AS CF
CD AEK AEL APOEL PAOK OFI ENP AEP PAEEK GR II III IV VI VII VIII IX XI XII
UCF UNC LSU BYU TCU UAB VCU RPI IU UMBC NJIT UTSA UMASS SIU UC UT UL USC UCLA SMU UNLV UTEP UIC FIU FAU LIU CSU CCSU
UTRGV UTSA SUNY MIT NYU LMU UMES MTSU ETSU WKU UNCW SFA SEMO UNI USF UMKC SDSU TCNJ RIT NIU
SE VMI FDU NCCU ECU FGCU UNCG UCSB CSUN CSUB UNF UTM CP US NZ AUS RSA USMNT USWNT NASCAR IMSA
WBC WBA IBF WBO NRL AFL NRLW AFLW BBL WBBL BWF UCI FIM FIA WRC WEC PBR PLL NLL AHL ECHL OHL WHL QMJHL CFL XFL UFL USFL
NWSL USL CPL AFC CAF CONCACAF CONMEBOL OFC AFCON ACC SEC NCAAB NCAAF NIT HBCU
""".split())
CAPS_SPECIAL = {"VFB": "VfB", "UALBANY": "UAlbany", "LALIGA": "LaLiga", "UMASS": "UMass", "DEPAUL": "DePaul"}
CAPS_SMALL = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with", "v", "vs", "del", "de"}
CAPS_WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*")
CAPS_ROMAN = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")


def mostly_caps(text):
    letters = [c for c in (text or "") if c.isalpha()]
    return len(letters) >= 5 and sum(c.isupper() for c in letters) / len(letters) >= 0.85


def tidy_caps(text):
    """ALL CAPS title -> normal case (see above); other titles are returned unchanged."""
    if not mostly_caps(text):
        return text

    def repl(m):
        w = m.group(0)
        if not w.isupper():
            return w
        if w in CAPS_SPECIAL:
            return CAPS_SPECIAL[w]
        if w == "V" and m.start() > 0 and text[m.start() - 1] == " ":
            return "v"
        if len(w) < 2 or w in KEEP_CAPS or (len(w) <= 4 and CAPS_ROMAN.match(w)):
            return w
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if before.isdigit() or after.isdigit():
            return w
        if len(w) <= 3 and before == "(" and after == ")":          # "XAVIER (LA)", "WESTMINSTER (UT)"
            return w
        low = w.lower()
        lead = text[:m.start()].rstrip()
        if low in CAPS_SMALL and lead and lead[-1] not in "-\u2013\u2014:|/(\"'.!?,":
            return low
        out = low.capitalize()
        if low.startswith("mc") and len(w) > 3:                      # McAfee, McNeese
            out = "Mc" + low[2:].capitalize()
        if len(w) > 2 and w[1] in "'\u2019" and w[0] in "DLO":      # D'Italia, O'Brien
            out = w[0] + w[1] + w[2:].lower().capitalize()
        return out
    return CAPS_WORD.sub(repl, text)



# "A - B" fixtures -> "A vs B" (4 Nov 2026, user). MAX UK writes every match as "RB LEIPZIG - MANCHESTER CITY (19:00)".
# Only a title with exactly ONE spaced hyphen and no "vs"/"v" already, whose two sides look like names, is changed;
# dates ("TUE, 11/3 - ESPN FC"), places ("Medicine Hat, AB - Day 2, Draw 6"), suffixes ("Brazil vs Germany - Women's M1")
# and round/day/episode labels stay as they are.
VS_SIDE_SKIP = re.compile(r"(?i)^(?:day|round|rd|week|wk|episode|ep\.?|match|game|session|part|heat|draw|race|stage|"
                          r"leg|lap|women'?s|men'?s|highlights?|preview|review)\b")
VS_DATE_SIDE = re.compile(r"(?i)^(?:mon|tue|wed|thu|fri|sat|sun)\w*,?\s*\d{1,2}[/.]\d{1,2}$")


def fixture_vs(title):
    t = title or ""
    if t.count(" - ") != 1 or re.search(r"(?i)\s(?:vs?\.?|@|at)\s", t):
        return t
    left, right = t.split(" - ", 1)
    core = re.sub(r"\s*\([^)]*\)\s*$", "", right).strip()
    left = left.strip()
    for side in (left, core):
        if not side or re.search(r"[:,]", side) or VS_SIDE_SKIP.match(side) or VS_DATE_SIDE.match(side) \
                or len(side.split()) > 6 or not side[0].isalpha():
            return t
    return f"{left} vs {right.strip()}"



# One style for fixtures: "v", "v.", "vs", "vs." between two names -> "vs" (4 Nov 2026, user: "make them all vs").
# Only the events guide; the football / Scottish guides keep their "A v B" on purpose.
VS_WORD = re.compile(r"(?<=\S)\s+(?:v|vs|Vs|VS)\.?\s+(?=\S)")      # a lone capital "V" (Super Bowl V, Henry V) stays


def normalise_vs(title):
    return VS_WORD.sub(" vs ", title or "")



def parse_name(name):
    """{slot_id, slot_name, title, extra, start (UTC)} for an event name, else None."""
    name = re.sub(r"\s+", " ", name or "").strip()
    ev = _parse_name(name)
    if ev is None:
        return empty_slot(name)
    if ev.get("title") and NO_EVENT.match(ev["title"]):    # "No Event (2026-10-24 20:00)" etc.
        return _empty_slot(name, ev["slot_id"], ev["slot_name"])
    if ev and not ev.get("untimed") and not (ev.get("title") or "").strip() \
            and ev.get("start") and ev["start"].year > 2090:   # "CA (SN+ 026) | (2098-12-31 08:00:01)": the provider's
        return _empty_slot(name, ev["slot_id"], ev["slot_name"])   # placeholder date = an EMPTY slot, not an event
    if ev and ev.get("title"):       # "• Chelsea v Tottenham" (Stan's second feed) -> no bullet
        ev["title"] = normalise_vs(fixture_vs(tidy_caps(re.sub(r"^[\s•·*\-–]+", "", ev["title"]).strip())))
        if ev.get("comp"):
            ev["comp"] = tidy_caps(ev["comp"])
    return ev


def _parse_name(name):
    name = re.sub(r"\s+", " ", name or "").strip()

    ppv = parse_ppv_event(name)                      # PPV EVENT 01: Title (10.30 8:30 PM ET)
    if ppv:
        return ppv

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
    pm = PARAMOUNT_AT.match(name)                    # Comp: A vs B @ Nov 4 2:00 PM :Paramount+  05 (US Central)
    if pm:
        title = re.sub(r"\s+", " ", pm["title"]).strip()
        approx = month_day_time(pm["mon"], pm["day"], pm["h"], pm["m"], pm["ap"], ZoneInfo(PARAMOUNT_AT_TZ))
        if approx is None or not title:
            return None
        num = int(pm["num"])
        is_match = bool(re.search(r"(?i)\s(?:vs?\.?|at|@)\s", title))
        ev = {"name": name, "slot_id": f"Paramount{num:03d}.us", "slot_name": f"US (Paramount {num:03d})",   # 3 digits, like the playlists
              "title": title, "extra": "", "comp": (pm["comp"] or "").strip() if is_match else "",
              "start": approx.astimezone(timezone.utc)}
        rs = real_start(ev["title"], ev["start"])          # stream time -> real kick-off (as for the other layout)
        note_timing(ev["slot_id"], ev["title"], ev["start"], rs[0] if rs else None, True)
        ev["_timed"] = True
        if rs:
            if abs(rs[0] - ev["start"]) >= timedelta(minutes=1):
                print(f"  US (Paramount {num:03d}) kick-off: {ev['title']}: stream {ev['start']:%d %b %H:%M} UTC, "
                      f"{rs[2] or '?'} {rs[0]:%d %b %H:%M} UTC")
            ev["start"], ev["early"] = rs[0], PROVIDER_EARLY_MINUTES      # Paramount+: LIVE at the kick-off (6 Nov 2026)
            ev["comp"] = rs[2] or ev["comp"]
        return ev
    b = NBA_AT.match(name)                           # A vs B @ Oct 24 6:00 PM :NBA 01 (US Eastern)
    if b:
        title = re.sub(r"\s+", " ", b["title"]).strip()
        approx = month_day_time(b["mon"], b["day"], b["h"], b["m"], b["ap"], ZoneInfo(NBA_TZ))
        if approx is None:
            return None
        start = espn_start(NBA_ESPN, "NBA", title, approx.astimezone(timezone.utc))
        num = int(b["num"])
        return {"name": name, "slot_id": f"NBA{num}.uk", "slot_name": f"NBA {num}",
                "title": nba_away_at_home(title), "extra": "", "comp": "NBA", "hours": NBA_EVENT_HOURS,
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

    n = NFL_SLOT.match(name) or NFL_SLOT_COLON.match(name)   # NFL | 02 - 9:30am Steelers at Saints (ET)  /  NHL 01: 7pm Mammoth @ Canadiens
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
        ev = {"name": name, "slot_id": f"{slug(a['prov'] + label)}{a['num']}.us",
              "slot_name": f"({a['prov'].strip()}) ({label}) {a['num']}",
              "title": a["title"].strip(), "extra": "",
              "comp": competition(a["title"], label) or label,
              "start": local.astimezone(timezone.utc)}
        # Apple MLS stream times are 5 min (up to ~95 min on some days) before the kick-off (7 Nov 2026, user: Dallas vs Colorado name
        # 18:55 Eastern, kick-off 00:00 UTC) - moved to the real kick-off like Peacock / Paramount+ / Stan (MLS is in the football guide / ESPN)
        rs = real_start(ev["title"], ev["start"])
        note_timing(ev["slot_id"], ev["title"], ev["start"], rs[0] if rs else None, True)
        ev["_timed"] = True
        if rs:
            if abs(rs[0] - ev["start"]) >= timedelta(minutes=1):
                print(f"  ({a['prov'].strip()}) ({label}) {a['num']} kick-off: {ev['title']}: stream {ev['start']:%d %b %H:%M} UTC, "
                      f"{rs[2] or '?'} {rs[0]:%d %b %H:%M} UTC")
            ev["start"], ev["early"] = rs[0], PROVIDER_EARLY_MINUTES
            ev["comp"] = rs[2] or ev["comp"]
        return ev

    m = SLOT_FIRST.match(name)                       # US (Peacock 003) | ... (date time)
    if m:
        tz = ZoneInfo(COUNTRY_TZ.get(m["cc"], "Europe/London"))
        local = datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        ev = {"name": name, "slot_id": f"{slug(m['slot'])}.{m['cc'].lower()}",
              "slot_name": f"{m['cc']} ({m['slot']})",
              "title": m["title"].strip(), "extra": "", "comp": competition(m["title"]),
              "start": local.astimezone(timezone.utc)}
        if m["slot"].lower().startswith(REAL_START_GROUPS):   # stream time -> real kick-off
            rs = real_start(ev["title"], ev["start"])
            note_timing(ev["slot_id"], ev["title"], ev["start"], rs[0] if rs else None, True)
            ev["_timed"] = True
            if rs:
                if abs(rs[0] - ev["start"]) >= timedelta(minutes=1):
                    print(f"  {m['cc']} ({m['slot']}) kick-off: {ev['title']}: stream "
                          f"{ev['start']:%d %b %H:%M} UTC, {rs[2] or '?'} {rs[0]:%d %b %H:%M} UTC")
                ev["start"], ev["early"] = rs[0], PROVIDER_EARLY_MINUTES      # Peacock / Paramount+: LIVE at the kick-off (6 Nov 2026)
                ev["comp"] = rs[2] or ev["comp"]
        return ev

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
    # Last resort: TOD-style names with a 2-letter region, e.g. Soccer PPV
    # "End | 2026 NFL Draft | all | 26-10-2026 | 00:30 (GMT) | 8K EXCLUSIVE | CA: SOCCER PPV 1"
    return parse_tod(name, any_region=True)


# Playlists to read (30 Oct 2026): the user has TWO PlaylistLabs playlists sharing this guide, mostly the same
# streams but each with a few the other lacks. Both are read and their stream names merged (a name in both counts
# once), so every slot from either playlist is in the guide. PLAYLIST_URL_2 is optional.
PLAYLIST_SECRETS = ["PLAYLIST_URL", "PLAYLIST_URL_2"]


# ---------------------------------------------------------------------------
# Overrides file (31 Oct 2026): events_overrides.json, edited by hand in the repo, for the big events where the
# stream name's time or the generic length is wrong (e.g. DAZN-only boxing cards that no other guide lists).
#   [{"match": ["canelo", "mbilli"], "exclude": ["prelims"],
#     "start": "2026-10-31 17:00", "end": "2026-11-01 03:00", "note": "Main event about 01:00"}]
# All times are UK time. Every word in "match" must be in the stream name (capitals/accents ignored), none of
# "exclude". "start" replaces the time from the name, "end" sets how long the LIVE block runs; give either or both.
# An entry stops applying OVERRIDE_KEEP_HOURS after its end. A broken file or entry is reported and skipped -
# the guide is then built from the stream names as usual.
# ---------------------------------------------------------------------------
OVERRIDES_FILE = "events_overrides.json"
OVERRIDE_KEEP_HOURS = 24


def _override_time(value):
    text = str(value).strip().replace("T", " ")
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=LONDON).astimezone(timezone.utc)


def load_overrides():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OVERRIDES_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"WARNING: {OVERRIDES_FILE} could not be read ({e}) - ignored")
        return []
    if not isinstance(data, list):
        print(f"WARNING: {OVERRIDES_FILE} must be a list of entries [ {{...}}, {{...}} ] - ignored")
        return []
    out = []
    for i, e in enumerate(data, 1):
        if not isinstance(e, dict):
            continue
        words = e.get("match")
        words = [words] if isinstance(words, str) else words
        if not isinstance(words, list) or not words or not all(isinstance(w, str) and _norm(w) for w in words):
            print(f"WARNING: override #{i}: \"match\" must be a word or a list of words - skipped")
            continue
        excl = e.get("exclude") or []
        excl = [excl] if isinstance(excl, str) else excl
        try:
            start = _override_time(e["start"]) if e.get("start") else None
            end = _override_time(e["end"]) if e.get("end") else None
        except (ValueError, TypeError):
            print(f"WARNING: override #{i} ({' + '.join(words)}): times must look like \"2026-10-31 17:00\" - skipped")
            continue
        if start is None and end is None:
            print(f"WARNING: override #{i} ({' + '.join(words)}): needs a \"start\" or an \"end\" - skipped")
            continue
        if start and end and end <= start:
            print(f"WARNING: override #{i} ({' + '.join(words)}): \"end\" is not after \"start\" - skipped")
            continue
        out.append({"i": i, "label": " + ".join(words), "match": [_norm(w) for w in words],
                    "exclude": [_norm(x) for x in excl if isinstance(x, str) and _norm(x)],
                    "start": start, "end": end, "note": str(e.get("note") or "").strip()})
    return out


def apply_overrides(events, now):
    """Changes the start / length of the parsed events that an override entry matches (first matching entry wins)."""
    overrides = load_overrides()
    if not overrides:
        return
    active = []
    for o in overrides:
        last = o["end"] or (o["start"] + timedelta(hours=12))
        if now <= last + timedelta(hours=OVERRIDE_KEEP_HOURS):
            active.append(o)
    hits = {o["i"]: 0 for o in active}
    for ev in events:
        if not ev.get("title"):                              # empty slots stay empty
            continue
        text = _norm(ev.get("name"))
        for o in active:
            if all(w in text for w in o["match"]) and not any(x in text for x in o["exclude"]):
                if ev.get("untimed") and not o["start"]:
                    print(f"WARNING: override #{o['i']} ({o['label']}) matches a stream with no time in its name "
                          f"but has no \"start\" - skipped")
                    break
                if o["start"]:
                    ev["start"] = o["start"]
                    ev.pop("untimed", None)
                if o["end"]:
                    ev["hours"] = max((o["end"] - ev["start"]).total_seconds() / 3600, 0.5)
                if o["note"]:
                    ev["info"] = (ev.get("info", "") + " " + o["note"]).strip()
                hits[o["i"]] += 1
                break
    print(f"Overrides: {len(active)} active of {len(overrides)} entries, {sum(hits.values())} streams changed")
    for o in active:
        if not hits[o["i"]]:
            print(f"WARNING: override #{o['i']} ({o['label']}) matched no stream - check the words against the stream name")


def read_playlist(args):
    """[(label, text)] for each playlist read."""
    if args.m3u:
        out = []
        for path in args.m3u:
            with open(path, encoding="utf-8", errors="replace") as f:
                out.append((path, f.read()))
        return out
    out = []
    for key in PLAYLIST_SECRETS:
        url = os.environ.get(key, "").strip()
        if not url:
            if key != PLAYLIST_SECRETS[0]:
                print(f"{key} not set - skipped")
            continue
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                out.append((key, r.read().decode("utf-8", errors="replace")))
        except Exception as e:              # one playlist down: carry on with the other
            print(f"WARNING: could not download {key} ({type(e).__name__}) - skipped")
    if not out:
        sys.exit("No playlist: set the PLAYLIST_URL secret (and optionally PLAYLIST_URL_2), or use --m3u FILE.")
    return out


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


def add_programme(tv, cid, start, stop, title, sub, desc, live=False):
    """Writes the programme in pieces of at most PIECE_HOURS, and only the pieces that start
    before the horizon (now + HORIZON_HOURS). PlaylistLabs never replaces a programme it has
    loaded, so when the provider moves a slot to a new event, the old listing can only linger
    until the end of what it already holds - at most HORIZON_HOURS."""
    title, sub, desc = clock12(title), clock12(sub), clock12(desc)   # 12-hour clock (6 Nov 2026)
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


def normalise_slot_ids(tv):
    """Slot ids with a stray two-digit number in a three-digit group (3 Nov 2026). Slot ids come from the provider's stream names
    ("US (Paramount 006)"), and the provider sometimes writes one with fewer digits ("US (Paramount 05)", "CA (TSN+ 04)"), which
    gives Paramount05.us / TSN04.ca while the playlists use Paramount005.us / TSN004.ca - so that slot never got a listing.
    When at least 90% of a group's ids (same name and country) have three digits, the outliers are padded to three digits.
    Groups that are naturally mixed (DAZN PPV 1-99, Stan 1-100 ...) are left alone."""
    groups = {}
    for ch in tv.findall("channel"):
        m = re.fullmatch(r"([A-Za-z+]+)(\d+)\.([A-Za-z0-9]+)", ch.get("id", ""))
        if m:
            groups.setdefault((m.group(1), m.group(3)), []).append((ch, m.group(2)))
    taken = {ch.get("id") for ch in tv.findall("channel")}
    renames, strays = {}, set()
    for (stem, cc), members in groups.items():
        three = sum(len(num) == 3 for _, num in members)
        if len(members) < 10 or three < 0.9 * len(members):
            continue
        for ch, num in members:
            if len(num) < 3:
                new = f"{stem}{int(num):03d}.{cc}"
                if new not in taken:
                    renames[ch.get("id")] = new
                    taken.add(new)
                else:                                  # the three-digit id exists already (4 Nov 2026: Paramount05 next to
                    strays.add(ch.get("id"))           # Paramount005 from the other layout's name) - the stray one goes
    for ch in list(tv.findall("channel")):
        if ch.get("id") in strays:
            tv.remove(ch)
    for pr in list(tv.findall("programme")):
        if pr.get("channel") in strays:
            tv.remove(pr)
    if strays:
        print("  Stray slot ids dropped (the three-digit id exists): " + ", ".join(sorted(strays)))
    if not renames:
        return
    for ch in tv.findall("channel"):
        if ch.get("id") in renames:
            ch.set("id", renames[ch.get("id")])
    for p in tv.findall("programme"):
        if p.get("channel") in renames:
            p.set("channel", renames[p.get("channel")])
    print("  Slot ids padded to three digits: " + ", ".join(f"{o} -> {n}" for o, n in sorted(renames.items())))


US_GAME_COMPS = {"NFL", "NBA", "NHL", "MLB", "WNBA", "NCAAF", "NCAAB", "NCAAM", "NCAAW", "CFB"}


def nba_away_at_home(title):
    """The NBA streams are named "HOME vs AWAY" (8 Nov 2026, checked against ESPN's schedule for all 7 games: "Chicago Bulls vs Philadelphia
    76ers" is Philadelphia AT Chicago). The user wants the US style - "AWAY @ HOME", as the NFL / NHL slots and the Teams guide - so the sides
    are swapped: "Philadelphia 76ers @ Chicago Bulls"."""
    m = re.match(r"^(.+?)\s+vs?\.?\s+(.+)$", title, re.I)
    return f"{m.group(2).strip()} @ {m.group(1).strip()}" if m else title


def next_label(title, comp="", sid=""):
    """"Next Game" for a US-style "A @ B" / "A at B" and for the NFL / NBA / NHL / MLB (like the Teams guide), "Next Match" for "A vs B",
    "Next Event" for anything else (a race, a card, a tournament day)."""
    if re.search(r"\s(?:@|at)\s", title) or re.match(r"(?:NFL|NBA|NHL|MLB)\d", sid or "") or (comp or "").upper() in US_GAME_COMPS:
        return "Next Game"
    if re.search(r"\s(?:vs?\.?|x)\s", title, re.I):
        return "Next Match"
    return "Next Event"


def build(events, now):
    global _HORIZON
    _HORIZON = now + timedelta(hours=HORIZON_HOURS)
    tv = ET.Element("tv", {"generator-info-name": "event_epg.py"})
    by_slot, ended = {}, {}
    untimed = {}
    cands = {}
    for ev in events:                       # one event per slot: the next one still to finish
        if ev.get("untimed"):
            untimed.setdefault(ev["slot_id"], ev)
            continue
        end = ev["start"] + timedelta(hours=event_hours(ev))
        if end + timedelta(hours=PAST_EVENT_HOURS) < now:
            ended.setdefault(ev["slot_id"], ev)
            continue
        cands.setdefault(ev["slot_id"], []).append(ev)
    for sid, evs in cands.items():
        # The next event still to finish - but when several names for ONE slot name different matches in the same window (6 Nov 2026:
        # Main IPTV's "US (Paramount 003)" said Venezia v Udinese while both naming patterns of the other playlist said Raith Rovers v
        # Dunfermline, and the earlier start won), the title most names agree on wins; a tie goes to the earlier start.
        first = min(evs, key=lambda e: e["start"])
        window = [e for e in evs if e["start"] < first["start"] + timedelta(hours=event_hours(first))]
        lo = min(e.get("pl", 0) for e in window)              # the FIRST playlist (PLAYLIST_URL = Continuum) wins a disagreement:
        window = [e for e in window if e.get("pl", 0) == lo]   # 7 Nov 2026 - the two playlists number some Stan / Paramount slots differently
        votes = {}
        for e in window:
            votes[_norm(e["title"])] = votes.get(_norm(e["title"]), 0) + 1
        best = max(window, key=lambda e: (votes[_norm(e["title"])], -e["start"].timestamp()))
        if len(set(_norm(e["title"]) for e in evs if e["start"] < first["start"] + timedelta(hours=event_hours(first)))) > 1:
            print(f"  Slot {sid}: names disagree ({len(evs)} streams, playlist {lo + 1} used) - using \"{best['title']}\"")
        by_slot[sid] = best
    untimed = {sid: ev for sid, ev in untimed.items() if sid not in by_slot}
    ended = {sid: ev for sid, ev in ended.items() if sid not in by_slot and sid not in untimed}
    for sid in sorted(untimed):
        add_channel(tv, sid, untimed[sid])
    for sid in sorted(set(by_slot) | set(ended)):
        add_channel(tv, sid, ended[sid] if sid in ended else by_slot[sid])
    count = 0
    for sid in sorted(by_slot):
        ev = by_slot[sid]
        kickoff = ev["start"]
        start = kickoff - timedelta(minutes=ev.get("early", 0))   # LIVE a little early where set
        end = kickoff + timedelta(hours=event_hours(ev))
        when = f"{uk(kickoff):%a} {uk(kickoff).day} {uk(kickoff):%b}, {uk(kickoff):%H:%M}"
        comp = ev.get("comp") or ""
        if comp and (comp.lower() in ev["title"].lower() or comp.lower() in (ev["extra"] or "").lower()):
            comp = ""                                      # already in the title / extra text
        desc = f"{ev['title']}." + (f" {comp}." if comp else "") + \
               (f" {ev['extra']}." if ev["extra"] else "") + \
               f" Starts {when} UK time." + (f" {ev['info']}" if ev.get("info") else "")
        in_range = start <= now + timedelta(days=MAX_DAYS_AHEAD)
        # Out of range: "Coming up" blocks only up to the range limit (the guide stops at
        # HORIZON_HOURS anyway); the LIVE block is added once the event comes into range.
        stop_at = start if in_range else now + timedelta(days=MAX_DAYS_AHEAD)
        t = now.replace(minute=0, second=0, microsecond=0)
        t -= timedelta(hours=uk(t).hour % BLOCK_HOURS)
        while t < stop_at:
            b = min(t + timedelta(hours=BLOCK_HOURS), stop_at)
            # "Coming up" blocks naming the event - also for events more than MAX_DAYS_AHEAD away
            # (changed 28 Oct 2026: those used to get the generic FILLER_TITLE, so e.g. 97 of the
            # 100 Peacock slots showed "Stream is live at event time only." with no event name).
            if in_range and b >= stop_at:
                # The last block before the LIVE one (3 Nov 2026): "Next up: LIVE" with the event and its start time -
                # the time alone when it starts within 24 h, with the day when later. No ⏭ here.
                soon = kickoff - now <= timedelta(hours=24)
                stamp = f"{uk(kickoff):%H:%M}" if soon else when
                add_programme(tv, sid, t, b, f"Next up: LIVE \u2013 {ev['title']} ({stamp})",
                              "Next up: LIVE",
                              f"Next up: LIVE. {ev['title']} starts " + (f"at {stamp}" if soon else stamp) + " UK time.")
            else:
                # 8 Nov 2026 (user): the same wording as the club guides - "Next Match" (US games "Next Game", other events "Next Event")
                # on every block before the event; only the LAST block before LIVE says "Next up: LIVE" (above). No ⏭.
                lab = next_label(ev["title"], ev.get("comp"), sid)
                add_programme(tv, sid, t, b, f"{ev['title']} ({when})",       # competition (and round)
                              f"{lab}: {ev['comp']}" if ev.get("comp") else   # when known (28 Oct)
                              f"{lab}: {uk(kickoff):%a} {uk(kickoff).day} {uk(kickoff):%b}",
                              f"{lab}: {desc}")
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
            fill = timedelta(hours=ended_filler_hours(sid))
            while t < end + fill:
                b = min(t + timedelta(hours=BLOCK_HOURS), end + fill)
                add_programme(tv, sid, t, b, FINISHED_TITLE, None, finished_desc(ev))
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
        finished = bool(ended[sid]["title"])
        desc = finished_desc(ended[sid]) if finished else OFFLINE_DESC
        t = t0
        while t < now + timedelta(hours=ended_filler_hours(sid)):
            b = t + timedelta(hours=BLOCK_HOURS)
            add_programme(tv, sid, t, b, FINISHED_TITLE if finished else offline_title(ended[sid]), None, desc)
            count += 1
            t = b
    normalise_slot_ids(tv)
    count = len(tv.findall("programme"))
    return tv, len(by_slot) + len(ended) + len(untimed), count


SEPARATE_IDS = re.compile(r"^(?P<g>Peacock|STAN|Paramount)(?P<num>\d+)\.(?P<cc>[a-z]+)$")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--m3u", nargs="+", help="read these playlist files instead of PLAYLIST_URL / PLAYLIST_URL_2")
    ap.add_argument("--out", default=OUTPUT_NAME)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    names, seen, name_pl, later = [], set(), {}, []
    for idx, (label, text) in enumerate(read_playlist(args)):
        mine = list(stream_names(text))
        if idx > 0:
            later.append((idx, list(dict.fromkeys(mine))))      # ALL of this playlist's names (for its own ids, see SEPARATE_IDS)
        new = [n for n in dict.fromkeys(mine) if n not in seen]
        seen.update(new)
        names.extend(new)
        name_pl.update({n: idx for n in new})
        print(f"{label}: {len(mine)} streams, {len(new)} names not already read")
    events, parsed = [], {}

    def parse_once(n):                                # every name is parsed (and counted in the statistics) once
        if n not in parsed:
            parsed[n] = parse_name(n)
        return parsed[n]
    for n in names:
        e = parse_once(n)
        if not e:
            continue
        if name_pl.get(n, 0) > 0 and SEPARATE_IDS.match(e["slot_id"]):
            continue                                  # a Main IPTV-only name in a separate-id group: only its own M id (below)
        e["pl"] = name_pl.get(n, 0)                   # which playlist this name came from (0 = the first)
        events.append(e)
    # Stan, Paramount+ and Peacock: the second playlist (Main IPTV) numbers its slots differently from the first (Continuum) and not always
    # the same ones (user, 7 Nov 2026), so ALL of its names in those groups get their own ids - STAN42.au (Continuum) / MSTAN42.au (Main IPTV, the same id with an M in FRONT)
    # - and each source always shows its own events. Every other group is Continuum only; a clash there is won by the first playlist.
    separate = 0
    for idx, mine in later:
        for n in mine:
            e = parse_once(n)
            m = SEPARATE_IDS.match(e["slot_id"]) if e else None
            if m:
                e2 = dict(e)
                e2["slot_id"] = f"M{m['g']}{m['num']}.{m['cc']}"
                e2["slot_name"] = f"{e['slot_name']} [Main IPTV]"
                e2["pl"] = idx
                events.append(e2)
                separate += 1
    if separate:
        print(f"  Main IPTV: {separate} Stan / Paramount+ / Peacock streams have their own ids (M…)")
    try:
        measure_unapplied(events)                    # timing statistics for the groups that are not moved (see note_timing)
    except Exception as e:                           # statistics must never stop the guide
        print(f"  timing statistics skipped: {e}")
    apply_overrides(events, now)
    print(f"{len(names)} streams in the playlist(s), {len(events)} with an event time")
    tv, chans, progs = build(events, now)
    save_seen(now)
    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(args.out, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {args.out}: {chans} channels, {progs} programmes")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
football_epg.py - Build an XMLTV EPG file of English football club fixtures,
using ESPN's public (unofficial, key-free) site API as the data source.

* Every competition is a separate set of channels, each with its own
  extension (see COMPETITION_EXT): Arsenal.pl, Arsenal.ucl, Arsenal.fac ...
* Club channels are only created for competitions the club has fixtures in.
* There are no whole-competition or combined all-matches channels.
* All times are written in Europe/London local time (GMT/BST offsets).

Usage:
    python3 football_epg.py                      # next 8 days
    python3 football_epg.py --days 30            # next 30 days
    python3 football_epg.py --days 0             # rest of the season
    python3 football_epg.py --out epg.xml        # writes epg1.xml, then epg2.xml, ...
    python3 football_epg.py --no-version         # overwrite football_epg.xml instead

Notes:
  * No API key is needed. Only the standard library is required
    (the optional `certifi` package is used for SSL certs if installed).
  * The ESPN endpoints are unofficial and could change. If a competition
    prints a warning and returns no fixtures, check its ESPN slug in COMPETITIONS.
  * On Windows, run `pip install tzdata` so zoneinfo knows Europe/London.
"""

import argparse
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
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
LONDON = ZoneInfo("Europe/London")

# display name -> ESPN league slug
COMPETITIONS = {
    "Premier League": "eng.1",
    "Championship": "eng.2",
    "League One": "eng.3",
    "League Two": "eng.4",
    "FA Cup": "eng.fa",
    "Carabao Cup": "eng.league_cup",
    "EFL Trophy": "eng.trophy",
    "UEFA Champions League": "uefa.champions",
    "UEFA Europa League": "uefa.europa",
    "UEFA Conference League": "uefa.europa.conf",
}

# Leagues whose clubs define "English clubs" (each gets a channel).
ENGLISH_TIER_LEAGUES = ["Premier League", "Championship", "League One", "League Two"]

# Event statuses to skip (no reliable kick-off).
SKIP_STATUSES = {"STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_CANCELLED",
                 "STATUS_ABANDONED", "STATUS_FORFEIT"}

# Channel-id extension for each competition (must be unique).
#   <club>.<ext>   e.g. Arsenal.pl, Chelsea.ucl
#   <competition>.<ext>  e.g. Premier.League.pl  (all matches in that competition)
COMPETITION_EXT = {
    "Premier League": "pl",
    "Championship": "champ",
    "League One": "l1",
    "League Two": "l2",
    "FA Cup": "fac",
    "Carabao Cup": "cc",
    "EFL Trophy": "eflt",
    "UEFA Champions League": "ucl",
    "UEFA Europa League": "uel",
    "UEFA Conference League": "uecl",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (football_epg.py)"}


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def _ssl_context():
    try:
        import certifi  # helps on macOS python.org builds
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ssl_context()


class NoData(Exception):
    """ESPN answered 400/404 for this request."""
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


def get_json(url, params=None, retries=3):
    """GET JSON. Raises NoData on HTTP 400/404 (bad slug or unsupported query)."""
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
    sys.exit(f"Failed to fetch {url}: {last_err}")


# --------------------------------------------------------------------------
# ESPN data
# --------------------------------------------------------------------------
def fetch_clubs():
    """Clubs in the top four English tiers -> {team_id: {name, logo}}."""
    clubs = {}
    for comp in ENGLISH_TIER_LEAGUES:
        slug = COMPETITIONS[comp]
        print(f"Fetching clubs from {comp} ...")
        try:
            data = get_json(f"{ESPN_BASE}/{slug}/teams", {"limit": 100})
        except NoData:
            print(f"  WARNING: no team list for {slug}")
            continue
        try:
            teams = data["sports"][0]["leagues"][0]["teams"]
        except (KeyError, IndexError):
            teams = []
        for t in teams:
            team = t.get("team", {})
            if not team.get("id"):
                continue
            logos = team.get("logos") or [{}]
            clubs[str(team["id"])] = {
                "name": short_name(team.get("displayName") or team.get("name")),
                "logo": logos[0].get("href"),
            }
        print(f"  {len(teams)} clubs")
    return clubs


def windows(start, end, step_days):
    """Yield (first, last) date pairs of up to step_days days."""
    cur = start
    while cur <= end:
        last = min(cur + timedelta(days=step_days - 1), end)
        yield cur, last
        cur = last + timedelta(days=1)


def scoreboard(slug, a, b):
    rng = f"{a:%Y%m%d}" if a == b else f"{a:%Y%m%d}-{b:%Y%m%d}"
    return get_json(f"{ESPN_BASE}/{slug}/scoreboard", {"dates": rng})


def fetch_events(start, end):
    """Return {competition_name: [event, ...]} for the date range.

    ESPN rejects multi-day ranges, so each day is requested separately
    (8 in parallel).
    """
    out = {}
    for comp, slug in COMPETITIONS.items():
        print(f"Fetching {comp} ({slug}) ...")

        # Probe the first day to check the slug is valid
        try:
            scoreboard(slug, start, start)
        except NoData as e:
            reason = "no such league" if e.code == 404 else "request rejected"
            print(f"  WARNING: ESPN {reason} for '{slug}' - skipping {comp}")
            out[comp] = []
            continue

        days = list(windows(start, end, 1))

        def grab(w):
            try:
                return scoreboard(slug, *w).get("events", [])
            except NoData:
                return []

        events, seen_ids = [], set()
        with ThreadPoolExecutor(max_workers=8) as pool:
            for evs in pool.map(grab, days):
                for ev in evs:
                    if ev.get("id") not in seen_ids:
                        seen_ids.add(ev.get("id"))
                        events.append(ev)
        print(f"  {len(events)} fixtures" if events else "  no fixtures found in range")
        out[comp] = events
    return out


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", ".", text).strip(".")


# Club name tidy-ups, applied to channel names, channel ids and match titles.
NAME_RULES = [
    (r"^AFC Bournemouth$", "Bournemouth"),
    (r"^Wolverhampton Wanderers$", "Wolves"),
    (r"^Milton Keynes Dons$", "MK Dons"),
    (r"\bUnited\b", "Utd"),
]


def short_name(name):
    if not name:
        return name
    for pattern, repl in NAME_RULES:
        name = re.sub(pattern, repl, name, flags=re.I)
    return name


def parse_espn_time(s):
    """ESPN dates look like '2026-10-17T14:00Z' (UTC)."""
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def xmltv_time(dt_utc):
    """XMLTV time in London local time, e.g. '20261017150000 +0100'."""
    return dt_utc.astimezone(LONDON).strftime("%Y%m%d%H%M%S %z")


def build_channels(clubs, events_by_comp):
    """Assign a unique channel base name to each English club."""
    # Safety net: add any tier-league club seen in fixtures but missing from /teams
    for comp in ENGLISH_TIER_LEAGUES:
        for ev in events_by_comp.get(comp, []):
            for c in ev["competitions"][0].get("competitors", []):
                t = c.get("team", {})
                tid = str(t.get("id", ""))
                if tid and tid not in clubs:
                    clubs[tid] = {"name": short_name(t.get("displayName")), "logo": t.get("logo")}

    channels, used = {}, set()
    for tid, c in sorted(clubs.items(), key=lambda kv: (kv[1]["name"] or "")):
        base = slugify(c["name"] or f"team{tid}")
        if base in used:
            base = f"{base}.{tid}"
        used.add(base)
        channels[tid] = {"base": base, "name": c["name"], "logo": c["logo"]}
    return channels


# --------------------------------------------------------------------------
# XMLTV generation
# --------------------------------------------------------------------------
def add_programme(tv, chan_id, start, stop, title, sub, desc, categories):
    p = ET.SubElement(tv, "programme", {
        "start": xmltv_time(start),
        "stop": xmltv_time(stop),
        "channel": chan_id,
    })
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    for cat in ["Sports", "Football"] + list(categories):
        ET.SubElement(p, "category", {"lang": "en"}).text = cat


def collect_matches(events_by_comp, match_minutes):
    matches, seen = [], set()
    for comp_name, events in events_by_comp.items():
        for ev in events:
            comp = (ev.get("competitions") or [{}])[0]
            status = (ev.get("status") or {}).get("type", {}).get("name", "")
            if status in SKIP_STATUSES or not ev.get("date") or ev.get("id") in seen:
                continue
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            seen.add(ev.get("id"))
            h, a = home["team"], away["team"]
            title = f"{short_name(h.get('displayName'))} v {short_name(a.get('displayName'))}"
            start = parse_espn_time(ev["date"])

            notes = [n.get("headline") for n in comp.get("notes", []) if n.get("headline")]
            sub = comp_name + (f" - {notes[0]}" if notes else "")

            desc_parts = [f"{start.astimezone(LONDON):%a %d %b}.", f"{sub}: {title}."]
            venue = comp.get("venue") or {}
            if venue.get("fullName"):
                city = (venue.get("address") or {}).get("city")
                desc_parts.append(f"{venue['fullName']}{', ' + city if city else ''}.")
            if comp.get("timeValid") is False:
                desc_parts.append("Kick-off time to be confirmed.")
            else:
                ko = start.astimezone(LONDON)
                desc_parts.append(f"Kick-off: {ko:%H:%M}.")

            matches.append({
                "comp": comp_name, "title": title, "sub": sub,
                "desc": " ".join(desc_parts),
                "start": start, "stop": start + timedelta(minutes=match_minutes),
                "home_id": str(h.get("id")), "away_id": str(a.get("id")),
            })
    return matches


def build_xmltv(events_by_comp, channels, match_minutes):
    tv = ET.Element("tv", {
        "generator-info-name": "football_epg.py",
        "source-info-name": "ESPN",
    })

    matches = collect_matches(events_by_comp, match_minutes)

    # Per (competition, club) match lists -> one channel each
    club_comp = {}  # (comp, tid) -> [matches]
    for m in matches:
        for tid in (m["home_id"], m["away_id"]):
            if tid in channels:
                club_comp.setdefault((m["comp"], tid), []).append(m)

    # ---- Channel definitions ----------------------------------------------
    club_channels = []  # (chan_id, comp, tid)
    for (comp, tid) in sorted(club_comp, key=lambda k: (channels[k[1]]["name"] or "", k[0])):
        ch = channels[tid]
        chan_id = f"{ch['base']}.{COMPETITION_EXT[comp]}"
        club_channels.append((chan_id, comp, tid))
        c = ET.SubElement(tv, "channel", {"id": chan_id})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = f"{ch['name']} {comp}"
        if ch["logo"]:
            ET.SubElement(c, "icon", {"src": ch["logo"]})

    written = 0

    # ---- Club + competition channels: one programme per match -------------
    for chan_id, comp, tid in club_channels:
        last_stop = None
        for m in sorted(club_comp[(comp, tid)], key=lambda m: m["start"]):
            start, stop = m["start"], m["stop"]
            if last_stop and start < last_stop:  # trim overlaps on one channel
                start = last_stop
                if stop <= start:
                    continue
            last_stop = stop
            add_programme(tv, chan_id, start, stop, m["title"], m["sub"], m["desc"], [comp])
            written += 1

    return tv, written


def write_xml(tv, path):
    ET.indent(tv, space="  ")
    body = ET.tostring(tv, encoding="unicode")
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(body + "\n")


def next_versioned_path(path):
    """football_epg.xml -> football_epg1.xml, football_epg2.xml, ... (next unused number)."""
    folder, name = os.path.split(path)
    stem, ext = os.path.splitext(name)
    pattern = re.compile(rf"^{re.escape(stem)}(\d+){re.escape(ext)}$")
    highest = 0
    for f in os.listdir(folder or "."):
        m = pattern.match(f)
        if m:
            highest = max(highest, int(m.group(1)))
    return os.path.join(folder, f"{stem}{highest + 1}{ext}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Generate an XMLTV EPG of English football fixtures from ESPN.")
    ap.add_argument("--out", default="football_epg.xml", help="Output XMLTV file")
    ap.add_argument("--from", dest="start", default=None,
                    help="Start date YYYY-MM-DD (default: today, London time)")
    ap.add_argument("--days", type=int, default=8,
                    help="Number of days to cover, including today (default 8; 0 = until 30 June)")
    ap.add_argument("--minutes", type=int, default=120,
                    help="Programme length per match in minutes (default 120)")
    ap.add_argument("--no-version", action="store_true",
                    help="Write exactly the --out name, overwriting it (no version number)")
    args = ap.parse_args()

    today = datetime.now(LONDON).date()
    start = date.fromisoformat(args.start) if args.start else today
    if args.days:
        end = start + timedelta(days=args.days - 1)
    else:
        end = date(start.year + (1 if start.month >= 7 else 0), 6, 30)

    print(f"Date range: {start} to {end} (times output in Europe/London)\n")

    clubs = fetch_clubs()
    events = fetch_events(start, end)
    channels = build_channels(clubs, events)
    if not channels:
        sys.exit("No English clubs found - ESPN may be unreachable or have changed its API.")

    tv, count = build_xmltv(events, channels, args.minutes)
    out_path = args.out if args.no_version else next_versioned_path(args.out)
    write_xml(tv, out_path)
    n_ch = len(tv.findall("channel"))
    print(f"\nWrote {out_path}: {n_ch} channels, {count} programmes")


if __name__ == "__main__":
    main()

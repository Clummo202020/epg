#!/usr/bin/env python3
"""
scottish_epg.py - XMLTV guide of Scottish football fixtures for IPTV event channels.

A companion to football_epg.py, built the same way:
  * Scottish clubs (Premiership, Championship, League One, League Two): their league
    matches plus the Scottish Cup, League Cup and Challenge Cup.
  * Scottish clubs' European matches are NOT included here: football_epg.py already
    gives every club in the Champions League, Europa League and Conference League a
    channel (Celtic.ChampsLge, Rangers.Europa ...), and repeating those ids in a
    second file would clash in PlaylistLabs.
  * Channel ids end in Scottish competition names (Celtic.ScotPrem, Hearts.ScotCup),
    so they can never clash with football_epg.py's ids either.

Data comes from ESPN's public (unofficial, key-free) site API.

What this script does, and why (lessons from getting it working on MyTV Online
and PlaylistLabs):

  * FIXED CHANNEL IDS AND FILE NAME (default).  Channels are <club>.<competition>,
    e.g. Celtic.ScotPrem, Aberdeen.ScotCup, and the output always overwrites
    OUTPUT_NAME below - the file name used on GitHub - so the raw link never
    changes.  PlaylistLabs re-reads that link and ADDS new programmes after the
    latest one it holds for each channel id; channels stay linked for good.
  * It never changes programmes it already holds, so when a kick-off time moves
    use --run-ids once: ids become <club>.<competition>Run<n> (Celtic.ScotPremRun3),
    brand new to PlaylistLabs, so it takes the whole file; relink to those ids.
    The last run number is kept in scottish_epg_run.json next to this script.
    (--suffix N forces a run number.)  --unique gives a new file name each run.
  * FILLER PROGRAMMES.  Between now and each kick-off the channel shows
    "Celtic v Rangers (Sat 17 Oct, 12:30)" with the match details,
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
    python3 scottish_epg.py                 # next 10 days -> OUTPUT_NAME (fixed ids, overwrites)
    python3 scottish_epg.py --days 30       # next 30 days
    python3 scottish_epg.py --days 0        # rest of the season (to 30 June)
    python3 scottish_epg.py --run-ids       # fresh ids (Celtic.ScotPremRun3) when kick-off times change
    python3 scottish_epg.py --suffix 12     # run ids with run 12 forced; later runs go on from it
    python3 scottish_epg.py --unique        # new file name each run: scottish_epg_<date-time>_<random>.xml
    python3 scottish_epg.py --channel-list channels.csv   # also write id,name list

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
HEADERS = {"User-Agent": "Mozilla/5.0 (scottish_epg.py)"}

# display name -> (ESPN league slug, channel-id competition part)
COMPETITIONS = {
    "Scottish Premiership":   ("sco.1", "ScotPrem"),
    "Scottish Championship":  ("sco.2", "ScotChamp"),
    "Scottish League One":    ("sco.3", "ScotLge1"),
    "Scottish League Two":    ("sco.4", "ScotLge2"),
    "Scottish Cup":           ("sco.tennents", "ScotCup"),
    "Scottish League Cup":    ("sco.cis", "ScotLgeCup"),
    "Scottish Challenge Cup": ("sco.challenge", "ChallengeCup"),
}

# Leagues that define "Scottish clubs": only these clubs get channels (their cup
# opponents from outside the SPFL, e.g. Highland League sides, do not).
# (The name ENGLISH_LEAGUES is kept from football_epg.py so the code stays the same.)
ENGLISH_LEAGUES = ["Scottish Premiership", "Scottish Championship",
                   "Scottish League One", "Scottish League Two"]

# No European competitions here: football_epg.py already covers them.
UEFA_COMPETITIONS = []

# Fixtures with these statuses have no reliable kick-off and are skipped.
SKIP_STATUSES = {"STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_CANCELLED",
                 "STATUS_ABANDONED", "STATUS_FORFEIT"}

# Club name tidy-ups, used in channel names, channel ids and match titles.
# Changing these changes channel ids, so leave them alone once mapped.
NAME_RULES = [
    (r"^Heart of Midlothian$", "Hearts"),
    (r"^Inverness Caledonian Thistle$", "Inverness CT"),
    (r"\bUnited\b", "Utd"),
]

RUN_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scottish_epg_run.json")


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
OUTPUT_NAME = "scottish_epg.xml"   # the file name on GitHub
FILLER_HOURS = 2          # longest filler block in hours (0 = one block per gap)
DOCTYPE = True            # write the standard XMLTV DOCTYPE line
COUNTDOWN = False         # add "- kick-off in 2d 23h" to each filler block
FILLER_STYLE = "plain"    # "plain": "Celtic v Rangers (Sat 17 Oct, 12:30)"
                          # "next":  "Next: Celtic v Rangers - Sat 17 Oct, 12:30"


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
    """{team_id: name} for every club in the four SPFL divisions."""
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
            desc = [f"{sub}: {title}."]
            venue = comp.get("venue") or {}
            if venue.get("fullName"):
                city = (venue.get("address") or {}).get("city")
                desc.append(f"{venue['fullName']}{', ' + city if city else ''}.")
            desc.append("Kick-off time to be confirmed." if tbc else f"Kick-off: {ko:%H:%M}.")

            matches.append({
                "comp": comp_name, "title": title, "sub": sub, "desc": utd(" ".join(desc)),
                "start": start, "stop": start + timedelta(minutes=match_minutes),
                "when": f"{ko:%a %d %b}, {'TBC' if tbc else f'{ko:%H:%M}'}",
                "teams": [h, a],
            })
    return matches


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
            if tid in english or (not english_only and m["comp"] in UEFA_COMPETITIONS):
                grouped.setdefault((tid, m["comp"]), []).append(m)

    channels = []
    for (tid, comp), ms in grouped.items():
        ext = COMPETITIONS[comp][1]
        channels.append((f"{bases[tid]}.{ext}{suffix}", f"{names[tid]} {comp}",
                         logos.get(tid), sorted(ms, key=lambda m: m["start"])))
    channels.sort(key=lambda c: c[1])
    return channels


# --------------------------------------------------------------------------
# XMLTV
# --------------------------------------------------------------------------
def add_programme(tv, chan_id, start, stop, title, sub, desc, comp):
    p = ET.SubElement(tv, "programme", {
        "start": xmltv_time(start), "stop": xmltv_time(stop), "channel": chan_id})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    for cat in ("Sports", "Football", comp):
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
    tv = ET.Element("tv", {"generator-info-name": "scottish_epg.py",
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
                        f_desc = f"Next Match: {m['desc']}"
                    if COUNTDOWN:    # optional "- kick-off in 2d 23h" per block
                        f_title += f" - kick-off in {countdown(start - a)}"
                    add_programme(tv, chan_id, a, b, f_title, m["sub"], f_desc, m["comp"])
                    count += 1
            add_programme(tv, chan_id, start, stop, m["title"], m["sub"], m["desc"], m["comp"])
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
    ap = argparse.ArgumentParser(description="XMLTV guide of Scottish football fixtures from ESPN.")
    ap.add_argument("--out", default=OUTPUT_NAME,
                    help="base output name (default scottish_epg.xml)")
    ap.add_argument("--unique", action="store_true",
                    help="add date-time and a random code to the file name instead of overwriting")
    ap.add_argument("--fixed-name", action="store_true", help=argparse.SUPPRESS)  # old flag, now default
    ap.add_argument("--from", dest="start", help="start date YYYY-MM-DD (default today)")
    ap.add_argument("--days", type=int, default=10,
                    help="days to cover including today (default 10; 0 = to 30 June)")
    ap.add_argument("--minutes", type=int, default=120, help="match length (default 120)")
    ap.add_argument("--suffix", type=int, default=None,
                    help="run ids with this run number forced (12 -> Celtic.ScotPremRun12); later runs continue from it")
    ap.add_argument("--run-ids", action="store_true",
                    help="fresh ids with a run number (Celtic.ScotPremRun3), e.g. when kick-off times change")
    ap.add_argument("--fixed-ids", action="store_true", help=argparse.SUPPRESS)   # old flag, now default
    ap.add_argument("--english-only", action="store_true", help=argparse.SUPPRESS)   # no effect here
    ap.add_argument("--no-filler", action="store_true",
                    help="no 'Next: ...' programmes before each match")
    ap.add_argument("--filler-hours", type=int, default=2, choices=[0, 1, 2, 3, 4, 6, 8, 12],
                    help="longest filler block in hours (default 2, as PlaylistLabs skips "
                         "long programmes; 0 = one block per gap)")
    ap.add_argument("--filler-style", choices=["plain", "next"], default="plain",
                    help="filler titles: plain = 'Celtic v Rangers (Sat 17 Oct, 12:30)' "
                         "(default), next = 'Next: Celtic v Rangers - Sat 17 Oct, 12:30'")
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
        sys.exit("No Scottish clubs found - ESPN may be unreachable or changed its API.")
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
        out_path = unique_path("scottish_epg.xml" if args.out == OUTPUT_NAME else args.out)
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

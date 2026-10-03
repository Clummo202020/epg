#!/usr/bin/env python3
"""
Generate an XMLTV (EPG) file of upcoming Arsenal senior men's fixtures across
the league, domestic cups and European competitions.

Data source: ESPN's public site API (no API key needed).
Usage:
    pip install requests
    python arsenal_epg.py                       # writes arsenal_fixtures.xml
    python arsenal_epg.py -o /path/out.xml --duration 120 --debug

Times are written in UK local time (Europe/London, handles GMT/BST) using the
XMLTV "YYYYMMDDHHMMSS +ZZZZ" format.
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ARSENAL_ID = "359"  # ESPN team id for Arsenal

# ESPN league slug -> display name. Edit freely; slugs that return nothing are skipped.
COMPETITIONS = {
    "eng.1": "Premier League",
    "eng.fa": "FA Cup",
    "eng.league_cup": "EFL Cup",
    "eng.charity": "FA Community Shield",
    "uefa.champions": "UEFA Champions League",
    "uefa.europa": "UEFA Europa League",
    "uefa.super_cup": "UEFA Super Cup",
    "fifa.cwc": "FIFA Club World Cup",
}

LOCAL_TZ = ZoneInfo("Europe/London")
CHANNEL_ID = "arsenal.fixtures.uk"
CHANNEL_NAME = "Arsenal FC Fixtures"
HEADERS = {"User-Agent": "Mozilla/5.0 (arsenal-epg script)"}


def fetch_schedule(slug, debug=False):
    url = f"{ESPN}/{slug}/teams/{ARSENAL_ID}/schedule"
    try:
        r = requests.get(url, params={"fixture": "true"}, headers=HEADERS, timeout=30)
        if r.status_code == 404:
            if debug:
                print(f"  {slug}: not found, skipping", file=sys.stderr)
            return []
        r.raise_for_status()
        return r.json().get("events", [])
    except (requests.RequestException, ValueError) as e:
        print(f"Warning: could not fetch {slug}: {e}", file=sys.stderr)
        return []


def parse_event(ev, comp_name):
    """Turn an ESPN event into a simple dict, or None if unusable."""
    comps = ev.get("competitions") or [{}]
    comp = comps[0]

    raw_date = ev.get("date") or comp.get("date")
    if not raw_date:
        return None
    start = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    home = away = None
    for c in comp.get("competitors", []):
        team = c.get("team", {})
        name = team.get("displayName") or team.get("shortDisplayName") or team.get("name")
        if c.get("homeAway") == "home":
            home = name
        elif c.get("homeAway") == "away":
            away = name
    if not (home and away):
        # Fall back to the event name, e.g. "Chelsea at Arsenal"
        name = ev.get("name", "")
        if " at " in name:
            away, home = [p.strip() for p in name.split(" at ", 1)]
        elif " v " in name:
            home, away = [p.strip() for p in name.split(" v ", 1)]
        else:
            return None

    venue = comp.get("venue") or ev.get("venue") or {}
    venue_name = venue.get("fullName") or venue.get("name")
    addr = venue.get("address") or {}
    place = ", ".join(p for p in (addr.get("city"), addr.get("country")) if p)
    if venue_name and place:
        venue_text = f"{venue_name}, {place}"
    elif venue_name:
        venue_text = venue_name
    elif home == "Arsenal":
        venue_text = "Emirates Stadium, London, England"
    else:
        venue_text = "Venue TBC"

    state = ((comp.get("status") or {}).get("type") or {}).get("state")
    return {
        "id": ev.get("id"),
        "start": start,
        "home": home,
        "away": away,
        "venue": venue_text,
        "competition": comp_name,
        "round": (ev.get("seasonType") or {}).get("name") or "",
        "time_tbc": comp.get("timeValid") is False,
        "state": state,
    }


def xmltv_time(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


def build_xmltv(fixtures, duration_min):
    # Plain <tv> root with no attributes: some strict/naive importers look for a literal "<tv>"
    tv = ET.Element("tv")
    ch = ET.SubElement(tv, "channel", {"id": CHANNEL_ID})
    ET.SubElement(ch, "display-name", {"lang": "en"}).text = CHANNEL_NAME

    for f in fixtures:
        start = f["start"].astimezone(LOCAL_TZ)
        stop = start + timedelta(minutes=duration_min)
        title = f"{f['home']} v {f['away']}"

        desc = f"{f['competition']}: {title}. Venue: {f['venue']}."
        if f["time_tbc"]:
            desc += " Kick-off time to be confirmed."

        prog = ET.SubElement(tv, "programme", {
            "start": xmltv_time(start),
            "stop": xmltv_time(stop),
            "channel": CHANNEL_ID,
        })
        ET.SubElement(prog, "title", {"lang": "en"}).text = title
        ET.SubElement(prog, "sub-title", {"lang": "en"}).text = f["competition"]
        ET.SubElement(prog, "desc", {"lang": "en"}).text = desc
        ET.SubElement(prog, "category", {"lang": "en"}).text = "Sports"
        ET.SubElement(prog, "category", {"lang": "en"}).text = "Football"
    return tv


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="arsenal_fixtures.xml")
    ap.add_argument("--duration", type=int, default=120, help="Programme length in minutes (default 120)")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    seen, fixtures = set(), []
    for slug, name in COMPETITIONS.items():
        events = fetch_schedule(slug, args.debug)
        count = 0
        for ev in events:
            fx = parse_event(ev, name)
            if not fx or fx["start"] <= now or fx["state"] not in (None, "pre"):
                continue
            key = fx["id"] or (fx["start"], fx["home"], fx["away"])
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(fx)
            count += 1
        if args.debug:
            print(f"  {name}: {count} upcoming", file=sys.stderr)

    fixtures.sort(key=lambda f: f["start"])
    if not fixtures:
        # Don't overwrite a good file with an empty guide that importers may reject
        sys.exit("No upcoming fixtures found (try --debug); output file not written.")

    tv = build_xmltv(fixtures, args.duration)
    ET.indent(tv)
    with open(args.output, "wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write(ET.tostring(tv, encoding="utf-8"))
    print(f"Wrote {len(fixtures)} fixtures to {args.output}")


if __name__ == "__main__":
    main()

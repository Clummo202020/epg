#!/usr/bin/env python3
"""
Generate an XMLTV (EPG) file of upcoming league fixtures for every EFL club
(Championship, League One, League Two), one channel per team. Cup ties (FA Cup,
EFL Cup, EFL Trophy) are left out unless you pass --include-cups.

Data source: ESPN's public site API (no API key needed). The clubs in each
division are fetched live from ESPN, so promotion/relegation is picked up
automatically each season.

Usage:
    pip install requests
    python efl_epg.py --list-ids                      # show the channel id each team will get
    python efl_epg.py --fill                          # writes efl_fixtures.xml.gz (all 72 clubs)
    python efl_epg.py --fill -o efl_fixtures.xml      # plain, uncompressed XML instead
    python efl_epg.py --fill --include-cups           # add FA Cup / EFL Cup / EFL Trophy ties
    python efl_epg.py --fill --divisions championship # just one division (smaller file)
    python efl_epg.py --fill --id-map ids.json        # override channel ids (see below)

Channel ids default to "<team-slug>.fc" (e.g. "leicester-city.fc"); change the
pattern with --id-template "{slug}.uk". To match the tvg-ids already in your
playlist, pass a JSON file mapping team name -> id (or list of ids):
    {"Leicester City": ["leicester.fc", "leicester-city.fc"], "Wrexham": "wrexham.fc"}

Times are written in UK local time (Europe/London, handles GMT/BST) using the
XMLTV "YYYYMMDDHHMMSS +ZZZZ" format.
"""
import argparse
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"

# --divisions name -> (ESPN league slug, competition display name)
DIVISIONS = {
    "championship": ("eng.2", "EFL Championship"),
    "league-one": ("eng.3", "EFL League One"),
    "league-two": ("eng.4", "EFL League Two"),
}

# Cup competitions queried for every club. Slugs that return nothing are skipped.
CUPS = {
    "eng.fa": "FA Cup",
    "eng.league_cup": "EFL Cup",
    "eng.trophy": "EFL Trophy",
}

DEFAULT_ID_MAP = {}

# Display-name tidying (applied to channel names, fixture titles and the default channel ids,
# e.g. "AFC Bournemouth" -> "Bournemouth" -> "bournemouth.fc").
NAME_OVERRIDES = {
    "AFC Bournemouth": "Bournemouth",
    "Wolverhampton Wanderers": "Wolves",
    "Milton Keynes Dons": "MK Dons",
}


def clean_name(name):
    if not name:
        return name
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]
    return re.sub(r"\bUnited\b", "Utd", name)


LOCAL_TZ = ZoneInfo("Europe/London")
HEADERS = {"User-Agent": "Mozilla/5.0 (efl-epg script)"}


# ------------------------------------------------------------------ fetching
def get_teams(league_slug):
    """Return [(espn_team_id, display_name), ...] for one division."""
    r = requests.get(f"{ESPN}/{league_slug}/teams", headers=HEADERS, timeout=30)
    r.raise_for_status()
    teams = r.json()["sports"][0]["leagues"][0]["teams"]
    return [(t["team"]["id"], t["team"]["displayName"]) for t in teams]


def fetch_schedule(team_id, slug):
    url = f"{ESPN}/{slug}/teams/{team_id}/schedule"
    try:
        r = requests.get(url, params={"fixture": "true"}, headers=HEADERS, timeout=30)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("events", [])
    except (requests.RequestException, ValueError) as e:
        print(f"Warning: could not fetch {slug} for team {team_id}: {e}", file=sys.stderr)
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
        name = ev.get("name", "")
        if " at " in name:
            away, home = [p.strip() for p in name.split(" at ", 1)]
        elif " v " in name:
            home, away = [p.strip() for p in name.split(" v ", 1)]
        else:
            return None

    home, away = clean_name(home), clean_name(away)

    venue = comp.get("venue") or ev.get("venue") or {}
    venue_name = venue.get("fullName") or venue.get("name")
    addr = venue.get("address") or {}
    place = ", ".join(p for p in (addr.get("city"), addr.get("country")) if p)
    if venue_name and place:
        venue_text = f"{venue_name}, {place}"
    elif venue_name:
        venue_text = venue_name
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
        "time_tbc": comp.get("timeValid") is False,
        "state": state,
    }


def team_fixtures(team_id, league_slug, league_name, debug_name=None, debug=False,
                  include_cups=False):
    """Upcoming, de-duplicated fixtures for one club: its league, plus the cups if requested."""
    now = datetime.now(timezone.utc)
    competitions = {league_slug: league_name, **(CUPS if include_cups else {})}
    seen, fixtures = set(), []
    for slug, comp_name in competitions.items():
        count = 0
        for ev in fetch_schedule(team_id, slug):
            fx = parse_event(ev, comp_name)
            if not fx or fx["start"] <= now or fx["state"] not in (None, "pre"):
                continue
            key = fx["id"] or (fx["start"], fx["home"], fx["away"])
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(fx)
            count += 1
        if debug and count:
            print(f"  {debug_name}: {comp_name}: {count}", file=sys.stderr)
    fixtures.sort(key=lambda f: f["start"])
    return fixtures


# ------------------------------------------------------------------ XMLTV
def slugify(name):
    s = name.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def channel_ids_for(name, id_map, template):
    mapped = id_map.get(name) or id_map.get(clean_name(name))
    if mapped:
        return [mapped] if isinstance(mapped, str) else list(mapped)
    return [template.format(slug=slugify(clean_name(name)))]


def xmltv_time(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


def make_items(fixtures, team_name, duration_min, fill, fill_days=3):
    """Return [(start, stop, title, sub_title, desc), ...] for one team."""
    items = []
    cursor = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    # Filler only covers today + the next (fill_days - 1) days; the daily refresh keeps it moving
    cutoff = datetime.combine(cursor.date() + timedelta(days=fill_days), datetime.min.time(),
                              tzinfo=LOCAL_TZ)
    for f in fixtures:
        start = f["start"].astimezone(LOCAL_TZ)
        stop = start + timedelta(minutes=duration_min)
        title = f"{f['home']} v {f['away']}"

        match_date = start.strftime("%a %d %b")
        desc = f"{f['competition']}: {title}. Date: {match_date}. Venue: {f['venue']}."
        if f["time_tbc"]:
            desc += " Kick-off time to be confirmed."
        desc += "\nStream goes Live just before kick off."

        if fill:
            next_txt = start.strftime("%a %d %b %H:%M")
            filler_desc = (f"Next fixture: {f['competition']}: {title}, {next_txt}. "
                           f"Venue: {f['venue']}.")
            while cursor < start and cursor < cutoff:
                midnight = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time(),
                                            tzinfo=LOCAL_TZ)
                end = min(midnight, start)
                items.append((cursor, end, f"{team_name} - Next: {title}", "No match today", filler_desc))
                cursor = end
        items.append((start, stop, title, f["competition"], desc))
        cursor = max(cursor, stop)
    return items


def build_xmltv(team_data, id_map, template, duration_min, fill, fill_days=3):
    """team_data: [(team_name, fixtures), ...]"""
    tv = ET.Element("tv")
    per_team = []
    used = set()
    for name, fixtures in team_data:
        ids = channel_ids_for(name, id_map, template)
        for cid in ids:
            if cid in used:
                print(f"Warning: duplicate channel id {cid!r} ({name})", file=sys.stderr)
            used.add(cid)
            ch = ET.SubElement(tv, "channel", {"id": cid})
            ET.SubElement(ch, "display-name", {"lang": "en"}).text = f"{clean_name(name)} Fixtures"
        per_team.append((name, ids, make_items(fixtures, clean_name(name), duration_min, fill, fill_days)))

    for name, ids, items in per_team:
        for cid in ids:
            for start, stop, title, sub, desc in items:
                prog = ET.SubElement(tv, "programme", {
                    "start": xmltv_time(start),
                    "stop": xmltv_time(stop),
                    "channel": cid,
                })
                ET.SubElement(prog, "title", {"lang": "en"}).text = title
                ET.SubElement(prog, "sub-title", {"lang": "en"}).text = sub
                ET.SubElement(prog, "desc", {"lang": "en"}).text = desc
                ET.SubElement(prog, "category", {"lang": "en"}).text = "Sports"
                ET.SubElement(prog, "category", {"lang": "en"}).text = "Football"
    return tv


def load_id_map(path):
    id_map = dict(DEFAULT_ID_MAP)
    if path:
        with open(path, encoding="utf-8") as fh:
            id_map.update(json.load(fh))
    return id_map


def load_teams(division_names):
    """[(team_id, team_name, league_slug, league_name), ...] for the chosen divisions."""
    teams, seen = [], set()
    for div in division_names:
        slug, league_name = DIVISIONS[div]
        try:
            found = get_teams(slug)
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            sys.exit(f"Could not fetch the {league_name} team list from ESPN: {e}")
        if not found:
            sys.exit(f"ESPN returned no teams for {league_name}.")
        for tid, name in sorted(found, key=lambda x: x[1]):
            if tid not in seen:
                seen.add(tid)
                teams.append((tid, name, slug, league_name))
    return teams


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="efl_fixtures.xml.gz",
                    help="Output path; a name ending in .gz is written gzip-compressed")
    ap.add_argument("--duration", type=int, default=120, help="Programme length in minutes (default 120)")
    ap.add_argument("--divisions", default=",".join(DIVISIONS),
                    help="Comma-separated divisions to include: %(default)s")
    ap.add_argument("--include-cups", action="store_true",
                    help="Also include FA Cup, EFL Cup and EFL Trophy ties (default: league fixtures only)")
    ap.add_argument("--fill", action="store_true",
                    help="Fill gaps before the next fixture with daily 'Next match' programmes so every "
                         "channel has something airing")
    ap.add_argument("--fill-days", type=int, default=3,
                    help="With --fill, only add filler for this many days from today "
                         "(default %(default)s). Keeps the file small; real fixtures are never limited")
    ap.add_argument("--id-template", default="{slug}.fc",
                    help="Channel id pattern for teams not in the id map (default: %(default)s)")
    ap.add_argument("--id-map", help="JSON file mapping team name -> channel id (or list of ids)")
    ap.add_argument("--list-ids", action="store_true", help="Print each team's channel id(s) and exit")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    divisions = [d.strip() for d in args.divisions.split(",") if d.strip()]
    bad = [d for d in divisions if d not in DIVISIONS]
    if bad:
        sys.exit(f"Unknown division(s): {', '.join(bad)}. Choose from: {', '.join(DIVISIONS)}")

    id_map = load_id_map(args.id_map)
    teams = load_teams(divisions)

    if args.list_ids:
        for _, name, _, league_name in teams:
            ids = ", ".join(channel_ids_for(name, id_map, args.id_template))
            print(f"{league_name:18s} {clean_name(name):30s} {ids}")
        print(f"\n{len(teams)} clubs")
        return

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(
            lambda t: team_fixtures(t[0], t[2], t[3], t[1], args.debug, args.include_cups), teams))

    team_data = [(t[1], fx) for t, fx in zip(teams, results)]
    total = sum(len(fx) for _, fx in team_data)
    if args.debug:
        for name, fx in team_data:
            print(f"{name}: {len(fx)} upcoming", file=sys.stderr)
    if total == 0:
        # Don't overwrite a good file with an empty guide
        sys.exit("No upcoming fixtures found (try --debug); output file not written.")

    tv = build_xmltv(team_data, id_map, args.id_template, args.duration, args.fill, args.fill_days)
    ET.indent(tv)
    body = re.sub(rb"\n[ \t]+", b"\n", ET.tostring(tv, encoding="utf-8"))  # drop indentation
    data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + body
    if args.output.endswith(".gz"):
        # mtime=0 / no embedded filename: identical content always gives an identical .gz
        with open(args.output, "wb") as raw, gzip.GzipFile(
                filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
            gz.write(data)
    else:
        with open(args.output, "wb") as fh:
            fh.write(data)
    print(f"Wrote {len(teams)} channels / {total} team fixtures to {args.output}")


if __name__ == "__main__":
    main()

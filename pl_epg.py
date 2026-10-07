#!/usr/bin/env python3
"""
Generate an XMLTV (EPG) file of upcoming fixtures for every Premier League club,
one channel per team, across the league and domestic cups (European competitions are in euro_epg.py).

Data source: ESPN's public site API (no API key needed). The list of clubs is
fetched live from ESPN's Premier League teams endpoint, so promotion/relegation
is picked up automatically each season.

Usage:
    pip install requests
    python pl_epg.py --list-ids                 # show the channel id each team will get
    python pl_epg.py --fill                     # writes pl_fixtures.xml
    python pl_epg.py --fill --id-map ids.json   # override channel ids (see below)

Channel ids default to "<team-slug>.live" (e.g. "arsenal.live", "manchester-city.live");
change the pattern with --id-template "{slug}.uk". To match the tvg-ids already in
your playlist, pass a JSON file mapping team name -> id (or list of ids):
    {"Arsenal": "arsenal.live", "Chelsea": "chelsea.live"}

Cache busting: add --stamp (and --prune, --raw-base URL) to write a new timestamped filename each run.

Times are written in UK local time (Europe/London, handles GMT/BST) using the
XMLTV "YYYYMMDDHHMMSS +ZZZZ" format.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"

# ESPN league slug -> display name. Edit freely; slugs that return nothing are skipped.
COMPETITIONS = {
    "eng.1": "Premier League",
    "eng.fa": "FA Cup",
    "eng.league_cup": "EFL Cup",
    "eng.charity": "FA Community Shield",
}

# Teams whose channel ids should differ from the "<slug>.live" pattern by default.
DEFAULT_ID_MAP = {}

# Display-name tidying (applied to channel names, fixture titles and the default channel ids,
# e.g. "AFC Bournemouth" -> "Bournemouth" -> "bournemouth.live").
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
HEADERS = {"User-Agent": "Mozilla/5.0 (pl-epg script)"}


# ------------------------------------------------------------------ fetching
def get_teams():
    """Return [(espn_team_id, display_name), ...] for the current Premier League."""
    r = requests.get(f"{ESPN}/eng.1/teams", headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    teams = data["sports"][0]["leagues"][0]["teams"]
    out = [(t["team"]["id"], t["team"]["displayName"]) for t in teams]
    return sorted(out, key=lambda x: x[1])


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


def team_fixtures(team_id, debug_name=None, debug=False):
    """All upcoming, de-duplicated fixtures for one team across all competitions."""
    now = datetime.now(timezone.utc)
    seen, fixtures = set(), []
    for slug, comp_name in COMPETITIONS.items():
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
        if not f["time_tbc"]:
            match_date += start.strftime(" %H:%M")
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


# ------------------------------------------------------------------ output naming
def stamped_name(path):
    """euro_fixtures.xml -> euro_fixtures_20261007_2310.xml (also handles .xml.gz)."""
    import os
    d, base = os.path.split(path)
    for ext in (".xml.gz", ".xml"):
        if base.endswith(ext):
            stem = base[:-len(ext)]
            break
    else:
        stem, ext = os.path.splitext(base)
    stamp = datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M")
    return os.path.join(d, f"{stem}_{stamp}{ext}")


def after_write(args):
    """Prune older stamped copies and print the raw URL (when --stamp / --raw-base are used)."""
    import os
    d, base = os.path.split(args.output)
    d = d or "."
    if args.stamp and args.prune:
        m = re.match(r"^(.*)_\d{8}_\d{4}(\.xml\.gz|\.xml|\.[^.]+)$", base)
        if m:
            pat = re.compile(rf"^{re.escape(m.group(1))}_\d{{8}}_\d{{4}}{re.escape(m.group(2))}$")
            for f in os.listdir(d):
                if f != base and pat.match(f):
                    os.remove(os.path.join(d, f))
                    print(f"Removed old file {f}")
    if args.raw_base:
        print(f"URL for Playlist Labs: {args.raw_base.rstrip('/')}/{base}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="pl_fixtures.xml")
    ap.add_argument("--duration", type=int, default=120, help="Programme length in minutes (default 120)")
    ap.add_argument("--fill", action="store_true",
                    help="Fill gaps between fixtures with daily 'Next match' programmes so every "
                         "channel always has something airing")
    ap.add_argument("--fill-days", type=int, default=3,
                    help="With --fill, only add 'Next match' filler for this many days from today "
                         "(default %(default)s). Keeps the file small; real fixtures are never limited")
    ap.add_argument("--id-template", default="{slug}.live",
                    help="Channel id pattern for teams not in the id map (default: %(default)s)")
    ap.add_argument("--id-map", help="JSON file mapping team name -> channel id (or list of ids)")
    ap.add_argument("--list-ids", action="store_true", help="Print each team's channel id(s) and exit")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--stamp", action="store_true",
                    help="Add the date and time to the output filename (e.g. name_20261007_2310.xml) "
                         "so Playlist Labs sees a new file and bypasses its cache")
    ap.add_argument("--prune", action="store_true",
                    help="With --stamp, delete older stamped copies of this file from the output folder")
    ap.add_argument("--raw-base",
                    help="Folder URL of your raw GitHub files; the full URL of the new file is printed")
    args = ap.parse_args()
    if args.stamp:
        args.output = stamped_name(args.output)

    id_map = load_id_map(args.id_map)
    try:
        teams = get_teams()
    except (requests.RequestException, KeyError, IndexError, ValueError) as e:
        sys.exit(f"Could not fetch the Premier League team list from ESPN: {e}")
    if not teams:
        sys.exit("ESPN returned no Premier League teams.")

    if args.list_ids:
        for _, name in teams:
            print(f"{clean_name(name):28s} {', '.join(channel_ids_for(name, id_map, args.id_template))}")
        return

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda t: team_fixtures(t[0], t[1], args.debug), teams))

    team_data = [(name, fx) for (_, name), fx in zip(teams, results)]
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
    with open(args.output, "wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write(body)
    print(f"Wrote {len(teams)} channels / {total} team fixtures to {args.output}")
    after_write(args)


if __name__ == "__main__":
    main()

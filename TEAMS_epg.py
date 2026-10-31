#!/usr/bin/env python3
"""
TEAMS_epg.py - our own "next game" guide for the NFL, NBA, MLB and NHL team channels (31 Oct 2026), a replacement for
PlaylistLabs' built-in "USA Sports Teams" source, with every time in LONDON time.

Each team channel keeps the id it already has in the playlist (NFL-ArizonaCardinals.us, NBA-LAClippers.us ...) and shows:
    "Next game: Arizona Cardinals at Dallas Cowboys"   sub-title "Sun 1 Nov, 18:00 UK time"
    description: kick-off in UK time, venue and city, TV channel(s), and the last result when the team played in the last 4 days
    "Game on now: ..." while the game is being played (estimated length per sport), then the next "Next game" block.
No game in range: "No game scheduled" (the MLB winter, a bye week beyond the range).

Source: ESPN's public scoreboard, one request per day and league (the same endpoint event_epg.py uses), 4 days back and 21
(NFL) / 14 days ahead. Like the events guide, only the next HORIZON_HOURS are written, in blocks of at most PIECE_HOURS: PlaylistLabs
keeps what it has loaded, so a block must not run for days (a postponed game would linger).
If ESPN can't be read for a league, that league's channels are kept from the previous TEAMS_epg.xml.gz.

Usage:
    python3 TEAMS_epg.py                  # read ESPN, write TEAMS_epg.xml.gz
    python3 TEAMS_epg.py --local DIR      # read DIR/<league>_<YYYYMMDD>.json instead of ESPN (testing)
"""

import argparse
import gzip
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OUTPUT = "TEAMS_epg.xml.gz"
LONDON = ZoneInfo("Europe/London")
ET_ZONE = ZoneInfo("America/New_York")
UA = "Mozilla/5.0 (TEAMS_epg.py)"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{}/scoreboard?dates={}"
# league -> (ESPN path, word for the start, estimated game hours, days ahead to look)
LEAGUES = {"NFL": ("football/nfl", "Kick-off", 3.5, 21), "NBA": ("basketball/nba", "Tip-off", 2.75, 14),
           "NHL": ("hockey/nhl", "Puck drop", 3.0, 14), "MLB": ("baseball/mlb", "First pitch", 3.5, 14)}
DAYS_BACK = 4
HORIZON_HOURS = 48
PIECE_HOURS = 6

TEAMS = [   # (league, tvg-id in the playlist, team name)
    ('NFL', 'NFL-ArizonaCardinals.us', 'Arizona Cardinals'),
    ('NFL', 'NFL-AtlantaFalcons.us', 'Atlanta Falcons'),
    ('NFL', 'NFL-BaltimoreRavens.us', 'Baltimore Ravens'),
    ('NFL', 'NFL-BuffaloBills.us', 'Buffalo Bills'),
    ('NFL', 'NFL-CarolinaPanthers.us', 'Carolina Panthers'),
    ('NFL', 'NFL-ChicagoBears.us', 'Chicago Bears'),
    ('NFL', 'NFL-CincinnatiBengals.us', 'Cincinnati Bengals'),
    ('NFL', 'NFL-ClevelandBrowns.us', 'Cleveland Browns'),
    ('NFL', 'NFL-DallasCowboys.us', 'Dallas Cowboys'),
    ('NFL', 'NFL-DenverBroncos.us', 'Denver Broncos'),
    ('NFL', 'NFL-DetroitLions.us', 'Detroit Lions'),
    ('NFL', 'NFL-GreenBayPackers.us', 'Green Bay Packers'),
    ('NFL', 'NFL-HoustonTexans.us', 'Houston Texans'),
    ('NFL', 'NFL-IndianapolisColts.us', 'Indianapolis Colts'),
    ('NFL', 'NFL-JacksonvilleJaguars.us', 'Jacksonville Jaguars'),
    ('NFL', 'NFL-KansasCityChiefs.us', 'Kansas City Chiefs'),
    ('NFL', 'NFL-LasVegasRaiders.us', 'Las Vegas Raiders'),
    ('NFL', 'NFL-LosAngelesChargers.us', 'Los Angeles Chargers'),
    ('NFL', 'NFL-LosAngelesRams.us', 'Los Angeles Rams'),
    ('NFL', 'NFL-MiamiDolphins.us', 'Miami Dolphins'),
    ('NFL', 'NFL-MinnesotaVikings.us', 'Minnesota Vikings'),
    ('NFL', 'NFL-NewEnglandPatriots.us', 'New England Patriots'),
    ('NFL', 'NFL-NewOrleansSaints.us', 'New Orleans Saints'),
    ('NFL', 'NFL-NewYorkGiants.us', 'New York Giants'),
    ('NFL', 'NFL-NewYorkJets.us', 'New York Jets'),
    ('NFL', 'NFL-PhiladelphiaEagles.us', 'Philadelphia Eagles'),
    ('NFL', 'NFL-PittsburghSteelers.us', 'Pittsburgh Steelers'),
    ('NFL', 'NFL-SanFrancisco49ers.us', 'San Francisco 49ers'),
    ('NFL', 'NFL-SeattleSeahawks.us', 'Seattle Seahawks'),
    ('NFL', 'NFL-TampaBayBuccaneers.us', 'Tampa Bay Buccaneers'),
    ('NFL', 'NFL-TennesseeTitans.us', 'Tennessee Titans'),
    ('NFL', 'NFL-WashingtonCommanders.us', 'Washington Commanders'),
    ('NBA', 'NBA-AtlantaHawks.us', 'Atlanta Hawks'),
    ('NBA', 'NBA-BostonCeltics.us', 'Boston Celtics'),
    ('NBA', 'NBA-BrooklynNets.us', 'Brooklyn Nets'),
    ('NBA', 'NBA-CharlotteHornets.us', 'Charlotte Hornets'),
    ('NBA', 'NBA-ChicagoBulls.us', 'Chicago Bulls'),
    ('NBA', 'NBA-ClevelandCavaliers.us', 'Cleveland Cavaliers'),
    ('NBA', 'NBA-DallasMavericks.us', 'Dallas Mavericks'),
    ('NBA', 'NBA-DenverNuggets.us', 'Denver Nuggets'),
    ('NBA', 'NBA-DetroitPistons.us', 'Detroit Pistons'),
    ('NBA', 'NBA-GoldenStateWarriors.us', 'Golden State Warriors'),
    ('NBA', 'NBA-HoustonRockets.us', 'Houston Rockets'),
    ('NBA', 'NBA-IndianaPacers.us', 'Indiana Pacers'),
    ('NBA', 'NBA-LAClippers.us', 'Los Angeles Clippers'),
    ('NBA', 'NBA-LosAngelesLakers.us', 'Los Angeles Lakers'),
    ('NBA', 'NBA-MemphisGrizzlies.us', 'Memphis Grizzlies'),
    ('NBA', 'NBA-MiamiHeat.us', 'Miami Heat'),
    ('NBA', 'NBA-MilwaukeeBucks.us', 'Milwaukee Bucks'),
    ('NBA', 'NBA-MinnesotaTimberwolves.us', 'Minnesota Timberwolves'),
    ('NBA', 'NBA-NewOrleansPelicans.us', 'New Orleans Pelicans'),
    ('NBA', 'NBA-NewYorkKnicks.us', 'New York Knicks'),
    ('NBA', 'NBA-OklahomaCityThunder.us', 'Oklahoma City Thunder'),
    ('NBA', 'NBA-OrlandoMagic.us', 'Orlando Magic'),
    ('NBA', 'NBA-Philadelphia76ers.us', 'Philadelphia 76ers'),
    ('NBA', 'NBA-PhoenixSuns.us', 'Phoenix Suns'),
    ('NBA', 'NBA-PortlandTrailBlazers.us', 'Portland Trail Blazers'),
    ('NBA', 'NBA-SacramentoKings.us', 'Sacramento Kings'),
    ('NBA', 'NBA-SanAntonioSpurs.us', 'San Antonio Spurs'),
    ('NBA', 'NBA-TorontoRaptors.us', 'Toronto Raptors'),
    ('NBA', 'NBA-UtahJazz.us', 'Utah Jazz'),
    ('NBA', 'NBA-WashingtonWizards.us', 'Washington Wizards'),
    ('MLB', 'MLB-ArizonaDiamondbacks.us', 'Arizona Diamondbacks'),
    ('MLB', 'MLB-AtlantaBraves.us', 'Atlanta Braves'),
    ('MLB', 'MLB-BaltimoreOrioles.us', 'Baltimore Orioles'),
    ('MLB', 'MLB-BostonRedSox.us', 'Boston Red Sox'),
    ('MLB', 'MLB-ChicagoCubs.us', 'Chicago Cubs'),
    ('MLB', 'MLB-CincinnatiReds.us', 'Cincinnati Reds'),
    ('MLB', 'MLB-ClevelandGuardians.us', 'Cleveland Guardians'),
    ('MLB', 'MLB-ColoradoRockies.us', 'Colorado Rockies'),
    ('MLB', 'MLB-ChicagoWhiteSox.us', 'Chicago White Sox'),
    ('MLB', 'MLB-DetroitTigers.us', 'Detroit Tigers'),
    ('MLB', 'MLB-HoustonAstros.us', 'Houston Astros'),
    ('MLB', 'MLB-KansasCityRoyals.us', 'Kansas City Royals'),
    ('MLB', 'MLB-LosAngelesAngels.us', 'Los Angeles Angels'),
    ('MLB', 'MLB-LosAngelesDodgers.us', 'Los Angeles Dodgers'),
    ('MLB', 'MLB-MiamiMarlins.us', 'Miami Marlins'),
    ('MLB', 'MLB-MilwaukeeBrewers.us', 'Milwaukee Brewers'),
    ('MLB', 'MLB-MinnesotaTwins.us', 'Minnesota Twins'),
    ('MLB', 'MLB-NewYorkMets.us', 'New York Mets'),
    ('MLB', 'MLB-NewYorkYankees.us', 'New York Yankees'),
    ('MLB', 'MLB-Athletics.us', 'Athletics'),
    ('MLB', 'MLB-PhiladelphiaPhillies.us', 'Philadelphia Phillies'),
    ('MLB', 'MLB-PittsburghPirates.us', 'Pittsburgh Pirates'),
    ('MLB', 'MLB-SanDiegoPadres.us', 'San Diego Padres'),
    ('MLB', 'MLB-SeattleMariners.us', 'Seattle Mariners'),
    ('MLB', 'MLB-SanFranciscoGiants.us', 'San Francisco Giants'),
    ('MLB', 'MLB-St.LouisCardinals.us', 'St. Louis Cardinals'),
    ('MLB', 'MLB-TampaBayRays.us', 'Tampa Bay Rays'),
    ('MLB', 'MLB-TexasRangers.us', 'Texas Rangers'),
    ('MLB', 'MLB-TorontoBlueJays.us', 'Toronto Blue Jays'),
    ('MLB', 'MLB-WashingtonNationals.us', 'Washington Nationals'),
    ('NHL', 'NHL-AnaheimDucks.us', 'Anaheim Ducks'),
    ('NHL', 'NHL-BostonBruins.us', 'Boston Bruins'),
    ('NHL', 'NHL-BuffaloSabres.us', 'Buffalo Sabres'),
    ('NHL', 'NHL-CalgaryFlames.us', 'Calgary Flames'),
    ('NHL', 'NHL-CarolinaHurricanes.us', 'Carolina Hurricanes'),
    ('NHL', 'NHL-ChicagoBlackhawks.us', 'Chicago Blackhawks'),
    ('NHL', 'NHL-ColoradoAvalanche.us', 'Colorado Avalanche'),
    ('NHL', 'NHL-ColumbusBlueJackets.us', 'Columbus Blue Jackets'),
    ('NHL', 'NHL-DallasStars.us', 'Dallas Stars'),
    ('NHL', 'NHL-DetroitRedWings.us', 'Detroit Red Wings'),
    ('NHL', 'NHL-EdmontonOilers.us', 'Edmonton Oilers'),
    ('NHL', 'NHL-FloridaPanthers.us', 'Florida Panthers'),
    ('NHL', 'NHL-LosAngelesKings.us', 'Los Angeles Kings'),
    ('NHL', 'NHL-MinnesotaWild.us', 'Minnesota Wild'),
    ('NHL', 'NHL-MontrealCanadiens.us', 'Montreal Canadiens'),
    ('NHL', 'NHL-NashvillePredators.us', 'Nashville Predators'),
    ('NHL', 'NHL-NewJerseyDevils.us', 'New Jersey Devils'),
    ('NHL', 'NHL-NewYorkIslanders.us', 'New York Islanders'),
    ('NHL', 'NHL-NewYorkRangers.us', 'New York Rangers'),
    ('NHL', 'NHL-OttawaSenators.us', 'Ottawa Senators'),
    ('NHL', 'NHL-PhiladelphiaFlyers.us', 'Philadelphia Flyers'),
    ('NHL', 'NHL-PittsburghPenguins.us', 'Pittsburgh Penguins'),
    ('NHL', 'NHL-SanJoseSharks.us', 'San Jose Sharks'),
    ('NHL', 'NHL-SeattleKraken.us', 'Seattle Kraken'),
    ('NHL', 'NHL-St.LouisBlues.us', 'St. Louis Blues'),
    ('NHL', 'NHL-TampaBayLightning.us', 'Tampa Bay Lightning'),
    ('NHL', 'NHL-TorontoMapleLeafs.us', 'Toronto Maple Leafs'),
    ('NHL', 'NHL-UtahMammoth.us', 'Utah Mammoth'),
    ('NHL', 'NHL-VancouverCanucks.us', 'Vancouver Canucks'),
    ('NHL', 'NHL-VegasGoldenKnights.us', 'Vegas Golden Knights'),
    ('NHL', 'NHL-WashingtonCapitals.us', 'Washington Capitals'),
    ('NHL', 'NHL-WinnipegJets.us', 'Winnipeg Jets'),
]


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def fetch_day(league, day, local):
    path = LEAGUES[league][0]
    if local:
        p = os.path.join(local, f"{league}_{day:%Y%m%d}.json")
        return json.load(open(p, encoding="utf-8")).get("events") or [] if os.path.exists(p) else None
    url = ESPN_SCOREBOARD.format(path, f"{day:%Y%m%d}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return json.loads(r.read().decode("utf-8")).get("events") or []
        except Exception as err:
            last = err
            time.sleep(1.5 * (attempt + 1))
    print(f"  WARNING: {league} {day} not available ({last})", file=sys.stderr)
    return None


def team_lookup(league):
    mine = [(i, n, norm(n)) for lg, i, n in TEAMS if lg == league]

    def find(team):
        for key in ("displayName", "shortDisplayName"):
            full = norm(team.get(key, ""))
            for i, n, nn in mine:
                if full and nn == full:
                    return i
        nick = norm(team.get("name", ""))
        if len(nick) >= 4:
            hits = [i for i, n, nn in mine if nn.endswith(nick)]
            if len(hits) == 1:
                return hits[0]
        loc = norm(team.get("location", ""))
        full = norm(team.get("displayName", ""))
        hits = [i for i, n, nn in mine if full and (full in nn or nn in full)]
        return hits[0] if len(hits) == 1 else None
    return find


def parse_game(ev):
    """ESPN scoreboard event -> dict, or None."""
    try:
        ko = datetime.strptime(ev["date"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        comp = ev["competitions"][0]
        sides = {}
        for c in comp["competitors"]:
            sides[c.get("homeAway")] = {"team": c.get("team") or {}, "score": c.get("score")}
        if "home" not in sides or "away" not in sides:
            return None
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    venue = comp.get("venue") or {}
    addr = venue.get("address") or {}
    where = ", ".join(x for x in (venue.get("fullName"), addr.get("city"), addr.get("state")) if x)
    tv = []
    for b in comp.get("broadcasts") or []:
        tv += [n for n in (b.get("names") or []) if n]
    for g in comp.get("geoBroadcasts") or []:
        n = (g.get("media") or {}).get("shortName")
        if n:
            tv.append(n)
    st = ((ev.get("status") or comp.get("status") or {}).get("type")) or {}
    return {"id": ev.get("id"), "ko": ko, "home": sides["home"], "away": sides["away"], "where": where,
            "tv": list(dict.fromkeys(tv)), "completed": bool(st.get("completed")), "state": st.get("state") or "",
            "neutral": bool(comp.get("neutralSite"))}


def uk(dt):
    d = dt.astimezone(LONDON)
    return f"{d:%a} {d.day} {d:%b}, {d:%H:%M}"


def name_of(side):
    return side["team"].get("displayName") or side["team"].get("name") or "TBD"


def result_line(g):
    a, h = g["away"], g["home"]
    sa, sh = a.get("score"), h.get("score")
    if sa is None or sh is None:
        return ""
    return f"Last game: {name_of(a)} {sa} - {sh} {name_of(h)} (final)."


def add(tv, cid, start, stop, title, sub, desc):
    fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S +0000")
    p = ET.SubElement(tv, "programme", {"start": fmt(start), "stop": fmt(stop), "channel": cid})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    if desc:
        ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    ET.SubElement(p, "category", {"lang": "en"}).text = "Sports"


def pieces(start, stop):
    t = start
    while t < stop:
        nxt = min(t + timedelta(hours=PIECE_HOURS), stop)
        yield t, nxt
        t = nxt


def build_team(tv, cid, league, games, now, horizon):
    word, hours = LEAGUES[league][1], LEAGUES[league][2]
    dur = timedelta(hours=hours)
    games = sorted(games, key=lambda g: g["ko"])
    past = [g for g in games if g["completed"] and g["ko"] <= now]
    last = result_line(past[-1]) if past else ""
    t = now.replace(minute=0, second=0, microsecond=0)
    while t < horizon:
        active = next((g for g in games if not g["completed"] and g["ko"] <= t < g["ko"] + dur), None)
        if active:
            end = min(active["ko"] + dur, horizon)
            title = f"Game on now: {name_of(active['away'])} at {name_of(active['home'])}"
            desc = (f"{word} was {uk(active['ko'])} UK time. {active['where']}." +
                    (f" TV: {', '.join(active['tv'])}." if active["tv"] else "")).replace("..", ".")
            for a, b in pieces(t, end):
                add(tv, cid, a, b, title, f"Started {active['ko'].astimezone(LONDON):%H:%M} UK time", desc)
            t = end
            continue
        nxt = next((g for g in games if not g["completed"] and g["ko"] > t), None)
        end = min(nxt["ko"], horizon) if nxt else horizon
        if end <= t:
            end = min(t + timedelta(hours=1), horizon)
        if nxt:
            title = f"Next game: {name_of(nxt['away'])} at {name_of(nxt['home'])}"
            sub = uk(nxt["ko"]) + " UK time"
            desc = f"{word} {uk(nxt['ko'])} UK time." + (f" {nxt['where']}." if nxt["where"] else "") + \
                   (f" TV: {', '.join(nxt['tv'])}." if nxt["tv"] else "") + (f" {last}" if last else "")
        else:
            title, sub = "No game scheduled", f"None in the next {LEAGUES[league][3]} days"
            desc = (f"No {league} game is listed for this team in the next {LEAGUES[league][3]} days." +
                    (f" {last}" if last else ""))
        for a, b in pieces(t, end):
            add(tv, cid, a, b, title, sub, desc)
        t = end


def previous_guide(path, now):
    progs, names = {}, {}
    try:
        with gzip.open(path, "rb") as f:
            root = ET.parse(f).getroot()
    except (OSError, ET.ParseError, EOFError):
        return progs
    for p in root.iter("programme"):
        try:
            stop = datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
        except (TypeError, ValueError):
            continue
        if stop > now:
            progs.setdefault(p.get("channel"), []).append(p)
    return progs


def write_xml(tv, path):
    ET.indent(tv, space=" ")
    text = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
            + ET.tostring(tv, encoding="unicode") + "\n").encode("utf-8")
    inner = os.path.basename(path)[:-3] if path.endswith(".gz") else path
    with open(path, "wb") as raw, gzip.GzipFile(filename=inner, mode="wb", fileobj=raw, mtime=0, compresslevel=9) as f:
        f.write(text)
    with gzip.open(path, "rb") as f:
        if ET.parse(f).getroot().tag != "tv":
            sys.exit(f"ERROR: {path} did not write correctly")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--local")
    ap.add_argument("--out", default=OUTPUT)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=HORIZON_HOURS)
    prev = previous_guide(args.out, now)
    tv = ET.Element("tv", {"generator-info-name": "TEAMS_epg.py", "source-info-name": "ESPN scoreboards"})
    for lg, cid, nm in TEAMS:
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = nm
    total = 0
    for league, (path, word, hours, ahead) in LEAGUES.items():
        today = datetime.now(ET_ZONE).date()
        days = [today + timedelta(days=d) for d in range(-DAYS_BACK, ahead + 1)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda d: fetch_day(league, d, args.local), days))
        mine = [(i, n) for lg, i, n in TEAMS if lg == league]
        if all(r is None for r in results):
            kept = 0
            for cid, nm in mine:
                for p in prev.get(cid, []):
                    tv.append(p)
                    kept += 1
            print(f"{league}: ESPN NOT AVAILABLE this run - {len(mine)} channels kept from the previous guide ({kept} programmes)")
            continue
        find = team_lookup(league)
        by_team, seen, unmatched = {}, set(), set()
        for evs in results:
            for ev in evs or []:
                g = parse_game(ev)
                if not g or g["id"] in seen:
                    continue
                seen.add(g["id"])
                for side in (g["home"], g["away"]):
                    cid = find(side["team"])
                    if cid:
                        by_team.setdefault(cid, []).append(g)
                    else:
                        unmatched.add(name_of(side))
        for cid, nm in mine:
            build_team(tv, cid, league, by_team.get(cid, []), now, horizon)
        n = sum(len(v) for v in by_team.values())
        print(f"{league}: {len(seen)} games, {len(by_team)} of {len(mine)} teams have a game in range"
              + (f" - ESPN teams not matched to a channel: {', '.join(sorted(unmatched))}" if unmatched else ""))
    total = len(tv.findall("programme"))
    write_xml(tv, args.out)
    print(f"\nWrote {args.out}: {len(TEAMS)} channels, {total} programmes")


if __name__ == "__main__":
    main()

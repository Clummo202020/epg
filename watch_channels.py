#!/usr/bin/env python3
"""
watch_channels.py - the channels that are named in "This match / game is available on ..." (17 Nov 2026, user request).

Shared by football_epg.py (football matches) and TEAMS_epg.py (NFL / NBA / NHL / MLB games), so the list lives in ONE place.
A channel is named when its own listing in our guides is on air at the match and names both teams (the test is in each script).
The listings come from our own guides in this folder (SPORT_epg.xml.gz, USA_epg.xml.gz, CANADA_epg.xml.gz), else from GitHub.

To add or remove a channel: edit CHANNELS below (id as written in the guide, the name shown in the sentence, the family).
The family only decides the ORDER the names appear in (FAMILIES). Pay-per-view / Box Office channels are NOT listed on purpose
(user, 17 Nov 2026: anything that costs extra is not to be listed).

This file must sit in the main folder next to football_epg.py and TEAMS_epg.py. If it is missing or breaks, the scripts carry on
without the new sentence (they never fail because of it).
"""

import gzip
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://raw.githubusercontent.com/Clummo202020/epg/main/"
GUIDE_FILES = ("SPORT_epg.xml.gz", "USA_epg.xml.gz", "CANADA_epg.xml.gz")
UA = {"User-Agent": "Mozilla/5.0 (watch_channels.py)"}

# order the families are named in the sentence: UK free-to-air, Ireland, Sky, TNT, Premier Sports, Prime (added by football_epg.py), then overseas
FAMILIES = ["fta", "rte", "virgin", "sky", "tnt", "premier", "prime", "nz", "sg", "bein", "cy", "usnb", "in", "us", "ca", "hk"]      # 19 Nov 2026 (user): Now (Hong Kong) last

_SKY = [("MainEvent", "Main Event"), ("MainEvent4K", "Main Event 4K"), ("PremierLeague", "Premier League"), ("Football", "Football"),
        ("Action", "Action"), ("Mix", "Mix"), ("NFL", "NFL"), ("Golf", "Golf"), ("Cricket", "Cricket"), ("F1", "F1"), ("F14K", "F1 4K"),
        ("Racing", "Racing"), ("Tennis", "Tennis"), ("UHD1", "UHD 1"), ("UHD2", "UHD 2")]

CHANNELS = (
    [("UK.BBCOne", "BBC One", "fta"), ("UK.BBCTwo", "BBC Two", "fta"), ("UK.ITV1", "ITV1", "fta"), ("UK.ITV4", "ITV4", "fta"),
     ("UK.Channel4", "Channel 4", "fta"), ("UK.Channel5", "Channel 5", "fta"),
     ("IE.RTEOne", "RTÉ One", "rte"), ("IE.RTE2", "RTÉ2", "rte"),
     ("IE.VirginMediaOne", "Virgin Media One", "virgin"), ("IE.VirginMediaTwo", "Virgin Media Two", "virgin"),
     ("IE.VirginMediaThree", "Virgin Media Three", "virgin"), ("IE.VirginMediaFour", "Virgin Media Four", "virgin")]
    + [(f"UK.SkySports{cid}", f"Sky Sports {name}", "sky") for cid, name in _SKY]          # all Sky Sports UK except News and Box Office
    + [("UK.SkySportsPlus", "Sky Sports+", "sky")]
    + [(f"UK.TNTSports{n}", f"TNT Sports {n}", "tnt") for n in range(1, 5)] + [("UK.TNTSportsUltimate", "TNT Sports Ultimate", "tnt")]      # 19 Nov 2026 (user): TNT Sports 1 to 4 and Ultimate only
    + [("UK.PremierSports1", "Premier Sports 1 (UK)", "premier"), ("UK.PremierSports2", "Premier Sports 2 (UK)", "premier"),      # UK pair added 17 Nov (user)
       ("IE.PremierSports1", "Premier Sports 1 (Ireland)", "premier"), ("IE.PremierSports2", "Premier Sports 2 (Ireland)", "premier")]
    + [(f"NZ.SkySport{n}NZ", f"Sky Sport {n} NZ", "nz") for n in range(1, 10)] + [("NZ.SkySportSelectNZ", "Sky Sport Select NZ", "nz")]
    # NZ.SkySportPremierLeagueNZ is the same channel as Sky Sport 8 NZ (user, 17 Nov): named once, as Sky Sport 8 NZ
    + [(f"SG.HubPremier{n}", f"Hub Premier {n}", "sg") for n in range(1, 7)] + [(f"SG.HubSports{n}", f"Hub Sports {n}", "sg") for n in range(1, 9)]
    # 18 Nov 2026 (user): the provider dropped Now Sports; only Now Sports 4K and Now Premier League 1-7 are kept (Now Sports 1, 2 and 641 removed)
    + [("HK.NowSports4K1", "Now Sports 4K", "hk")]
    + [(f"HK.NowSportsPL{n}", f"Now Premier League {n}", "hk") for n in range(1, 8)]
    + [(f"{c}.beINSPORTS{n}", f"beIN Sports {name} {n}", "bein")        # 19 Nov 2026 (user): beIN Sports Singapore, Hong Kong, Malaysia, Indonesia (good for the Champions League)
       for c, name, top in (("SG", "Singapore", 5), ("HK", "Hong Kong", 6), ("MY", "Malaysia", 3), ("ID", "Indonesia", 2)) for n in range(1, top + 1)]
    + [("CY.CytavisionSports3", "Cytavision Sport 3", "cy")]          # 19 Nov 2026 (user): Cyprus; NOT the RealTime id
    + [("IN.SonySportsTen1", "Sony Sports Ten 1", "in"), ("IN.SonySportsTen2", "Sony Sports Ten 2", "in"), ("IN.SonySportsTen5", "Sony Sports Ten 5", "in"),
       ("IN.StarSportsSelect1", "Star Sports Select 1", "in"), ("IN.StarSportsSelect2", "Star Sports Select 2", "in")]       # + Sony Ten 1, Star Sports Select 1 / 2 (user, 17 Nov)
    + [("US.NBC", "NBC", "usnb"), ("US.USANetwork", "USA Network", "usnb")]      # 19 Nov 2026 (user): NBC and USA Network listed before the India channels
    + [("US.CBSSportsNetwork", "CBS Sports Network", "us"), ("US.CBSSportsGolazo", "CBS Sports Golazo", "us")]
    # 17 Nov (user): the main US networks and sports channels, for the Teams guide (not the Spanish-language ones, not RedZone)
    + [("US.CBS", "CBS", "us"), ("US.ABC", "ABC", "us"), ("US.FOX", "FOX", "us"), ("US.ESPN", "ESPN", "us"), ("US.ESPN2", "ESPN2", "us"),
       ("US.FS1", "FS1", "us"), ("US.TNT", "TNT", "us"), ("US.TBS", "TBS", "us"), ("US.NFLNetwork", "NFL Network", "us"),
       ("US.NBATV", "NBA TV", "us"), ("US.MLBNetwork", "MLB Network", "us"), ("US.NHLNetwork", "NHL Network", "us")]
    + [("CA.CTVMontreal", "CTV", "ca")]         # CTV (NFL, Super Bowl ...): needs the CA.CTVMontreal line in USA_epg.py's CA_CHANNELS
    + [(f"CA.TSN{n}", f"TSN{n}", "ca") for n in range(1, 6)]
    + [("CA.SportsnetOne", "Sportsnet One", "ca"), ("CA.SportsnetEast", "Sportsnet East", "ca"), ("CA.SportsnetWest", "Sportsnet West", "ca"),
       ("CA.SportsnetOntario", "Sportsnet Ontario", "ca"), ("CA.SportsnetPacific", "Sportsnet Pacific", "ca"),
       ("CA.SportsnetWorld", "Sportsnet World", "ca"), ("CA.Sportsnet360", "Sportsnet 360", "ca")])


def _read_guide(fname):
    """One of our guides as an XML root (local copy next to this file, else GitHub), or None."""
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    try:
        if os.path.exists(local):
            with open(local, "rb") as f:
                raw = f.read()
        else:
            req = urllib.request.Request(BASE_URL + fname, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return ET.fromstring(raw)
    except Exception as e:                 # one guide missing = its channels are simply not named
        print(f"  WARNING: watch_channels could not read {fname} ({e})")
        return None


def load_listings(sport_root=None):
    """{channel id: [(start, stop, text)]} for the channels in CHANNELS, from the SPORT, USA and CANADA guides.
    sport_root = an already parsed SPORT guide (football_epg.py has one), to save reading it twice."""
    wanted = {cid for cid, _, _ in CHANNELS}
    out = {}
    for fname in GUIDE_FILES:
        root = sport_root if (fname == GUIDE_FILES[0] and sport_root is not None) else _read_guide(fname)
        if root is None:
            continue
        for p in root.iter("programme"):
            cid = p.get("channel")
            if cid not in wanted:
                continue
            try:
                start = datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
                stop = datetime.strptime(p.get("stop"), "%Y%m%d%H%M%S %z")
            except (TypeError, ValueError):
                continue
            text = " ".join((e.text or "") for e in p if e.tag in ("title", "sub-title", "desc"))
            out.setdefault(cid, []).append((start, stop, text))
    return out


_NUMBERED = re.compile(r"^(?P<pre>.+?)(?<!\d)(?P<sp> ?)(?P<n>\d{1,2})(?P<suf>(?: NZ| \((?:UK|Ireland)\))?)$")
# which broadcaster a channel name belongs to (the first prefix that matches); anything else is its own broadcaster
BROADCASTERS = (("Sky Sports", "sky"), ("Sky Sport ", "sky-nz"), ("TNT Sports", "tnt"), ("Hub ", "hub"), ("beIN Sports Singapore", "bein-sg"), ("beIN Sports Hong Kong", "bein-hk"), ("beIN Sports Malaysia", "bein-my"), ("beIN Sports Indonesia", "bein-id"), ("Now ", "now"),
                ("Virgin Media", "virgin"), ("RT\u00c9", "rte"), ("Premier Sports", "premier"), ("Sony Sports", "sony"), ("Star Sports", "star"),
                ("Sportsnet", "sportsnet"), ("TSN", "tsn"), ("CBS Sports", "cbs"), ("BBC", "bbc"), ("ITV", "itv"))


def broadcaster(name):
    for prefix, key in BROADCASTERS:
        if name.startswith(prefix):
            return key
    return name


def group_numbered(names):
    """Numbered channels of one family are joined (17 Nov 2026, user): 'Hub Premier 1', 'Hub Premier 2' -> 'Hub Premier 1 & 2';
    'TSN1', 'TSN3', 'TSN4' -> 'TSN1, 3 & 4'; 'Sky Sport 8 NZ', 'Sky Sport 9 NZ' -> 'Sky Sport 8 & 9 NZ'. The group sits where its first channel
    was. Names alone in their family, or with no number at the end, are left as they are."""
    groups = {}
    for n in names:
        m = _NUMBERED.match(n)
        if m:
            groups.setdefault((m["pre"], m["sp"], m["suf"]), []).append(m["n"])
    out, done = [], set()
    for n in names:
        m = _NUMBERED.match(n)
        key = (m["pre"], m["sp"], m["suf"]) if m else None
        if not m or len(groups[key]) < 2:
            out.append(n)
        elif key not in done:
            done.add(key)
            nums = groups[key]
            joined = nums[0] if len(nums) == 1 else ", ".join(nums[:-1]) + " & " + nums[-1]
            out.append(f"{key[0]}{key[1]}{joined}{key[2]}")
    return out


SHORTEN_PREFIX = {"sky": "Sky Sports ", "sportsnet": "Sportsnet "}      # "now" removed 18 Nov 2026: "Now Sports 4K" and "Now Premier League 1 & 2" keep their full names


def shorten_sky(names, prefix="Sky Sports "):
    """With two or more channels of one broadcaster sharing a prefix only the first keeps it - 'Sky Sports Main Event, Main Event 4K & Premier
    League', 'Sportsnet One, East, West, Ontario & Pacific', 'Now Sports 4K 1, Premier League 1 & 2' (17 Nov 2026, user: shorten long lists).
    "Sky Sports+" and the NZ "Sky Sport N NZ" channels are not touched."""
    hit = [i for i, n in enumerate(names) if n.startswith(prefix)]
    if len(hit) < 2:
        return names
    return [n[len(prefix):] if i in hit[1:] else n for i, n in enumerate(names)]


def _one_broadcaster(names):
    """The channels of ONE broadcaster, joined with '&': 'Hub Premier 1 & 2'; 'Sky Sports Main Event, Main Event 4K & Premier League'."""
    names = group_numbered(names)
    if broadcaster(names[0]) in SHORTEN_PREFIX:
        names = shorten_sky(names, SHORTEN_PREFIX[broadcaster(names[0])])
    if len(names) == 1:
        return names[0]
    if any(" & " in n for n in names):               # a joined pair already uses '&': plain commas between the rest
        return ", ".join(names)
    return ", ".join(names[:-1]) + " & " + names[-1]


def join_names(names):
    """The sentence's channel list (17 Nov 2026, user): several channels of the SAME broadcaster are joined with '&', different broadcasters
    are separated with 'and' (commas, one 'and' before the last; semicolons when a broadcaster's own group has commas) - 'Sky Sports Main Event, Main Event 4K & Premier League and Hub Premier 1 & 2'. A broadcaster's group sits where its
    first channel was."""
    groups, order = {}, []
    for n in names:
        k = broadcaster(n)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(n)
    parts = [_one_broadcaster(groups[k]) for k in order]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return " and ".join(parts)
    if any("," in x for x in parts):               # commas already used inside a broadcaster's group: semicolons between broadcasters (17 Nov 2026, user)
        return "; ".join(parts[:-1]) + "; and " + parts[-1]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def order_names(by_family):
    """{family: [names]} -> one list in FAMILIES order (families not in FAMILIES go last)."""
    keys = [f for f in FAMILIES if f in by_family] + [f for f in by_family if f not in FAMILIES]
    out = []
    for f in keys:
        for n in by_family[f]:
            if n not in out:
                out.append(n)
    # 17 Nov 2026 (user): a "(UK)" / "(Ireland)" label is only kept when the match is on ONE of the two versions of a channel;
    # on both, the channel is named once with no label ("Premier Sports 1").
    base = lambda n: re.sub(r" \((?:UK|Ireland)\)$", "", n)
    labelled = {}
    for n in out:
        if base(n) != n:
            labelled.setdefault(base(n), []).append(n)
    both = {b for b, ns in labelled.items() if len(ns) > 1}
    res = []
    for n in out:
        n2 = base(n) if base(n) in both else n
        if n2 not in res:
            res.append(n2)
    return res


# ---------------------------------------------------------------------------------------------------------------------------------------
# EVENT-STREAM SERVICES (17 Nov 2026, user): when a match has NO or only ONE channel from CHANNELS above, the events guide (events_epg.xml, in this
# folder) is checked for the match on a Paramount+, Peacock or Stan Sport stream slot, and the SERVICE is named - never the slot number, because the
# two playlists number their slots differently (Continuum STAN04 / Main IPTV MSTAN14) and a slot can change. "This match is available on Peacock and
# Stan Sport." (nothing else found) or "... It is also available on Peacock and Stan Sport." (one other channel). Women's matches are skipped
# (the same club names appear in WSL / NWSL streams). To add a service: one line in EVENT_SERVICES.
# ---------------------------------------------------------------------------------------------------------------------------------------
EVENT_SERVICES = (("Paramount+", re.compile(r"^M?Paramount\d")), ("Peacock", re.compile(r"^M?Peacock\d")), ("Stan Sport", re.compile(r"^M?STAN\d")))
EVENTS_FILE = "events_epg.xml"
_LONDON = ZoneInfo("Europe/London")
_SPANISH = re.compile(r"\(Spanish\)|\bSpanish\b|\ben Espa\u00f1ol|\bEspa\u00f1ol|\ben Espanol|\bTelemundo|\(ES\)|\(Esp\)", re.I)   # Spanish-language duplicate streams (user)
_WOMENS = re.compile(r"\bWSL\b|\bNWSL\b|Women|Lionesses|\bFemminile\b|\bFeminin", re.I)
_TITLE_WHEN = re.compile(r"\((?:\w{3}) (\d{1,2}) (\w{3}), ([^()]+)\)\s*$")
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _clock(text):
    """'Midday' / 'Midnight' / '3pm' / '5:45pm' / '12:30am' -> (hour, minute), or None."""
    t = text.strip().lower()
    if t == "midday":
        return 12, 0
    if t == "midnight":
        return 0, 0
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s?(am|pm)$", t)
    if not m or not 1 <= int(m.group(1)) <= 12:
        return None
    return int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0), int(m.group(2) or 0)


def load_event_slots(root=None):
    """[(service, kick-off UTC, title)] for the real matches on the Paramount+ / Peacock / Stan slots in the events guide. The kick-off is the
    time in the title '(Sat 21 Nov, 3pm)' (UK time); a live block with no time in its title uses its own start. Finished / empty / women's / Spanish-language
    events are left out."""
    root = root if root is not None else _read_guide(EVENTS_FILE)
    out, seen = [], set()
    if root is None:
        return out
    for p in root.iter("programme"):
        cid = p.get("channel") or ""
        service = next((name for name, rx in EVENT_SERVICES if rx.match(cid)), None)
        if not service:
            continue
        title = (p.findtext("title") or "").strip()
        sub = p.findtext("sub-title") or ""
        if not title or title.startswith(("This event", "No ", "Next up")) or _WOMENS.search(title + " " + sub) or _SPANISH.search(title):
            continue
        try:
            block = datetime.strptime(p.get("start"), "%Y%m%d%H%M%S %z")
        except (TypeError, ValueError):
            continue
        m = _TITLE_WHEN.search(title)
        ko = None
        if m and m.group(2).lower()[:3] in _MONTHS and _clock(m.group(3)):
            hh, mm = _clock(m.group(3))
            for year in (block.year, block.year + 1):
                try:
                    cand = datetime(year, _MONTHS[m.group(2).lower()[:3]], int(m.group(1)), hh, mm, tzinfo=_LONDON)
                except ValueError:
                    continue
                if abs((cand - block).days) < 200:
                    ko = cand
                    break
        elif title.startswith("\U0001F534 LIVE:"):
            ko = block                                # a live block starts at the kick-off
        if ko is not None and (service, ko, title) not in seen:        # the same match fills many blocks / slots
            seen.add((service, ko, title))
            out.append((service, ko.astimezone(block.tzinfo), title))
    return out


def event_services_for(ko, teams_match, slots, tolerance_minutes=60):
    """Names of the event-stream services that have this match: `teams_match(title)` says whether the title names both teams, and the
    slot's kick-off must be within `tolerance_minutes` of `ko`. In the order of EVENT_SERVICES, each once."""
    found = []
    for service, sko, title in slots:
        if service in found or abs((sko - ko).total_seconds()) > tolerance_minutes * 60:
            continue
        if teams_match(title):
            found.append(service)
    return [n for n, _ in EVENT_SERVICES if n in found]

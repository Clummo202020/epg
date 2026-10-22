#!/usr/bin/env python3
"""
event_epg.py - XMLTV guide built from the event times in your IPTV stream names.

Event streams are named with their start time, e.g.
    US (Peacock 003) | Celtics vs. Pistons (2026-10-20 14:50:05)
    AU (STAN 08) | Manchester City v AEK Athens  UEFA Champions League ... (2026-10-21 05:55:15)
    End | College Swimming League - Match 3 | College Swimming League | 2026-10-03 | 00:30 (GMT) | 8K EXCLUSIVE | GB: DAZN PPV 5

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
import os
import re
import sys
import unicodedata
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
PAST_EVENT_HOURS = 2       # an event that has ended still shows for this long
MAX_DAYS_AHEAD = 2         # events further ahead than this get filler until they come into range
FILLER_TITLE = "Stream is live at event time only."
FILLER_DESC = "The next event on this stream will be listed nearer the time."

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
ENDED_FILLER_HOURS = 2         # a stream whose event is over shows filler for this long
# Name sections that are labels, not event information ("8K EXCLUSIVE", "4K", "HD" ...)
JUNK_RE = re.compile(r"(?i)\s*((8K|4K|UHD|FHD|HD|SD)\s*)?(EXCLUSIVE|ONLY)?\s*|\s*(8K|4K|UHD|FHD|HD|SD)\s*")
# "Wed 21 Oct 19:00 EDT (US)" - date and time in one field, no year
DAYTIME_RE = re.compile(r"^(?:[A-Za-z]{3}\s+)?(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{1,2}:\d{2})"
                        r"(?:\s+([A-Z]{2,5}))?(?:\s*\([A-Z]{2}\))?$")
TIME_RE = re.compile(r"^(\d{1,2}:\d{2})(?::\d{2})?\s*(?:\((\w+)\))?$")


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "", text)


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
    """[(home_key, away_key, kick-off datetime UK)] from the football guide, or None."""
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
        out.add((_team_key(m[1]), _team_key(m[2]), ko))
    _FIXTURES = sorted(out, key=lambda r: r[2])
    return _FIXTURES or None


def fixture_date(title, h, mi, now):
    """Kick-off (UK) of the fixture named in `title` at h:mi, from the football guide.
    Returns a datetime, False if the guide is loaded but has no such fixture (match over),
    or None if the football guide isn't available."""
    fx = load_fixtures()
    if fx is None:
        return None
    sides = re.split(r"\s+(?:vs?\.?|-)\s+", title, maxsplit=1, flags=re.I)
    if len(sides) != 2:
        return None
    hk, ak = _team_key(sides[0]), _team_key(sides[1])
    hits = [ko for (fh, fa, ko) in fx if {fh, fa} == {hk, ak}]
    if not hits:
        return False
    same_time = [ko for ko in hits if (ko.hour, ko.minute) == (h, mi)] or hits
    return min(same_time, key=lambda ko: abs(ko - now))


def parse_name(name):
    """{slot_id, slot_name, title, extra, start (UTC)} for an event name, else None."""
    name = re.sub(r"\s+", " ", name or "").strip()

    e = EMPTY_SLOT.match(name)                       # "UEFA | 08 -": no match on this slot yet
    if e:
        label = e["label"].strip()
        return {"name": name, "slot_id": f"{slug(label)}{int(e['num'])}.uk",
                "slot_name": f"{label} | {int(e['num'])}", "title": "", "extra": "", "comp": "",
                "start": datetime.now(timezone.utc) - timedelta(days=1)}   # -> filler only

    k = KICKOFF_ONLY.match(name)                     # UEFA | 28 - A vs B 20:00 pm (UK, today)
    if k:
        h, mi, ap = int(k["h"]), int(k["m"]), (k["ap"] or "").lower()
        if ap.startswith("p") and h < 12:
            h += 12
        elif ap.startswith("a") and h == 12:
            h = 0
        now = datetime.now(LONDON)
        found = fixture_date(k["title"].strip(), h, mi, now)
        if found:                                     # date from the football guide
            local = found
        elif found is False:                          # match no longer listed: it's over
            local = now.replace(hour=h, minute=mi, second=0, microsecond=0) - timedelta(days=1)
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
                return {"name": name, "slot_id": f"{slug(slot_label)}.{cc.lower()}",
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
            return {"name": name, "slot_id": f"{slug(slot_label)}.{cc.lower()}",
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
    """Display names of every #EXTINF line (the text after the last comma)."""
    for line in text.splitlines():
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-name="([^"]*)"', line)
            yield (m.group(1) if m else line.rsplit(",", 1)[-1]).strip()


def uk(dt):
    return dt.astimezone(LONDON)


def xmltv_time(dt):
    return uk(dt).strftime("%Y%m%d%H%M%S %z")


def add_programme(tv, cid, start, stop, title, sub, desc, live=False):
    p = ET.SubElement(tv, "programme", {"start": xmltv_time(start), "stop": xmltv_time(stop),
                                        "channel": cid})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    if desc:
        ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    ET.SubElement(p, "category", {"lang": "en"}).text = "Sports"
    if live:
        ET.SubElement(p, "category", {"lang": "en"}).text = "Live"


def build(events, now):
    tv = ET.Element("tv", {"generator-info-name": "event_epg.py"})
    by_slot, ended = {}, {}
    for ev in events:                       # one event per slot: the next one still to finish
        end = ev["start"] + timedelta(hours=EVENT_HOURS)
        if end + timedelta(hours=PAST_EVENT_HOURS) < now:
            ended.setdefault(ev["slot_id"], ev)
            continue
        cur = by_slot.get(ev["slot_id"])
        if cur is None or ev["start"] < cur["start"]:
            by_slot[ev["slot_id"]] = ev
    ended = {sid: ev for sid, ev in ended.items() if sid not in by_slot}
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
        end = kickoff + timedelta(hours=EVENT_HOURS)
        when = f"{uk(kickoff):%a} {uk(kickoff).day} {uk(kickoff):%b}, {uk(kickoff):%H:%M}"
        desc = f"{ev['title']}." + (f" {ev['extra']}." if ev["extra"] else "") + \
               f" Starts {when} UK time."
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
    t0 = now.replace(minute=0, second=0, microsecond=0)
    t0 -= timedelta(hours=uk(t0).hour % BLOCK_HOURS)
    for sid in sorted(ended):    # kept short, so the slot's next event can follow it
        t = t0
        while t < now + timedelta(hours=ENDED_FILLER_HOURS):
            b = t + timedelta(hours=BLOCK_HOURS)
            add_programme(tv, sid, t, b, FILLER_TITLE, None, FILLER_DESC)
            count += 1
            t = b
    return tv, len(by_slot) + len(ended), count


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
    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(args.out, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {args.out}: {chans} channels, {progs} programmes")


if __name__ == "__main__":
    main()

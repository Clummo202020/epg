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
    * the event itself (EVENT_HOURS long) with "🔴 LIVE" as the secondary title
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

# "US (Peacock 003) | Title (2026-10-20 14:50:05)"
SLOT_FIRST = re.compile(
    r"^\s*(?P<cc>[A-Z]{2})\s*\((?P<slot>[^)]*)\)\s*\|\s*(?P<title>.*?)\s*"
    r"\((?P<date>\d{4}-\d{2}-\d{2})[ T](?P<time>\d{1,2}:\d{2})(?::\d{2})?\)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^(\d{1,2}:\d{2})(?::\d{2})?\s*(?:\((\w+)\))?$")


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "", text)


def parse_name(name):
    """{slot_id, slot_name, title, extra, start (UTC)} for an event name, else None."""
    name = re.sub(r"\s+", " ", name or "").strip()

    m = SLOT_FIRST.match(name)                       # US (Peacock 003) | ... (date time)
    if m:
        tz = ZoneInfo(COUNTRY_TZ.get(m["cc"], "Europe/London"))
        local = datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        return {"slot_id": f"{slug(m['slot'])}.{m['cc'].lower()}",
                "slot_name": f"{m['cc']} ({m['slot']})",
                "title": m["title"].strip(), "extra": "",
                "start": local.astimezone(timezone.utc)}

    parts = [p.strip() for p in name.split("|")]     # End | Title | Comp | date | time (TZ) | ... | GB: SLOT
    if len(parts) >= 4:
        di = next((i for i, p in enumerate(parts) if DATE_RE.match(p)), None)
        ti = next((i for i, p in enumerate(parts) if TIME_RE.match(p)), None)
        slot = next((p for p in reversed(parts) if re.match(r"^[A-Z]{2}:\s*\S", p)), None)
        if di is not None and ti is not None and slot:
            tm = TIME_RE.match(parts[ti])
            cc, slot_label = slot.split(":", 1)
            zone = ABBREV_TZ.get((tm.group(2) or "").upper()) or COUNTRY_TZ.get(cc, "Europe/London")
            local = datetime.strptime(f"{parts[di]} {tm.group(1)}", "%Y-%m-%d %H:%M") \
                .replace(tzinfo=ZoneInfo(zone))
            text = [p for i, p in enumerate(parts) if i not in (di, ti) and p != slot]
            if text and text[0].lower() in STATUS_WORDS:
                text = text[1:]
            title = text[0] if text else slot_label.strip()
            extra = ". ".join(t for t in text[1:] if t)
            return {"slot_id": f"{slug(slot_label)}.{cc.lower()}",
                    "slot_name": f"{cc}: {slot_label.strip()}",
                    "title": title, "extra": extra,
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
    by_slot = {}
    for ev in events:                       # one event per slot: the next one still to finish
        end = ev["start"] + timedelta(hours=EVENT_HOURS)
        if end + timedelta(hours=PAST_EVENT_HOURS) < now:
            continue
        cur = by_slot.get(ev["slot_id"])
        if cur is None or ev["start"] < cur["start"]:
            by_slot[ev["slot_id"]] = ev
    for sid in sorted(by_slot):
        c = ET.SubElement(tv, "channel", {"id": sid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = by_slot[sid]["slot_name"]
    count = 0
    for sid in sorted(by_slot):
        ev = by_slot[sid]
        start, end = ev["start"], ev["start"] + timedelta(hours=EVENT_HOURS)
        when = f"{uk(start):%a} {uk(start).day} {uk(start):%b}, {uk(start):%H:%M}"
        desc = f"{ev['title']}." + (f" {ev['extra']}." if ev["extra"] else "") + \
               f" Starts {when} UK time."
        t = now.replace(minute=0, second=0, microsecond=0)
        t -= timedelta(hours=uk(t).hour % BLOCK_HOURS)
        while t < start:                                   # "Coming up" blocks
            b = min(t + timedelta(hours=BLOCK_HOURS), start)
            add_programme(tv, sid, t, b, f"{ev['title']} ({when})",
                          f"⏭ Coming up {uk(start):%a} {uk(start).day} {uk(start):%b}",
                          f"Coming up: {desc}")
            count += 1
            t = b
        add_programme(tv, sid, start, end, ev["title"], "🔴 LIVE", desc, live=True)
        count += 1
    return tv, len(by_slot), count


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

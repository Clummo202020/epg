#!/usr/bin/env python3
"""
SPORT_search_extra.py - extra channels for the search page only (SPORT_search.html).

They are NOT part of the guide (SPORT_epg.xml.gz) that PlaylistLabs reads. Browsers may not
read epgshare01's files from another site, so this script (run by GitHub Actions) downloads
them, keeps only the channels below, and writes SPORT_search_extra.xml.gz next to the guide,
where the search page can read it.

Source: epgshare01.online ready-made XMLTV files (free, no login), one per country.
Times stay as given (with their offsets); the search page shows UK time.
Titles in another script (Cytavision's Greek) are translated to English with SPORT_epg.py's
translators and its cache, SPORT_translations.json (each text is translated only once).

    python3 SPORT_search_extra.py              # writes SPORT_search_extra.xml.gz
    python3 SPORT_search_extra.py --debug      # also lists programme counts per channel
    python3 SPORT_search_extra.py --no-translate   # keep Greek titles as they are
"""
import argparse
import gzip
import io
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "SPORT_search_extra.xml.gz")
URL = "{scheme}://epgshare01.online/epgshare01/epg_ripper_{file}.xml.gz"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DAYS = 8                      # keep programmes up to this many days ahead

# file -> (ID prefix, {epgshare01 channel id: channel name}); ids sharing a name are one channel
EXTRAS = {
    "UK1": ("UK", {
        "SkySpMainEvHD.uk": "Sky Sports Main Event", "SkySp.PL.HD.uk": "Sky Sports Premier League",
        "SkySp.Fball.HD.uk": "Sky Sports Football", "Sky.Sports.Football.HD.uk": "Sky Sports Football",
        "SkySpCricket.HD.uk": "Sky Sports Cricket", "SkySp.Golf.HD.uk": "Sky Sports Golf",
        "SkySp.F1.HD.uk": "Sky Sports F1", "SkySp.ActionHD.uk": "Sky Sports Action",
        "SkySp.Mix.HD.uk": "Sky Sports Mix", "SkySp.News.HD.uk": "Sky Sports News",
        "SkySp.Racing.HD.uk": "Sky Sports Racing", "SkySp.Tennis.HD.uk": "Sky Sports Tennis",
        "Sky.Sports.NFL.uk": "Sky Sports NFL", "SkySp+HD.uk": "Sky Sports+",
        "SkySpBoxOff.uk": "Sky Sports Box Office", "Sky.Sports.Ultra.HD.1.uk": "Sky Sports Ultra HD 1",
        "Sky.Sports.Ultra.HD.2.uk": "Sky Sports Ultra HD 2",
        **{f"TNT.Sports.{n}.HD.uk": f"TNT Sports {n}" for n in range(1, 11)},
        "TNT.Sports.Ultimate.HD.uk": "TNT Sports Ultimate",
        "TNT.Sport.BoxOffice.HD.uk": "TNT Sports Box Office", "TNTSBoxOff2HD.uk": "TNT Sports Box Office 2",
    }),
    "IE1": ("IE", {"Premier.Sports.1.HD.ie": "Premier Sports 1", "Premier.Sports.1.ie": "Premier Sports 1",
                   "Premier.Sports.2.HD.ie": "Premier Sports 2", "Premier.Sports.2.ie": "Premier Sports 2"}),
    "SG1": ("SG", {f"Hub.Premier.{n}.sg": f"Hub Premier {n}" for n in range(1, 7)}),
    "NZ1": ("NZ", {**{f"Sky.Sport.{n}.nz": f"Sky Sport {n} NZ" for n in range(1, 10)},
                   "Sky.Sport.Premier.League.nz": "Sky Sport Premier League NZ",
                   "Sky.Sport.Select.nz": "Sky Sport Select NZ"}),
    "US2": ("US", {"USA.Network.HD.us2": "USA Network", "NBC.East.Stream.us2": "NBC"}),
    "CA2": ("CA", {"Sportsnet.Ontario.HD.ca2": "Sportsnet Ontario", "Sportsnet.East.HD.ca2": "Sportsnet East",
                   "Sportsnet.West.HD.ca2": "Sportsnet West", "Sportsnet.(Pacific).HD.ca2": "Sportsnet Pacific",
                   "Sportsnet.One.HD.ca2": "Sportsnet One", "Sportsnet.360.HD.ca2": "Sportsnet 360",
                   "Sportsnet.World.HD.ca2": "Sportsnet World", "Sportsnet.4K.ca2": "Sportsnet 4K"}),
    "CY1": ("CY", {**{f"Cytavision.Sports.{n}HD.cy": f"Cytavision Sports {n}" for n in range(1, 9)},
                   "Cytavision.Sports.Premier.League.cy": "Cytavision Sports Premier League"}),
    "MY1": ("MY", {"Astro.Arena.my": "Astro Arena", "Astro.Arena.2.my": "Astro Arena 2",
                   "Astro.Football.my": "Astro Football", "Astro.Premier.League.my": "Astro Premier League",
                   **{f"Astro.Premier.League.{n}.my": f"Astro Premier League {n}" for n in range(2, 6)},
                   "Astro.Grandstand.my": "Astro Grandstand", "Astro.Badminton.my": "Astro Badminton",
                   "Astro.Cricket.my": "Astro Cricket", "Astro.Sports.Plus.my": "Astro Sports Plus",
                   "Astro.Sports.UHD.my": "Astro Sports UHD"}),
}
# Live markers: "Live PL: Nott'm Forest v Arsenal" (Sky UK), "(L) PL: ..." (Astro),
# "... (Live)", "Live: ...", "... [Live]"
LIVE = re.compile(r"^\s*live\b|^\s*\(L\)|\(\s*live\s*\)|\[\s*live\s*\]|\blive\s*$", re.I)
LIVE_STRIP = re.compile(r"^\s*live\b\s*[:\-]?\s*|^\s*\(L\)\s*|\s*\(\s*live\s*\)|\s*\[\s*live\s*\]"
                        r"|\s*[-:]?\s*\blive\s*$", re.I)


def download(file):
    """The decompressed XML of one epgshare01 file, or None (with the reason printed)."""
    why = "no answer"
    for scheme in ("https", "http"):                 # the site's advice: try http if https fails
        for attempt in range(2):
            try:
                req = urllib.request.Request(URL.format(scheme=scheme, file=file), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read()
                return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
            except urllib.error.HTTPError as e:
                why = f"HTTP {e.code} {e.reason}"
                if e.code in (403, 404):
                    break
            except (urllib.error.URLError, TimeoutError, OSError, EOFError) as e:
                why = f"{type(e).__name__}: {e}"[:120]
            time.sleep(3 * (attempt + 1))
    print(f"  WARNING: could not fetch epgshare01 {file}: {why}", file=sys.stderr)
    return None


def stamp(text):
    try:
        return datetime.strptime((text or "")[:20], "%Y%m%d%H%M%S %z")
    except ValueError:
        return None


def first_text(el, tag):
    kids = el.findall(tag)
    best = next((k for k in kids if (k.get("lang") or "").lower().startswith("en")), kids[0] if kids else None)
    return re.sub(r"\s+", " ", (best.text or "") if best is not None else "").strip()


def translate(programmes):
    """Greek (or other non-Latin) titles and sub-titles in English, using SPORT_epg.py's
    translators and cache. If that can't be used, the titles are kept as they are."""
    try:
        sys.path.insert(0, HERE)
        import SPORT_epg as guide
    except Exception as e:                            # never lose the file over a translation
        print(f"  WARNING: translation skipped - SPORT_epg.py could not be used ({type(e).__name__}: {e})",
              file=sys.stderr)
        return programmes
    guide.load_cache()
    texts = {t for p in programmes for t in (p[3], p[4]) if t and guide.FOREIGN.search(t)}
    if texts:
        try:
            guide.translate_all(texts)                # prints its own summary and saves the cache
        except Exception as e:
            print(f"  WARNING: translation stopped ({type(e).__name__}: {e})", file=sys.stderr)
    return [(cid, start, stop, guide.en(title), guide.en(sub) if sub else sub, live)
            for cid, start, stop, title, sub, live in programmes]


def main():
    ap = argparse.ArgumentParser(description="Search-only extra channels from epgshare01.")
    ap.add_argument("--out", default=OUT, help="output file (default SPORT_search_extra.xml.gz)")
    ap.add_argument("--debug", action="store_true", help="list programme counts per channel")
    ap.add_argument("--no-translate", action="store_true", help="keep titles in their own language")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    until = now + timedelta(days=DAYS)
    tv = ET.Element("tv", {"generator-info-name": "SPORT_search_extra.py",
                           "source-info-name": "epgshare01.online (search page only)"})
    channels, programmes, loaded = {}, [], 0
    for file, (prefix, wanted) in EXTRAS.items():
        data = download(file)
        if data is None:
            continue
        loaded += 1
        seen, counts = set(), {}
        try:
            for _, el in ET.iterparse(io.BytesIO(data), events=("end",)):
                if el.tag != "programme":
                    if el.tag == "channel":
                        el.clear()
                    continue
                name = wanted.get(el.get("channel"))
                if name:
                    start, stop = stamp(el.get("start")), stamp(el.get("stop"))
                    title = first_text(el, "title")
                    if start and stop and title and stop > now and start < until:
                        cid = prefix + "." + re.sub(r"[^A-Za-z0-9]+", "", name.replace("+", "Plus"))
                        if (cid, start) not in seen:            # an HD and SD copy: keep one
                            seen.add((cid, start))
                            live = bool(LIVE.search(title))
                            if live:
                                title = LIVE_STRIP.sub("", title).strip() or title
                            channels[cid] = name
                            counts[name] = counts.get(name, 0) + 1
                            programmes.append((cid, start, stop, title, first_text(el, "sub-title"), live))
                el.clear()
        except ET.ParseError as e:
            print(f"  WARNING: epgshare01 {file} could not be read completely ({e})", file=sys.stderr)
        print(f"{file}: {sum(counts.values())} programmes on {len(counts)} channel(s)")
        if args.debug:
            for name in sorted(set(wanted.values())):
                print(f"    {name}: {counts.get(name, 0)}")

    if not programmes:
        print("Nothing found - keeping the previous file (if any).")
        return 0 if loaded else 1
    if not args.no_translate:
        programmes = translate(programmes)
    for cid, name in sorted(channels.items()):
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = name
    for cid, start, stop, title, sub, live in sorted(programmes, key=lambda p: (p[0], p[1])):
        p = ET.SubElement(tv, "programme", {"start": start.strftime("%Y%m%d%H%M%S %z"),
                                            "stop": stop.strftime("%Y%m%d%H%M%S %z"), "channel": cid})
        ET.SubElement(p, "title", {"lang": "en"}).text = title
        if sub and sub != title:
            ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
        ET.SubElement(p, "category", {"lang": "en"}).text = "Sports"
        if live:
            ET.SubElement(p, "category", {"lang": "en"}).text = "Live"
    ET.indent(tv, space=" ")
    text = ('<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tv, encoding="unicode") + "\n").encode()
    with open(args.out, "wb") as raw, gzip.GzipFile(filename=os.path.basename(args.out)[:-3], mode="wb",
                                                   fileobj=raw, mtime=0, compresslevel=9) as f:
        f.write(text)                                  # mtime=0: the file only changes when the data does
    print(f"Wrote {os.path.basename(args.out)}: {len(channels)} channels, {len(programmes)} programmes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

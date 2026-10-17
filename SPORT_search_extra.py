#!/usr/bin/env python3
"""
SPORT_search_extra.py - extra channels for the search page only (SPORT_search.html).

They are NOT part of the guide (SPORT_epg.xml.gz) that PlaylistLabs reads. Browsers may not
read epgshare01's files from another site, so this script (run by GitHub Actions) downloads
them, keeps only the channels below, and writes SPORT_search_extra.xml.gz next to the guide,
where the search page can read it.

Sources:
  - Sky's public TV guide (the one behind sky.com's TV guide; free, no login or key) for
    Sky Sports, TNT Sports and Premier Sports - 7 days ahead, with 4K channels:
      https://awk.epgsky.com/hawk/linear/schedule/20261021/4002,1120     (header X-SkyOTT-Territory: GB)
      https://atlantis.epgsky.com/as/schedule/20261021/7201              (4K channels)
  - epgshare01.online ready-made XMLTV files (free, no login), one per country; for UK and
    Ireland only a backup, used for a channel Sky's guide sends nothing for.
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
import json
import os
import re
import ssl
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


def _ssl_context():
    """Trusted certificates from certifi when installed (python.org's Python on a Mac has none
    of its own), else the system's - as SPORT_epg.py does. Certificates are always checked."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ssl_context()

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
        "SkySpBoxOff.uk": "Sky Sports Box Office",
        # (Sky Sports Ultra HD 1-2 left out: Sky's own guide gives Main Event 4K and F1 4K)
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
# Cytavision marks live with "(Z)" / "(Ζ)" (Ζωντανά = live).
LIVE = re.compile(r"^\s*live\b|^\s*\(L\)|\(\s*live\s*\)|\[\s*live\s*\]|\blive\s*$|\(\s*[ZΖ]\s*\)", re.I)
LIVE_STRIP = re.compile(r"^\s*live\b\s*[:\-]?\s*|^\s*\(L\)\s*|\s*\(\s*live\s*\)|\s*\[\s*live\s*\]|\s*\(\s*[ZΖ]\s*\)"
                        r"|\s*[-:]?\s*\blive\s*$", re.I)


# Sky's guide: our ID -> (name, [Sky service ids, best first], 4K?)
SKY_HAWK = "https://awk.epgsky.com/hawk/linear/schedule/{date}/{sids}"
SKY_ATLANTIS = "https://atlantis.epgsky.com/as/schedule/{date}/{sid}"
SKY_CHANNELS = {
    "UK.SkySportsMainEvent": ("Sky Sports Main Event", ["4002", "1701", "4005"], False),
    "UK.SkySportsPremierLeague": ("Sky Sports Premier League", ["4010", "1096", "4011"], False),
    "UK.SkySportsFootball": ("Sky Sports Football", ["3939", "3843", "3942"], False),
    "UK.SkySportsCricket": ("Sky Sports Cricket", ["4081", "1702", "4085"], False),
    "UK.SkySportsGolf": ("Sky Sports Golf", ["4026", "1704", "4027"], False),
    "UK.SkySportsF1": ("Sky Sports F1", ["3835", "3836", "4202"], False),
    "UK.SkySportsAction": ("Sky Sports Action", ["4022", "1703", "4024"], False),
    "UK.SkySportsMix": ("Sky Sports Mix", ["4090", "4092"], False),
    "UK.SkySportsNews": ("Sky Sports News", ["4049", "1340", "4036"], False),
    "UK.SkySportsRacing": ("Sky Sports Racing", ["4032", "4038"], False),
    "UK.SkySportsTennis": ("Sky Sports Tennis", ["1705", "1284"], False),
    "UK.SkySportsPlus": ("Sky Sports+", ["3940", "3858", "3945"], False),
    "UK.SkySportsBoxOffice": ("Sky Sports Box Office", ["1035"], False),
    "UK.SkySportsMainEvent4K": ("Sky Sports Main Event 4K", ["7201", "7211"], True),
    "UK.SkySportsF14K": ("Sky Sports F1 4K", ["7202", "7212"], True),
    "UK.TNTSports1": ("TNT Sports 1", ["1120", "3625", "1125"], False),
    "UK.TNTSports2": ("TNT Sports 2", ["3627", "3628"], False),
    "UK.TNTSports3": ("TNT Sports 3", ["3629", "3630"], False),
    "UK.TNTSports4": ("TNT Sports 4", ["4040", "4041"], False),
    "UK.TNTSports5": ("TNT Sports 5", ["1242"], False),
    "UK.TNTSports6": ("TNT Sports 6", ["1239", "5382"], False),
    "UK.TNTSports7": ("TNT Sports 7", ["1240", "5383"], False),
    "UK.TNTSports8": ("TNT Sports 8", ["1241", "5384"], False),
    "UK.TNTSports9": ("TNT Sports 9", ["1237", "5385"], False),
    "UK.TNTSports10": ("TNT Sports 10", ["1243", "5386"], False),
    "UK.TNTSportsBoxOffice": ("TNT Sports Box Office", ["1210", "6014"], False),
    "UK.TNTSportsBoxOffice2": ("TNT Sports Box Office 2", ["1099", "1218"], False),
    "UK.TNTSportsUltimate": ("TNT Sports Ultimate", ["1336", "1337"], True),
    "IE.PremierSports1": ("Premier Sports 1", ["1192", "1289"], False),
    "IE.PremierSports2": ("Premier Sports 2", ["1193", "1290"], False),
}
SKY_DAYS = 7


def sky_get(url, headers, state):
    """JSON from Sky's guide, or None (the reason is printed). Gives up on Sky after 3 failures in a row."""
    if state["fails"] >= 3:
        return None
    why = "no answer"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **headers})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                data = json.load(resp)
            state["fails"] = 0
            return data
        except urllib.error.HTTPError as e:
            why = f"HTTP {e.code} {e.reason}"
            if e.code in (400, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            why = f"{type(e).__name__}: {e}"[:120]
        time.sleep(3 * (attempt + 1))
    state["fails"] += 1
    print(f"  WARNING: Sky guide: {url.split('/schedule/')[-1]}: {why}", file=sys.stderr)
    if state["fails"] == 3:
        print("  WARNING: Sky guide failed 3 times in a row - skipping the rest of it this run "
              "(epgshare01 fills in)", file=sys.stderr)
    return None


def fetch_sky(now, debug=False):
    """{our id: (name, [programme tuples])} from Sky's guide, for SKY_DAYS days from today."""
    per_sid = {}                                       # Sky service id -> {start: programme}
    state = {"fails": 0}
    hd = [sid for _, sids, uhd in SKY_CHANNELS.values() if not uhd for sid in sids]
    uhd = [sid for _, sids, is_uhd in SKY_CHANNELS.values() if is_uhd for sid in sids]
    until = now + timedelta(days=DAYS)

    def take(data):
        for sched in (data or {}).get("schedule") or []:
            if not isinstance(sched, dict):
                continue
            sid = str(sched.get("sid"))
            for ev in sched.get("events") or []:
                try:
                    start = datetime.fromtimestamp(int(ev["st"]), timezone.utc)
                    stop = start + timedelta(seconds=int(ev["d"]))
                except (KeyError, TypeError, ValueError):
                    continue
                title = re.sub(r"\s+", " ", str(ev.get("t") or "")).strip()
                if not title or stop <= now or start >= until:
                    continue
                live = bool(LIVE.search(title))
                if live:
                    title = LIVE_STRIP.sub("", title).strip() or title
                synopsis = re.sub(r"\s+", " ", str(ev.get("sy") or "")).strip()
                if len(synopsis) > 160:
                    synopsis = synopsis[:160].rsplit(" ", 1)[0] + " …"
                per_sid.setdefault(sid, {})[start] = (start, stop, title, synopsis, live)

    for day in range(SKY_DAYS + 1):
        date = (now + timedelta(days=day)).strftime("%Y%m%d")
        for i in range(0, len(hd), 20):                # Sky answers up to 20 channels at once
            take(sky_get(SKY_HAWK.format(date=date, sids=",".join(hd[i:i + 20])),
                         {"X-SkyOTT-Territory": "GB"}, state))
        for sid in uhd:                                # 4K channels: Sky's other address
            take(sky_get(SKY_ATLANTIS.format(date=date, sid=sid),
                         {"X-SkyOTT-Territory": "GB", "X-SkyOTT-Proposition": "SKYQ",
                          "X-SkyOTT-Provider": "SKY"}, state))
        time.sleep(0.3)
    out = {}
    for cid, (name, sids, _) in SKY_CHANNELS.items():
        best = max(sids, key=lambda s: len(per_sid.get(s) or {}))
        progs = per_sid.get(best) or {}
        if debug:
            print(f"    {name}: {len(progs)} from Sky service {best}")
        if progs:
            out[cid] = (name, [(cid, *progs[k]) for k in sorted(progs)])
    print(f"Sky guide: {sum(len(p) for _, p in out.values())} programmes on {len(out)} channel(s)")
    return out


def download(file):
    """The decompressed XML of one epgshare01 file, or None (with the reason printed)."""
    why = "no answer"
    for scheme in ("https", "http"):                 # the site's advice: try http if https fails
        for attempt in range(2):
            try:
                req = urllib.request.Request(URL.format(scheme=scheme, file=file), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120, context=CTX) as resp:
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
    ap.add_argument("--no-sky", action="store_true", help="don't read Sky's guide (epgshare01 only)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    until = now + timedelta(days=DAYS)
    tv = ET.Element("tv", {"generator-info-name": "SPORT_search_extra.py",
                           "source-info-name": "Sky TV guide, epgshare01.online (search page only)"})
    channels, programmes, loaded = {}, [], 0
    sky = {} if args.no_sky else fetch_sky(now, args.debug)
    for cid, (name, progs) in sky.items():
        channels[cid] = name
        programmes += progs
    loaded += bool(sky)
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
                        if cid in sky:                          # Sky's own guide has this channel
                            pass
                        elif (cid, start) not in seen:          # an HD and SD copy: keep one
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

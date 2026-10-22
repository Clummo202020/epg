#!/usr/bin/env python3
"""
general_epg.py - your own general TV guide (UK Freeview/satellite + world channels).

Reads your merged playlist (FULL_PLAYLIST_URL secret), takes the live channels in the
general groups (Entertainment, News, Documentary, Movies, Music, Shopping, DirecTV USA,
Hub Sports),
finds each one in a listings source by name, and writes general_epg.xml.gz.

  * Sources, per channel country (from the stream's current EPG id, e.g. "amc.us"):
      UK/Ireland -> Sky's own TV guide first, then epgshare01 (UK1/IE1)
      USA        -> epgshare01 (US1, US sports, US locals, then free-TV lists)
      Canada     -> epgshare01 (CA1)
      Singapore  -> StarHub TV+'s own guide first, then epgshare01 (SG1)
      Hong Kong  -> Now TV's own guide first, then epgshare01 (HK1)
      Change SOURCE_ORDER to switch a country's source.
  * Channel ids: <name>.<country>.5651, e.g. BBCOneEast.uk.5651 - fixed, whatever the source,
    so switching a country's source never needs relinking.
  * The guide's channel name shows the source for PlaylistLabs: "BBC One East [Sky]".
  * general_epg_report.csv lists every channel, its id, and what it was matched to
    (or "NOT FOUND"), so you can link them and spot mismatches. Fix a wrong or missing
    match in OVERRIDES below.

    FULL_PLAYLIST_URL=... python3 general_epg.py
    python3 general_epg.py --m3u playlist.m3u
"""
import argparse
import csv
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
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
MARKER = "5651"
DAYS = 4
OUTPUT = "general_epg.xml.gz"
REPORT = "general_epg_report.csv"
GROUPS = ["Entertainment", "News", "Documentary", "Movies", "Music", "Shopping", "DirecTV USA",
          "Hub Sports", "Now Premier League"]
GROUP_COUNTRY = {"Hub Sports": "sg", "Now Premier League": "hk"}   # one-country groups
INCLUDE_COUNTRIES = {"hk", "sg"}   # also take these countries' channels from any other group
LONDON = ZoneInfo("Europe/London")
# Films and TV-show episodes are never given a guide: files like .mkv/.mp4, or
# provider movie/series links
VOD_RE = re.compile(r"\.(mkv|mp4|avi|m4v|mov|wmv|flv|webm|mpg|mpeg)(\?|$)|/(movie|movies|series)/", re.I)
MIN_SCORE = 0.9            # how sure a name match must be to be used

FAST = ["SAMSUNG1", "PLEX1", "DISTROTV1"]          # free streaming-TV channel lists
SOURCE_ORDER = {           # channel country -> sources to try, best first
    "uk": ["sky", "UK1", "US1", "CA1"] + FAST,
    "ie": ["sky", "IE1", "UK1"],
    "us": ["US1", "US_SPORTS1", "US_LOCALS2", "CA1", "sky"] + FAST,
    "ca": ["CA1", "US1"] + FAST,
    "dk": ["DK1", "sky"],
    "es": ["ES1", "sky"],
    "sg": ["starhub", "SG1"],
    "hk": ["nowtv", "HK1"],
    "": ["sky", "US1", "UK1", "CA1", "US_LOCALS2"] + FAST,
}
COUNTRY_FIX = {"ca2": "ca", "rteone": "ie", "rte2": "ie", "virginmediaone": "ie",
               "virginmediatwo": "ie", "virginmediathree": "ie", "virginmediafour": "ie"}

# Manual fixes: playlist channel name -> (source, source channel id), or None to leave out.
# Sources: "sky" (Sky service number) or an epgshare01 file name such as "US1".
OVERRIDES = {
    # "History 2": ("sky", "1112"),
}
ALIASES = {   # playlist name -> other names a source may use
    "TCM": ["Turner Classic Movies"], "GSN": ["Game Show Network"], "LMN": ["Lifetime Movie Network"],
    "OWN": ["Oprah Winfrey Network"], "FXM": ["FX Movie Channel"], "BTN": ["Big Ten Network"],
    "Reelz": ["ReelzChannel"], "Virgin Media One": ["Virgin One"], "Virgin Media Two": ["Virgin Two"],
    "Virgin Media Three": ["Virgin Three"], "Virgin Media Four": ["Virgin Four"],
    "RTE One": ["RTÉ One"], "RTE Two": ["RTÉ2", "RTE2"], "BBC World News": ["BBC News World"],
    "Talk TV": ["TalkTV"], "Discovery Science": ["Disc.Science"], "NBC News Now": ["NBC News NOW"],
    "CMT Music": ["CMT Music"], "All Reality WETV": ["WE tv"], "FX": ["FX USA", "FX - Eastern"],
    "Sundance": ["SundanceTV"], "Home Shopping Network": ["HSN"], "ShortsTV": ["Shorts TV"],
    "Now Sports ᵁᴴᴰ": ["Now Sports 4K 1"], "beIN Sports 1": ["beIN SPORTS HD"],
}

SKY_LIST = "https://raw.githubusercontent.com/iptv-org/epg/master/sites/sky.com/sky.com.channels.xml"
SKY_HAWK = "https://awk.epgsky.com/hawk/linear/schedule/{date}/{sids}"
SKY_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "X-SkyOTT-Territory": "GB"}
EPGSHARE = "https://epgshare01.online/epgshare01/epg_ripper_{file}.xml.gz"
STARHUB = "https://waf-starhub-metadata-api-p001.ifs.vubiquity.com/v3.1/epg/"
STARHUB_Q = "locale=en_US&locale_default=en_US&device=1"
STARHUB_LIST = ("https://raw.githubusercontent.com/iptv-org/epg/master/sites/starhubtvplus.com/"
                "starhubtvplus.com_en.channels.xml")       # backup channel list
SOURCE_LABEL = {"sky": "Sky", "starhub": "StarHub", "nowtv": "Now TV"}   # anything else: [epgshare]
NOW_GUIDE = "https://nowplayer.now.com/tvguide/epglist?{ids}&day={day}"
NOW_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/javascript, */*",
               "X-Requested-With": "XMLHttpRequest", "Cookie": "LANG=en",
               "Referer": "https://nowplayer.now.com/tvguide"}
NOW_CHANNELS = {   # Now TV channel number -> [names it may appear under in your playlist]
    "611": ["Now Sports 4K 1", "Now Sports UHD"], "612": ["Now Sports 4K 2"], "613": ["Now Sports 4K 3"],
    "620": ["Now Sports Premier League TV", "Now Premier League TV"],
    **{str(620 + n): [f"Now Sports Premier League {n}", f"Now Premier League {n}"] for n in range(1, 10)},
    "630": ["Now Sports Prime"], **{str(630 + n): [f"Now Sports {n}"] for n in range(1, 8)},
    "638": ["beIN Sports 1"], "639": ["beIN Sports 2"], "643": ["beIN Sports 3"],
    "644": ["beIN Sports 4"], "645": ["beIN Sports 5"], "646": ["beIN Sports 6"],
    "640": ["MUTV"], "642": ["NBA TV"], "680": ["Now Sports Plus"],
}
HEADERS = {"User-Agent": "Mozilla/5.0 (general_epg.py)"}


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
def fetch(url, headers=None, tries=3, timeout=120):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                       # network trouble of any kind
            if i == tries - 1:
                print(f"  WARNING: could not fetch {url.split('?')[0]}: {e}")
            time.sleep(3 * (i + 1))
    return None


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------
NOISE = {"hd", "hdtv", "uhd", "fhd", "4k", "sd", "eastern", "east", "feed", "usa", "us", "uk",
         "tv", "channel", "network", "the", "e", "hq", "stream"}
SMALL = {"u", "and", "w", "sky"}      # "Dave" = "U&Dave", "History" = "Sky History"


def words(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("+1", " plus1 ").replace("+", " plus ")
    s = re.sub(r"\([^)]*\)", " ", s)
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


QUALITY = {"hd", "hdtv", "uhd", "fhd", "4k", "sd"}


def toks(s):
    w = [x for x in words(s) if x not in NOISE]
    if len("".join(w)) <= 2:          # "5 USA" must stay "5usa", not shrink to "5" (= Channel 5)
        w = [x for x in words(s) if x not in QUALITY and x not in {"channel", "the"}]
    return w or words(s)


def key(s):
    return "".join(toks(s))


def score(name, cand_name, cand_keys):
    k = key(name)
    if k in cand_keys:
        return 1.0
    if re.findall(r"\d+", " ".join(words(name))) != re.findall(r"\d+", " ".join(words(cand_name))) \
            and not any(re.findall(r"\d+", c) == re.findall(r"\d+", k) for c in cand_keys):
        return 0.0                  # different numbers: "Hub Premier 9" is not "Hub Premier 6"
    ut, ct = toks(name), toks(cand_name)
    if ut and ct:
        if set(ut) == set(ct):
            return 0.99
        if set(ut) < set(ct) and (set(ct) - set(ut)) <= SMALL:      # "Dave" = "U&Dave"
            return 0.97
        if "".join(x for x in ut if x not in SMALL) == "".join(x for x in ct if x not in SMALL):
            return 0.97                                              # "History 2" = "Sky History2"
    r = max([SequenceMatcher(None, k, c).ratio() for c in cand_keys if c] or [0])
    return min(r, 0.7) if len(k) <= 4 else r                         # short names: exact only


def sky_keys(xmltv_id, name):
    keys = {key(name)}
    m = re.match(r"([^.]+)\.uk@(.+)$", xmltv_id or "")
    if m:
        base = key(re.sub(r"([a-z])([A-Z0-9])", r"\1 \2", m.group(1)))
        region = key(re.sub(r"([a-z])([A-Z])", r"\1 \2", re.sub(r"(HD|SD|Plus1)$", "", m.group(2))))
        keys |= {base + region, base}
        if base.startswith("itv1"):
            keys.add("itv" + region)
    return {k for k in keys if k}


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
class Sources:
    def __init__(self):
        self.lists = {}        # source -> [(id, name, keys)]
        self.raw = {}          # epgshare file -> xml bytes

    def channels(self, src):
        if src in self.lists:
            return self.lists[src]
        out = []
        if src == "nowtv":
            for num, names in NOW_CHANNELS.items():
                out.append((num, names[0], {key(n) for n in names}))
        elif src == "starhub":
            page, total = 1, 1
            while page <= total and page <= 20:
                try:
                    data = json.loads(fetch(f"{STARHUB}channels?{STARHUB_Q}&limit=50&page={page}") or b"{}")
                except ValueError:
                    data = {}
                for ch in data.get("resources") or []:
                    if ch.get("id") and ch.get("title"):
                        out.append((ch["id"], ch["title"], {key(ch["title"])}))
                total = (data.get("page") or {}).get("total") or 0
                page += 1
            if not out:                                # API down: use the saved channel list
                raw = (fetch(STARHUB_LIST) or b"").decode("utf-8", "replace")
                for sid, name in re.findall(r'site_id="([^"]+)"[^>]*>([^<]*)<', raw):
                    name = name.replace("&amp;", "&")
                    out.append((sid, name, {key(name)}))
        elif src == "sky":
            raw = fetch(SKY_LIST)
            for sid, xid, name in re.findall(r'site_id="GB#(\d+)"[^>]*xmltv_id="([^"]*)"[^>]*>([^<]*)<',
                                             (raw or b"").decode("utf-8", "replace")):
                if "plus1" in xid.lower():
                    continue
                name = name.replace("&amp;", "&")
                out.append((sid, name, sky_keys(xid, name)))
        else:
            raw = fetch(EPGSHARE.format(file=src))
            if raw:
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass
                self.raw[src] = raw
                for _, el in ET.iterparse(io.BytesIO(raw), events=("end",)):
                    if el.tag == "channel":
                        name = (el.findtext("display-name") or "").strip()
                        if name and "+1" not in name:
                            out.append((el.get("id"), name, {key(name)}))
                        el.clear()
                    elif el.tag == "programme":
                        break
        print(f"  {src}: {len(out)} channels")
        self.lists[src] = out
        return out


def best_match(name, srcs, sources):
    names = [name] + ALIASES.get(name, [])
    pick = (0.0, None, None)
    for src in srcs:
        for n in names:
            for cid, cname, ckeys in sources.channels(src):
                s = score(n, cname, ckeys)
                if s > pick[0] + 0.02 or (s >= 0.97 and pick[0] < 0.97):
                    pick = (s, src, (cid, cname))
        if pick[0] >= 0.97:
            break
    return pick


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------
def sky_listings(sids, first, end):
    per = {}
    days = sorted({(first + timedelta(days=i)).astimezone(LONDON).strftime("%Y%m%d")
                   for i in range((end - first).days + 2)})
    for ymd in days:
        for i in range(0, len(sids), 20):
            raw = fetch(SKY_HAWK.format(date=ymd, sids=",".join(sids[i:i + 20])), SKY_HEADERS)
            try:
                data = json.loads(raw or b"{}")
            except ValueError:
                continue
            for sched in data.get("schedule") or []:
                sid = str(sched.get("sid"))
                for ev in sched.get("events") or []:
                    try:
                        start = datetime.fromtimestamp(int(ev["st"]), timezone.utc)
                        stop = start + timedelta(seconds=int(ev["d"]))
                    except (KeyError, TypeError, ValueError):
                        continue
                    title = re.sub(r"\s+", " ", str(ev.get("t") or "")).strip()
                    if re.match(r"(?i)live\b[\s:.-]*", title):                 # "Live: ..." on Sky
                        title = "🔴 LIVE: " + re.sub(r"(?i)^live\b[\s:.-]*", "", title)
                    if title and stop > first and start < end:
                        per.setdefault(sid, {})[start] = (start, stop, title, "",
                                                          re.sub(r"\s+", " ", str(ev.get("sy") or "")).strip())
    return {sid: [evs[k] for k in sorted(evs)] for sid, evs in per.items()}


def starhub_listings(ids, first, end):
    per = {}
    for cid in ids:
        day = first
        while day < end:
            nxt = min(day + timedelta(days=1), end)
            page, total = 1, 1
            while page <= total and page <= 10:
                url = (f"{STARHUB}schedules?{STARHUB_Q}&in_channel_id={cid}&gt_end={int(day.timestamp())}"
                       f"&lt_start={int(nxt.timestamp())}&limit=100&page={page}")
                try:
                    data = json.loads(fetch(url) or b"{}")
                except ValueError:
                    data = {}
                for it in data.get("resources") or []:
                    try:
                        start = datetime.fromtimestamp(int(it["start"]), timezone.utc)
                        stop = datetime.fromtimestamp(int(it["end"]), timezone.utc)
                    except (KeyError, TypeError, ValueError):
                        continue
                    serie, ep = (it.get("serie_title") or "").strip(), (it.get("title") or "").strip()
                    title = serie or ep
                    sub = ep if serie and ep and ep != serie else ""
                    per.setdefault(cid, {})[start] = (start, stop, title, sub,
                                                      re.sub(r"\s+", " ", it.get("description") or "").strip())
                total = (data.get("page") or {}).get("total") or 0
                page += 1
            day = nxt
    return {cid: [evs[k] for k in sorted(evs)] for cid, evs in per.items()}


def now_listings(ids, first, end):
    per = {}
    for d in range(1, DAYS + 2):
        for cid in ids:
            try:
                data = json.loads(fetch(NOW_GUIDE.format(ids="channelIdList%5B%5D=" + cid, day=d),
                                        NOW_HEADERS) or b"[]")
            except ValueError:
                continue
            for it in (data[0] if isinstance(data, list) and data and isinstance(data[0], list) else []):
                try:
                    start = datetime.fromtimestamp(int(it["start"]) / 1000, timezone.utc)
                    stop = datetime.fromtimestamp(int(it["end"]) / 1000, timezone.utc)
                except (KeyError, TypeError, ValueError):
                    continue
                raw = str(it.get("name") or "")
                title = re.sub(r"\s*\[\s*live(\s+chat)?\s*\]", "", raw, flags=re.I)
                title = re.sub(r"\s+-(?=\S)", " - ", re.sub(r"\s+", " ", title)).strip()
                if re.search(r"\[\s*live\s*\]|直播", raw, re.I):          # Now TV marks live matches
                    title = f"🔴 LIVE: {title}"
                if title and stop > first and start < end:
                    per.setdefault(cid, {})[start] = (start, stop, title, "", "")
            time.sleep(0.2)
    return {cid: [evs[k] for k in sorted(evs)] for cid, evs in per.items()}


def stamp(s):
    return datetime.strptime(s.strip(), "%Y%m%d%H%M%S %z")


def epgshare_listings(raw, ids, first, end):
    per = {}
    for _, el in ET.iterparse(io.BytesIO(raw), events=("end",)):
        if el.tag == "programme" and el.get("channel") in ids:
            try:
                start, stop = stamp(el.get("start")), stamp(el.get("stop"))
            except (TypeError, ValueError):
                el.clear()
                continue
            if stop > first and start < end:
                per.setdefault(el.get("channel"), {})[start] = (
                    start, stop, (el.findtext("title") or "").strip(),
                    (el.findtext("sub-title") or "").strip(), (el.findtext("desc") or "").strip())
            el.clear()
        elif el.tag in ("programme", "channel"):
            el.clear()
    return {cid: [evs[k] for k in sorted(evs)] for cid, evs in per.items()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def read_playlist(args):
    if args.m3u:
        with open(args.m3u, encoding="utf-8", errors="replace") as f:
            return f.read()
    url = os.environ.get("FULL_PLAYLIST_URL", "").strip()
    if not url:
        sys.exit("No FULL_PLAYLIST_URL secret (or use --m3u FILE).")
    raw = fetch(url, timeout=180)
    if not raw:
        sys.exit("Could not download the playlist.")
    return raw.decode("utf-8", "replace")


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode())


def main():
    ap = argparse.ArgumentParser(description="General TV guide from your playlist's live channels.")
    ap.add_argument("--m3u")
    args = ap.parse_args()

    channels = {}                                    # our id -> {name, country, group}
    lines = read_playlist(args).splitlines()
    skipped_vod = 0
    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue
        url = next((l.strip() for l in lines[i + 1:i + 4] if l.strip() and not l.startswith("#")), "")
        if VOD_RE.search(url):                       # films and TV episodes (.mkv, .mp4 ...)
            skipped_vod += 1
            continue
        group = (re.search(r'group-title="([^"]*)"', line) or [None, ""])[1]
        tvg = (re.search(r'tvg-id="([^"]*)"', line) or [None, ""])[1]
        tvg_cc = tvg.rsplit(".", 1)[-1].lower() if "." in tvg else ""
        if not tvg or (group not in GROUPS and tvg_cc not in INCLUDE_COUNTRIES):
            continue                                 # live channels only (they have an EPG id)
        name = line.rsplit(",", 1)[-1].strip()
        cc = tvg.rsplit(".", 1)[-1].lower() if "." in tvg else ""
        cc = COUNTRY_FIX.get(cc, cc if cc in SOURCE_ORDER else "")
        cc = GROUP_COUNTRY.get(group, cc)
        cid = f"{slug(name)}.{cc or 'int'}.{MARKER}"
        channels.setdefault(cid, {"name": name, "country": cc, "group": group})
    print(f"{len(channels)} live channels in the general groups ({skipped_vod} films/episodes skipped)")

    sources = Sources()
    report, wanted = [], {}                          # wanted: source -> {source id: [our ids]}
    for cid, ch in channels.items():
        if ch["name"] in OVERRIDES:
            fix = OVERRIDES[ch["name"]]
            pick = (1.0, fix[0], (fix[1], "manual")) if fix else (0, None, None)
        else:
            pick = best_match(ch["name"], SOURCE_ORDER[ch["country"]], sources)
        ok = pick[0] >= MIN_SCORE and pick[1]
        if ok:
            ch["src"], ch["sid"], ch["label"] = pick[1], pick[2][0], SOURCE_LABEL.get(pick[1], "epgshare")
            wanted.setdefault(pick[1], {}).setdefault(pick[2][0], []).append(cid)
        report.append({"group": ch["group"], "name": ch["name"], "epg_id": cid,
                       "source": pick[1] if ok else "", "matched_to": pick[2][1] if ok else "NOT FOUND",
                       "score": f"{pick[0]:.2f}"})

    now = datetime.now(timezone.utc)
    first = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    end = first + timedelta(days=DAYS)
    listings = {}                                    # our id -> events
    for src, ids in wanted.items():
        if src == "sky":
            got = sky_listings(list(ids), first, end)
        elif src == "starhub":
            got = starhub_listings(list(ids), first, end)
        elif src == "nowtv":
            got = now_listings(list(ids), first, end)
        else:
            got = epgshare_listings(sources.raw.get(src, b"<tv/>"), set(ids), first, end)
        for sid, evs in got.items():
            for cid in ids[sid]:
                listings[cid] = evs
        print(f"  {src}: listings for {len(got)} of {len(ids)} channels")

    tv = ET.Element("tv", {"generator-info-name": "general_epg.py"})
    for cid in sorted(listings):
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = f"{channels[cid]['name']} [{channels[cid]['label']}]"
        ET.SubElement(c, "display-name", {"lang": "en"}).text = channels[cid]["name"]
    count = 0
    for cid in sorted(listings):
        for start, stop, title, sub, desc in listings[cid]:
            p = ET.SubElement(tv, "programme", {"start": start.astimezone(LONDON).strftime("%Y%m%d%H%M%S %z"),
                                                "stop": stop.astimezone(LONDON).strftime("%Y%m%d%H%M%S %z"),
                                                "channel": cid})
            ET.SubElement(p, "title", {"lang": "en"}).text = title or "Programme"
            if sub and sub != title:
                ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
            if desc and desc not in (title, sub):
                ET.SubElement(p, "desc", {"lang": "en"}).text = desc
            count += 1
    data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    with gzip.open(OUTPUT, "wb") as f:
        f.write(data)
    for r in report:
        if r["source"] and r["epg_id"] not in listings:
            r["matched_to"] += " (no listings this run)"
    with open(REPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "name", "epg_id", "source", "matched_to", "score"])
        w.writeheader()
        w.writerows(sorted(report, key=lambda r: (r["matched_to"] != "NOT FOUND", r["group"], r["name"])))
    found = sum(1 for r in report if r["source"])
    print(f"\nMatched {found} of {len(report)} channels; {len(listings)} have listings")
    print(f"Wrote {OUTPUT}: {len(listings)} channels, {count} programmes; report in {REPORT}")


if __name__ == "__main__":
    main()

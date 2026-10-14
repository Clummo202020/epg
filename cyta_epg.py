#!/usr/bin/env python3
"""
Generate an XMLTV file from the Cyta (Cyprus) TV guide.

The page https://epg.cyta.com.cy/tv-guide/en is a JavaScript app; it loads its
data from these JSON endpoints, which this script uses directly:

  GET /api/mediacatalog/fetchChannels?language=1
  GET /api/mediacatalog/fetchEpg?startTimeEpoch=..&endTimeEpoch=..&language=1&channelIds=..

Usage:
  pip install requests
  python cyta_epg.py                       # 3 days -> cyta_epg.xml (overwritten each run)
  python cyta_epg.py --run-ids             # fresh channel ids (cyta-5-Run3) when the guide must be replaced
  python cyta_epg.py --unique              # new file name each run: cyta_epg_<date-time>_<random>.xml
  python cyta_epg.py --days 7 -o guide.xml
  python cyta_epg.py --list-channels
  python cyta_epg.py --channels 12,15 --debug
  python cyta_epg.py --no-translate        # keep Greek text as-is (default: translate to English)

Channel ids are fixed by default (cyta-5, cyta-12 ...) so playlist links never
need changing. PlaylistLabs only ADDS programmes after the latest one it holds
for a channel id and never changes old ones; when old programmes must be
replaced, run once with --run-ids (ids become cyta-5-Run3 ...) and relink.
The last run number is kept in cyta_epg_run.json next to this script.
"""
import argparse
import json
import re
import subprocess
import unicodedata
import uuid
import sys
import time
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

BASE = "https://epg.cyta.com.cy/api/mediacatalog"
TZ = ZoneInfo("Europe/London")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://epg.cyta.com.cy/tv-guide/en",
}

HEADERS["Connection"] = "close"  # avoid reusing connections the server has dropped
DELAY = 0.3  # seconds between requests (set via --delay)
FAILED = []


def curl_json(url, params):
    """Fallback: use the system curl (different TLS stack from Python's)."""
    cmd = ["curl", "-sS", "--fail", "--max-time", "30", "-G", url]
    for k, v in params.items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    for k, v in HEADERS.items():
        cmd += ["-H", f"{k}: {v}"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if out.returncode != 0:
        raise requests.RequestException(out.stderr.strip() or f"curl exit {out.returncode}")
    return json.loads(out.stdout)


def get_json(url, params, retries=6):
    # No shared Session: a fresh connection per request is far more reliable
    # against servers that cut off keep-alive / parallel connections.
    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            try:
                r = requests.get(url, params=params, headers=HEADERS, timeout=30)
                r.raise_for_status()
                return r.json()
            except requests.exceptions.SSLError:
                return curl_json(url, params)  # Python's TLS rejected; try curl
        except (requests.RequestException, ValueError, subprocess.SubprocessError) as e:
            if attempt == retries - 1:
                FAILED.append(params.get("channelIds", "channels"))
                print(f"  ! gave up on {params.get('channelIds', url)}: "
                      f"{type(e).__name__}: {str(e)[:300]}", file=sys.stderr)
                return None
            time.sleep(2 * (attempt + 1))  # 2s, 4s, 6s ...


def pick(d, *keys, default=None):
    """Return the first non-empty value among several possible key names."""
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


def to_dt(value):
    """Accept epoch seconds/milliseconds or an ISO-8601 string -> aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        n = float(value)
        if n > 1e11:  # milliseconds
            n /= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def xmltv_time(dt):
    # London local time with its real offset (+0000 in winter, +0100 in summer)
    return dt.astimezone(TZ).strftime("%Y%m%d%H%M%S %z")


def fetch_channels(language):
    data = get_json(f"{BASE}/fetchChannels", {"language": language})
    if not data:
        sys.exit("Could not fetch the channel list.")
    channels = []
    for c in data.get("channels", []):
        cid = pick(c, "id", "channelId")
        if cid is None:
            continue
        # Any category/genre-like text the API provides, used for sports matching
        extra = " ".join(
            str(v) for k, v in c.items()
            if isinstance(v, str) and any(t in k.lower() for t in ("categor", "genre", "type", "tag"))
        )
        channels.append({
            "id": str(cid),
            "name": pick(c, "name", "title", default=f"Channel {cid}"),
            "logo": pick(c, "logo", "logoUrl", "imageUrl", "image", "icon"),
            "meta": extra,
        })
    return channels


# Each comma-separated entry matches when ALL its words appear in the channel
# name, so "cyta sport" matches "Cytavision Sports 1" and "Cyta Vision Sports 2"
# but not "Eurosport" or "Cytavision Movies".
DEFAULT_SPORTS_KEYWORDS = "cyta sport"


def is_sports(channel, keywords):
    text = f"{channel['name']} {channel.get('meta', '')}".lower()
    return any(all(w in text for w in k.split()) for k in keywords)


def fetch_day(channel_ids, day_start, language):
    """Fetch one local-calendar day for a batch of channels -> [(channel_id, programme)]."""
    start = day_start.astimezone(timezone.utc)
    end = (day_start + timedelta(days=1)).astimezone(timezone.utc)
    params = {
        "startTimeEpoch": int(start.timestamp() * 1000),
        "endTimeEpoch": int(end.timestamp() * 1000),
        "language": language,
        "channelIds": ",".join(channel_ids),
    }
    data = get_json(f"{BASE}/fetchEpg", params)
    out = []
    if not data:
        return out
    for ch in data.get("channelEpgs", []):
        ch_id = str(pick(ch, "channelId", "id", default=""))
        for p in ch.get("epgPlayables", []):
            cid = str(p.get("channelId") or ch_id or channel_ids[0])
            out.append((cid, p))
    return out


DESC_WORDS = ("descr", "synops", "summar", "plot", "overview", "story")


def find_description(obj):
    """Search a details response (any nesting) for the longest description-like text."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and v.strip() and any(w in k.lower() for w in DESC_WORDS):
                    found.append(v.strip())
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return max(found, key=len) if found else None


DETAILS_SAMPLE = []


def parse_details(data):
    """Pull description, genres, image and rating out of a fetchEpgDetails response."""
    d = data.get("playbillDetail") if isinstance(data, dict) else None
    d = d if isinstance(d, dict) else (data if isinstance(data, dict) else {})
    desc = pick(d, "introduce", "description", "longDescription", "shortDescription",
                "synopsis") or find_description(d)
    genres = [g.get("genreName") for g in d.get("genres", [])
              if isinstance(g, dict) and g.get("genreName")]
    pic = d.get("picture") if isinstance(d.get("picture"), dict) else {}
    icons = pic.get("icons") or []
    posters = pic.get("posters") or []
    image = (icons or posters or [None])[0]
    rating = d.get("rating", {}).get("name") if isinstance(d.get("rating"), dict) else None
    return {"description": desc, "genres": genres, "image": image, "rating": rating}


def fetch_details(programme_id, language):
    data = get_json(f"{BASE}/fetchEpgDetails", {"language": language, "id": programme_id})
    if not DETAILS_SAMPLE:
        DETAILS_SAMPLE.append((programme_id, data))  # keep even if empty/None
    return parse_details(data) if data else None
    for ch in data.get("channelEpgs", []):
        for p in ch.get("epgPlayables", []):
            out.append(p)
    return out


RUN_STATE_FILE = Path(__file__).resolve().with_name("cyta_epg_run.json")


def load_last_run():
    try:
        return int(json.loads(RUN_STATE_FILE.read_text(encoding="utf-8"))["last_run"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_last_run(n):
    try:
        RUN_STATE_FILE.write_text(json.dumps({"last_run": n}), encoding="utf-8")
    except OSError as e:
        print(f"WARNING: could not save run number: {e}", file=sys.stderr)


def unique_path(path):
    """cyta_epg.xml -> cyta_epg_20261013-153045_a1b2c3.xml (never an existing file)."""
    out = Path(path)
    while True:
        rid = f"{datetime.now(ZoneInfo('Europe/London')):%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:6]}"
        cand = out.with_name(f"{out.stem}_{rid}{out.suffix}")
        if not cand.exists():
            return cand


GREEK = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
GREEK_RUN = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]+")
TRANSLATIONS = {}  # Greek text -> English text


def has_greek(text):
    return bool(text) and bool(GREEK.search(text))


TRANSLATE_ERRORS = []
GOOGLE_BLOCKED = False  # set after Google keeps answering 429 in this run
TRANSLATE_DELAY = 1.0  # seconds between requests; Google's free endpoint rate-limits quickly
CACHE_FILE = Path(__file__).resolve().with_name("cyta_translations.json")


def mymemory_translate(text):
    """Fallback: MyMemory's free endpoint (no key; ~5000 characters/day, 500 per request)."""
    if len(text) > 480:
        return None
    try:
        time.sleep(TRANSLATE_DELAY)
        r = requests.get("https://api.mymemory.translated.net/get",
                         params={"q": text, "langpair": "el|en"}, timeout=30)
        r.raise_for_status()
        out = r.json().get("responseData", {}).get("translatedText")
        if out and "MYMEMORY WARNING" not in out.upper():
            return out
    except (requests.RequestException, ValueError, AttributeError) as e:
        TRANSLATE_ERRORS.append(f"MyMemory {type(e).__name__}: {str(e)[:150]}")
    return None


def google_translate(text, retries=2):
    """Translate via Google's free, unofficial web endpoint (no API key)."""
    global GOOGLE_BLOCKED
    if GOOGLE_BLOCKED:
        return None
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text}
    for attempt in range(retries):
        wait = 3 * (attempt + 1)
        try:
            time.sleep(TRANSLATE_DELAY)
            try:
                r = requests.get(url, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
            except requests.exceptions.SSLError:
                data = curl_json(url, params)  # system curl has a different TLS stack
            out = "".join(seg[0] for seg in data[0] if seg and seg[0])
            if out:
                return out
        except requests.HTTPError as e:
            TRANSLATE_ERRORS.append(f"{type(e).__name__}: {str(e)[:200]}")
            if e.response is not None and e.response.status_code == 429:
                wait = 8  # rate limited: short pause, then give up for this run
                if attempt == retries - 1:
                    GOOGLE_BLOCKED = True
        except (requests.RequestException, ValueError, IndexError, TypeError,
                subprocess.SubprocessError) as e:
            TRANSLATE_ERRORS.append(f"{type(e).__name__}: {str(e)[:200]}")
        time.sleep(wait)
    return None


def load_cache():
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            TRANSLATIONS.update({k: v for k, v in data.items() if isinstance(v, str)})
    except (OSError, ValueError):
        pass


def save_cache():
    try:
        CACHE_FILE.write_text(json.dumps(TRANSLATIONS, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    except OSError as e:
        print(f"Could not save translation cache: {e}", file=sys.stderr)


def translate_all(texts, use_cache=True):
    """Translate each unique Greek string once, one at a time (the free endpoint
    rate-limits). Stops early after repeated failures; the rest is transliterated."""
    if use_cache:
        load_cache()
    todo = sorted({t for t in texts if has_greek(t) and t not in TRANSLATIONS})
    if not todo:
        return
    print(f"Translating {len(todo)} unique Greek text(s) "
          f"(about {int(len(todo) * (TRANSLATE_DELAY + 0.5))}s)...")
    failed = 0
    consecutive = 0
    for i, src in enumerate(todo, 1):
        out = google_translate(src) or mymemory_translate(src)
        if out:
            TRANSLATIONS[src] = out
            consecutive = 0
        else:
            failed += 1
            consecutive += 1
        print(f"  {i}/{len(todo)} translated", end="\r")
        if consecutive >= 3:
            failed += len(todo) - i
            print("\n  Translation service keeps refusing requests; stopping.", file=sys.stderr)
            break
    print()
    if use_cache:
        save_cache()  # keep what worked, so the next run only does the rest
    if failed:
        print(f"WARNING: {failed} text(s) could not be translated and were transliterated "
              "instead. Run again later to translate the rest.", file=sys.stderr)
        if TRANSLATE_ERRORS:
            print(f"  last translation error: {TRANSLATE_ERRORS[-1]}", file=sys.stderr)


TRANSLITERATE = False
_SINGLE = dict(zip("αβγδεζηθικλμνξοπρστυφχψω",
                   ["a", "v", "g", "d", "e", "z", "i", "th", "i", "k", "l", "m", "n",
                    "x", "o", "p", "r", "s", "t", "y", "f", "ch", "ps", "o"]))
_PAIRS = {"αι": "ai", "ει": "ei", "οι": "oi", "ου": "ou", "υι": "yi",
          "γγ": "ng", "τσ": "ts", "τζ": "tz"}


def _translit_word(word):
    """Greek -> Latin (ELOT 743 style), keeping the original capitalisation."""
    w = "".join(c for c in unicodedata.normalize("NFD", word.lower())
                if unicodedata.category(c) != "Mn").replace("ς", "σ")
    out, i = [], 0
    while i < len(w):
        two, nxt = w[i:i + 2], w[i + 2:i + 3]
        if two in ("αυ", "ευ", "ηυ"):
            out.append({"α": "a", "ε": "e", "η": "i"}[two[0]]
                       + ("f" if nxt == "" or nxt in "θκξπστφχψ" else "v"))
        elif two == "μπ":
            out.append("b" if i == 0 else "mp")
        elif two == "ντ":
            out.append("d" if i == 0 else "nt")
        elif two == "γκ":
            out.append("g" if i == 0 else "gk")
        elif two in _PAIRS:
            out.append(_PAIRS[two])
        else:
            out.append(_SINGLE.get(w[i], w[i]))
            i += 1
            continue
        i += 2
    result = "".join(out)
    if word.isupper():
        return result.upper()
    if word[:1].isupper():
        return result[:1].upper() + result[1:]
    return result


def transliterate(text):
    return GREEK_RUN.sub(lambda m: _translit_word(m.group(0)), text)


def tr(text):
    t = TRANSLATIONS.get(text, text)
    if TRANSLITERATE and has_greek(t):
        t = transliterate(t)
    return t


def collect_texts(channels, programmes_by_channel):
    texts = [c["name"] for c in channels]
    for items in programmes_by_channel.values():
        for p in items:
            texts.append(pick(p, "name", "title"))
            texts.append(pick(p, "description", "shortDescription", "synopsis"))
            texts.append(pick(p, "programEvent", "category", "genre"))
            texts.extend(p.get("genres") or [])
    return [str(t) for t in texts if t]


# ---- ALL CAPS -> normal capitalisation -------------------------------------
KEEP_CAPS = set("""
UFC NBA NFL NHL MLB MLS WNBA NCAA UEFA FIFA FA EFL EPL WWE AEW ATP WTA PGA LPGA LIV DP
IPL ICC ODI GP MMA PFL BKFC DAZN ESPN BBC CNN BT TNT TV HD UHD PPV VAR USA UK UAE EU
FC SC AC AS CF CD FK SK BK AEK AEL APOEL PAOK OFI ENP AEP PAEEK GR
""".split())
SMALL_WORDS = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "v", "vs"}
WORD_RE = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*")
ROMAN_RE = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
CAPS_TAGS = {"title", "desc", "category", "display-name"}


def fix_caps(text, keep=KEEP_CAPS):
    """Turn words written entirely in capitals into normal capitalisation.
    Acronyms, roman numerals, single letters and words touching digits are left alone."""
    def repl(m):
        w = m.group(0)
        if len(w) < 2 or not w.isupper() or w in keep:
            return w
        if len(w) <= 4 and ROMAN_RE.match(w):
            return w
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if before.isdigit() or after.isdigit():
            return w
        lead = text[:m.start()].rstrip()
        starts = (not lead) or lead[-1] in "-\u2013\u2014:|/(\"'.!?"
        low = w.lower()
        if low in SMALL_WORDS and not starts:
            return low
        return low.capitalize()
    return WORD_RE.sub(repl, text)


def build_xml(channels, programmes_by_channel, lang, suffix=""):
    tv = ET.Element("tv", {
        "source-info-name": "Cyta EPG",
        "source-info-url": "https://epg.cyta.com.cy/tv-guide/en",
        "generator-info-name": "cyta_epg.py",
    })
    for ch in channels:
        el = ET.SubElement(tv, "channel", {"id": f"cyta-{ch['id']}{suffix}"})
        ET.SubElement(el, "display-name", {"lang": lang}).text = tr(ch["name"])
        if ch["logo"]:
            ET.SubElement(el, "icon", {"src": ch["logo"]})

    for ch in channels:
        seen = set()
        for p in programmes_by_channel.get(ch["id"], []):
            start = to_dt(pick(p, "startTime", "start"))
            stop = to_dt(pick(p, "endTime", "end"))
            if not start or not stop:
                continue
            key = (start, stop)
            if key in seen:  # day windows can overlap at midnight
                continue
            seen.add(key)

            el = ET.SubElement(tv, "programme", {
                "start": xmltv_time(start),
                "stop": xmltv_time(stop),
                "channel": f"cyta-{ch['id']}{suffix}",
            })
            ET.SubElement(el, "title", {"lang": lang}).text = \
                tr(str(pick(p, "name", "title", default="Unknown")))
            desc = pick(p, "description", "shortDescription", "synopsis")
            if desc:
                ET.SubElement(el, "desc", {"lang": lang}).text = tr(str(desc))
            cats = p.get("genres") or [pick(p, "programEvent", "category", "genre")]
            for cat in cats:
                if cat:
                    ET.SubElement(el, "category", {"lang": lang}).text = tr(str(cat))
            img = pick(p, "imageUrl", "image", "thumbnail", "poster")
            if isinstance(img, str) and img.startswith("http"):
                ET.SubElement(el, "icon", {"src": img})
            rating = pick(p, "rating")
            if rating:
                r_el = ET.SubElement(el, "rating", {"system": "Cyta"})
                ET.SubElement(r_el, "value").text = str(rating)
    return tv


def main():
    ap = argparse.ArgumentParser(description="Create an XMLTV guide from Cyta's EPG")
    ap.add_argument("-o", "--output", default="cyta_epg.xml")
    ap.add_argument("-d", "--days", type=int, default=3, help="days to fetch (default 3)")
    ap.add_argument("--language", default="0",
                    help="API language id; the English site uses 0 (default 0)")
    ap.add_argument("--batch", type=int, default=8,
                    help="channels per schedule request (default 8)")
    ap.add_argument("--no-details", action="store_true",
                    help="skip the per-programme description requests (much faster)")
    ap.add_argument("--lang-tag", default="en", help="lang attribute in XML (default en)")
    ap.add_argument("--channels", help="comma-separated channel IDs to include")
    ap.add_argument("--all", action="store_true",
                    help="include all channels, not just sports")
    ap.add_argument("--keywords", default=DEFAULT_SPORTS_KEYWORDS,
                    help="comma-separated words that mark a channel as sports "
                         "(matched against channel name/category)")
    ap.add_argument("--exclude", default="",
                    help="comma-separated words to drop from the sports list")
    ap.add_argument("--list-channels", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--delay", type=float, default=0.3,
                    help="seconds to wait before each request (default 0.3)")
    ap.add_argument("--no-translate", action="store_true",
                    help="leave Greek text as it is (by default it is translated to English)")
    ap.add_argument("--no-fix-caps", action="store_true",
                    help="keep ALL CAPS words as they are (default: convert to normal case)")
    ap.add_argument("--keep", default="",
                    help="extra comma-separated acronyms to keep in capitals, e.g. 'PAEEK,ENP'")
    ap.add_argument("--no-cache", action="store_true",
                    help="don't read/write cyta_translations.json (saved translations)")
    ap.add_argument("--transliterate", action="store_true",
                    help="only write Greek in Latin letters (offline; skips the web translation)")
    ap.add_argument("--debug", action="store_true", help="print the first raw programme")
    ap.add_argument("--run-ids", action="store_true",
                    help="fresh channel ids with a run number (cyta-5-Run3) so PlaylistLabs "
                         "takes the whole guide again; relink channels afterwards")
    ap.add_argument("--suffix", type=int, default=None,
                    help="run ids with this run number forced (12 -> cyta-5-Run12)")
    ap.add_argument("--unique", action="store_true",
                    help="add date-time and a random code to the file name instead of overwriting")
    args = ap.parse_args()
    global DELAY
    DELAY = args.delay

    channels = fetch_channels(args.language)
    if not args.all:
        kws = [k.strip().lower() for k in args.keywords.split(",") if k.strip()]
        excl = [k.strip().lower() for k in args.exclude.split(",") if k.strip()]
        channels = [
            c for c in channels
            if is_sports(c, kws) and not any(x in c["name"].lower() for x in excl)
        ]
        if not channels:
            sys.exit("No sports channels matched. Run with --all --list-channels "
                     "to see every channel, then adjust --keywords.")
    if args.list_channels:
        for c in channels:
            print(f"{c['id']}\t{c['name']}")
        return
    if args.channels:
        wanted = {x.strip() for x in args.channels.split(",")}
        channels = [c for c in channels if c["id"] in wanted]
    if not channels:
        sys.exit("No channels selected.")
    print(f"{len(channels)} channels, {args.days} day(s)")

    today = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    days = [today + timedelta(days=i) for i in range(args.days)]
    ids = [c["id"] for c in channels]
    batches = [ids[i:i + args.batch] for i in range(0, len(ids), max(1, args.batch))]

    results = {c["id"]: [] for c in channels}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_day, b, d, args.language) for b in batches for d in days]
        for i, fut in enumerate(futures, 1):
            for cid, prog in fut.result():
                if cid in results:
                    results[cid].append(prog)
            print(f"  schedule: {i}/{len(futures)} requests done", end="\r")
    print()

    if not args.no_details:
        pids = sorted({str(p["id"]) for items in results.values() for p in items if p.get("id")})
        print(f"Fetching descriptions for {len(pids)} programme(s)...")
        details = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i, (pid, d) in enumerate(
                    zip(pids, pool.map(lambda x: fetch_details(x, args.language), pids)), 1):
                if d:
                    details[pid] = d
                print(f"  descriptions: {i}/{len(pids)}", end="\r")
        print()
        for items in results.values():
            for p in items:
                d = details.get(str(p.get("id")))
                if not d:
                    continue
                if d["description"]:
                    p["description"] = d["description"]
                if d["genres"]:
                    p["genres"] = d["genres"]
                if d["image"]:
                    p["imageUrl"] = d["image"]
                if d["rating"]:
                    p["rating"] = d["rating"]
        descs = [d for d in details.values() if d["description"]]
        print(f"  {len(descs)} of {len(pids)} programmes have a description")
        if DETAILS_SAMPLE and (args.debug or not descs):
            sid, sdata = DETAILS_SAMPLE[0]
            print(f"First details response (programme id {sid}) -- paste this to the developer:\n",
                  repr(sdata)[:1500])

    if args.debug:
        for items in results.values():
            if items:
                print("Sample programme:", items[0])
                break

    run_no = None
    suffix = ""
    if args.run_ids or args.suffix is not None:
        run_no = args.suffix if args.suffix is not None else load_last_run() + 1
        suffix = f"-Run{run_no}"
    global TRANSLITERATE
    # Default: translate via the web service, and transliterate whatever it could not.
    TRANSLITERATE = not args.no_translate
    if not args.no_translate and not args.transliterate:
        translate_all(collect_texts(channels, results), use_cache=not args.no_cache)
    tv = build_xml(channels, results, args.lang_tag, suffix)
    if not args.no_translate:
        # Safety net: convert Greek in ANY element's text, whichever field it came from
        for el in tv.iter():
            if el.text and has_greek(el.text):
                el.text = tr(el.text)
        left = [el.text for el in tv.iter() if el.text and has_greek(el.text)]
        if left:
            print(f"WARNING: {len(left)} text(s) still contain Greek, e.g. {left[0]!r}",
                  file=sys.stderr)
    if not args.no_fix_caps:
        keep = KEEP_CAPS | {k.strip().upper() for k in args.keep.split(",") if k.strip()}
        for el in tv.iter():
            if el.tag in CAPS_TAGS and el.text:
                el.text = fix_caps(el.text, keep)
    ET.indent(tv)
    out_path = unique_path(args.output) if args.unique else Path(args.output)
    ET.ElementTree(tv).write(out_path, encoding="utf-8", xml_declaration=True)
    if run_no is not None:
        save_last_run(run_no)
    total = len(tv.findall("programme"))
    first = tv.find("channel")
    print(f"Wrote {total} programmes to {out_path}"
          + (f" - example channel id: {first.get('id')}" if first is not None else ""))
    if FAILED:
        print(f"WARNING: {len(FAILED)} request(s) failed; the guide has gaps. "
              "Try --workers 1 --delay 1", file=sys.stderr)


if __name__ == "__main__":
    main()

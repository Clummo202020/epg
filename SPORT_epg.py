#!/usr/bin/env python3
"""
SPORT_epg.py - XMLTV guide of sports TV in Israel (Sport 5), Greece (Novasports),
the Netherlands (ESPN, Ziggo Sport), Romania (Digi Sport, Prima Sport ...)
Bulgaria (MAX Sport, Diema Sport, Nova Sport, Ring ...) and the Balkans (Arena Sport,
Sport Klub).

ISRAEL - Sport 5's public broadcast sheet, one day at a time:
    https://www.sport5.co.il/Ajax/GetBroadcastSheetData.aspx?Type=&Date=YYYY-MM-DD
  Type empty = the "live" view: every live broadcast, grouped by channel.
  Channels: IL.5Sport, IL.5Plus, IL.5Live, IL.5Stars, IL.5Max, IL.5Gold ...
  Only live events are listed, so FILLER fills the gaps (2-hour blocks).

NETHERLANDS - Ziggo GO's public guide (already in English):
    channels: https://spark-prod-nl.gnp.cloud.ziggogo.tv/eng/web/linear-service/v2/channels?...
    events:   https://staticqbr-prod-nl.gnp.cloud.ziggogo.tv/eng/web/epg-service-lite/nl/en/
              events/segments/YYYYMMDDHH0000   (6-hour blocks, UTC)
  Only channels whose name matches --nl-channels (default: ESPN or Ziggo Sport).
  Channels: NL.ESPN, NL.ESPN2, NL.ZiggoSport, NL.ZiggoSportTotaal ...

ROMANIA - Cinemagia's TV programme pages (server-built HTML), one page per channel and day:
    https://www.cinemagia.ro/program-tv/digi-sport-1/          (today)
    https://www.cinemagia.ro/program-tv/digi-sport-1/vineri/   (next days, by weekday name)
  Each page shows a few channels side by side; all of them are read at once.
  Channels chosen with --ro-channels (default: the whole Cinemagia sports column).
  Romanian titles are translated; "LIVE" in a title marks a live event.
  Channels: RO.DigiSport1 ... RO.PrimaSport5

BALKANS - Arena Sport's own TV page (Serbian feed), all channels and 7 days in one page:
    https://tvarenasport.com/tv-scheme    (the data is the window.TV_SCHEMES object)
  Arena Sport 1-10, Arena Premium 1-5, Arena Tenis, Adrenalin, Arena 1X2.
  "uzivo" marks a live event. Serbian text is translated.
  Channels: RS.ArenaSport1 ... RS.ArenaPremium1 ... RS.ArenaTenis, RS.Adrenalin

SPORT KLUB - Delo's TV guide (Slovenia), one page per channel and day:
    https://tvspored.delo.si/oddaje/sk1/vsi/vsi/20261016
  Channels chosen with --sk-channels (default SK 1-10; ones the site doesn't have are skipped).
  Slovenian text is translated. Channels: SI.SK1 ... SI.SK10

BULGARIA - тв-програма.bg (server-built HTML), one page per channel and day:
    https://www.xn----8sbafg9clhjcp.bg/tv/diema-sport/          (today)
    https://www.xn----8sbafg9clhjcp.bg/tv/diema-sport/Петък/    (next days, by weekday name)
  Channels chosen with --bg-channels (default: MAX Sport 1-4, MAX One, Diema Sport 1-3,
  Nova Sport, Ring, BNT 3, bTV Action, Eurosport 1-2). Bulgarian text is translated;
  "На живо" in the listing marks a live event.
  Channels: BG.MaxSport1 ... BG.DiemaSport, BG.NovaSport, BG.Ring ...

GREECE - Novasports' TV programme (novasports.gr/tv-program), one day at a time:
    https://www.novasports.gr/wp-admin/admin-ajax.php?action=nova_get_template
        &template=tv-program/broadcast&dt=YYYY-MM-DD
  The full schedule of every channel on the page (Novasports, Eurosport,
  Magenta Sport ...). Channels: GR.NovasportsPrime, GR.Novasports1HD ...
  Programmes run back to back, so no filler is needed.

Both:
  * Hebrew / Greek titles are translated to English (free Google endpoint,
    cached in SPORT_translations.json next to this script). --no-translate keeps them.
  * Times are converted to UK time; descriptions also give local time.
  * FIXED CHANNEL IDS and a fixed file name (SPORT_epg.xml). --run-ids gives fresh
    ids (IL.5Sport-Run3, GR.NovasportsPrime-Run3) when PlaylistLabs must replace
    programmes it already holds; --unique gives a new file name each run.

Usage:
    python3 SPORT_epg.py                  # all countries, next 7 days -> SPORT_epg.xml
    python3 SPORT_epg.py --no-israel      # leave out Israel (also --no-greece, --no-netherlands, --no-romania, --no-bulgaria, --no-arena, --no-sportklub)
    python3 SPORT_epg.py --days 10
    python3 SPORT_epg.py --debug          # print what was read for each day

Only the Python standard library is needed. On Windows: pip install tzdata
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
SHEET_URL = "https://www.sport5.co.il/Ajax/GetBroadcastSheetData.aspx"
PAGE_URL = "https://www.sport5.co.il/html/pages/broadcastsheet.html"
ISRAEL = ZoneInfo("Asia/Jerusalem")
ATHENS = ZoneInfo("Europe/Athens")
NOVA_URL = "https://www.novasports.gr/wp-admin/admin-ajax.php"
NOVA_PAGE = "https://www.novasports.gr/tv-program/"
AMSTERDAM = ZoneInfo("Europe/Amsterdam")
BUCHAREST = ZoneInfo("Europe/Bucharest")
SOFIA = ZoneInfo("Europe/Sofia")
BELGRADE = ZoneInfo("Europe/Belgrade")
LJUBLJANA = ZoneInfo("Europe/Ljubljana")
DELO_PAGE = "https://tvspored.delo.si/oddaje/{slug}/vsi/vsi/{day:%Y%m%d}"
SK_DEFAULT = ",".join(f"sk{i}" for i in range(1, 11))
ARENA_PAGE = "https://tvarenasport.com/tv-scheme"
BG_SITE = "https://www.xn----8sbafg9clhjcp.bg/tv/{slug}/{day}"
BG_WEEKDAYS = ["Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота", "Неделя"]
BG_CHANNELS = {          # page name on the site -> channel name
    "max-sport-1": "MAX Sport 1", "max-sport-2": "MAX Sport 2", "max-sport-3": "MAX Sport 3",
    "max-sport-4": "MAX Sport 4", "max-one": "MAX One",
    "diema-sport": "Diema Sport", "diema-sport-2": "Diema Sport 2", "diema-sport-3": "Diema Sport 3",
    "nova-sport": "Nova Sport", "ring-bg": "Ring", "bnt3": "BNT 3", "btv-action": "bTV Action",
    "eurosport": "Eurosport 1", "eurosport2": "Eurosport 2",
}
CINEMAGIA = "https://www.cinemagia.ro/program-tv/{slug}/{day}"
# Every channel in Cinemagia's "sports" column (HD duplicates left out: same schedule).
RO_DEFAULT = ("digi-sport-1,digi-sport-2,digi-sport-3,digi-sport-4,digi-4k,"
              "prima-sport-1,prima-sport-2,prima-sport-3,prima-sport-4,prima-sport-5,"
              "prima-sport-ppv1,prima-sport-ppv2,prima-sport-ppv3,prima-sport-ppv4,"
              "eurosport-1,eurosport-2,eurosport-4k,tvr-sport-hd,sport-extra,"
              "extreme-sports-channel,nautical-channel,pro-arena,"
              "auto-motor-und-sport-channel,fast-fun-box-hd")
RO_WEEKDAYS = ["luni", "marti", "miercuri", "joi", "vineri", "sambata", "duminica"]
ZIGGO_CHANNELS = ("https://spark-prod-nl.gnp.cloud.ziggogo.tv/eng/web/linear-service/v2/channels"
                  "?cityId=65535&language=en&productClass=Orion-DASH&platform=web")
ZIGGO_SEGMENT = ("https://staticqbr-prod-nl.gnp.cloud.ziggogo.tv/eng/web/epg-service-lite/nl/en/"
                 "events/segments/{stamp}")
ZIGGO_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                 "Origin": "https://www.ziggogo.tv", "Referer": "https://www.ziggogo.tv/",
                 "Accept": "application/json"}
LONDON = ZoneInfo("Europe/London")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": PAGE_URL,
    "Accept": "text/html, */*; q=0.01",
}

OUTPUT_NAME = "SPORT_epg.xml"
HERE = os.path.dirname(os.path.abspath(__file__))
RUN_STATE_FILE = os.path.join(HERE, "SPORT_epg_run.json")
CACHE_FILE = os.path.join(HERE, "SPORT_translations.json")
OLD_CACHE_FILE = os.path.join(HERE, "israel_translations.json")   # read once if the new one is missing

# Channel logo file on the site -> (channel id part, English name).
# Unknown logos still work: the id comes from the file name, the name from its alt text.
KNOWN_CHANNELS = {
    "SPORT5_CHANNEL": ("5Sport", "Sport 5"),
    "SPORT5_PLUS": ("5Plus", "Sport 5 Plus"),
    "SPORT5_LIVE": ("5Live", "Sport 5 Live"),
    "SPORT5_STARS": ("5Stars", "Sport 5 Stars"),
    "SPORT5_MAX": ("5Max", "Sport 5 Max"),
    "SPORT5_GOLD": ("5Gold", "Sport 5 Gold"),
    "SPORT5_MOBILE": ("5Mobile", "Sport 5 Mobile"),
    "SPORT5_4K": ("5Sport4K", "Sport 5 4K"),
}

DEFAULT_MINUTES = 120     # event length when the next event isn't sooner
FILLER_HOURS = 2          # longest filler block


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ssl_context()


def get_text(url, params, retries=3, headers=None):
    full = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers=headers or HEADERS)
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (400, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(getattr(e, "reason", e))
        time.sleep(2 * (attempt + 1))
    print(f"  WARNING: could not fetch {full}: {last}", file=sys.stderr)
    return None


# --------------------------------------------------------------------------
# Parsing the broadcast sheet
# --------------------------------------------------------------------------
class SheetParser(HTMLParser):
    """Collects (channel_key, channel_alt, time_text, title, is_live) rows."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.channel_key = None
        self.channel_alt = None
        self._in_header = False
        self._td_class = None
        self._row = None
        self._date_text = []
        self._title_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "tr":
            self._in_header = "tr-header" in cls
            self._row = None if self._in_header else {"live": False}
            self._date_text, self._title_text = [], []
        elif tag == "img":
            src = a.get("src") or ""
            if self._in_header and "/channels/" in src.lower():
                name = os.path.basename(src)
                name = re.sub(r"\.(svg|png|jpe?g|gif|webp)$", "", name, flags=re.I)
                name = re.sub(r"_(white|black|color|colour|logo)$", "", name, flags=re.I)
                self.channel_key = name.upper()
                self.channel_alt = (a.get("alt") or a.get("title") or "").strip()
            elif self._row is not None and "img-live" in src.lower():
                self._row["live"] = True
        elif tag == "td" and self._row is not None:
            self._td_class = "date" if "date" in cls else "text" if "text" in cls else None

    def handle_endtag(self, tag):
        if tag == "td":
            self._td_class = None
        elif tag == "tr" and self._row is not None:
            when = re.search(r"\b(\d{1,2}):(\d{2})\b", " ".join(self._date_text))
            title = re.sub(r"\s+", " ", "".join(self._title_text)).strip()
            if when and title and self.channel_key:
                self.rows.append((self.channel_key, self.channel_alt,
                                  int(when.group(1)), int(when.group(2)),
                                  title, self._row["live"]))
            self._row = None

    def handle_data(self, data):
        if self._td_class == "date":
            self._date_text.append(data)
        elif self._td_class == "text":
            self._title_text.append(data)


def fetch_day(day, sheet_type, debug=False):
    html = get_text(SHEET_URL, {"Type": sheet_type, "Date": day.isoformat()})
    if not html:
        return []
    p = SheetParser()
    p.feed(html)
    if debug:
        print(f"  {day}: {len(p.rows)} rows")
        for r in p.rows[:5]:
            print("    ", r)
    return p.rows


# --------------------------------------------------------------------------
# Greece: Novasports TV programme
# --------------------------------------------------------------------------
LOOKALIKE = str.maketrans("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧαβεικνορτυχ", "ABEZHIKMNOPTYXabeiknoptyx")
NOVA_HEADERS = {**HEADERS, "Referer": NOVA_PAGE, "X-Requested-With": "XMLHttpRequest"}
TOKEN = re.compile(
    r'class="channel-title[^"]*">\s*(?P<ch>[^<]+?)\s*</div>'
    r'|class="(?P<cls>tv-broadcast[^"]*)"')


def clean(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_unescape(text)).strip()


def html_unescape(text):
    import html
    return html.unescape(text)


def parse_nova(page):
    """[(channel_name, hh, mm, title, subtitle, live)] from the channels view."""
    rows, channel = [], None
    marks = list(TOKEN.finditer(page))
    for i, m in enumerate(marks):
        if m.group("ch"):
            channel = clean(m.group("ch")).translate(LOOKALIKE)
            channel = re.sub(r"^Novasports(?=\S)", "Novasports ", channel)     # Novasports1HD
            channel = re.sub(r"(\d)(HD)$", r"\1 \2", channel)                  # -> Novasports 1 HD
            continue
        cls = m.group("cls").split()
        if channel is None or "column" in cls:      # "column" = the events view
            continue
        end = marks[i + 1].start() if i + 1 < len(marks) else len(page)
        block = page[m.end():end]
        t = re.search(r'class="time">\s*(\d{1,2}):(\d{2})', block)
        title = re.search(r'class="title">(.*?)</div>', block, re.S)
        sub = re.search(r'class="subtitle[^"]*">(.*?)</div>', block, re.S)
        if not (t and title):
            continue
        name = clean(title.group(1))
        live = "live-now" in block or bool(re.search(r"\((Ζ|Z)\)", name))
        name = re.sub(r"\s*\((Ζ|Z)\)\s*", " ", name).strip()     # (Ζ) = live
        rows.append((channel, int(t.group(1)), int(t.group(2)), name,
                     clean(sub.group(1)) if sub else "", live))
    return rows


def fetch_greece(days, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    channels = {}
    for day in days:
        page = get_text(NOVA_URL, {"action": "nova_get_template",
                                   "template": "tv-program/broadcast",
                                   "dt": day.isoformat()}, headers=NOVA_HEADERS)
        rows = parse_nova(page) if page else []
        if debug:
            print(f"  Greece {day}: {len(rows)} rows")
            for r in rows[:5]:
                print("    ", r)
        last = {}
        for ch, hh, mm, title, sub, live in rows:
            start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=ATHENS)
            if ch in last and start < last[ch]:      # past midnight
                start += timedelta(days=1)
            last[ch] = start
            channels.setdefault(ch, []).append(
                {"start": start.astimezone(timezone.utc), "title": title, "sub": sub, "live": live})
    for ch, evs in channels.items():
        seen, uniq = set(), []
        for ev in sorted(evs, key=lambda e: e["start"]):
            if ev["start"] not in seen:
                seen.add(ev["start"])
                uniq.append(ev)
        channels[ch] = uniq
    return channels


# --------------------------------------------------------------------------
# Netherlands: Ziggo GO guide (ESPN, Ziggo Sport)
# --------------------------------------------------------------------------
def get_json_url(url, headers):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(2 * (attempt + 1))
    print(f"  WARNING: could not fetch {url}", file=sys.stderr)
    return None


def ziggo_channels(pattern):
    """{channel_code: name} for channels whose name matches pattern."""
    data = get_json_url(ZIGGO_CHANNELS, ZIGGO_HEADERS)
    items = data if isinstance(data, list) else (data or {}).get("channels") or []
    wanted, rx = {}, re.compile(pattern, re.I)
    for ch in items:
        if not isinstance(ch, dict):
            continue
        code = ch.get("id") or ch.get("channelId") or ch.get("stationId")
        name = (ch.get("name") or ch.get("title") or ch.get("channelName")
                or ch.get("stationName") or "")
        if code and name and rx.search(name):
            wanted[code] = name.strip()
    return wanted


def fetch_netherlands(days, pattern, debug=False):
    """{channel_name: [{start, stop, title, sub, live}]}"""
    names = ziggo_channels(pattern)
    if debug:
        print(f"  Netherlands: {len(names)} matching channels: {sorted(set(names.values()))}")
    if not names:
        return {}
    events = {code: {} for code in names}
    for day in days:
        for hour in (0, 6, 12, 18):
            stamp = f"{day:%Y%m%d}{hour:02d}0000"
            data = get_json_url(ZIGGO_SEGMENT.format(stamp=stamp), ZIGGO_HEADERS) or {}
            for entry in data.get("entries") or []:
                code = entry.get("channelId")
                if code not in events:
                    continue
                for ev in entry.get("events") or []:
                    try:
                        start = datetime.fromtimestamp(int(ev["startTime"]), timezone.utc)
                        stop = datetime.fromtimestamp(int(ev["endTime"]), timezone.utc)
                    except (KeyError, TypeError, ValueError):
                        continue
                    title = (ev.get("title") or "").strip()
                    series = (ev.get("seriesName") or "").strip()
                    if title and stop > start:
                        events[code][start] = {
                            "start": start, "stop": stop, "title": title,
                            "sub": series if series and series != title else "",
                            "live": bool(ev.get("isLive"))}
            if debug:
                print(f"  Netherlands {stamp}: {len(data.get('entries') or [])} channels in block")
    out = {}
    for code, evs in events.items():
        if not evs:
            continue
        name = names[code]
        if name in out:                         # same name twice (e.g. SD and HD): keep the fuller one
            if len(evs) <= len(out[name]):
                continue
        out[name] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Romania: Cinemagia programme pages
# --------------------------------------------------------------------------
def parse_cinemagia(page):
    """({slug: name}, {slug: [(hh, mm, title)]}) for every channel column on the page."""
    import html as _html
    names, order = {}, []
    for m in re.finditer(r'id="([a-z0-9-]+)-logo-\d+"[^>]*>.*?alt="([^"]+)"', page, re.S):
        if m.group(1) not in names:
            names[m.group(1)] = _html.unescape(m.group(2)).strip()
            order.append(m.group(1))
    out = {k: [] for k in order}
    for row in re.split(r'<tr id="showContainer-[A-Z]+"', page)[1:]:
        tables = row.split('class="events"')[1:]
        for idx, t in enumerate(tables[:len(order)]):
            for m in re.finditer(r'<td class="ora">\s*<div>(\d{1,2}):(\d{2})</div>.*?'
                                 r'<div class="title">(.*?)</div>', t, re.S):
                title = re.sub(r"\s+", " ",
                               _html.unescape(re.sub(r"<[^>]+>", " ", m.group(3)))).strip()
                if title:
                    out[order[idx]].append((int(m.group(1)), int(m.group(2)), title))
    return names, out


def fetch_romania(days, slugs, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    wanted = [x.strip() for x in slugs.split(",") if x.strip()]
    today = datetime.now(BUCHAREST).date()
    names, events = {}, {s: {} for s in wanted}
    for day in days:
        offset = (day - today).days
        if offset < 0 or offset > 6:
            continue                                   # the site offers today + 6 days
        day_part = "" if offset == 0 else RO_WEEKDAYS[day.weekday()] + "/"
        done = set()
        for slug in wanted:
            if slug in done:
                continue
            page = get_text(CINEMAGIA.format(slug=slug, day=day_part).rstrip("?"), {},
                            headers={"User-Agent": HEADERS["User-Agent"],
                                     "Accept-Language": "ro-RO,ro;q=0.9"})
            if not page:
                continue
            page_names, cols = parse_cinemagia(page)
            names.update(page_names)
            for col_slug, rows in cols.items():
                if col_slug not in events or col_slug in done:
                    continue
                done.add(col_slug)
                last = None
                for hh, mm, title in rows:
                    start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=BUCHAREST)
                    if last and start < last:          # past midnight
                        start += timedelta(days=1)
                    last = start
                    live = bool(re.match(r"\s*live\b", title, re.I))
                    clean_title = re.sub(r"^\s*live\s*[:\-]?\s*", "", title, flags=re.I) or title
                    events[col_slug][start.astimezone(timezone.utc)] = {
                        "start": start.astimezone(timezone.utc), "title": clean_title,
                        "sub": "", "live": live}
            if debug:
                print(f"  Romania {day} {slug}: columns {list(cols)}")
    out = {}
    for slug, evs in events.items():
        if evs:
            out[names.get(slug, slug.replace("-", " ").title())] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Bulgaria: тв-програма.bg channel pages
# --------------------------------------------------------------------------
def parse_bg(page):
    """[(hh, mm, title, info, live)] from one channel page."""
    import html as _html
    rows = []
    for m in re.finditer(r'<div class="programTime">\s*(?:<span[^>]*>)?\s*(\d{1,2}):(\d{2}).*?'
                         r'<a href="/predavane/[^"]*">(.*?)</a>', page, re.S):
        body = m.group(3)
        strong = re.search(r"<strong>(.*?)</strong>(.*)", body, re.S)
        text = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
        if strong:
            title, rest = text(strong.group(1)), text(strong.group(2))
            extra = re.match(r"^(:[^:]*?)?\s*(?:-\s+(.*))?$", rest)
            if extra and extra.group(1):
                title = f"{title}: {extra.group(1)[1:].strip()}"
            info = (extra.group(2) if extra else rest) or ""
        else:
            title, info = text(body), ""
        live = bool(re.search(r"на живо|пряко", info, re.I))
        if title:
            rows.append((int(m.group(1)), int(m.group(2)), title, info, live))
    return rows


def fetch_bulgaria(days, slugs, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    wanted = [x.strip() for x in slugs.split(",") if x.strip()]
    today = datetime.now(SOFIA).date()
    out = {}
    for slug in wanted:
        evs = {}
        for day in days:
            offset = (day - today).days
            if offset < 0 or offset > 6:
                continue
            day_part = "" if offset == 0 else urllib.parse.quote(BG_WEEKDAYS[day.weekday()]) + "/"
            page = get_text(BG_SITE.format(slug=slug, day=day_part), {},
                            headers={"User-Agent": HEADERS["User-Agent"],
                                     "Accept-Language": "bg-BG,bg;q=0.9"})
            rows = parse_bg(page) if page else []
            if debug:
                print(f"  Bulgaria {slug} {day}: {len(rows)} rows")
            last = None
            for hh, mm, title, info, live in rows:
                start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=SOFIA)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title, "sub": info, "live": live}
        if evs:
            out[BG_CHANNELS.get(slug, slug.replace("-", " ").title())] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Balkans: Arena Sport TV page
# --------------------------------------------------------------------------
def fetch_arena(days, debug=False):
    """{channel_name: [{start, title, sub, live}]} for the dates in days."""
    page = get_text(ARENA_PAGE, {}, headers={"User-Agent": HEADERS["User-Agent"],
                                             "Accept-Language": "sr-RS,sr;q=0.9"})
    if not page:
        return {}
    i = page.find("window.TV_SCHEMES")
    if i < 0:
        print("  WARNING: Arena Sport page has no TV_SCHEMES data", file=sys.stderr)
        return {}
    try:
        data, _ = json.JSONDecoder().raw_decode(page[page.index("{", i):])
    except ValueError:
        print("  WARNING: could not read Arena Sport data", file=sys.stderr)
        return {}
    wanted = {d.isoformat() for d in days}
    out = {}
    for channel, info in data.items():
        evs = {}
        for day_str, day in sorted((info.get("days") or {}).items()):
            if day_str not in wanted:
                continue
            y, mo, d = map(int, day_str.split("-"))
            last = None
            for e in day.get("emisije") or []:
                tm = re.match(r"(\d{1,2}):(\d{2})", e.get("time") or "")
                title = (e.get("content") or "").strip()
                if not (tm and title):
                    continue
                start = datetime(y, mo, d, int(tm.group(1)), int(tm.group(2)), tzinfo=BELGRADE)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                sub = " - ".join(x for x in ((e.get("sport") or "").strip(),
                                             (e.get("category") or "").strip()) if x)
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title, "sub": sub,
                            "live": (e.get("description") or "").lower() == "uzivo"}
        if debug:
            print(f"  Arena {channel}: {len(evs)} programmes")
        if evs:
            out[channel.strip()] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Sport Klub: Delo TV guide (Slovenia)
# --------------------------------------------------------------------------
def parse_delo(page):
    """(channel_name, [(hh, mm, title, genre)])"""
    import html as _html
    name = re.search(r'itemtype="https://schema.org/TelevisionChannel".*?itemprop="name"[^>]*>(.*?)</h2>',
                     page, re.S)
    rows = []
    for block in re.findall(r'itemtype="https://schema.org/BroadcastEvent">(.*?)</a>', page, re.S):
        t = re.search(r'itemprop="startDate"[^>]*>\s*(\d{1,2}):(\d{2})', block)
        n = re.search(r'itemprop="name"[^>]*>(.*?)</div>', block, re.S)
        g = re.search(r'class="text-text text-sm[^"]*">(.*?)</div>', block, re.S)
        clean = lambda x: re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
        if t and n and clean(n.group(1)):
            rows.append((int(t.group(1)), int(t.group(2)), clean(n.group(1)),
                         clean(g.group(1)) if g else ""))
    return (clean(name.group(1)) if name else None), rows


def fetch_sportklub(days, slugs, debug=False):
    """{channel_name: [{start, title, sub, live}]}"""
    out = {}
    for slug in [x.strip() for x in slugs.split(",") if x.strip()]:
        evs, chname = {}, None
        for day in days:
            page = get_text(DELO_PAGE.format(slug=slug, day=day), {},
                            headers={"User-Agent": HEADERS["User-Agent"],
                                     "Accept-Language": "sl-SI,sl;q=0.9"}, retries=2)
            name, rows = parse_delo(page) if page else (None, [])
            chname = chname or name
            if debug:
                print(f"  Sport Klub {slug} {day}: {len(rows)} rows")
            if not rows:
                if day == days[0]:
                    break                        # channel not on the site
                continue
            # The first row can be the end of the previous evening (e.g. 23:00 before 00:30)
            prev_day = len(rows) > 1 and (rows[0][0], rows[0][1]) > (rows[1][0], rows[1][1]) \
                and rows[0][0] >= 12
            last = None
            for i, (hh, mm, title, genre) in enumerate(rows):
                d = day - timedelta(days=1) if (i == 0 and prev_day) else day
                start = datetime(d.year, d.month, d.day, hh, mm, tzinfo=LJUBLJANA)
                if last and start < last:
                    start += timedelta(days=1)
                last = start
                key = start.astimezone(timezone.utc)
                evs[key] = {"start": key, "title": title,
                            "sub": genre.replace("•", "-"), "live": False}
        if evs:
            out[chname or slug.upper()] = [evs[k] for k in sorted(evs)]
    return out


# --------------------------------------------------------------------------
# Translation (Hebrew / Greek -> English), cached
# --------------------------------------------------------------------------
FOREIGN = re.compile(r"[\u0590-\u05FF\u0370-\u03FF\u1F00-\u1FFF\u0400-\u04FF]")  # Hebrew, Greek, Cyrillic
TRANSLATIONS = {}


def load_cache():
    path = CACHE_FILE if os.path.exists(CACHE_FILE) else OLD_CACHE_FILE
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        TRANSLATIONS.update({k: v for k, v in data.items() if isinstance(v, str)})
    except (OSError, ValueError):
        pass


def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TRANSLATIONS, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError as e:
        print(f"WARNING: could not save translations: {e}", file=sys.stderr)


def google_translate(text):
    params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text}
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    for attempt in range(2):
        try:
            time.sleep(1.0)
            req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as resp:
                data = json.load(resp)
            out = "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
            if out:
                return out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return None          # rate limited: keep Hebrew this run
        except (urllib.error.URLError, TimeoutError, ValueError, IndexError, TypeError):
            pass
        time.sleep(3 * (attempt + 1))
    return None


def translate_all(texts, force=()):
    """Translate texts in Hebrew/Greek script, plus everything in force (e.g. Romanian)."""
    todo = sorted({t for t in texts if t and FOREIGN.search(t) and t not in TRANSLATIONS} |
                  {t for t in force if t and t not in TRANSLATIONS})
    if todo:
        print(f"Translating {len(todo)} new text(s) (about {int(len(todo) * 1.5)}s)...")
    done = 0
    for t in todo:
        out = google_translate(t)
        if out:
            TRANSLATIONS[t] = out
            done += 1
    if todo:
        print(f"  translated {done}/{len(todo)}")
        save_cache()


def en(text):
    return TRANSLATIONS.get(text, text)


# --------------------------------------------------------------------------
# Building programmes
# --------------------------------------------------------------------------
def collect(days, sheet_type, debug):
    """{channel_key: {"alt":..., "events":[{start, title, live}]}}"""
    channels = {}
    for day in days:
        rows = fetch_day(day, sheet_type, debug)
        last = {}
        for key, alt, hh, mm, title, live in rows:
            start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=ISRAEL)
            # a time earlier than the previous one on the same channel is after midnight
            if key in last and start < last[key]:
                start += timedelta(days=1)
            last[key] = start
            ch = channels.setdefault(key, {"alt": alt, "events": []})
            ch["events"].append({"start": start.astimezone(timezone.utc),
                                 "title": title, "live": live})
    for ch in channels.values():
        seen, uniq = set(), []
        for ev in sorted(ch["events"], key=lambda e: e["start"]):
            k = (ev["start"], ev["title"])
            if k not in seen:
                seen.add(k)
                uniq.append(ev)
        ch["events"] = uniq
    return channels


# Tidy ids and English names for the logos seen on the site (by id part).
NICE_NAMES = {
    "5Sport": "Sport 5", "5Plus": "Sport 5 Plus", "5Live": "Sport 5 Live",
    "5Stars": "Sport 5 Stars", "5Max": "Sport 5 Max", "5Gold": "Sport 5 Gold",
    "5Mobile": "Sport 5 Mobile", "5Radio": "Sport 5 Radio", "5Site": "Sport 5 Website",
    "5Sport4K": "Sport 5 4K", "54K": "Sport 5 4K",
}


def channel_ident(key, alt):
    if key in KNOWN_CHANNELS:
        part, name = KNOWN_CHANNELS[key]
    else:
        part = re.sub(r"[^A-Za-z0-9]+", "", key.title()) or "Channel"
        name = en(alt) if alt else key.replace("_", " ").title()
    part = re.sub(r"Channel$", "", part) or part      # 5MaxChannel -> 5Max
    return part, NICE_NAMES.get(part, name)


def xmltv_time(dt):
    return dt.astimezone(LONDON).strftime("%Y%m%d%H%M%S %z")


def add_programme(tv, cid, start, stop, title, sub, desc, live):
    p = ET.SubElement(tv, "programme", {
        "start": xmltv_time(start), "stop": xmltv_time(stop), "channel": cid})
    ET.SubElement(p, "title", {"lang": "en"}).text = title
    if sub:
        ET.SubElement(p, "sub-title", {"lang": "en"}).text = sub
    ET.SubElement(p, "desc", {"lang": "en"}).text = desc
    ET.SubElement(p, "category", {"lang": "en"}).text = "Sports"
    if live:
        ET.SubElement(p, "category", {"lang": "en"}).text = "Live"


def filler_blocks(start, stop):
    cur = start
    while cur < stop:
        local = cur.astimezone(LONDON).replace(minute=0, second=0, microsecond=0)
        boundary = local + timedelta(hours=FILLER_HOURS - local.hour % FILLER_HOURS)
        nxt = min(boundary.astimezone(timezone.utc), stop)
        if nxt <= cur:
            nxt = min(cur + timedelta(hours=1), stop)
        yield cur, nxt
        cur = nxt


def build_xmltv(records, suffix, minutes):
    """records: [{id, name, tz, place, filler, back_to_back, events:[{start,title,sub,live}]}]"""
    tv = ET.Element("tv", {"generator-info-name": "SPORT_epg.py",
                           "source-info-name": "Sport 5 (IL), Novasports (GR), Ziggo GO (NL), Cinemagia (RO), tv-programa.bg (BG), Arena Sport (RS), Delo (SI)"})
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    count, listed = 0, []
    for rec in records:
        cid, name = f"{rec['id']}{suffix}", rec["name"]
        listed.append((cid, name))
        c = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(c, "display-name", {"lang": "en"}).text = name

        evs = rec["events"]
        last_stop = None
        for i, ev in enumerate(evs):
            start = ev["start"]
            if last_stop and start < last_stop:
                start = last_stop
            nxt = evs[i + 1]["start"] if i + 1 < len(evs) else None
            if ev.get("stop"):
                stop = ev["stop"]
            elif rec["back_to_back"] and nxt and nxt - ev["start"] <= timedelta(hours=6):
                stop = nxt
            else:
                stop = ev["start"] + timedelta(minutes=minutes)
                if nxt and nxt < stop:
                    stop = nxt
            if stop <= start:
                continue
            title = en(ev["title"])
            sub = en(ev.get("sub") or "") or None
            loc = ev["start"].astimezone(rec["tz"])
            uk = ev["start"].astimezone(LONDON)
            when = f"{uk:%a %d %b, %H:%M}"
            orig = f" Original title: {ev['title']}." if title != ev["title"] else ""
            desc = (f"{'LIVE. ' if ev['live'] else ''}{sub + '. ' if sub else ''}{name}, "
                    f"{when} UK ({loc:%H:%M} {rec['place']}).{orig}")
            if rec["filler"]:
                for a, b in filler_blocks(last_stop or now, start):
                    add_programme(tv, cid, a, b, f"{title} ({when})", "Coming up",
                                  f"Upcoming on {name}: {title}, {when} UK "
                                  f"({loc:%H:%M} {rec['place']}).", False)
                    count += 1
            add_programme(tv, cid, start, stop, title,
                          sub or ("Live" if ev["live"] else None), desc, ev["live"])
            count += 1
            last_stop = stop
    return tv, count, listed


def write_xml(tv, path):
    ET.indent(tv, space="  ")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(ET.tostring(tv, encoding="unicode") + "\n")
    if ET.parse(path).getroot().tag != "tv":
        sys.exit(f"ERROR: {path} did not write correctly")


def load_last_run():
    try:
        with open(RUN_STATE_FILE, encoding="utf-8") as f:
            return int(json.load(f)["last_run"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_last_run(n):
    try:
        with open(RUN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_run": n}, f)
    except OSError as e:
        print(f"WARNING: could not save run number: {e}", file=sys.stderr)


def unique_path(path):
    stem, ext = os.path.splitext(path)
    while True:
        cand = f"{stem}_{datetime.now(LONDON):%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:6]}{ext}"
        if not os.path.exists(cand):
            return cand


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="XMLTV guide of sports TV in Israel and Greece.")
    ap.add_argument("--out", default=OUTPUT_NAME, help=f"output file (default {OUTPUT_NAME})")
    ap.add_argument("--unique", action="store_true", help="new file name each run")
    ap.add_argument("--days", type=int, default=7, help="days to cover from today (default 7)")
    ap.add_argument("--minutes", type=int, default=DEFAULT_MINUTES,
                    help=f"event length if the next event isn't sooner (default {DEFAULT_MINUTES})")
    ap.add_argument("--type", default="", help="Sport 5 sheet Type value (default empty = live view)")
    ap.add_argument("--no-israel", action="store_true", help="leave out the Sport 5 channels")
    ap.add_argument("--no-greece", action="store_true", help="leave out the Novasports page channels")
    ap.add_argument("--no-netherlands", action="store_true", help="leave out the Ziggo GO channels")
    ap.add_argument("--no-romania", action="store_true", help="leave out the Romanian channels")
    ap.add_argument("--no-bulgaria", action="store_true", help="leave out the Bulgarian channels")
    ap.add_argument("--no-arena", action="store_true", help="leave out the Arena Sport channels")
    ap.add_argument("--no-sportklub", action="store_true", help="leave out the Sport Klub channels")
    ap.add_argument("--sk-channels", default=SK_DEFAULT,
                    help="Delo channel names from the page address, comma separated (default sk1-sk10)")
    ap.add_argument("--bg-channels", default=",".join(BG_CHANNELS),
                    help="тв-програма.bg channel names from the page address, comma separated")
    ap.add_argument("--ro-channels", default=RO_DEFAULT,
                    help="Cinemagia channel names from the page address, comma separated "
                         "(default: every channel in Cinemagia's sports column)")
    ap.add_argument("--nl-channels", default=r"ESPN|Ziggo Sport",
                    help="which Ziggo channels to include, by name (default: 'ESPN|Ziggo Sport')")
    ap.add_argument("--no-filler", action="store_true", help="no programmes between Israeli events")
    ap.add_argument("--no-translate", action="store_true", help="keep Hebrew / Greek titles")
    ap.add_argument("--run-ids", action="store_true", help="fresh ids with a run number")
    ap.add_argument("--suffix", type=int, default=None, help="run ids with this run number")
    ap.add_argument("--debug", action="store_true", help="print rows read for each day")
    args = ap.parse_args()

    il_days = [datetime.now(ISRAEL).date() + timedelta(days=i) for i in range(max(args.days, 1))]
    gr_days = [datetime.now(ATHENS).date() + timedelta(days=i) for i in range(max(args.days, 1))]

    il = {}
    if not args.no_israel:
        print(f"Israel: reading Sport 5 broadcast sheet {il_days[0]} to {il_days[-1]} ...")
        il = collect(il_days, args.type, args.debug)
        print(f"  {sum(len(c['events']) for c in il.values())} broadcasts on {len(il)} channel(s)")
    gr = {}
    if not args.no_greece:
        print(f"Greece: reading Novasports TV programme {gr_days[0]} to {gr_days[-1]} ...")
        gr = fetch_greece(gr_days, args.debug)
        print(f"  {sum(len(v) for v in gr.values())} programmes on {len(gr)} channel(s)")
    nl = {}
    if not args.no_netherlands:
        nl_days = [datetime.now(timezone.utc).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Netherlands: reading Ziggo GO guide {nl_days[0]} to {nl_days[-1]} ...")
        nl = fetch_netherlands(nl_days, args.nl_channels, args.debug)
        print(f"  {sum(len(v) for v in nl.values())} programmes on {len(nl)} channel(s)")
    ro = {}
    if not args.no_romania:
        ro_days = [datetime.now(BUCHAREST).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Romania: reading Cinemagia {ro_days[0]} to {ro_days[-1]} ...")
        ro = fetch_romania(ro_days, args.ro_channels, args.debug)
        print(f"  {sum(len(v) for v in ro.values())} programmes on {len(ro)} channel(s)")
    bg = {}
    if not args.no_bulgaria:
        bg_days = [datetime.now(SOFIA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Bulgaria: reading тв-програма.bg {bg_days[0]} to {bg_days[-1]} ...")
        bg = fetch_bulgaria(bg_days, args.bg_channels, args.debug)
        print(f"  {sum(len(v) for v in bg.values())} programmes on {len(bg)} channel(s)")
    arena = {}
    if not args.no_arena:
        ar_days = [datetime.now(BELGRADE).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Balkans: reading Arena Sport TV page {ar_days[0]} to {ar_days[-1]} ...")
        arena = fetch_arena(ar_days, args.debug)
        print(f"  {sum(len(v) for v in arena.values())} programmes on {len(arena)} channel(s)")
    sk = {}
    if not args.no_sportklub:
        sk_days = [datetime.now(LJUBLJANA).date() + timedelta(days=i) for i in range(max(args.days, 1))]
        print(f"Sport Klub: reading Delo TV guide {sk_days[0]} to {sk_days[-1]} ...")
        sk = fetch_sportklub(sk_days, args.sk_channels, args.debug)
        print(f"  {sum(len(v) for v in sk.values())} programmes on {len(sk)} channel(s)")
    if not il and not gr and not nl and not ro and not bg and not arena and not sk:
        sys.exit("Nothing found - the sites may be unreachable from here, or changed.")

    if not args.no_translate:
        load_cache()
        texts = [e["title"] for c in il.values() for e in c["events"]]
        texts += [c["alt"] for c in il.values()]
        texts += [t for evs in gr.values() for e in evs for t in (e["title"], e["sub"])]
        texts += [t for evs in bg.values() for e in evs for t in (e["title"], e["sub"])]
        force = [e["title"] for evs in ro.values() for e in evs]
        force += [t for evs in arena.values() for e in evs for t in (e["title"], e["sub"])]
        force += [t for evs in sk.values() for e in evs for t in (e["title"], e["sub"])]
        translate_all(texts, force=force)

    records = []
    for key, ch in il.items():
        part, name = channel_ident(key, ch["alt"])
        records.append({"id": f"IL.{part}", "name": name, "tz": ISRAEL, "place": "Israel",
                        "filler": not args.no_filler, "back_to_back": False,
                        "events": [dict(e, sub="") for e in ch["events"]]})
    for chname, evs in gr.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"GR.{part}", "name": chname, "tz": ATHENS, "place": "Greece",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in sk.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"SI.{part}", "name": chname.replace("SK ", "Sport Klub "),
                        "tz": LJUBLJANA, "place": "Slovenia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in arena.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"RS.{part}", "name": chname, "tz": BELGRADE, "place": "Serbia",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in bg.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"BG.{part}", "name": chname, "tz": SOFIA, "place": "Bulgaria",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in ro.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"RO.{part}", "name": chname, "tz": BUCHAREST, "place": "Romania",
                        "filler": False, "back_to_back": True, "events": evs})
    for chname, evs in nl.items():
        part = re.sub(r"[^A-Za-z0-9]+", "", chname) or "Channel"
        records.append({"id": f"NL.{part}", "name": chname, "tz": AMSTERDAM, "place": "NL",
                        "filler": False, "back_to_back": True, "events": evs})
    records.sort(key=lambda r: r["id"])

    run_no, suffix = None, ""
    if args.run_ids or args.suffix is not None:
        run_no = args.suffix if args.suffix is not None else load_last_run() + 1
        suffix = f"-Run{run_no}"

    tv, count, listed = build_xmltv(records, suffix, args.minutes)
    out_path = unique_path(args.out) if args.unique else args.out
    write_xml(tv, out_path)
    if run_no is not None:
        save_last_run(run_no)

    print(f"\nWrote {out_path}: {len(listed)} channels, {count} programmes")
    for cid, name in listed:
        print(f"  {cid:<32} {name}")


if __name__ == "__main__":
    main()

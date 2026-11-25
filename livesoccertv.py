#!/usr/bin/env python3
"""livesoccertv.py - channels by country from livesoccertv.com for the football reference page fixtures.html (25 Nov 2026).

Used by liveonsat_fixtures.py (same workflow, same file). LiveOnSat stays the list of fixtures and its own channel list; this adds, per
fixture, `cc` = {"UK": [...], "IE": [...], "US": [...], ...} from LiveSoccerTV's match page ("International Coverage" table: every country,
plain HTML, not tied to the visitor's country). fixtures.html shows those channels FIRST and LiveOnSat's after them.

How (a small hobby site: one request every LSTV_PAUSE seconds, at most LSTV_MAX_PAGES match pages per run, browser-like User-Agent):
  1. /schedules/<date>/ for today .. +LSTV_DAYS_AHEAD (6, as far as LiveOnSat's football pages go): every row has an id, the kick-off as a UTC epoch (the `dv` attribute - the page's own
     times are in the visitor's zone, the epoch is not), "A vs B" and the match link.
  2. each LiveOnSat fixture is paired with a row: kick-off within 20 minutes AND team names alike (see `pair`).
  3. the match page of each paired fixture is read (soonest first) and kept in `lstv_cache` (id -> {"t": fetch time, "cc": {...}}); a page is
     read again after LSTV_REFRESH_NEAR hours when the match is within a day, otherwise after LSTV_REFRESH_FAR hours.
Anything that fails keeps what was there. A 403 / 429 / captcha stops the whole step for the run (logged) - the page then simply shows
LiveOnSat's channels as before.
"""
import difflib, html as htmllib, re, time, unicodedata, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

BASE = "https://www.livesoccertv.com"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-GB,en;q=0.9"}
LSTV_DAYS_AHEAD = 6
LSTV_MAX_PAGES = 90
LSTV_PAUSE = 3.0
LSTV_REFRESH_NEAR, LSTV_REFRESH_FAR = 5, 20            # hours
LSTV_KEEP_HOURS = 36                                    # cache entries for matches older than this are dropped
PAIR_MINUTES = 20
COMP_PAGES = ["/competitions/england/premier-league/", "/competitions/england/championship/", "/competitions/england/league-one/",
              "/competitions/england/league-two/", "/competitions/england/fa-cup/", "/competitions/england/football-league-cup/",
              "/competitions/scotland/premier-league/", "/competitions/scotland/fa-cup/",
              "/competitions/international/uefa-champions-league/", "/competitions/international/uefa-europa-league/",
              "/competitions/international/uefa-europa-conference-league/"]

# LiveSoccerTV's country names -> the short keys fixtures.html uses (display order there)
STATUS = {}        # what the last run() did - liveonsat_fixtures.py stores it in the JSON ("lstv_status") for guide_health.py

COUNTRIES = {"Great Britain": "UK", "United Kingdom": "UK", "Ireland Republic": "IE", "Ireland": "IE", "USA": "US", "United States": "US", "Canada": "CA",
             "New Zealand": "NZ", "Australia": "AU", "Singapore": "SG", "Hong Kong": "HK", "India": "IN", "Malaysia": "MY", "Thailand": "TH",
             "Indonesia": "ID", "Cyprus": "CY"}
# beIN MENA English: the English-commentary channels (beIN Sports English 1 / 2) from the Middle East / North Africa rows, one line for all of them
MENA = {"Algeria", "Bahrain", "Egypt", "Iraq", "Jordan", "Kuwait", "Lebanon", "Libya", "Morocco", "Oman", "Palestine", "Qatar", "Syria", "Tunisia",
        "United Arab Emirates", "Yemen", "Saudi Arabia", "Iran"}
CARIBBEAN = {"Jamaica", "Trinidad and Tobago", "Barbados", "Bahamas", "Antigua and Barbuda", "Cayman Islands", "Bermuda", "Grenada", "Saint Lucia",
             "St. Vincent / Grenadines", "Saint Kitts and Nevis", "Dominica", "Anguilla", "Aruba", "Montserrat", "British Virgin Islands",
             "Turks and Caicos Islands", "Suriname"}
# Only British and UEFA football is looked up (user, 25 Nov 2026)
WANTED_COMP = re.compile(r"^(English|Scottish|Welsh|Irish|Northern Ireland|Northern Irish|UEFA|Europa League|Champions League|Conference League)\b|"
                         r"^(Emirates |Isuzu |Vanarama |England |Scotland |Wales )?(FA Cup|FA Trophy|Carabao|EFL|Premier League|Championship|League One|League Two|National League|Premiership|Scottish|"
                         r"Champions League|Europa League|Conference League|Youth League|Nations League)\b", re.I)
# (anchored 25 Nov 2026: unanchored, "Ukrainian Premier League" and "South African Premiership" were looked up as British football)


# "AFC Champions League Elite" / "CAF Champions League" are not UEFA football (25 Nov 2026: they were being looked up as if they were)
OTHER_CONFED = re.compile(r"(?i)^(AFC|CAF|CONCACAF|CONMEBOL|OFC|Asian|African)\b|\b(AFC|CAF|CONCACAF|CONMEBOL) (Champions|Cup|Challenge)")


def fetch(url):
    """(status, text). Never raises."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        print(f"  {url}: {e}")
        return 0, ""


# ---------------------------------------------------------------------------------------------------------------- parsing
ROW = re.compile(r'<tr id="(\d+)" class="matchrow[^"]*"(.*?)</tr>', re.S)      # also "matchrow livematch" (a game under way) - 25 Nov 2026


def parse_schedule(text):
    """[{id, epoch (UTC seconds), a, b, comp, href, has_tv}] from a /schedules/ page."""
    out = []
    for m in ROW.finditer(text):
        rid, body = m.group(1), m.group(2)
        dv = re.search(r"dv='(\d{10,13})'", body)
        link = re.search(r'<a href="(/match/[^"#]+)[^"]*"[^>]*title="([^"]+)"', body)
        if not dv or not link:
            continue
        title = htmllib.unescape(link.group(2))
        sides = re.split(r"\s+vs\.?\s+", title, maxsplit=1)
        if len(sides) != 2:
            continue
        comp = re.search(r'class="complogocell[^>]*>.*?title="([^"]+)"', body, re.S)
        out.append({"id": rid, "epoch": int(dv.group(1)) // 1000, "a": sides[0].strip(), "b": sides[1].strip(),
                    "comp": htmllib.unescape(comp.group(1)) if comp else "", "href": link.group(1),
                    "has_tv": 'data-has-tv="1"' in m.group(0)})
    return out


def parse_match(text):
    """{country name: [channel names]} from a match page's "International Coverage" table (all countries)."""
    i = text.find("id='dynamic-international-tv'")
    if i < 0:
        return None
    seg = text[i:]
    seg = seg[:seg.find("</table>")] if "</table>" in seg else seg
    out = {}
    for flag, name, cell in re.findall(r'<span class="flag ([^"]+)">([^<]+)</span></td><td valign=\'top\'>(.*?)</td></tr>', seg, re.S):
        chans = [htmllib.unescape(c).strip() for c in re.findall(r'<a href="/channels/[^"]*"[^>]*>([^<]+)</a>', cell)]
        if chans:
            out[htmllib.unescape(name).strip()] = chans
    return out


def wanted(table):
    """{"UK": [...], ...} - only the countries fixtures.html shows (English-commentary markets); a channel listed twice is kept once.
    CY keeps Cytavision Sports only; ME = beIN Sports English from the MENA rows; CB = the Caribbean rows together."""
    cc = {}

    def add(key, chans):
        have = cc.setdefault(key, [])
        for c in chans:
            if c not in have:
                have.append(c)
    for name, chans in (table or {}).items():
        key = COUNTRIES.get(name)
        if key == "CY":
            chans = [c for c in chans if re.search(r"(?i)cytavision sport", c)]
        if key:
            add(key, chans)
        if name in MENA:
            add("ME", [c for c in chans if re.search(r"(?i)bein sports english", c)])
        if name not in CARIBBEAN:       # any channel named "Caribbean" (ESPN Caribbean, Disney+ Premium Caribbean ...) from any row
            add("CB", [c for c in chans if re.search(r"(?i)caribbean", c)])
        if name in CARIBBEAN:
            add("CB", [c for c in chans if not re.search(r"(?i)norte|espa[nñ]ol", c)])        # the Spanish-language ESPN feeds are left out
    return {k: v for k, v in cc.items() if v}


# ---------------------------------------------------------------------------------------------------------------- pairing
_DROP = re.compile(r"\b(?:fc|cf|afc|sc|ac|as|cd|fk|sk|bk|sv|vfb|vfl|tsv|ssc|ud|rc|rcd|us|ss|1|the|de|del|la|el|club|calcio|sporting club)\b")
_ALIAS = {"manchester utd": "manchester united", "man utd": "manchester united", "man united": "manchester united", "man city": "manchester city",
          "psg": "paris saint germain", "paris st germain": "paris saint germain", "paris sg": "paris saint germain", "spurs": "tottenham",
          "tottenham hotspur": "tottenham", "inter": "internazionale", "inter milan": "internazionale", "sporting lisbon": "sporting cp",
          "sporting": "sporting cp", "wolves": "wolverhampton", "atletico madrid": "atletico", "atl madrid": "atletico", "ath madrid": "atletico",
          "slavia prague": "slavia praha", "red bull salzburg": "salzburg", "rb salzburg": "salzburg", "rb leipzig": "leipzig",
          "bayern munich": "bayern", "borussia dortmund": "dortmund", "bor dortmund": "dortmund", "olympiakos": "olympiacos",
          "olympiakos piraeus": "olympiacos", "club brugge": "brugge", "club bruges": "brugge", "newcastle united": "newcastle",
          "west ham united": "west ham", "brighton hove albion": "brighton", "brighton and hove albion": "brighton",
          "nottingham forest": "nottm forest", "nottingham": "nottm forest", "sheffield united": "sheffield utd", "sheffield wednesday": "sheffield wed"}


def norm(name):
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("&", " and ").replace(".", " ").replace("-", " ").replace("'", "")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bu ?(\d\d)\b", r"u\1", s)             # "U-19" / "U 19" / "U19"
    s = _ALIAS.get(s, s)
    t = re.sub(r"\s+", " ", _DROP.sub(" ", s)).strip() or s
    return _ALIAS.get(t, t)


def sim(x, y):
    x, y = (re.sub(r"\bu\d\d\b", "", norm(v)).strip() or norm(v) for v in (x, y))      # the age tag is compared by youth_tag(), not here
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    r = difflib.SequenceMatcher(None, x, y).ratio()
    xs, ys = set(x.split()), set(y.split())
    if xs and ys and (xs <= ys or ys <= xs):
        r = max(r, 0.85)                         # "Sporting" in "Sporting CP", "Barcelona" in "FC Barcelona"
    return r


def youth_tag(*names):
    return any(re.search(r"(?i)\bU-?\d{2}\b|\bunder[- ]?\d{2}\b|\bwomen\b|\(w\)|\bw$", n or "") for n in names)


def pair(fx, rows):
    """The LSTV row for LiveOnSat fixture fx ({start ISO, a, b}), else None. Same kick-off (within PAIR_MINUTES) and alike teams; the sides may
    come either way round. A same-time row whose one team is alike (>= 0.8) and the other not wholly different (>= 0.4) also counts when no
    other row at that time does."""
    try:
        ko = datetime.fromisoformat(fx["start"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return None
    best, loose = None, []
    for r in rows:
        if abs(r["epoch"] - ko) > PAIR_MINUTES * 60:
            continue
        if youth_tag(fx["a"], fx["b"]) != youth_tag(r["a"], r["b"]):
            continue
        s1 = min(sim(fx["a"], r["a"]), sim(fx["b"], r["b"]))
        s2 = min(sim(fx["a"], r["b"]), sim(fx["b"], r["a"]))
        s = max(s1, s2)
        if s >= 0.62 and (best is None or s > best[0]):
            best = (s, r)
        else:
            hi = max(sim(fx["a"], r["a"]), sim(fx["a"], r["b"]), sim(fx["b"], r["a"]), sim(fx["b"], r["b"]))
            lo = max(min(sim(fx["a"], r["a"]), sim(fx["b"], r["b"])), min(sim(fx["a"], r["b"]), sim(fx["b"], r["a"])))
            if hi >= 0.8 and lo >= 0.4:
                loose.append((hi + lo, r))
    if best:
        return best[1]
    if len(loose) == 1:
        return loose[0][1]
    return None


# ---------------------------------------------------------------------------------------------------------------- the run
def run(fixtures, cache, now=None, fetcher=fetch, sleeper=time.sleep):
    """Attach `cc` to each fixture in `fixtures` (LiveOnSat football rows, changed in place) and return the new cache.
    `cache` = {lstv id: {"t": ISO fetch time, "ko": ISO kick-off, "cc": {...}}}. Prints what it did."""
    now = now or datetime.now(timezone.utc)
    cache = {k: v for k, v in (cache or {}).items()
             if isinstance(v, dict) and v.get("ko") and datetime.fromisoformat(v["ko"]) > now - timedelta(hours=LSTV_KEEP_HOURS)}
    rows, days_ok = [], 0
    blocked = False
    ok_days, unpaired = set(), []
    for n in range(0, LSTV_DAYS_AHEAD + 1):
        day = (now + timedelta(days=n)).strftime("%Y-%m-%d")
        status, text = fetcher(f"{BASE}/schedules/{day}/")
        sleeper(LSTV_PAUSE)
        if status in (403, 429, 503) or (status == 200 and "matchrow" not in text and re.search(r"(?i)captcha|just a moment|access denied", text)):
            blocked = True
            print(f"  LiveSoccerTV: {day} refused (HTTP {status}) - step stopped, LiveOnSat's channels only")
            break
        if status != 200:
            print(f"  LiveSoccerTV: schedule {day}: HTTP {status}")
            continue
        got = parse_schedule(text)
        eps = sorted(g["epoch"] for g in got)
        print(f"  LiveSoccerTV {day}: HTTP {status}, {len(text)} bytes, {len(got)} rows, {sum(1 for g in got if g['has_tv'])} with TV, "
              f"{sum(1 for g in got if g['comp'])} with a competition name"
              + (f", kick-offs {datetime.fromtimestamp(eps[0], timezone.utc):%d %b %H:%M} - {datetime.fromtimestamp(eps[-1], timezone.utc):%d %b %H:%M} UTC" if eps else "")
              + f", {text.count('matchrow')} 'matchrow' marks in the page")
        if got:
            days_ok += 1
            ok_days.add(day)
        rows.extend(got)
    # Backup source (25 Nov 2026): a day page can come back thin (Fri 27 Nov: 24 rows against ~45 in a browser, no Forest v Chelsea). The
    # competition pages list their next fixtures with the same row markup, so when British / UEFA fixtures are left unpaired those pages are read too.
    if not blocked:
        def _left():
            out = []
            for fx in fixtures:
                try:
                    k = datetime.fromisoformat(fx["start"].replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                if now < k <= now + timedelta(hours=(LSTV_DAYS_AHEAD + 1) * 24) and WANTED_COMP.search(fx.get("comp") or "") \
                        and not OTHER_CONFED.search(fx.get("comp") or "") and not pair(fx, rows):
                    out.append(fx)
            return out
        left = _left()
        if left:
            print(f"  LiveSoccerTV: {len(left)} British / UEFA fixture(s) unpaired after the day pages - reading competition pages as a backup")
            for path in COMP_PAGES:
                if not _left():
                    break
                status, text = fetcher(f"{BASE}{path}")
                sleeper(LSTV_PAUSE)
                if status in (403, 429, 503):
                    print(f"  LiveSoccerTV {path}: refused (HTTP {status}) - backup stopped")
                    break
                got = parse_schedule(text) if status == 200 else []
                have = {r["id"] for r in rows}
                new = [g for g in got if g["id"] not in have]
                rows.extend(new)
                print(f"  LiveSoccerTV {path}: HTTP {status}, {len(text)} bytes, {len(got)} rows, {len(new)} not on the day pages, "
                      f"{text.count('matchrow')} 'matchrow' marks")
    uniq = {r["id"]: r for r in rows}
    rows = list(uniq.values())
    horizon = now + timedelta(hours=(LSTV_DAYS_AHEAD + 1) * 24)
    todo, paired, used = [], 0, set()
    for fx in fixtures:
        try:
            ko = datetime.fromisoformat(fx["start"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if ko > horizon or ko < now - timedelta(hours=3):
            continue
        if not WANTED_COMP.search(fx.get("comp") or "") or OTHER_CONFED.search(fx.get("comp") or ""):
            continue
        r = pair(fx, rows) if rows else None
        if not r and ko <= now:
            # under way / just finished: LiveSoccerTV's schedule rows for live games may look different, and the match is no use to the page
            # as a miss (25 Nov 2026: 88 "unpaired", all of today's kicked-off games). Keep what was found before; do not report it.
            fx["_keep_cc"] = True
            continue
        if not r:
            if ko.strftime("%Y-%m-%d") in ok_days:      # only for days whose LiveSoccerTV schedule page was read
                unpaired.append(f"{ko:%a %d %b %H:%M} {fx.get('a')} v {fx.get('b')} ({(fx.get('comp') or '')[:35]})")
            continue
        paired += 1
        fx["_lstv"] = r
        used.add(r["id"])
        c = cache.get(r["id"])
        age = (now - datetime.fromisoformat(c["t"])).total_seconds() / 3600 if c else None
        limit = LSTV_REFRESH_NEAR if ko - now < timedelta(hours=24) else LSTV_REFRESH_FAR
        if r["has_tv"] and (c is None or age >= limit):
            todo.append((ko, r))
    # rows with TV that LiveOnSat does not list at all (Youth League, lower leagues ...): added as fixtures of their own (src "lstv") once their
    # channels are known; never when a LiveOnSat fixture at that time has a team alike (a pairing that failed would otherwise show a match twice)
    extras = []
    for r in rows:
        if r["id"] in used or not r["has_tv"] or not WANTED_COMP.search(r["comp"] or "") or OTHER_CONFED.search(r["comp"] or ""):
            continue
        ko = datetime.fromtimestamp(r["epoch"], timezone.utc)
        if ko > horizon or ko < now - timedelta(hours=3):
            continue
        dup = any(abs((datetime.fromisoformat(f["start"].replace("Z", "+00:00")) - ko).total_seconds()) <= 3600 and
                  max(sim(f["a"], r["a"]), sim(f["a"], r["b"]), sim(f["b"], r["a"]), sim(f["b"], r["b"])) >= 0.5
                  for f in fixtures if f.get("start") and f.get("src") != "lstv")
        if dup:
            continue
        extras.append(r)
        c = cache.get(r["id"])
        age = (now - datetime.fromisoformat(c["t"])).total_seconds() / 3600 if c else None
        limit = LSTV_REFRESH_NEAR if ko - now < timedelta(hours=24) else LSTV_REFRESH_FAR
        if c is None or age >= limit:
            todo.append((ko, r))
    todo.sort(key=lambda x: x[0])
    read, fails = 0, 0
    seen = set()
    for ko, r in todo:
        if blocked or read >= LSTV_MAX_PAGES:
            break
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        status, text = fetcher(BASE + r["href"])
        sleeper(LSTV_PAUSE)
        if status in (403, 429, 503):
            blocked = True
            print(f"  LiveSoccerTV: match page refused (HTTP {status}) - stopped after {read} page(s)")
            break
        table = parse_match(text) if status == 200 else None
        if table is None:
            fails += 1
            if fails <= 3:       # what came back, so a failure can be understood from the log
                print(f"  LiveSoccerTV: match page {r['href']}: HTTP {status}, {len(text)} bytes, 'International Coverage' "
                      f"{'present' if 'International Coverage' in text else 'absent'}, 'dynamic-match' {'present' if 'dynamic-match' in text else 'absent'}; "
                      f"start: {re.sub(chr(10), ' ', text[:200])!r}")
            if fails >= 5 and read == 0:
                print("  LiveSoccerTV: five match pages in a row gave no channel table - step stopped")
                break
            continue
        read += 1
        cache[r["id"]] = {"t": now.strftime("%Y-%m-%dT%H:%M:%S+00:00"), "ko": ko.strftime("%Y-%m-%dT%H:%M:%S+00:00"), "cc": wanted(table)}
    with_cc = 0
    for fx in fixtures:
        r = fx.pop("_lstv", None)
        c = cache.get(r["id"]) if r else None
        keep = fx.pop("_keep_cc", None) and not r
        if c and c.get("cc"):
            fx["cc"] = c["cc"]
            with_cc += 1
        elif "cc" in fx and not r and not keep:
            fx.pop("cc", None)                    # no longer paired - do not keep stale channels
    added = 0
    for r in extras:
        c = cache.get(r["id"])
        if c and c.get("cc"):
            fixtures.append({"sport": "Football", "comp": r["comp"], "a": r["a"], "b": r["b"], "ch": [], "src": "lstv", "cc": c["cc"],
                             "start": datetime.fromtimestamp(r["epoch"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
            added += 1
    print(f"  LiveSoccerTV: {added} fixture(s) LiveOnSat does not list added")
    print(f"  LiveSoccerTV: {len(rows)} schedule rows ({days_ok} day page(s)), {paired} fixtures paired, {read} match page(s) read, "
          f"{with_cc} fixtures carry channels")
    if unpaired:                      # UK / UEFA fixtures with no LiveSoccerTV row (25 Nov 2026, user): a name the matcher did not recognise shows up here
        print(f"  LiveSoccerTV: {len(unpaired)} UK / UEFA fixture(s) found no LiveSoccerTV row:")
        for u in unpaired[:25]:
            print(f"    - {u}")
    STATUS.clear()
    STATUS.update({"ran": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "rows": len(rows), "days_ok": days_ok, "paired": paired, "read": read,
                   "with_cc": with_cc, "blocked": blocked, "failed_pages": fails, "unpaired": unpaired[:40], "unpaired_n": len(unpaired)})
    return cache

#!/usr/bin/env python3
"""
One-off check, round 3 (4 Nov 2026) - NOT part of the guides. Run once from the GitHub runner, read the log, delete.

Round 2 found how YourTV's pay-TV choice works: the page's own JavaScript calls
   GET /api/regions/<payRegionId>/channels     (channel list of a pay-TV service)
   GET /api/guide/?region=<id>&...             (the guide)
with pay region ids 168 = Foxtel, 371 = Foxtel Now, 192 = Optus TV feat. Foxtel, 284 = Fetch.
(ontvtonight sent the runner an EMPTY page - no title, no body - so it is dropped.)
Round 3 tries those calls for Foxtel (168) and prints: channel names (Fox Sports / ESPN?), how many days the guide
returns, and what one programme looks like. Read-only, about 30 small GET requests. Nothing is written to the repo.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = "https://www.yourtv.com.au"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
SPORT_RE = re.compile(r"fox|espn|kayo|sport|cricket|footy|league|racing|bein", re.I)


def get(path, accept="application/json, text/javascript, */*; q=0.01"):
    url = path if path.startswith("http") else BASE + path
    hdrs = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-AU,en;q=0.9",
            "Referer": BASE + "/guide/", "X-Requested-With": "XMLHttpRequest"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", "replace") if e.fp else "")
    except Exception as e:
        return 0, "ERROR %s: %s" % (type(e).__name__, e)


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


def ctx(text, pattern, width=130, limit=8):
    out = []
    for m in re.finditer(pattern, text):
        out.append(squash(text[max(0, m.start() - width):m.end() + width]))
        if len(out) >= limit:
            break
    return out


def head(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def as_json(body):
    try:
        return json.loads(body)
    except Exception:
        return None


def describe(data, label):
    if isinstance(data, list):
        print("  %s: list of %d" % (label, len(data)))
        if data:
            first = data[0]
            print("  first item: %s" % json.dumps(first)[:900])
            if isinstance(first, dict):
                print("  item fields: %s" % list(first.keys()))
    elif isinstance(data, dict):
        print("  %s: object keys %s" % (label, list(data.keys())[:30]))
        for k, v in list(data.items())[:6]:
            print("   %s -> %s" % (k, json.dumps(v)[:400]))
    else:
        print("  %s: %s" % (label, type(data)))


def names_of(items):
    out = []
    for c in items:
        if isinstance(c, dict):
            out.append(str(c.get("name") or c.get("description") or c.get("displayName") or c.get("title") or "?"))
    return out


def hints():
    head("1. where the guide call gets its parameters (page + JS bundle)")
    st, page = get("/guide/", accept="text/html")
    for s in ctx(page, r'(?i)ftaRegion|data-region-id|"regionId"', 100, 6):
        print("  page: " + s[:300])
    m = re.search(r'src="(/js/bundle-[^"]+\.js)"', page)
    if not m:
        return
    st2, js = get(m.group(1), accept="*/*")
    print("  bundle HTTP %s, %d bytes" % (st2, len(js)))
    for label, pat in [("getGuide( callers", r'getGuide\('), ("ftaRegionId", r'ftaRegionId'),
                       ("payRegionId", r'payRegionId'), ("channel id params", r'channelIds|channels:'),
                       ("date/day/time params", r'(?:startTime|endTime|dayRoute|date:|day:)')]:
        hits = ctx(js, pat, 140, 6)
        print("-- %s (%d shown) --" % (label, len(hits)))
        for s in hits:
            print("  " + s[:420])


def probe_regions():
    head("2. channel lists: /api/regions/<id>/channels")
    channels = {}
    for rid, name in ((168, "Foxtel"), (371, "Foxtel Now"), (192, "Optus TV feat. Foxtel"), (284, "Fetch")):
        st, body = get("/api/regions/%d/channels" % rid)
        data = as_json(body)
        print("GET /api/regions/%d/channels (%s) -> HTTP %s, %d bytes" % (rid, name, st, len(body)))
        if st != 200 or data is None:
            print("  body: %r" % body[:200])
            continue
        items = data if isinstance(data, list) else (data.get("channels") or data.get("data") or [])
        describe(data, "channels")
        names = names_of(items)
        sporty = [n for n in names if SPORT_RE.search(n)]
        print("  %d channels; sport-looking (%d): %s" % (len(names), len(sporty), ", ".join(sporty)[:900]))
        if rid == 168:
            channels = items
            print("  ALL Foxtel channel names: %s" % ", ".join(names)[:1800])
    return channels


def probe_guide(chan_items):
    head("3. guide: /api/guide/ for Foxtel (region 168)")
    today = date.today()
    first_ok = None
    ok_days = []
    forms = [
        "/api/guide/?day=%s&region=168",
        "/api/guide/?day=%s&timezone=Australia/Sydney&format=json&region=168",
        "/api/guide/?date=%s&region=168",
    ]
    chosen = None
    for form in forms:
        st, body = get(form % today.isoformat())
        print("try %s -> HTTP %s, %d bytes, start %r" % (form % today.isoformat(), st, len(body), body[:100]))
        if st == 200 and as_json(body) is not None:
            chosen = form
            break
    if not chosen:
        print("no working guide url form - see the bundle hints in section 1")
        return
    print("using form: %s" % chosen)
    for i in range(-1, 12):
        d = (today + timedelta(days=i)).isoformat()
        st, body = get(chosen % d)
        data = as_json(body)
        n = None
        if data is not None:
            n = len(data) if isinstance(data, list) else len(data.keys())
        print("  %s -> HTTP %s, %7d bytes, items=%s" % (d, st, len(body), n))
        if st == 200 and n:
            ok_days.append(d)
            if first_ok is None:
                first_ok = data
    print("days with data: %d %s" % (len(ok_days), (ok_days[0] + " .. " + ok_days[-1]) if ok_days else ""))
    if first_ok is None:
        return
    head("4. what one day of the Foxtel guide contains")
    items = first_ok if isinstance(first_ok, list) else (first_ok.get("channels") or first_ok.get("data") or [])
    describe(first_ok, "guide")
    names = names_of(items)
    print("  channel names in the guide (%d): %s" % (len(names), ", ".join(names)[:1500]))
    sporty = [n for n in names if re.search(r"fox|espn", n, re.I)]
    print("  FOX / ESPN channels: %s" % sporty)
    for c in items:
        if isinstance(c, dict) and re.search(r"fox sports 503|fox footy|espn$", str(c.get("name") or c.get("description") or ""), re.I):
            print("  sample channel %s keys: %s" % (c.get("name") or c.get("description"), list(c.keys())))
            for key in ("airings", "programs", "programmes", "events", "shows", "blocks"):
                v = c.get(key)
                if isinstance(v, list) and v:
                    print("  %d programmes in '%s'; first: %s" % (len(v), key, json.dumps(v[0])[:900]))
                    print("  last: %s" % json.dumps(v[-1])[:500])
                    break
            break


def main():
    print("Python %s" % sys.version.split()[0])
    hints()
    chans = probe_regions()
    probe_guide(chans)
    print("\nDONE")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
One-off check, round 4 (4 Nov 2026) - NOT part of the guides. Run once from the GitHub runner, read the log, delete.

Round 3 result: YourTV's Foxtel channel list (pay region 168) HAS every channel we need (Fox Sports 503/505/506/507,
Fox Footy, Fox Cricket, Fox League, Fox Sports News, ESPN, ESPN2). Its guide call is GET /api/guide/ with the
parameters day, timezone, format="html" and region - my first three guesses (no format / format=json) were 404.
Round 4 calls it the way the page's own JavaScript does and prints: what comes back, how many days ahead it goes,
the programmes of the Fox / ESPN channels for one day, and what /api/airings/<id> adds (description, end time).
Read-only, about 30 small GET requests to YourTV. Nothing is written to the repo.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "https://www.yourtv.com.au"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
WANT = re.compile(r"fox sports|fox footy|fox cricket|fox league|espn", re.I)


def get(path, accept):
    url = path if path.startswith("http") else BASE + path
    hdrs = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-AU,en;q=0.9",
            "Referer": BASE + "/guide/", "X-Requested-With": "XMLHttpRequest"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30) as r:
            return r.status, r.headers.get("Content-Type"), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.headers or {}).get("Content-Type"), (e.read().decode("utf-8", "replace") if e.fp else "")
    except Exception as e:
        return 0, None, "ERROR %s: %s" % (type(e).__name__, e)


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


def head(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


HTML_ACCEPT = "text/html, */*; q=0.01"
JSON_ACCEPT = "application/json, text/javascript, */*; q=0.01"


def qs(**kw):
    return "?" + urllib.parse.urlencode(kw)


def try_forms(day):
    head("1. the guide call, exactly as the page's JavaScript builds it")
    forms = [
        ("bundle form, Foxtel 168, Accept html", "/api/guide/" + qs(day=day, timezone="Australia/Sydney", format="html", region=168), HTML_ACCEPT),
        ("bundle form, Foxtel 168, Accept json", "/api/guide/" + qs(day=day, timezone="Australia/Sydney", format="html", region=168), JSON_ACCEPT),
        ("bundle form, Sydney FTA 73, Accept html", "/api/guide/" + qs(day=day, timezone="Australia/Sydney", format="html", region=73), HTML_ACCEPT),
        ("no format, Foxtel 168", "/api/guide/" + qs(day=day, timezone="Australia/Sydney", region=168), HTML_ACCEPT),
        ("format=json, Foxtel 168", "/api/guide/" + qs(day=day, timezone="Australia/Sydney", format="json", region=168), JSON_ACCEPT),
        ("trailing path /168/", "/api/guide/168/" + qs(day=day, timezone="Australia/Sydney", format="html"), HTML_ACCEPT),
        ("region path /api/regions/168/guide", "/api/regions/168/guide/" + qs(day=day, timezone="Australia/Sydney", format="html"), HTML_ACCEPT),
    ]
    good = None
    for label, path, acc in forms:
        st, ct, body = get(path, acc)
        print("%-42s HTTP %s %s, %d bytes" % (label, st, ct, len(body)))
        print("    %s" % path)
        print("    start: %r" % squash(body[:260]))
        if st == 200 and good is None and len(body) > 2000:
            good = (path, body)
    return good


def parse_html(body):
    """channel name -> list of (event_id, title, 'h:mm AM', style)."""
    out = {}
    parts = re.split(r'(?=data-channel-id=")', body)
    for p in parts[1:]:
        name = re.search(r'data-channel-name="([^"]*)"', p)
        num = re.search(r'data-channel-number="([^"]*)"', p)
        if not name:
            continue
        key = "%s (%s)" % (name.group(1), num.group(1) if num else "?")
        progs = []
        for m in re.finditer(r'<div class="guide__row__block[^"]*"([^>]*)>.*?<a class="show-link"[^>]*href="([^"]*)"[^>]*data-event-id="(\d+)"[^>]*>\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>', p, re.S):
            progs.append((m.group(3), squash(re.sub("<[^>]+>", "", m.group(4))), squash(m.group(5)), squash(m.group(1))))
        out.setdefault(key, []).extend(progs)
    return out


def reach(good_path):
    head("3. how many days ahead (Foxtel 168)")
    today = date.today()
    seen = []
    for i in range(-1, 14):
        d = (today + timedelta(days=i)).isoformat()
        path = re.sub(r"day=[0-9-]+", "day=" + d, good_path)
        st, ct, body = get(path, HTML_ACCEPT)
        chans = parse_html(body) if st == 200 else {}
        fox = {k: len(v) for k, v in chans.items() if WANT.search(k)}
        n_fox = sum(fox.values())
        print("  %s HTTP %s %7d bytes, %3d channels, Fox/ESPN channels %d with %d programmes" % (d, st, len(body), len(chans), len(fox), n_fox))
        if st == 200 and n_fox:
            seen.append(d)
    print("days with Fox / ESPN programmes: %d %s" % (len(seen), (seen[0] + " .. " + seen[-1]) if seen else ""))


def main():
    print("Python %s" % sys.version.split()[0])
    day = date.today().isoformat()
    good = try_forms(day)
    if not good:
        print("\nNo form returned a guide - stop here and tell Claude.")
        return
    path, body = good
    head("2. one day of the Foxtel guide: Fox / ESPN channels")
    chans = parse_html(body)
    print("%d channels parsed: %s" % (len(chans), ", ".join(sorted(chans))[:1400]))
    first_event = None
    for key in sorted(chans):
        if WANT.search(key):
            progs = chans[key]
            print("\n  %s: %d programmes" % (key, len(progs)))
            for ev, title, start, style in progs[:6]:
                print("    %s | %-9s | %s | %s" % (ev, start, title[:60], style[:70]))
            if first_event is None and progs:
                first_event = progs[0][0]
    reach(path)
    if first_event:
        head("4. /api/airings/<event id> (detail of one programme)")
        st, ct, b = get("/api/airings/%s" % first_event, JSON_ACCEPT)
        print("GET /api/airings/%s -> HTTP %s %s, %d bytes" % (first_event, st, ct, len(b)))
        try:
            data = json.loads(b)
            print("  keys: %s" % list(data.keys()) if isinstance(data, dict) else type(data))
            print("  %s" % json.dumps(data)[:1600])
        except Exception:
            print("  start: %r" % squash(b[:500]))
    print("\nDONE")


if __name__ == "__main__":
    main()

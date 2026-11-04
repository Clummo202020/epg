#!/usr/bin/env python3
"""
One-off check, round 5 (4 Nov 2026) - NOT part of the guides. Run once from the GitHub runner, read the log, delete.

Round 4: all 7 variants of GET /api/guide/ returned YourTV's 404 page (the channel-list call worked, so the runner is
not blocked). The page's JavaScript names its days with slugs (today / tomorrow / mon ...), so the guide call may only
accept those, not YYYY-MM-DD. Round 5 tries slugs, and also asks the normal /guide/ page for the Foxtel channels
(the page has a hidden form with 'region' and 'payRegion' fields), and prints how the JavaScript's ajax helper builds
its requests. Read-only, about 30 small GET requests to YourTV. Nothing is written to the repo.
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
    head("1. the guide call with day slugs and other region ids")
    good = None
    slugs = ["today", "tomorrow", "yesterday", day]
    n = 0
    for slug in slugs:
        for region in (168, 73):
            for fmt in ("html", None):
                kw = dict(day=slug, timezone="Australia/Sydney", region=region)
                if fmt:
                    kw["format"] = fmt
                path = "/api/guide/" + qs(**kw)
                st, ct, body = get(path, HTML_ACCEPT)
                n += 1
                print("%-92s HTTP %s %6d bytes %s" % (path[:92], st, len(body), "" if st == 200 else "(404 page)" if st == 404 else repr(body[:80])))
                if st == 200 and good is None and len(body) > 2000:
                    good = (path, body)
        if good:
            break
    return good


def page_probes():
    head("2. the normal /guide/ page with a pay region")
    for path in ("/guide/?payRegion=168", "/guide/?region=73&payRegion=168", "/guide/sydney/?payRegion=168",
                 "/guide/today/?payRegion=168&region=73"):
        st, ct, body = get(path, "text/html")
        fox = len(re.findall(r"(?i)fox sports|fox footy|espn", body))
        chans = len(re.findall(r'data-channel-id="', body))
        print("%-45s HTTP %s %7d bytes, channels in page: %d, Fox/ESPN mentions: %d" % (path, st, len(body), chans, fox))
    head("3. how the JavaScript's ajax helper builds a request")
    st, ct, page = get("/guide/", "text/html")
    m = re.search(r'src="(/js/bundle-[^"]+\.js)"', page)
    if not m:
        return
    st2, ct2, js = get(m.group(1), "*/*")
    for label, pat in [("xhr open / fetch", r'\.open\(|XMLHttpRequest\(\)|fetch\('),
                       ("custom headers", r'setRequestHeader|withCredentials'),
                       ("api base / prefix", r'["\'](?:/api|api/)["\']|apiBase|API_BASE|baseUrl'),
                       ("guide html consumer", r'format:\s*"html"|\.guide\b|getGuide')]:
        hits = []
        for mm in re.finditer(pat, js):
            hits.append(squash(js[max(0, mm.start() - 160):mm.end() + 220]))
            if len(hits) >= 4:
                break
        print("-- %s (%d shown) --" % (label, len(hits)))
        for h in hits:
            print("  " + h[:420])


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
    page_probes()
    if not good:
        print("\nNo /api/guide/ form returned a guide - tell Claude (sections 2 and 3 above show what else to try).")
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

#!/usr/bin/env python3
"""
One-off check, round 6 (4 Nov 2026) - NOT part of the guides. Run once from the GitHub runner, read the log, delete.

Round 5 WORKS: GET /api/guide/?day=today&timezone=Australia/Sydney&format=html&region=168 returns the Foxtel guide
(132 channels incl. all 10 Fox/ESPN ones; ISO dates were the 404 - the day must be a slug). GET /api/airings/<id>
gives UTC start, duration (minutes), title, episode title, synopsis, live / repeat flags. Two things are still open:
  1. 'today' only returned ~16:00 onwards (Sydney) - how do we get the WHOLE day? (slugs morning / afternoon /
     evening? weekday slugs?) and how many days ahead are there? (my round-5 loop reused 'today' by mistake)
  2. what do the live / matchId / repeat flags look like on real Fox Sports programmes?
Read-only, ~40 small GET requests to YourTV. Nothing is written to the repo.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.yourtv.com.au"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
WANT = re.compile(r"fox sports|fox footy|fox cricket|fox league|espn", re.I)
HTML_ACCEPT = "text/html, */*; q=0.01"
JSON_ACCEPT = "application/json, text/javascript, */*; q=0.01"


def get(path, accept):
    url = BASE + path
    hdrs = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-AU,en;q=0.9",
            "Referer": BASE + "/guide/", "X-Requested-With": "XMLHttpRequest"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", "replace") if e.fp else "")
    except Exception as e:
        return 0, "ERROR %s: %s" % (type(e).__name__, e)


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


def head(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def guide(slug, region=168):
    q = urllib.parse.urlencode(dict(day=slug, timezone="Australia/Sydney", format="html", region=region))
    return get("/api/guide/?" + q, HTML_ACCEPT)


def hhmm(minutes):
    minutes = int(round(minutes))
    d, m = divmod(minutes, 1440)
    return "%02d:%02d%s" % (m // 60, m % 60, ("+%dd" % d) if d else "")


def parse(body):
    """channel -> list of dict(id, title, start_text, width_pct, margin_left_pct)."""
    out = {}
    for p in re.split(r'(?=data-channel-id=")', body)[1:]:
        name = re.search(r'data-channel-name="([^"]*)"', p)
        if not name:
            continue
        blocks = []
        for m in re.finditer(r'<div class="guide__row__block[^"]*"\s*([^>]*)>.*?<a class="show-link"[^>]*data-event-id="(\d+)"[^>]*>\s*<h4>(.*?)</h4>\s*<p>(.*?)</p>', p, re.S):
            style = m.group(1)
            w = re.search(r'width:\s*([\d.]+)%', style)
            ml = re.search(r'margin-left:\s*(-?[\d.]+)%', style)
            blocks.append(dict(id=m.group(2), title=squash(re.sub("<[^>]+>", "", m.group(3))), start_text=squash(m.group(4)),
                               width=float(w.group(1)) if w else 0.0, ml=float(ml.group(1)) if ml else 0.0))
        out.setdefault(name.group(1), []).extend(blocks)
    return out


def window(blocks):
    """(first start, last end) in minutes from the grid's 00:00, from margin-left + widths."""
    if not blocks:
        return None
    start = blocks[0]["ml"] * 14.4
    total = sum(b["width"] + b["ml"] for b in blocks) * 14.4
    return start, total


def slug_test():
    head("1. which day slugs work, and how much of the day each returns (Fox / ESPN channels)")
    slugs = ["today", "yesterday", "tomorrow", "morning", "afternoon", "evening", "nownext",
             "wed", "thu", "fri", "sat", "sun", "mon", "tue"]
    keep = {}
    for slug in slugs:
        st, body = guide(slug)
        if st != 200:
            print("%-10s HTTP %s %r" % (slug, st, squash(body[:60])))
            continue
        ch = parse(body)
        fox = {k: v for k, v in ch.items() if WANT.search(k)}
        keep[slug] = fox
        n = sum(len(v) for v in fox.values())
        w503 = fox.get("FOX SPORTS 503 HD") or []
        wnd = window(w503)
        print("%-10s HTTP 200 %7d bytes, %3d channels, Fox/ESPN: %2d channels %3d programmes | Fox Sports 503 HD: %d programmes %s" % (
            slug, len(body), len(ch), len(fox), n, len(w503), ("%s .. %s" % (hhmm(wnd[0]), hhmm(wnd[1]))) if wnd else ""))
    return keep


def weekday_check(keep):
    head("2. Fox Sports 503 HD: titles and first start, per slug (is each slug a different day / part of day?)")
    for slug, fox in keep.items():
        w = fox.get("FOX SPORTS 503 HD") or []
        print("%-10s %s" % (slug, " | ".join("%s %s" % (b["start_text"], b["title"][:26]) for b in w[:4])))


def live_flags(keep):
    head("3. live / repeat / matchId flags on real programmes (airings of Fox Sports 503/Footy/League/Cricket)")
    fox = keep.get("tomorrow") or keep.get("today") or {}
    ids = []
    for name in ("FOX SPORTS 503 HD", "FOX FOOTY HD", "FOX League HD", "FOX Cricket HD", "FOX SPORTS 505 HD", "ESPN HD"):
        for b in (fox.get(name) or [])[:3]:
            ids.append((name, b["id"], b["title"]))
    for name, ev, title in ids[:16]:
        st, body = get("/api/airings/%s" % ev, JSON_ACCEPT)
        try:
            d = json.loads(body)
        except Exception:
            print("%s %s -> HTTP %s" % (name, ev, st))
            continue
        print("%-18s %-26s date=%s dur=%s live=%s repeat=%s new=%s matchId=%s epTitle=%r synopsis=%r" % (
            name, title[:26], d.get("date"), d.get("duration"), d.get("live"), d.get("repeat"), d.get("newEpisode"),
            d.get("matchId"), (d.get("episodeTitle") or "")[:40], (d.get("synopsis") or "")[:70]))


def bundle_dayparts():
    head("4. day / time-of-day names in the JavaScript")
    st, page = get("/guide/", "text/html")
    m = re.search(r'src="(/js/bundle-[^"]+\.js)"', page)
    if not m:
        return
    st2, js = get(m.group(1), "*/*")
    for label, pat in [("daySlug list", r'daySlug'), ("morning/afternoon/evening", r'"(?:morning|afternoon|evening)"')]:
        n = 0
        for mm in re.finditer(pat, js):
            print("  %s: %s" % (label, squash(js[max(0, mm.start() - 120):mm.end() + 260])[:420]))
            n += 1
            if n >= 3:
                break


def main():
    print("Python %s" % sys.version.split()[0])
    keep = slug_test()
    weekday_check(keep)
    live_flags(keep)
    bundle_dayparts()
    print("\nDONE")


if __name__ == "__main__":
    main()

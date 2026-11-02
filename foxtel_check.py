#!/usr/bin/env python3
"""One-off check (2 Nov 2026): can the Foxtel Now TV guide (https://www.foxtel.com.au/now/tv-guide/grid) be read from the
GitHub runner, and what does its HTML look like?

The guide is built into the page itself (no separate JSON service was found in the browser's Network tab). Each day is a page
https://www.foxtel.com.au/now/tv-guide/grid/YYYY/MM/DD/HHMM (HHMM = where the grid starts, seen in the browser as 0349 = the
current time in eastern Australia). No cookies, no login, no keys. Prints only: writes no files, commits nothing.
Run from Actions ("Check Foxtel guide" -> Run workflow). It reports, for three pages (today, tomorrow, 13 days ahead):
HTTP status, size, how many programmes look like they are in the page (age ratings such as (M) (PG) (MA15+)), the most common
HTML class names, and the raw HTML around the first programmes, so the structure can be read.
"""
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BASE = "https://www.foxtel.com.au/now/tv-guide/grid"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-AU,en;q=0.9"}
RATING = re.compile(r"\((?:G|PG|M|MA15\+|MA|R18\+|AV15\+|P|C|TBC)\)")


def get(url):
    print(f"GET {url}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"  HTTP {r.status}, {len(body) / 1000:.0f} kB, {r.headers.get('content-type')}")
            return body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        flat = re.sub(r"\s+", " ", body)
        print(f"  HTTP {e.code}: {flat[:300]!r}")
    except Exception as e:
        print(f"  FAILED: {e}")
    return None


def analyse(html, label, detail=True):
    print(f"\n== {label} ==")
    ratings = list(RATING.finditer(html))
    print(f"  age-rating marks (about one per programme): {len(ratings)}")
    nums_ = sorted(set(re.findall(r">\s*(\d{3})\s*<", html)), key=int)
    print(f"  three-digit channel numbers seen: {len(nums_)}")
    if not detail:
        return
    classes = Counter(c for m in re.finditer(r'class="([^"]+)"', html) for c in m.group(1).split())
    print(f"  most common HTML classes: {dict(classes.most_common(40))}")
    print(f"  channel numbers: {nums_[:60]}")
    for k, m in enumerate(ratings[:2]):
        a = max(0, m.start() - 1400)
        print(f"\n  --- raw HTML around programme {k + 1} ---\n{html[a:m.end() + 500]}\n  --- end ---")
    nxt = re.findall(r'href="([^"]*tv-guide/grid[^"]*)"', html)
    print(f"\n  links to other grid pages: {len(nxt)}; first ones: {sorted(set(nxt))[:12]}")


def main():
    aest = ZoneInfo("Australia/Sydney")
    now = datetime.now(aest)
    print(f"Now: {now:%Y-%m-%d %H:%M} Sydney time")
    pages = [(0, f"{now:%H%M}", "today, now"), (1, "0000", "tomorrow from midnight"), (13, "0000", "13 days ahead")]
    for add, hhmm, label in pages:
        d = now + timedelta(days=add)
        html = get(f"{BASE}/{d:%Y/%m/%d}/{hhmm}")
        if html:
            analyse(html, label if add else f"{label} (the first page, in full detail)", detail=not add)
    return 0


if __name__ == "__main__":
    sys.exit(main())

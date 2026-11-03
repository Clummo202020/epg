#!/usr/bin/env python3
"""One-off check (3 Nov 2026): can Astro's public guide service (the one behind astro.com.my/content/channels, TV schedule view)
be read from the GitHub runner, which sport channels does it have, and how many days ahead does it go?

Request (no cookies, no login, no keys - same as the page): contenthub-api.eco.astro.com.my/api/v2/search-linear
  ?channelGuide=true&platform=acm&channelOrderBy=stbNumber,asc&scheduleDate=YYYY-MM-DD&channelLimit=20&channelPage=N
Prints only: writes no files, commits nothing. Run from Actions ("Check Astro guide" -> Run workflow).
It reports: HTTP status/size, the response layout, every sport-looking channel (number, title, programmes today), how far ahead
each sport channel's schedule goes (asks for 15 days), a sample, and whether one big request (channelLimit=200) returns all channels.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
           "Accept": "application/json, */*", "Origin": "https://www.astro.com.my", "Referer": "https://www.astro.com.my/"}
SPORT = re.compile(r"sport|arena|football|premier league|golf|badminton|grandstand|cricket|f1|formula|wwe|racing|tennis|bein|motor|fight|olympic", re.I)
DAYS = 15
MYT = timezone(timedelta(hours=8))


def call(date, page, limit=20, label=""):
    params = {"channelGuide": "true", "platform": "acm", "channelOrderBy": "stbNumber,asc", "scheduleDate": date,
              "channelLimit": limit, "channelPage": page}
    url = API + "?" + urllib.parse.urlencode(params, safe=",")
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
            body = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        print(f"[{label}] HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:250]!r}")
        return None
    except Exception as e:
        print(f"[{label}] FAILED: {e}")
        return None
    try:
        data = json.loads(body)
    except ValueError:
        print(f"[{label}] not JSON: {body[:250]!r}")
        return None
    if label:
        print(f"[{label}] HTTP {status}, {len(body) / 1000:.0f} kB, {time.time() - t0:.1f} s")
    return data


def channels_of(data):
    ch = ((data or {}).get("response") or {}).get("channels") or {}
    return ch.get("data") or [], {k: v for k, v in ch.items() if k != "data"}


def prog_list(ch):
    return ch.get("schedule") or []


def main():
    today = datetime.now(MYT).date()
    print(f"Today in Malaysia: {today}")
    # 1. all channels for today, page by page
    print("\n== 1. all channels, today, 20 per page ==")
    allch, pages_with_sport, page = [], set(), 1
    while page <= 15:
        data = call(today.isoformat(), page, 20, f"page {page}")
        chs, extra = channels_of(data)
        if page == 1:
            print(f"  other response fields next to the channel data: {extra}")
            print(f"  top-level keys: {sorted((data or {}).keys())}; response keys: {sorted(((data or {}).get('response') or {}).keys())}")
        if not chs:
            break
        for c in chs:
            c["_page"] = page
            allch.append(c)
            if SPORT.search(c.get("title") or "") or "sport" in (c.get("category") or "").lower() or "sport" in " ".join(c.get("genreKey") or []).lower():
                pages_with_sport.add(page)
        page += 1
    print(f"channels found: {len(allch)}; categories: {sorted({c.get('category') for c in allch})}")
    sport = [c for c in allch if SPORT.search(c.get("title") or "") or "sport" in (c.get("category") or "").lower()
             or "sport" in " ".join(c.get("genreKey") or []).lower()]
    print(f"\n== 2. sport-looking channels ({len(sport)}) ==")
    for c in sport:
        print(f"  CH {str(c.get('stbNumber')):>4} | {str(c.get('title'))[:34]:34} | id {c.get('id')} | {c.get('category')} | {len(prog_list(c))} programmes today | page {c['_page']}")
    # 3. reach: only the pages with sport channels, day by day
    print(f"\n== 3. how far ahead (pages {sorted(pages_with_sport)} only, {DAYS} days) ==")
    wanted = {c["id"]: c for c in sport}
    per = {cid: {} for cid in wanted}
    sample = {}
    for d in range(DAYS):
        day = (today + timedelta(days=d)).isoformat()
        got = 0
        for pg in sorted(pages_with_sport):
            data = call(day, pg, 20, "")
            chs, _ = channels_of(data)
            for c in chs:
                if c.get("id") in wanted:
                    n = len(prog_list(c))
                    per[c["id"]][day] = n
                    got += n
                    if d == 1 and c.get("id") not in sample:
                        sample[c["id"]] = prog_list(c)[:4]
        print(f"  {day}: {got} sport programmes")
    print("\n  per channel: first day with data -> last day with data (days with data / 15)")
    for cid, c in wanted.items():
        days = sorted(k for k, v in per[cid].items() if v)
        print(f"  CH {str(c.get('stbNumber')):>4} {str(c.get('title'))[:30]:30} {days[0] if days else '-':>10} -> {days[-1] if days else '-':>10}  ({len(days)}/{DAYS})")
    print("\n== 4. sample: day +1, first programmes of a few sport channels ==")
    for cid, progs in list(sample.items())[:6]:
        print(f"  {wanted[cid].get('title')}:")
        for p in progs:
            print(f"     {p.get('eventStartMyt', '')[11:16]}-{p.get('eventEndMyt', '')[11:16]} | {p.get('title')} | keys={sorted(p)}")
    # 5. one big request?
    print("\n== 5. one request with channelLimit=200 ==")
    data = call(today.isoformat(), 1, 200, "limit 200")
    chs, extra = channels_of(data)
    print(f"  returned {len(chs)} channels; other fields: {extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

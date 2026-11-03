#!/usr/bin/env python3
"""One-off check (3 Nov 2026): what does beIN's API really send for the Malaysian blocks titled just 'Tue' / 'Wed'?
Writes nothing to the repo. Prints: the raw fields of a few such rows, then every such row with its neighbours.
Delete this file and .github/workflows/bein_check.yml afterwards."""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://www.beinsports.com/api/opta/"
HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
       "Accept": "application/json, */*", "Referer": "https://www.beinsports.com/"}
CHANNELS = {"0FA3DEF0-234B-4E25-934F-392DF2C3162C": "beIN SPORTS 1",
            "07C1C284-D784-4AD2-9F7E-022DCD196D04": "beIN SPORTS 3"}
DAY = re.compile(r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?\s*$", re.I)


def get(url):
    try:
        req = urllib.request.Request(url, headers=HDR)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  request failed: {url[:120]} -> {e}")
        return None


def cut(v, n=160):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + "..."


def main():
    start = datetime.now(timezone.utc).date() - timedelta(days=1)
    days = [start + timedelta(days=i) for i in range(10)]
    for cid, name in CHANNELS.items():
        rows = {}
        for day in days:
            nxt = day + timedelta(days=1)
            url = (f"{API}tv-event?&startBefore={nxt:%Y-%m-%d}T00:00:00.000Z"
                   f"&endAfter={day:%Y-%m-%d}T00:00:00.000Z&channelIds={cid}")
            data = get(url)
            for it in ((data.get("rows") if isinstance(data, dict) else data) or []):
                if isinstance(it, dict) and it.get("startDate"):
                    rows[(it["startDate"], it.get("title"))] = it
        ordered = [rows[k] for k in sorted(rows)]
        print(f"\n===== {name}: {len(ordered)} rows =====")
        hits = [i for i, it in enumerate(ordered) if DAY.match(str(it.get("title") or ""))]
        print(f"{len(hits)} row(s) with a weekday-only title")
        for n, i in enumerate(hits[:3]):
            print(f"\n--- RAW ROW {n + 1} (all fields) ---")
            print(json.dumps(ordered[i], ensure_ascii=False, indent=1)[:2500])
        print("\n--- every weekday-only row, with the row before and after ---")
        for i in hits:
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(ordered):
                    it = ordered[j]
                    d = it.get("data") if isinstance(it.get("data"), dict) else {}
                    mark = ">>" if j == i else "  "
                    print(f"{mark} {it.get('startDate', '')[:16]} -> {it.get('endDate', '')[11:16]} | "
                          f"title={cut(it.get('title'), 70)} | data.title={cut(d.get('title'), 50)} | "
                          f"desc={cut(it.get('description') or it.get('synopsis'), 80)}")
            print()
        keys = sorted({k for it in ordered for k in it})
        print("all top-level fields seen:", keys)
    return 0


if __name__ == "__main__":
    sys.exit(main())

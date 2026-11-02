#!/usr/bin/env python3
"""One-off check (2 Nov 2026): does beIN's own public TV-guide API answer for the Middle East (the page
https://www.beinsports.com/en-mena/tv-guide), and how good is it for the beIN SPORTS channels?

Uses the same two requests SPORT_epg.py already makes for beIN Asia-Pacific (api/opta/tv-channel, api/opta/tv-event),
no cookies, no login, no keys. Prints only: writes no files, commits nothing.
Run from Actions ("Check beIN MENA guide" -> Run workflow). It reports, per region code tried: HTTP status, the channel
names, then for the best answer: programmes per channel over the next 8 days, how far ahead they run, the fields beIN gives
(sport / competition / description), and a sample of beIN SPORTS EN 1 and EN 2 for the next few hours.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://www.beinsports.com/api/opta/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
           "Accept": "application/json, */*", "Referer": "https://www.beinsports.com/"}
# The page's "Edition" dropdown: MENA, France, United States, Australia, New Zealand, Asia (+ English / Arabic switch).
# Codes are guesses from the ones SPORT_epg.py already uses (en-au, en-my ...); every one that answers is reported.
# beIN's own error message (2 Nov 2026) lists the valid codes: default, en-mena, ar-mena, fr-fr, en-us, es-us, en-hk, en-ph,
# en-th, en-id, en-my, en-sg, en-au, en-nz, bein-xtra
REGIONS = ["en-mena", "ar-mena", "bein-xtra", "default", "en-ph", "en-hk", "en-th", "en-id"]
DAYS = 8
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def valid(chans):
    """beIN rejects the whole request if ANY channel id is not a UUID (HTTP 400, seen 2 Nov 2026), so ask only for valid ones."""
    ok = {i: n for i, n in chans.items() if UUID.fullmatch(i)}
    bad = {i: n for i, n in chans.items() if i not in ok}
    if bad:
        print(f"    NOT valid UUIDs, left out of the programme requests: {bad}")
    return ok


def get(url, label):
    print(f"[{label}] GET {url[:150]}{'...' if len(url) > 150 else ''}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"[{label}] HTTP {r.status}, {len(body) / 1000:.0f} kB")
    except urllib.error.HTTPError as e:
        print(f"[{label}] HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]!r}")
        return None
    except Exception as e:
        print(f"[{label}] FAILED: {e}")
        return None
    try:
        return json.loads(body)
    except ValueError:
        print(f"[{label}] not JSON: {body[:200]!r}")
        return None


def rows_of(data):
    return (data.get("rows") if isinstance(data, dict) else data if isinstance(data, list) else None) or []


def events_one(cid, first_day, last_day, label):
    """beIN's tv-event only takes ONE channel id per request (several comma-joined ids -> HTTP 400 "must be a UUID",
    seen 2 Nov 2026 - which is why SPORT_epg.py falls back to one by one). One request covers the whole window."""
    url = (f"{API}tv-event?&startBefore={last_day + timedelta(days=1):%Y-%m-%d}T00:00:00.000Z"
           f"&endAfter={first_day:%Y-%m-%d}T00:00:00.000Z&channelIds={cid}")
    return [r for r in rows_of(get(url, label)) if isinstance(r, dict)]


def t(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)


def main():
    now = datetime.now(timezone.utc)
    print(f"Now: {now:%Y-%m-%d %H:%M} UTC")
    best_code, best = None, {}
    for code in REGIONS:
        data = get(f"{API}tv-channel?region={code}", f"channels {code}")
        chans = {str(r["id"]): " ".join(str(r.get("name") or "").split()) for r in rows_of(data)
                 if isinstance(r, dict) and r.get("id")}
        print(f"  region {code}: {len(chans)} channel(s): {sorted(set(chans.values()))[:40]}")
        if chans and len(chans) <= 6:                       # small regions: count today + tomorrow per channel
            names = {}
            for cid, cname in sorted(valid(chans).items(), key=lambda kv: kv[1]):
                ev = events_one(cid, now.date(), now.date() + timedelta(days=1), f"survey {code} {cname}")
                names[cname] = len(ev)
            print(f"  region {code}: programmes over today+tomorrow: {names}")
        if chans and code in ("en-mena",) and not best:
            best_code, best = code, chans
    if not best:                                  # en-mena gave nothing: use the first region that did
        pass
    if not best:
        print("\nen-mena gave no channel list - the other regions above are all this check can report.")
        return 0
    print(f"\n== using region {best_code}: {len(best)} channels ==")
    sports = valid({i: n for i, n in best.items() if "sport" in n.lower() or "xtra" in n.lower() or "max" in n.lower()} or best)
    ids = sorted(sports)
    per, sample_row = {i: [] for i in ids}, None
    first_day, last_day = now.date(), now.date() + timedelta(days=DAYS - 1)
    for cid in ids:
        rows = events_one(cid, first_day, last_day, f"{sports[cid]}")
        per[cid] = rows
        sample_row = sample_row or (rows[0] if rows else None)
    if sample_row:
        print(f"\nfields in a programme row: {sorted(sample_row)}")
        print(f"sample row: {json.dumps(sample_row, ensure_ascii=False)[:700]}")
    print("\n== programmes per channel (all 8 days) ==")
    for cid in ids:
        rows = {r.get("id") or (r.get("startDate"), r.get("title")): r for r in per[cid]}.values()
        ends = [t(r["endDate"]) for r in rows if r.get("endDate")]
        last = f"{(max(ends) - now).total_seconds() / 3600:.0f} h ahead" if ends else "none"
        print(f"  {sports[cid]:32} {len(rows):4} programmes, {last}")
    for want in ("EN 1", "EN 2"):
        cid = next((i for i in ids if sports[i].upper().endswith(want) or f" {want}" in sports[i].upper()), None)
        if not cid:
            print(f"\n-- {want}: not found among {sorted(set(sports.values()))[:12]}")
            continue
        rows = sorted({(r.get("startDate"), r.get("title")): r for r in per[cid]}.values(), key=lambda r: r.get("startDate") or "")
        rows = [r for r in rows if r.get("endDate") and t(r["endDate"]) > now][:8]
        print(f"\n-- {sports[cid]}: next {len(rows)}")
        for r in rows:
            data = r.get("data") or {}
            print(f"   {str(r.get('startDate'))[5:16]} -> {str(r.get('endDate'))[11:16]} | {r.get('title')} | data.title={data.get('title')!r} | "
                  f"desc={str(r.get('description') or '')[:70]!r} | keys={sorted(k for k in data)[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

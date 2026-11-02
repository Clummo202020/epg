#!/usr/bin/env python3
"""One-off check (2 Nov 2026): can the Sky Go (NZ) TV guide be read from the GitHub runner, and how good is it?

Uses the same public request the skygo.co.nz TV guide page makes (api.skyone.co.nz GraphQL "getSlots"), cut down to
the fields we'd need. Sends NO cookies, NO login and NO keys - if the API refuses that, we stop here.
Prints only: writes no files, commits nothing. Run from Actions ("Check Sky Go guide" -> Run workflow).
Part 2 (added 2 Nov): asks for the synopsis/duration text for the next 48 h and prints samples for Sky Sport 1, 7 and Premier League.
It reports: HTTP status; how many channels / which Sky Sport channels; how far ahead the slots go (asks for 10 days);
a sample of Sky Sport 1; and which text fields (synopsis / description) the API offers, if it allows schema queries.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.skyone.co.nz/exp/graph"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://www.skygo.co.nz",
    "Referer": "https://www.skygo.co.nz/",
}
SLOTS_QUERY = """query getSlots($from: DateTime!, $to: DateTime!) { channels { __typename
 ... on LinearChannel { id title number slots(from: $from, to: $to) { id start end live
  programme { __typename ... on Title { id title }
   ... on Movie { year primaryGenres { title } }
   ... on Episode { id title number show { id title type primaryGenres { title } } season { id number } } } } } } }"""
TYPES_TO_LIST = ["Title", "Episode", "Movie", "Show", "Season", "ViewableContent", "LinearChannel", "Slot"]


def call(query, variables=None, label=""):
    params = {"query": query}
    if variables:
        params["variables"] = json.dumps(variables)
    url = API + "?" + urllib.parse.urlencode(params)
    print(f"[{label}] GET {len(url)} chars ...")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"[{label}] HTTP {r.status}, {len(body) / 1000:.0f} kB, {r.headers.get('content-type')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"[{label}] HTTP {e.code}: {body[:300]!r}")
        return None
    except Exception as e:
        print(f"[{label}] FAILED: {e}")
        return None
    try:
        data = json.loads(body)
    except ValueError:
        print(f"[{label}] not JSON: {body[:300]!r}")
        return None
    if data.get("errors"):
        for err in data["errors"][:4]:
            print(f"[{label}] API error: {str(err.get('message'))[:250]}")
    return data


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


DETAIL_QUERY = """query getSlots($from: DateTime!, $to: DateTime!) { channels { __typename
 ... on LinearChannel { id title number slots(from: $from, to: $to) { id start end live
  programme { __typename ... on Title { id title }
   ... on Movie { synopsis duration year primaryGenres { title } }
   ... on Episode { id title synopsis duration number show { id title type synopsis primaryGenres { title } } season { id number } } } } } } }"""


def part2(now, fmt):
    print("\n== part 2: descriptions (next 48 h) ==")
    data = call(DETAIL_QUERY, {"from": fmt(now), "to": fmt(now + timedelta(hours=48))}, "detail")
    chans = [c for c in ((data or {}).get("data") or {}).get("channels") or [] if c.get("slots") is not None]
    if not chans:
        print("no detail data - see the API error above (it names the field that was refused)")
        return
    kinds = {}
    for c in chans:
        if "sport" in (c.get("title") or "").lower():
            for sl in c["slots"]:
                k = (sl.get("programme") or {}).get("__typename")
                kinds[k] = kinds.get(k, 0) + 1
    print(f"programme types on the sport channels: {kinds}")
    for want in ("Sky Sport 1", "Sky Sport 7", "Sky Sport Premier League"):
        c = next((c for c in chans if (c.get("title") or "") == want), None)
        if not c:
            print(f"-- {want}: not found")
            continue
        sl = sorted(c["slots"], key=lambda s: s["start"])
        with_syn = sum(1 for s in sl if (s.get("programme") or {}).get("synopsis")
                       or ((s.get("programme") or {}).get("show") or {}).get("synopsis"))
        print(f"-- {want}: {len(sl)} slots in 48 h, {with_syn} with a synopsis, {sum(1 for s in sl if s.get('live'))} marked live")
        for s in sl[:7]:
            p = s.get("programme") or {}
            show = p.get("show") or {}
            print(f"   {s['start'][11:16]}-{s['end'][11:16]} live={s.get('live')} | {p.get('title')} | "
                  f"type={show.get('type')} dur={p.get('duration')} genre={[g['title'] for g in show.get('primaryGenres') or p.get('primaryGenres') or []]}")
            print(f"      episode synopsis: {(p.get('synopsis') or '')[:160]!r}")
            print(f"      show synopsis:    {(show.get('synopsis') or '')[:160]!r}")


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    print(f"Now: {now:%Y-%m-%d %H:%M} UTC")

    data = call(SLOTS_QUERY, {"from": fmt(now), "to": fmt(now + timedelta(days=10))}, "10-day window")
    chans = [c for c in ((data or {}).get("data") or {}).get("channels") or [] if c.get("slots") is not None]
    print(f"linear channels returned: {len(chans)}")
    sport = [c for c in chans if "sport" in (c.get("title") or "").lower()]
    for c in sorted(sport, key=lambda c: c.get("number") or 0):
        sl = c["slots"]
        ends = [parse(s["end"]) for s in sl if s.get("end")]
        last = max(ends) if ends else None
        ahead = f"{(last - now).total_seconds() / 3600:.0f} h ahead" if last else "no slots"
        print(f"  {c.get('number')!s:>4} {c.get('title')!s:34} {len(sl):4} slots, {ahead}")
    s1 = next((c for c in sport if (c.get("title") or "").lower().replace(" ", "") in ("skysport1", "skysport1hd")), None) \
        or (sport[0] if sport else None)
    if s1:
        print(f"-- sample: {s1.get('title')} (next 6 slots)")
        for s in sorted(s1["slots"], key=lambda s: s["start"])[:6]:
            p = s.get("programme") or {}
            show = (p.get("show") or {}).get("title")
            season = (p.get("season") or {}).get("number")
            print(f"   {s['start'][:16]} -> {s['end'][11:16]} live={s.get('live')} | {p.get('title')} | "
                  f"{p.get('__typename')} | show={show} S{season} E{p.get('number')}")

    part2(now, fmt)
    print("\n== schema: text fields offered (works only if the API allows introspection) ==")
    for t in TYPES_TO_LIST:
        d = call('query($n:String!){ __type(name:$n){ name fields { name } } }', {"n": t}, f"type {t}")
        ty = ((d or {}).get("data") or {}).get("__type")
        if ty:
            names = [f["name"] for f in ty.get("fields") or []]
            print(f"  {t}: {', '.join(names)}")
        elif d is not None:
            print(f"  {t}: (not found or introspection off)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

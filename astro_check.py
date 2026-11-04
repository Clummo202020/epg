#!/usr/bin/env python3
"""One-off check (5 Nov 2026): does Astro's own guide carry the "(L)" live flag,
how far ahead does it go, and which request parameters does it want?
Delete this file and astro_check.yml afterwards."""
import json, re, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

BASE = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
      "Accept": "application/json, text/html, */*"}


def get(url, timeout=40, limit=4_000_000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(limit)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def walk(o, path=""):
    """yield (path, list) for every list of dicts"""
    if isinstance(o, list):
        if o and isinstance(o[0], dict):
            yield path, o
        for i, x in enumerate(o[:3]):
            yield from walk(x, f"{path}[{i}]")
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, list):
        for x in o:
            yield from strings(x)
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)


def analyse(label, raw):
    try:
        data = json.loads(raw)
    except Exception:
        print(f"  [{label}] not JSON: {raw[:150]!r}")
        return False
    lists = sorted(walk(data), key=lambda t: -len(t[1]))[:4]
    print(f"  [{label}] JSON {len(raw):,} bytes; top-level: "
          f"{list(data)[:10] if isinstance(data, dict) else type(data).__name__}")
    for p, l in lists:
        print(f"    list {p or '<root>'}: {len(l)} items; keys {list(l[0])[:14]}")
    if lists:
        print("    sample item:", json.dumps(lists[0][1][0], ensure_ascii=False)[:900])
    L = [s for s in strings(data) if "(L)" in s]
    print(f"    strings containing '(L)': {len(L)}; first 8: {L[:8]}")
    U = [s for s in strings(data) if re.search(r"(?i)sports uhd", s)]
    print(f"    strings mentioning 'Sports UHD': {len(U)}; first 4: {U[:4]}")
    return True


def main():
    myt = datetime.now(timezone.utc) + timedelta(hours=8)
    print("Now (MYT):", myt.strftime("%a %d %b %H:%M"))
    print("\n=== 1. Parameter probe on", BASE)
    days = [myt.date(), (myt + timedelta(days=4)).date(), (myt + timedelta(days=6)).date()]
    for d in days:
        D = d.isoformat()
        variants = {
            "none": {},
            "date": {"date": D},
            "day": {"day": D},
            "startDate/endDate": {"startDate": D, "endDate": D},
            "start/end": {"start": D, "end": D},
            "startTime/endTime": {"startTime": D + "T00:00:00+08:00", "endTime": D + "T23:59:59+08:00"},
            "from/to": {"from": D + "T00:00:00+08:00", "to": D + "T23:59:59+08:00"},
        }
        print(f"\n--- day {D}")
        for name, extra in variants.items():
            q = {"channelLimit": 200, **extra}
            url = BASE + "?" + urllib.parse.urlencode(q)
            st, raw = get(url)
            print(f"* {name}: HTTP {st}, {len(raw):,} bytes   {url}")
            if st == 200 and raw[:1] in (b"{", b"["):
                analyse(name, raw)
                if name != "none":
                    break          # first working variant per day is enough

    print("\n=== 2. How the astro.com.my site calls it (script bundles)")
    st, html = get("https://www.astro.com.my/channels")
    print("page HTTP", st, len(html))
    text = html.decode("utf-8", "replace")
    srcs = re.findall(r'src="([^"]+\.js[^"]*)"', text) + re.findall(r'href="([^"]+\.js[^"]*)"', text)
    srcs = [urllib.parse.urljoin("https://www.astro.com.my/channels", s) for s in dict.fromkeys(srcs)]
    print(len(srcs), "script files")
    shown = 0
    for s in srcs[:60]:
        st, js = get(s, limit=6_000_000)
        if st != 200:
            continue
        t = js.decode("utf-8", "replace")
        for m in re.finditer(r"search-linear", t):
            print("  in", s.split("/")[-1][:60], "::", t[max(0, m.start() - 250): m.end() + 350].replace("\n", " "))
            shown += 1
            if shown >= 4:
                break
        if shown >= 4:
            break
    if not shown:
        print("  no 'search-linear' text found in the first 60 scripts")
    print("\nDone.")


if __name__ == "__main__":
    main()

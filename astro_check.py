#!/usr/bin/env python3
"""One-off check (5 Nov 2026), round 2: Astro's own guide (the call astro.com.my makes).
Reports: structure, the "(L)" live flag, reach in days, Astro Sports UHD (CH 805) and the other
sport channels, and how UHD's times compare with our SPORT guide.
Delete this file and astro_check.yml afterwards."""
import gzip, json, re, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
      "Accept": "application/json, text/plain, */*", "Origin": "https://www.astro.com.my",
      "Referer": "https://www.astro.com.my/"}
SPORT_RE = re.compile(r"(?i)sport|arena|premier league|football|golf|grandstand|badminton|cricket|uhd")


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return 0, str(e).encode()


def keyl(d, part):
    return [k for k in d if part in k.lower()]


def find_channels(o):
    """dicts that carry a stbNumber key"""
    out = []
    if isinstance(o, dict):
        if keyl(o, "stbnumber"):
            out.append(o)
        else:
            for v in o.values():
                out += find_channels(v)
    elif isinstance(o, list):
        for x in o:
            out += find_channels(x)
    return out


def find_progs(o):
    """dicts that look like a programme: a title plus a start/time key"""
    out = []
    if isinstance(o, dict):
        if keyl(o, "title") and (keyl(o, "start") or keyl(o, "time")) and not keyl(o, "stbnumber"):
            out.append(o)
        for v in o.values():
            out += find_progs(v)
    elif isinstance(o, list):
        for x in o:
            out += find_progs(x)
    return out


def ptitle(p):
    k = keyl(p, "title")
    return str(p[k[0]]) if k else ""


def pwhen(p):
    ks = [k for k in p if re.search(r"(?i)start|end|time|date", k) and not isinstance(p[k], (dict, list))]
    return {k: p[k] for k in ks[:4]}


def cname(c):
    for k in ("title", "name", "channelTitle", "channelName"):
        if k in c:
            return str(c[k])
    return "?"


def stb(c):
    k = keyl(c, "stbnumber")
    return str(c[k[0]]) if k else "?"


def main():
    myt = datetime.now(timezone.utc) + timedelta(hours=8)
    print("Now (MYT):", myt.strftime("%a %d %b %H:%M"))
    first = None
    summary = []
    for off in range(0, 10):
        d = (myt + timedelta(days=off)).date().isoformat()
        q = {"channelGuide": "true", "platform": "acm", "channelOrderBy": "stbNumber,asc",
             "scheduleDate": d, "channelLimit": 200, "channelPage": 1}
        st, raw = get(BASE + "?" + urllib.parse.urlencode(q, safe=","))
        if st != 200:
            print(f"\n=== {d}: HTTP {st} {raw[:200]!r}")
            summary.append((d, st, 0, 0, 0))
            continue
        data = json.loads(raw)
        chans = find_channels(data)
        nprog = nL = nsport = 0
        for c in chans:
            ps = find_progs(c)
            nprog += len(ps)
            nL += sum(1 for p in ps if ptitle(p).startswith("(L)"))
        summary.append((d, st, len(chans), nprog, nL))
        print(f"\n=== {d}: HTTP 200, {len(raw):,} bytes, {len(chans)} channels, {nprog} programmes, {nL} marked (L)")
        if first is None:
            first = data
            print("top-level keys:", list(data)[:12] if isinstance(data, dict) else type(data).__name__)
            if chans:
                c0 = chans[0]
                print("channel keys:", list(c0)[:25])
                print("channel sample:", json.dumps(c0, ensure_ascii=False)[:1200])
        for c in chans:
            n, t = stb(c), cname(c)
            if n.startswith("8") or SPORT_RE.search(t):
                ps = find_progs(c)
                Ls = [p for p in ps if ptitle(p).startswith("(L)")]
                print(f"  CH {n:>4} {t[:34]:34} {len(ps):3} prog, {len(Ls):2} (L)")
                if "uhd" in t.lower() or n == "805":
                    for p in ps[:14]:
                        print("      ", ptitle(p)[:60], pwhen(p))
                    if ps:
                        print("      raw sample:", json.dumps(ps[0], ensure_ascii=False)[:700])
    print("\n=== Reach summary (date, HTTP, channels, programmes, (L))")
    for row in summary:
        print("  ", row)

    # compare with our SPORT guide (Astro Sports UHD)
    print("\n=== Our SPORT guide, MY.AstroSportsUHD")
    st, gz = get("https://raw.githubusercontent.com/Clummo202020/epg/main/SPORT_epg.xml.gz")
    if st == 200:
        x = gzip.decompress(gz).decode("utf-8", "replace")
        for m in re.findall(r'<programme start="(\d{14}) \+0000" stop="(\d{14}) \+0000" channel="MY\.AstroSportsUHD">\s*<title[^>]*>([^<]*)', x):
            print("   ", m[0], m[1], m[2])
    else:
        print("  could not read:", st)
    print("\nDone.")


if __name__ == "__main__":
    main()

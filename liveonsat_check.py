#!/usr/bin/env python3
"""One-off check (6 Nov 2026): can the GitHub runner read liveonsat.com's sport pages, which time zone do they show,
and do their start times ("ST: HH:MM") match what our events guide gets from the Stan / Peacock / Paramount+ stream names?
Reads each page ONCE with a pause in between; writes nothing to the repo. Delete this file and liveonsat_check.yml afterwards."""
import gzip, html, re, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

BASE = "https://liveonsat.com/"
PAGES = {
    "Rugby Union": "x-rugby-union.php", "Rugby League": "x-rugby-league.php", "Aussie Rules": "x-aussie-rules.php",
    "Motor Sport": "x-formula1.php", "Boxing / Fighting": "x-boxing-mma.php", "NFL": "usa-nfl-football.php",
    "NBA": "usa-nba-basketball.php", "NHL": "usa-nhl-hockey.php",
}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15 Version/17.0 Safari/605.1.15",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-GB,en;q=0.9"}
DAY = re.compile(r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (\d{1,2})(?:st|nd|rd|th) (\w+)$")
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                      "October", "November", "December"], 1)}
FIXTURE = re.compile(r"^(.{2,70}?) v (.{2,70})$")
ST = re.compile(r"^ST:\s*(\d{1,2}):(\d{2})$")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return r.status, raw.decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400].decode("utf-8", "replace"), dict(e.headers)
    except Exception as e:
        return 0, str(e), {}


def tokens(page):
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    page = re.sub(r"(?i)</?(td|tr|p|br|div|li|h\d|table|a|span|b|strong)[^>]*>", "\n", page)
    page = re.sub(r"<[^>]+>", " ", page)
    out = []
    for line in html.unescape(page).split("\n"):
        t = re.sub(r"\s+", " ", line).strip()
        if t:
            out.append(t)
    return out


def zone_of(page):
    cands = re.findall(r"selected[^>]*>\s*\(GMT\s*([+-]\d\d:\d\d)\)\s*([A-Za-z_]+/[A-Za-z_/]+)", page)
    cands += re.findall(r"\*\s*\(GMT\s*([+-]\d\d:\d\d)\)\s*([A-Za-z_]+/[A-Za-z_/]+)", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    return cands


def parse(page):
    """[(date, 'HH:MM', teamA, teamB, comp, [channels])]"""
    toks = tokens(page)
    year = datetime.now(timezone.utc).year
    date, comp, out, cur = None, "", [], None
    for i, t in enumerate(toks):
        m = DAY.match(t)
        if m and m.group(2) in MONTHS:
            date = (year, MONTHS[m.group(2)], int(m.group(1)))
            continue
        m = ST.match(t)
        if m and date:
            a = b = ""
            for back in range(1, 7):                                       # the teams are just above the "ST:" line
                f = FIXTURE.match(toks[i - back]) if i - back >= 0 else None
                if f:
                    a, b = f.group(1), f.group(2)
                    comp = toks[i - back - 1] if i - back - 1 >= 0 else ""
                    break
            cur = {"date": date, "time": (int(m.group(1)), int(m.group(2))), "a": a, "b": b, "comp": comp, "ch": []}
            out.append(cur)
            continue
        if cur is not None and not FIXTURE.match(t) and not DAY.match(t) and len(t) < 70 and t not in ("|", "---"):
            cur["ch"].append(t)
    return out


def main():
    print("Now (UTC):", datetime.now(timezone.utc).strftime("%a %d %b %H:%M"))
    results = {}
    for name, path in PAGES.items():
        status, body, hdrs = get(BASE + path)
        print(f"\n=== {name}  {BASE + path}\n  HTTP {status}, {len(body):,} chars, server={hdrs.get('Server') or hdrs.get('server')}")
        if status != 200:
            print("  first 300 chars:", re.sub(r"\s+", " ", body)[:300])
            time.sleep(4)
            continue
        if re.search(r"(?i)just a moment|cf-chl|captcha-bypass|attention required", body[:6000]):
            print("  !! looks like a Cloudflare / bot challenge page")
        zc = zone_of(body)
        print("  time zone marker(s):", zc[:3] if zc else "NONE FOUND")
        fx = parse(body)
        print(f"  fixtures with a start time: {len(fx)}")
        if not fx:
            sample = [t for t in tokens(body) if len(t) < 90][:60]
            print("  !! no fixtures parsed - first text pieces of the page:", sample)
        for f in fx[:4]:
            print("    ", f"{f['date'][2]:02d}/{f['date'][1]:02d}", f"{f['time'][0]:02d}:{f['time'][1]:02d}", "|", f["a"], "v", f["b"], "|", f["comp"][:30],
                  "| stan" if any("Stan Sport" in c for c in f["ch"]) else "")
        results[name] = (zc, fx)
        time.sleep(4)

    # compare with our events guide: Stan / Peacock / Paramount stream slots
    print("\n=== Our events guide (Stan / Peacock / Paramount) against LiveOnSat")
    try:
        with urllib.request.urlopen(urllib.request.Request(
                "https://raw.githubusercontent.com/Clummo202020/epg/main/events_epg.xml", headers=UA), timeout=60) as r:
            xml = r.read().decode("utf-8", "replace")
    except Exception as e:
        print("  could not read events_epg.xml:", e)
        return
    seen = set()
    rows = re.findall(r'<programme start="(\d{14}) \+0000" stop="\d+ \+0000" channel="((?:STAN|Peacock|Paramount)\d+\.[a-z]+)">\s*<title[^>]*>([^<]*)</title>', xml)
    for start, ch, title in rows:
        t = html.unescape(re.sub(r"^🔴 LIVE: ", "", title))
        if " vs " not in t or (ch, t) in seen:
            continue
        seen.add((ch, t))
        a, b = [x.strip().lower() for x in t.split(" vs ", 1)]
        words_a, words_b = set(re.findall(r"\w{4,}", a)), set(re.findall(r"\w{4,}", b))
        ours = datetime.strptime(start, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        for name, (zc, fx) in results.items():
            zname = zc[0][1] if zc else None
            try:
                tz = ZoneInfo(zname) if zname else timezone.utc
            except Exception:
                tz = timezone.utc
            for f in fx:
                fa, fb = set(re.findall(r"\w{4,}", f["a"].lower())), set(re.findall(r"\w{4,}", f["b"].lower()))
                if (words_a & fa and words_b & fb) or (words_a & fb and words_b & fa):
                    ko = datetime(*f["date"], f["time"][0], f["time"][1], tzinfo=tz).astimezone(timezone.utc)
                    print(f"  {ch:14} {t[:44]:44} ours {ours:%a %d %H:%M} UTC | LiveOnSat ST {ko:%a %d %H:%M} UTC (page zone {zname}) "
                          f"[{name}] {'stan listed' if any('Stan Sport' in c for c in f['ch']) else ''}")
        if len(seen) >= 40:
            break
    print("\nDone.")


if __name__ == "__main__":
    main()

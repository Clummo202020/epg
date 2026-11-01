#!/usr/bin/env python3
"""One-off check (1 Nov 2026): how many programmes, and how far ahead, do these epgshare01 channels have?

Reads epgshare01's XMLTV files (the same way SPORT_epg.py does) and prints, for each id listed in CHECKS,
the number of programmes, the first start, the last stop and how many hours ahead of now the last one ends.
Prints only - writes no files and commits nothing. Run it from Actions ("Check epgshare channels" -> Run workflow).
To check other ids, edit CHECKS: file name (without epg_ripper_ / .xml.gz) -> list of channel ids.
"""
import gzip
import io
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

CHECKS = {
    "BEIN1": ["Alkass_1_EN.bein", "Alkass_1_AR.bein", "Alkass_2_EN.bein", "Alkass_2_AR.bein",
              "Alkass_3_EN.bein", "Alkass_3_AR.bein", "Alkass_4_EN.bein", "Alkass_4_AR.bein"],
    "AE1": ["Alkass.One.HD.ae", "Alkass.Two.HD.ae", "Alkass.Three.ae", "Alkass.Four.ae"],
}
URL = "{scheme}://epgshare01.online/epgshare01/epg_ripper_{file}.xml.gz"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def download(name):
    last = None
    for scheme in ("https", "http"):
        try:
            req = urllib.request.Request(URL.format(scheme=scheme, file=name), headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        except Exception as e:                      # try the other scheme, then report
            last = e
    raise RuntimeError(f"could not download {name}: {last}")


def parse_time(s):
    s = (s or "").strip()
    for fmt in ("%Y%m%d%H%M%S %z", "%Y%m%d%H%M%S"):
        try:
            d = datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def main():
    now = datetime.now(timezone.utc)
    print(f"Now: {now:%Y-%m-%d %H:%M} UTC")
    for name, ids in CHECKS.items():
        print(f"\n=== epg_ripper_{name} ===")
        try:
            data = download(name)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        print(f"  downloaded {len(data) / 1e6:.1f} MB")
        want = set(ids)
        found, stats = set(), {i: [0, None, None] for i in ids}
        for _, el in ET.iterparse(io.BytesIO(data), events=("end",)):
            if el.tag == "channel":
                if el.get("id") in want:
                    found.add(el.get("id"))
                el.clear()
            elif el.tag == "programme":
                cid = el.get("channel")
                if cid in want:
                    s, e = parse_time(el.get("start")), parse_time(el.get("stop"))
                    st = stats[cid]
                    st[0] += 1
                    if s and (st[1] is None or s < st[1]):
                        st[1] = s
                    if e and (st[2] is None or e > st[2]):
                        st[2] = e
                el.clear()
        for i in ids:
            n, first, last = stats[i]
            if n == 0:
                print(f"  {i}: {'channel is in the file' if i in found else 'NOT in the file'}, NO programmes")
            else:
                ahead = (last - now).total_seconds() / 3600
                print(f"  {i}: {n} programmes, {first:%a %d %b %H:%M} -> {last:%a %d %b %H:%M} UTC "
                      f"(ends {ahead:.0f} h ahead)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
survey_playlist.py - one-off survey of your full playlist, for planning the general EPG.

Reads the playlist from the FULL_PLAYLIST_URL secret and writes playlist_survey.csv:
one row per stream with its group, name and current EPG id (tvg-id). Stream links and
logins are NOT written. Also prints a summary (groups, EPG-id endings) to the log.

    FULL_PLAYLIST_URL=... python3 survey_playlist.py
    python3 survey_playlist.py --m3u playlist.m3u        # a local file instead
"""
import argparse
import collections
import csv
import os
import re
import sys
import urllib.request

ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def read(args):
    if args.m3u:
        with open(args.m3u, encoding="utf-8", errors="replace") as f:
            return f.read()
    url = os.environ.get("FULL_PLAYLIST_URL", "").strip()
    if not url:
        sys.exit("No FULL_PLAYLIST_URL secret (or use --m3u FILE).")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (survey_playlist.py)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m3u")
    ap.add_argument("--out", default="playlist_survey.csv")
    args = ap.parse_args()
    rows = []
    for line in read(args).splitlines():
        if not line.startswith("#EXTINF"):
            continue
        attrs = dict(ATTR.findall(line))
        name = line.rsplit(",", 1)[-1].strip()
        rows.append({"group": attrs.get("group-title", ""), "name": name,
                     "tvg_id": attrs.get("tvg-id", ""), "tvg_name": attrs.get("tvg-name", "")})
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "name", "tvg_id", "tvg_name"])
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} streams, {sum(1 for r in rows if r['tvg_id'])} with an EPG id")
    print("\nGroups (streams / with EPG id):")
    groups = collections.OrderedDict()
    for r in rows:
        g = groups.setdefault(r["group"], [0, 0])
        g[0] += 1
        g[1] += bool(r["tvg_id"])
    for g, (n, k) in groups.items():
        print(f"  {n:5} {k:5}  {g}")
    ends = collections.Counter(r["tvg_id"].rsplit(".", 1)[-1].lower() if "." in r["tvg_id"] else
                               ("(none)" if not r["tvg_id"] else "(no dot)") for r in rows)
    print("\nEPG id endings:", ", ".join(f"{k} {v}" for k, v in ends.most_common(40)))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()

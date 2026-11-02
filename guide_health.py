#!/usr/bin/env python3
"""Guide health report (2 Nov 2026). Compares each committed guide with its version from about a day ago and prints a
report (also written to the run's Summary page). Reads files only - writes nothing to the repo.

  FAIL (red cross, GitHub emails you): a guide is missing / unreadable / empty, hasn't been committed for far too long,
        or lost more than half its programmes.
  WARN (yellow note on the run, no email): a group of channels lost channels, lost a lot of programmes or reach, or a
        channel is 'live' on (almost) every programme (like the XTRA channels were).

Run from Actions ("Guide health" -> Run workflow), or on its schedule. Needs a checkout that includes the last ~2 days of commits.
"""
import gzip
import io
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# guide file -> (hours without a new commit that counts as stale, how the id is grouped)
GUIDES = {
    "events_epg.xml": (4, "stem"),
    "football_epg.xml": (30, "dot"),
    "scottish_epg.xml": (30, "dot"),
    "SPORT_epg.xml.gz": (30, "prefix"),
    "TEAMS_epg.xml.gz": (30, "dot"),
    "USA_epg.xml.gz": (30, "dot"),
    "CANADA_epg.xml.gz": (30, "dot"),
    "GENERAL_epg.xml.gz": (30, "dot"),
}
BASELINE_HOURS = 20          # compare with the newest version at least this old
PLACEHOLDER = re.compile(r"no schedule available|no information|channel is offline|end of transmission|coming up|will be listed", re.I)
RED = "\U0001F534"


def sh(*args):
    return subprocess.run(args, capture_output=True, check=False)


def commit_time(path, before=None):
    cmd = ["git", "log", "-1", "--format=%H %ct"] + ([f"--before={before}"] if before else []) + ["--", path]
    out = sh(*cmd).stdout.decode().split()
    return (out[0], datetime.fromtimestamp(int(out[1]), timezone.utc)) if len(out) == 2 else (None, None)


def parse(raw, gz):
    if gz:
        raw = gzip.decompress(raw)
    chans, progs = {}, defaultdict(lambda: {"n": 0, "red": 0, "ph": 0, "last": None})
    for _, el in ET.iterparse(io.BytesIO(raw), events=("end",)):
        if el.tag == "channel":
            chans[el.get("id")] = True
            el.clear()
        elif el.tag == "programme":
            d = progs[el.get("channel")]
            d["n"] += 1
            title = (el.findtext("title") or "")
            if title.startswith(RED):
                d["red"] += 1
            if PLACEHOLDER.search(title) or PLACEHOLDER.search(el.findtext("sub-title") or ""):
                d["ph"] += 1
            stop = el.get("stop", "")[:14]
            if stop and (d["last"] is None or stop > d["last"]):
                d["last"] = stop
            el.clear()
    return chans, progs


def group_of(cid, how):
    if how == "prefix" and "." in cid:
        return cid.split(".")[0]
    if how == "stem":
        m = re.match(r"[A-Za-z+]+", cid)
        return m.group(0) if m else cid
    return cid.split(".")[-1] if "." in cid else cid       # "dot": the suffix after the dot (.uk, .us ...)


def reach_hours(last, ref):
    if not last:
        return None
    t = datetime.strptime(last, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return (t - ref).total_seconds() / 3600


def summarize(chans, progs, ref, how):
    groups = defaultdict(lambda: {"channels": set(), "programmes": 0, "reach": []})
    for cid in set(chans) | set(progs):
        g = groups[group_of(cid, how)]
        g["channels"].add(cid)
        p = progs.get(cid)
        if p:
            g["programmes"] += p["n"]
            r = reach_hours(p["last"], ref)
            if r is not None:
                g["reach"].append(r)
    return groups


def main():
    now = datetime.now(timezone.utc)
    fails, warns, lines = [], [], []
    lines.append(f"# Guide health report - {now:%a %d %b %Y %H:%M} UTC\n")
    lines.append("| guide | channels | programmes | last commit | vs ~1 day ago |\n|---|---|---|---|---|")
    details = []
    for path, (stale_h, how) in GUIDES.items():
        gz = path.endswith(".gz")
        if not os.path.exists(path):
            fails.append(f"{path}: file is missing")
            lines.append(f"| {path} | - | - | - | MISSING |")
            continue
        rev, ctime = commit_time(path)
        try:
            chans, progs = parse(open(path, "rb").read(), gz)
        except Exception as e:
            fails.append(f"{path}: cannot be read ({e})")
            lines.append(f"| {path} | - | - | - | UNREADABLE |")
            continue
        n_ch, n_pr = len(chans), sum(p["n"] for p in progs.values())
        age = (now - ctime).total_seconds() / 3600 if ctime else None
        if n_pr == 0 or n_ch == 0:
            fails.append(f"{path}: the guide is empty")
        if age is not None and age > stale_h:
            fails.append(f"{path}: last committed {age:.0f} h ago (allowed {stale_h} h)")
        # baseline
        brev, btime = commit_time(path, f"{BASELINE_HOURS} hours ago")
        verdict = "no older version to compare"
        if brev and brev != rev:
            braw = sh("git", "show", f"{brev}:{path}").stdout
            try:
                bch, bpr = parse(braw, gz)
            except Exception:
                bch, bpr = {}, {}
            b_pr = sum(p["n"] for p in bpr.values())
            if b_pr:
                change = 100 * (n_pr - b_pr) / b_pr
                verdict = f"{change:+.0f}% programmes ({b_pr} -> {n_pr})"
                if change < -50:
                    fails.append(f"{path}: lost {-change:.0f}% of its programmes ({b_pr} -> {n_pr})")
                elif change < -25:
                    warns.append(f"{path}: lost {-change:.0f}% of its programmes ({b_pr} -> {n_pr})")
            cur_g, old_g = summarize(chans, progs, ctime or now, how), summarize(bch, bpr, btime or now, how)
            for g, o in sorted(old_g.items()):
                c = cur_g.get(g)
                if not c:
                    warns.append(f"{path}: group '{g}' has gone ({len(o['channels'])} channels)")
                    continue
                gone = o["channels"] - c["channels"]
                if gone:
                    warns.append(f"{path}: group '{g}' lost {len(gone)} channel(s): {', '.join(sorted(gone)[:6])}")
                if o["programmes"] >= 30 and c["programmes"] < 0.6 * o["programmes"]:
                    warns.append(f"{path}: group '{g}' programmes {o['programmes']} -> {c['programmes']}")
                if o["reach"] and c["reach"]:
                    ro, rc = sum(o["reach"]) / len(o["reach"]), sum(c["reach"]) / len(c["reach"])
                    if ro >= 24 and rc < 0.6 * ro:
                        warns.append(f"{path}: group '{g}' reach {ro:.0f} h -> {rc:.0f} h")
        # (almost) always-red channels
        for cid, p in progs.items():
            if p["n"] >= 20 and p["red"] >= 0.9 * p["n"]:
                warns.append(f"{path}: {cid} is marked live on {p['red']} of {p['n']} programmes")
        lines.append(f"| {path} | {n_ch} | {n_pr} | {ctime:%d %b %H:%M} ({age:.0f} h ago) | {verdict} |"
                     if ctime else f"| {path} | {n_ch} | {n_pr} | unknown | {verdict} |")
        sg = sorted(summarize(chans, progs, ctime or now, how).items(), key=lambda kv: -kv[1]["programmes"])
        details.append((path, sg))
    lines.append("")
    lines.append(f"## FAIL ({len(fails)})" if fails else "## FAIL (0) - none")
    lines += [f"- {x}" for x in fails]
    lines.append(f"\n## WARN ({len(warns)})" if warns else "\n## WARN (0) - none")
    lines += [f"- {x}" for x in warns[:60]]
    if len(warns) > 60:
        lines.append(f"- ... and {len(warns) - 60} more")
    lines.append("\n## Groups (channels / programmes / average reach in hours)")
    for path, sg in details:
        lines.append(f"\n**{path}**: " + ", ".join(
            f"{g} {len(v['channels'])}/{v['programmes']}/{(sum(v['reach']) / len(v['reach'])):.0f}h" if v["reach"] else f"{g} {len(v['channels'])}/{v['programmes']}/-"
            for g, v in sg[:25]))
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")
    for w in warns[:20]:
        print(f"::warning title=Guide health::{w}")
    for x in fails:
        print(f"::error title=Guide health::{x}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

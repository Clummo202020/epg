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
import json
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
# Tuned after the first report (2 Nov 2026): these come and go naturally, so they are not reported as group changes.
CHURN_GUIDES = {"events_epg.xml"}                      # PPV / event slots appear and disappear all day
CUP_GROUPS = {"ChallengeCup", "ScotLgeCup", "ScotCup", "Carabao", "FACup", "NationsLge", "ChampsLge", "Europa", "ConfLeague"}
MATCH_DRIVEN = {"football_epg.xml", "scottish_epg.xml"}    # a club's blocks end at its next match, so programmes and reach swing with the
                                                          # fixture list (every weekend) - only lost channels / placeholders count there (7 Nov 2026)
MIN_CHANNELS_LOST = 3                                  # a group must lose at least this many channels (and 20%) to be reported
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


def liveonsat_section(now, lines, warns, fails):
    """liveonsat_fixtures.json: how old, how many fixtures, which page failed (7 Nov 2026)"""
    path = "liveonsat_fixtures.json"
    lines.append("\n## LiveOnSat fixtures")
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        fetched = datetime.strptime(d["fetched"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception as e:
        warns.append(f"{path}: missing or unreadable ({e}) - event start times fall back to the stream-name time")
        lines.append("(file missing or unreadable)")
        return
    age = (now - fetched).total_seconds() / 3600
    rugby, fb = d.get("fixtures", []), (d.get("football") or {})
    lines.append(f"fetched {fetched:%d %b %H:%M} UTC ({age:.0f} h ago); rugby / fighting {len(rugby)} fixtures "
                 f"({sum(1 for f in rugby if f.get('stan'))} on Stan Sport); football {len(fb.get('fixtures', []))} fixtures.")
    if age > 48:
        fails.append(f"{path}: not refreshed for {age:.0f} h (its workflow runs every 6 h)")
    elif age > 14:
        warns.append(f"{path}: last refreshed {age:.0f} h ago (its workflow runs every 6 h)")
    pages = dict(d.get("pages", {}))
    pages.update({f"football {k}": v for k, v in (fb.get("pages") or {}).items()})
    bad = []
    for name, info in pages.items():
        if info.get("status") != 200 or "kept" in info:
            bad.append(f"{name}: HTTP {info.get('status')}, kept {info.get('kept', 0)} earlier fixture(s)")
        elif str(info.get("read", "")).startswith("text") and info.get("count", 0) > 0:
            bad.append(f"{name}: read by the text fallback - the page's markup may have changed")
    for b in bad:
        warns.append(f"LiveOnSat {b}")
    if (d.get("pages", {}).get("Rugby Union") or {}).get("count") == 0:
        warns.append("LiveOnSat Rugby Union page returned 0 fixtures")
    if fb and len(fb.get("fixtures", [])) < 100:
        warns.append(f"LiveOnSat football has only {len(fb.get('fixtures', []))} fixtures (normally 500+)")
    lines.append("pages: " + ", ".join(f"{n} {i.get('count', 'kept ' + str(i.get('kept', 0)))}" for n, i in pages.items() if not n.startswith("football ")) +
                 f"; football days {sum(1 for n in pages if n.startswith('football '))}")


def timing_section(lines, warns):
    """events_seen.json -> _timing: per provider group, the stream-name time minus the real start (event_epg.py, 7 Nov 2026)"""
    try:
        with open("events_seen.json", encoding="utf-8") as fh:
            t = json.load(fh).get("_timing")
    except Exception:
        t = None
    lines.append("\n## Stream times vs real start (events guide)")
    if not t or not t.get("groups"):
        lines.append("(no statistics in events_seen.json yet - they appear after the next events run)")
        return
    lines.append(f"Time in the stream name minus the real start, in minutes (negative = the stream opens EARLY); this run's streams, "
                 f"updated {t.get('updated', '?')}. \"moved\" = the guide already uses the real start for that group.\n")
    lines.append("| group | timed | not found | median | range | moved |\n|---|---|---|---|---|---|")
    for g, v in sorted(t["groups"].items(), key=lambda kv: -(kv[1].get("n", 0) + kv[1].get("missed", 0))):
        if v.get("n", 0) + v.get("missed", 0) == 0:
            continue
        med = f"{v['median']:+d}" if "median" in v else "-"
        rng = f"{v['min']:+d} .. {v['max']:+d}" if "min" in v else "-"
        lines.append(f"| {g} | {v.get('n', 0)} | {v.get('missed', 0)} | {med} | {rng} | {'yes' if v.get('applied') else 'no'} |")
        if not v.get("applied") and v.get("n", 0) >= 5 and abs(v.get("median", 0)) >= 8:
            warns.append(f"events: {g} stream times are {abs(v['median'])} min {'early' if v['median'] < 0 else 'late'} "
                         f"(median of {v['n']} matches) - consider moving this group to the real start")


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
                if path in CHURN_GUIDES or g in CUP_GROUPS:
                    continue
                c = cur_g.get(g)
                if not c:
                    if len(o["channels"]) >= MIN_CHANNELS_LOST:
                        warns.append(f"{path}: group '{g}' has gone ({len(o['channels'])} channels)")
                    continue
                gone = o["channels"] - c["channels"]
                if len(gone) >= MIN_CHANNELS_LOST and len(gone) >= 0.2 * len(o["channels"]):
                    warns.append(f"{path}: group '{g}' lost {len(gone)} channel(s): {', '.join(sorted(gone)[:6])}")
                if path in MATCH_DRIVEN:
                    continue
                if len(o["channels"]) >= MIN_CHANNELS_LOST and o["programmes"] >= 30 and c["programmes"] < 0.6 * o["programmes"]:
                    warns.append(f"{path}: group '{g}' programmes {o['programmes']} -> {c['programmes']}")
                if o["reach"] and c["reach"]:
                    ro, rc = sum(o["reach"]) / len(o["reach"]), sum(c["reach"]) / len(c["reach"])
                    if ro >= 48 and rc < 0.5 * ro:
                        warns.append(f"{path}: group '{g}' reach {ro:.0f} h -> {rc:.0f} h")
            # channels that were real yesterday and are now only "no schedule" blocks (the source lost them)
            if path not in CHURN_GUIDES:
                for cid, p_ in progs.items():
                    b_ = bpr.get(cid)
                    if (b_ and b_["n"] >= 6 and p_["n"] >= 6 and b_["ph"] < 0.5 * b_["n"] and p_["ph"] >= 0.9 * p_["n"]):
                        warns.append(f"{path}: {cid} now shows only placeholder blocks (its source lost it)")
        # (almost) always-red channels
        for cid, p in progs.items():
            if p["n"] >= 20 and p["red"] >= 0.9 * p["n"]:
                warns.append(f"{path}: {cid} is marked live on {p['red']} of {p['n']} programmes")
        lines.append(f"| {path} | {n_ch} | {n_pr} | {ctime:%d %b %H:%M} ({age:.0f} h ago) | {verdict} |"
                     if ctime else f"| {path} | {n_ch} | {n_pr} | unknown | {verdict} |")
        sg = sorted(summarize(chans, progs, ctime or now, how).items(), key=lambda kv: -kv[1]["programmes"])
        details.append((path, sg))
    extra = []
    liveonsat_section(now, extra, warns, fails)
    timing_section(extra, warns)
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
    lines += extra
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

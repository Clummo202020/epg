#!/usr/bin/env python3
"""
One-off check, round 2 (4 Nov 2026) - NOT part of the guides. Run once from the GitHub runner, read the log, delete.

Round 1 showed: ontvtonight and YourTV both answer the runner (HTTP 200); neither page lists Fox Sports / ESPN by
default; YourTV has a "Foxtel" pay-TV selector (data-pay-region-name="Foxtel") and my guessed JSON api was a 404.
Round 2 looks at HOW YourTV's pay-TV choice works (page markup + its one JavaScript bundle) and what ontvtonight
really sends the runner. Read-only: 3 GET requests to yourtv, 1 to ontvtonight. Nothing is written to the repo.
"""
import re
import sys
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


def get(url, referer=None):
    hdrs = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-AU,en;q=0.9"}
    if referer:
        hdrs["Referer"] = referer
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), (e.read().decode("utf-8", "replace") if e.fp else "")
    except Exception as e:
        return 0, {}, "ERROR %s: %s" % (type(e).__name__, e)


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


def ctx(text, pattern, width=110, limit=12, flags=re.I):
    out = []
    for m in re.finditer(pattern, text, flags):
        out.append(squash(text[max(0, m.start() - width):m.end() + width]))
        if len(out) >= limit:
            break
    return out


def head(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def yourtv():
    head("YourTV: the pay-TV selector in the page")
    st, h, body = get("https://www.yourtv.com.au/guide/")
    print("page HTTP %s, %d bytes" % (st, len(body)))
    i = body.find("user-prefs__panel")
    print("-- first user-prefs panel markup (2500 chars) --")
    print(squash(body[max(0, i - 200):i + 2500]))
    print("-- every data-pay-region attribute (with the tag around it) --")
    for m in re.finditer(r'<a[^>]*data-pay-region[^>]*>[^<]*', body):
        print("  " + squash(m.group(0))[:260])
    print("-- data-module-ns-tvguide modules --")
    print("  " + ", ".join(sorted(set(re.findall(r'data-module-ns-tvguide="([^"]+)"', body)))))
    print("-- hrefs/forms/inputs mentioning pay / foxtel / subscription --")
    for s in ctx(body, r'(href|action|name|value)="[^"]*(pay|foxtel|subscription)[^"]*"', 60, 15):
        print("  " + s[:300])
    print("-- cookies the page sets --")
    print("  " + str({k: v[:120] for k, v in h.items() if k.lower() == "set-cookie"}))
    print("-- one programme + one channel container (markup) --")
    j = body.find("/program/")
    print("  programme: " + squash(body[max(0, j - 500):j + 400]))
    k = re.search(r'class="[^"]*channel[^"]*"', body)
    if k:
        print("  channel: " + squash(body[k.start() - 100:k.start() + 500]))
    print("-- channel names (img alt / title) in the page --")
    alts = re.findall(r'alt="([^"]{2,40})"', body)
    print("  " + ", ".join(sorted(set(alts))[:80]))

    head("YourTV: the JavaScript bundle")
    m = re.search(r'src="(/js/bundle-[^"]+\.js)"', body)
    if not m:
        print("no /js/bundle-*.js found")
        return
    url = "https://www.yourtv.com.au" + m.group(1)
    st2, h2, js = get(url, referer="https://www.yourtv.com.au/guide/")
    print("%s -> HTTP %s, %d bytes" % (url, st2, len(js)))
    if st2 != 200:
        return
    for label, pat in [("pay-region / payRegion", r'pay[-_ ]?region'), ("cookie", r'cookie'),
                       ("api / ajax / fetch urls", r'["\'](/(?:api|ajax|data|json|guide)[^"\']{0,80})["\']'),
                       ("subscription", r'subscription'), ("region param", r'region(?:Id|_id|=)')]:
        hits = ctx(js, pat, 90, 10)
        print("-- %s (%d shown) --" % (label, len(hits)))
        for s in hits:
            print("  " + s[:320])


def ontvtonight():
    head("ontvtonight: what the runner actually receives")
    st, h, body = get("https://www.ontvtonight.com/au/guide/listings/SydneyNight.html")
    print("HTTP %s, %d bytes; 'cid=' links: %d; 'channel/' links: %d" % (
        st, len(body), body.count("cid="), body.count("listings/channel/")))
    print("title: %s" % (re.findall(r"<title>([^<]*)", body) or ["?"])[0])
    print("first 1200 chars of <body>:")
    b = body.find("<body")
    print("  " + squash(body[b:b + 1200]))


def main():
    print("Python %s" % sys.version.split()[0])
    yourtv()
    ontvtonight()
    print("\nDONE")


if __name__ == "__main__":
    main()

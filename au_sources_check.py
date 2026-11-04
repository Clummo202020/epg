#!/usr/bin/env python3
"""
One-off check (4 Nov 2026) - NOT part of the guides. Run once from the GitHub runner, read the log, then delete.

Question: can ontvtonight.com/au and yourtv.com.au (Nine) replace epgshare AU1 for the Fox Sports / ESPN channels?
It only READS public pages (a handful of requests, no login, no cookies) and prints:
  - HTTP status / size / server for each page (a 403 here = the site refuses the runner, as Foxtel did - then stop)
  - whether the words Fox Sports / ESPN / Fox Footy ... appear in the pages
  - hints of a data service behind the pages (api paths, JSON blobs, script files)
  - for YourTV: a guess at its JSON guide service, how many days it returns, channel names, fields of a programme
Nothing is written to the repo.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
TIMEOUT = 30
KEYWORDS = ["Fox Sports", "FoxSports", "Fox Footy", "Fox Cricket", "Fox League", "ESPN", "Foxtel", "Kayo",
            "Sky Racing", "beIN"]


def get(url, accept="text/html,application/json;q=0.9,*/*;q=0.8", extra=None):
    """Return (status, headers dict, body text). Never raises."""
    hdrs = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-AU,en;q=0.9"}
    if extra:
        hdrs.update(extra)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, dict(e.headers or {}), body
    except Exception as e:  # DNS, timeout, TLS ...
        return 0, {}, "ERROR %s: %s" % (type(e).__name__, e)


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def show_page(url):
    st, h, body = get(url)
    print("GET %s" % url)
    print("  -> HTTP %s, %d bytes, content-type=%s, server=%s" % (
        st, len(body), h.get("Content-Type") or h.get("content-type"), h.get("Server") or h.get("server")))
    for k in ("x-deny-reason", "X-Deny-Reason", "cf-ray", "x-amzn-waf-action", "x-datadome", "x-akamai-edgescape"):
        if k in h:
            print("  header %s: %s" % (k, h[k]))
    if st != 200:
        print("  body starts: %r" % body[:300])
    return st, h, body


def keyword_report(body):
    low = body.lower()
    found = {k: low.count(k.lower()) for k in KEYWORDS}
    print("  keyword counts: " + ", ".join("%s=%d" % (k, v) for k, v in found.items()))


def hints(body):
    """Pointers to a data service behind the page."""
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', body)
    print("  script files (%d): %s" % (len(scripts), ", ".join(s[:90] for s in scripts[:12])))
    apis = sorted(set(re.findall(r'["\'(](/api/[A-Za-z0-9_\-./?=&%]*)', body)))
    print("  /api/ paths in the page (%d): %s" % (len(apis), ", ".join(apis[:20])))
    full = sorted(set(re.findall(r'https?://[A-Za-z0-9.\-]+/(?:api|graphql|guide)[A-Za-z0-9_\-./?=&%]*', body)))
    print("  absolute api-like urls (%d): %s" % (len(full), ", ".join(u[:110] for u in full[:15])))
    blobs = re.findall(r'<script[^>]*(?:id="__NEXT_DATA__"|type="application/(?:ld\+)?json")[^>]*>(.{0,200})', body, re.S)
    print("  inline JSON blobs: %d %s" % (len(blobs), [b[:80].replace("\n", " ") for b in blobs[:3]]))
    for word in ("subscription", "provider", "foxtel", "region", "postcode"):
        hits = [m.start() for m in re.finditer(word, body, re.I)]
        if hits:
            i = hits[0]
            print("  '%s' x%d, first: ...%s..." % (word, len(hits), re.sub(r"\s+", " ", body[max(0, i - 60):i + 100])))


def check_ontvtonight():
    head("1. ontvtonight.com/au")
    st, h, body = show_page("https://www.ontvtonight.com/au/guide/listings/SydneyNight.html")
    if st == 200:
        keyword_report(body)
        hints(body)
        chans = re.findall(r'listings/channel/(\d+)/([a-z0-9\-]+)\.html', body)
        names = sorted(set(n for _, n in chans))
        print("  channels in default (Free TV) view: %d" % len(names))
        print("  " + ", ".join(names))
        # provider / pay tv links
        links = sorted(set(re.findall(r'href="([^"]*(?:provider|pay|foxtel)[^"]*)"', body, re.I)))
        print("  provider / pay links: %s" % links[:15])
        forms = re.findall(r'<form[^>]*>', body)
        print("  forms: %s" % [f[:140] for f in forms[:5]])
    # a few guesses at the Free + Pay TV view (harmless GETs)
    for url in ("https://www.ontvtonight.com/au/guide/listings/SydneyNight.html?provider=0",
                "https://www.ontvtonight.com/au/guide/tvbycity.html",
                "https://www.ontvtonight.com/au/user/provider"):
        st2, h2, b2 = show_page(url)
        if st2 == 200:
            keyword_report(b2)
            opts = re.findall(r'<option[^>]*>([^<]{2,60})</option>', b2)
            if opts:
                print("  <option> values: %s" % opts[:30])


def check_yourtv():
    head("2. yourtv.com.au (Nine)")
    st, h, body = show_page("https://www.yourtv.com.au/guide/")
    if st == 200:
        keyword_report(body)
        hints(body)
        chan_links = sorted(set(re.findall(r'(?:/guide/channel|/channel)/[A-Za-z0-9\-_/]+', body)))
        print("  channel links in page: %d %s" % (len(chan_links), chan_links[:10]))
    # JSON guide service - guess (used by other open-source EPG grabbers)
    today = date.today()
    head("2b. yourtv JSON guide guess: /api/guide/?day=...&timezone=Australia/Sydney&format=json&region=75")
    first_payload = None
    days_ok = []
    for i in range(-1, 11):
        d = (today + timedelta(days=i)).isoformat()
        url = ("https://www.yourtv.com.au/api/guide/?day=%s&timezone=Australia/Sydney&format=json&region=75" % d)
        st3, h3, b3 = get(url, accept="application/json,text/plain,*/*",
                          extra={"Referer": "https://www.yourtv.com.au/guide/"})
        n = None
        try:
            data = json.loads(b3)
            if first_payload is None and st3 == 200:
                first_payload = data
            n = len(data) if isinstance(data, list) else len(data.keys())
        except Exception:
            pass
        print("  %s -> HTTP %s, %d bytes, top-level items=%s%s" % (
            d, st3, len(b3), n, "" if st3 == 200 else "  body: %r" % b3[:120]))
        if st3 == 200 and n:
            days_ok.append(d)
    print("  days with data: %d %s" % (len(days_ok), (days_ok[0] + " .. " + days_ok[-1]) if days_ok else ""))
    if first_payload is not None:
        describe_yourtv(first_payload)
    else:
        print("  (no JSON from the guess - see the page hints above for the real service)")


def describe_yourtv(data):
    head("2c. what the YourTV JSON looks like")
    chans = data if isinstance(data, list) else data.get("channels") or data.get("data") or []
    print("  channel entries: %d" % len(chans))
    if not chans:
        print("  raw start: %s" % json.dumps(data)[:600])
        return
    c0 = chans[0]
    print("  channel fields: %s" % (list(c0.keys()) if isinstance(c0, dict) else type(c0)))
    names = []
    for c in chans:
        if isinstance(c, dict):
            names.append(str(c.get("description") or c.get("name") or c.get("title") or c.get("number") or "?"))
    print("  channel names: %s" % ", ".join(names[:80]))
    pay = [n for n in names if re.search(r"fox|espn|kayo|foxtel|sky racing|sport", n, re.I)]
    print("  Fox / ESPN / sport-looking channels: %d %s" % (len(pay), pay))
    # programme fields
    for key in ("airings", "programs", "programmes", "events", "shows"):
        if isinstance(c0, dict) and isinstance(c0.get(key), list) and c0[key]:
            print("  first programme (%s): %s" % (key, json.dumps(c0[key][0])[:700]))
            break
    else:
        print("  channel 0 sample: %s" % json.dumps(c0)[:700])


def main():
    print("Python %s" % sys.version.split()[0])
    check_ontvtonight()
    check_yourtv()
    print()
    print("DONE - read the HTTP codes first: 403/429/0 means the site refuses or cannot be reached from the runner.")


if __name__ == "__main__":
    main()

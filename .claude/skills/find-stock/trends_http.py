#!/usr/bin/env python3
"""Google Trends without a browser — stdlib only. Built for cloud sessions
where Claude-in-Chrome/Playwright don't exist; works locally too.

    python3 trends_http.py "NBIS stock" "nebius stock" "PLTR stock"
    python3 trends_http.py --time "now 7-d" --geo US --property youtube KW [KW ...]
    python3 trends_http.py --related "NBIS stock"

Defaults match the find-stock skill: property=youtube, time=now 7-d, geo=US.
Max 5 keywords per comparison (Google's limit). Values are relative 0-100
within one comparison set — reuse an anchor keyword across batches.

If Google returns 429/blocked (datacenter IPs sometimes are), this prints a
clear error — fall back to the skill's autocomplete + view-velocity path.
Verified working 2026-08-15 from a residential IP.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36")}


def _get(url, cookie=None, tries=3):
    h = dict(UA)
    if cookie:
        h["Cookie"] = cookie
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            return urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                time.sleep(3 * (i + 1))
                continue
            raise
    raise SystemExit(f"BLOCKED: Google answered {last.code} after {tries} tries "
                     f"— fall back to the autocomplete/view-velocity path.")


def _cookie():
    r = _get("https://trends.google.com/")
    for k, v in r.headers.items():
        if k.lower() == "set-cookie" and "NID" in v:
            return v.split(";")[0]
    return None


def explore(keywords, geo, timeframe, prop, cookie):
    payload = {"comparisonItem": [{"keyword": k, "geo": geo, "time": timeframe}
                                  for k in keywords],
               "category": 0, "property": prop}
    url = "https://trends.google.com/trends/api/explore?" + urllib.parse.urlencode(
        {"hl": "en-US", "tz": "300", "req": json.dumps(payload)})
    body = _get(url, cookie).read().decode()
    return json.loads(body[body.index("{"):])["widgets"]


def widget_data(widget, cookie, kind):
    url = (f"https://trends.google.com/trends/api/widgetdata/{kind}?"
           + urllib.parse.urlencode({"hl": "en-US", "tz": "300",
                                     "req": json.dumps(widget["request"]),
                                     "token": widget["token"]}))
    body = _get(url, cookie).read().decode()
    return json.loads(body[body.index("{"):])


def timeseries(keywords, geo, timeframe, prop, cookie):
    widgets = explore(keywords, geo, timeframe, prop, cookie)
    tl = next(w for w in widgets if w["id"] == "TIMESERIES")
    pts = widget_data(tl, cookie, "multiline")["default"]["timelineData"]
    # bucket hourly points into days -> daily averages per keyword
    daily = defaultdict(lambda: [0.0] * len(keywords))
    counts = defaultdict(int)
    for p in pts:
        day = p["formattedTime"].split(" at ")[0]
        counts[day] += 1
        for i, v in enumerate(p["value"]):
            daily[day][i] += v
    days = list(daily)
    print(f"\n=== {prop or 'web'} · {timeframe} · {geo} — daily averages ===")
    print("day".ljust(14) + "".join(k[:16].ljust(18) for k in keywords))
    for d in days:
        row = [daily[d][i] / counts[d] for i in range(len(keywords))]
        print(d.ljust(14) + "".join(f"{v:6.1f}".ljust(18) for v in row))
    if len(days) >= 4:
        print("\n=== momentum: last-2-day avg vs prior avg ===")
        for i, k in enumerate(keywords):
            head = [daily[d][i] / counts[d] for d in days[:-2]]
            tail = [daily[d][i] / counts[d] for d in days[-2:]]
            ha = sum(head) / len(head) if head else 0
            ta = sum(tail) / len(tail) if tail else 0
            arrow = "RISING" if ta > ha * 1.15 else ("fading" if ta < ha * 0.85 else "flat")
            print(f"  {k[:28].ljust(30)} early {ha:5.1f} -> recent {ta:5.1f}   {arrow}")


def related(keyword, geo, timeframe, prop, cookie):
    widgets = explore([keyword], geo, timeframe, prop, cookie)
    for w in widgets:
        if w["id"] != "RELATED_QUERIES":
            continue
        data = widget_data(w, cookie, "relatedsearches")
        for rank in data["default"]["rankedList"]:
            kind = "TOP" if rank is data["default"]["rankedList"][0] else "RISING"
            print(f"\n=== related queries ({kind}) for {keyword!r} ===")
            for item in rank["rankedKeyword"][:10]:
                val = item.get("formattedValue", item.get("value", ""))
                print(f"  {str(val).rjust(9)}  {item['query']}")
        return
    print("no related-queries widget returned")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("keywords", nargs="+", help="1-5 keywords")
    ap.add_argument("--geo", default="US")
    ap.add_argument("--time", default="now 7-d", dest="timeframe")
    ap.add_argument("--property", default="youtube", dest="prop",
                    choices=["youtube", "web", "news", "images", "froogle"])
    ap.add_argument("--related", action="store_true",
                    help="pull related queries (single keyword)")
    a = ap.parse_args()
    if len(a.keywords) > 5:
        sys.exit("max 5 keywords per comparison")
    prop = "" if a.prop == "web" else a.prop
    c = _cookie()
    if a.related:
        related(a.keywords[0], a.geo, a.timeframe, prop, c)
    else:
        timeseries(a.keywords, a.geo, a.timeframe, prop, c)

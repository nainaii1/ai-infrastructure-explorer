#!/usr/bin/env python3
"""Support floors for the accumulate list, from the Google Sheet's
`price_history` tab (GOOGLEFINANCE daily bars, about a year, public CSV export,
no key). Each name is a block of six columns (Date, Open, High, Low, Close,
Volume) under a header cell holding the desk ticker; add a block to the tab to
add a name.

A floor is a daily swing low: the lowest low within five sessions either side.
Floors within 3% of each other are merged into one band. The weekly memo uses
them for the levels (see the weekly-memo skill):

    buyBelow   3% above the floor the stock is testing now
    addBelow   the next floor down
    stopAbove  the valuation ceiling (from a sourced multiple, not the chart)

Each name also gets a stretch line: its move over the last five sessions
against SMH's, and its distance from the 50-day average. A name that rose
more than STRETCH in five sessions is not testing a floor: the nearest floor
below it is an old one it just reclaimed, so keep the last memo's lines
rather than raising them (no chasing).

    python3 desk/support.py              all names in the tab
    python3 desk/support.py MU NBIS      just these
"""
import csv
import io
import sys
from datetime import datetime

from common import http_get

HISTORY_CSV = ("https://docs.google.com/spreadsheets/d/"
               "1Zeqqq01H1KiSvJnNArm0kr2rcn-F3FV8uxYjjX8mihA/export?format=csv&gid=175825543")
SIDE = 5        # sessions either side for a swing low
MERGE = 0.03    # floors within 3% are one band
BAND = 0.03     # buy line sits this far above the floor being tested
STRETCH = 0.08  # a five-session rise above this means "not testing a floor"


def load():
    rows = list(csv.reader(io.StringIO(http_get(HISTORY_CSV, timeout=60).decode("utf-8"))))
    out = {}
    for c, key in enumerate(rows[0] if rows else []):
        if not key:
            continue
        bars = []
        for r in rows[2:]:
            if c + 4 >= len(r) or not r[c]:
                continue
            try:
                d = datetime.strptime(r[c].split()[0], "%m/%d/%Y").date()
                bars.append((d, float(r[c + 2]), float(r[c + 3]), float(r[c + 4])))   # date, high, low, close
            except ValueError:
                continue
        out[key] = bars
    return out


def floors(bars):
    """Swing-low bands below the last close, nearest first: [(low, high, [dates])]."""
    px = bars[-1][3]
    piv = []
    for i in range(SIDE, len(bars) - 1):
        w = bars[i - SIDE:i + SIDE + 1]
        if bars[i][2] == min(b[2] for b in w) and bars[i][2] < px:
            piv.append((bars[i][2], bars[i][0]))
    bands = []
    for low, d in sorted(piv, reverse=True):
        if bands and abs(low / bands[-1][0] - 1) < MERGE:
            bands[-1] = (low, bands[-1][1], bands[-1][2] + [d])
        else:
            bands.append((low, low, [d]))
    return bands


def avg(bars, n):
    return sum(b[3] for b in bars[-n:]) / n if len(bars) >= n else None


def move(bars, n=5):
    return bars[-1][3] / bars[-1 - n][3] - 1 if len(bars) > n else None


def main():
    data = load()
    want = sys.argv[1:] or list(data)
    bench = move(data["SMH"]) if data.get("SMH") else None
    for key in want:
        bars = data.get(key)
        if not bars:
            print("{}: not in the price_history tab".format(key))
            continue
        d, _, _, px = bars[-1]
        hi = max(b[1] for b in bars)
        ma50, ma200 = avg(bars, 50), avg(bars, 200)
        print("\n{}  close {:,.2f} on {}  |  {:+.1f}% from 1y high {:,.2f}  |  50d {}  200d {}".format(
            key, px, d, (px / hi - 1) * 100, hi,
            "{:,.2f}".format(ma50) if ma50 else "n/a", "{:,.2f}".format(ma200) if ma200 else "n/a"))
        m5 = move(bars)
        stretched = m5 is not None and m5 > STRETCH
        if m5 is not None:
            print("   stretch: {:+.1f}% in 5 sessions{}{}{}".format(
                m5 * 100, " (SMH {:+.1f}%)".format(bench * 100) if bench is not None else "",
                ", {:+.1f}% vs 50d".format((px / ma50 - 1) * 100) if ma50 else "",
                "  STRETCHED: not testing a floor; keep the last memo's lines" if stretched else ""))
        bands = floors(bars)
        if not bands:
            print("   no floor below the close in the last year")
        for i, (lo, top, ds) in enumerate(bands[:5]):
            note = ("  <- buy line {:,.2f}{}".format(top * (1 + BAND), " (only if it pulls back to test it)" if stretched else "")
                    if i == 0 else ("  <- add line" if i == 1 else ""))
            print("   floor {:,.2f}-{:,.2f} ({:+.1f}%)  {}{}".format(
                lo, top, (top / px - 1) * 100, ", ".join(x.strftime("%d %b %y") for x in sorted(ds)), note))
    return 0


if __name__ == "__main__":
    sys.exit(main())

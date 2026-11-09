"""List which Kalshi series charge a maker fee, from Kalshi's public API (no key needed).

    python3 fee_types.py              # prints counts by category
    python3 fee_types.py --csv out.csv  # writes every series that charges makers

A series charges resting (maker) orders when its fee_type is quadratic_with_maker_fees
(maker 0.0175 x P x (1 - P)) or quadratic_with_combo_maker_fees (0.035). Every other
series charges takers only.
"""
import csv, json, sys, urllib.request
from collections import Counter

API = "https://api.elections.kalshi.com/trade-api/v2/series"


def series():
    with urllib.request.urlopen(urllib.request.Request(API, headers={"User-Agent": "kalshi-fees"}), timeout=60) as r:
        return json.load(r)["series"]


def maker_fee_series(all_series=None):
    rows = all_series if all_series is not None else series()
    return [s for s in rows if str(s.get("fee_type", "")).startswith("quadratic_with")]


def main(argv):
    rows = series()
    mk = maker_fee_series(rows)
    print("%d of %d series charge a maker fee" % (len(mk), len(rows)))
    for cat, n in Counter(s.get("category") for s in mk).most_common():
        print("  %-28s %d" % (cat, n))
    if argv[1:2] == ["--csv"]:
        with open(argv[2], "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ticker", "title", "category", "fee_type", "fee_multiplier"])
            for s in sorted(mk, key=lambda s: (s.get("category") or "", s["ticker"])):
                w.writerow([s["ticker"], s.get("title", ""), s.get("category", ""), s.get("fee_type", ""), s.get("fee_multiplier", "")])
        print("wrote", argv[2])


if __name__ == "__main__":
    main(sys.argv)

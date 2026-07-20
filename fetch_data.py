"""Fetch 12 months of weekly closes for the whole game universe (universe2.json)
via the stockanalysis.com history API.

Default mode (nightly rebuild): refetch EVERY ticker; a per-ticker failure keeps the
previous run's series for that ticker (chart goes at most one day staler, never blank).
`python3 fetch_data.py resume` skips tickers already present — for resuming an
interrupted initial population only.

Exits non-zero if too many tickers have no data at all (protects the nightly
workflow from committing a gutted build).
"""
import json, time, os, sys, urllib.request

D = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json"}
OUT = os.path.join(D, "prices_raw.json")
RESUME = "resume" in sys.argv[1:]

UNI = json.load(open(os.path.join(D, "universe2.json")))

def fetch(tk):
    url = f"https://stockanalysis.com/api/symbol/s/{tk}/history?range=1Y&period=Weekly"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)
    pts = sorted([(row["t"], row["c"]) for row in j["data"] if row.get("c") is not None])
    if len(pts) < 20:   # recent IPOs/spinoffs have short history; the chart plots what exists
        raise ValueError(f"only {len(pts)} pts")
    return pts

out = json.load(open(OUT)) if os.path.exists(OUT) else {}
fresh, kept_stale, failed = 0, 0, []
for n, tk in enumerate(UNI):
    if RESUME and tk in out:
        continue
    ok = False
    for attempt in range(3):
        try:
            out[tk] = fetch(tk)
            fresh += 1; ok = True
            break
        except Exception as e:
            if attempt == 2:
                if tk in out: kept_stale += 1
                else: failed.append((tk, str(e)))
                print(f"{tk}: FAILED {e}", flush=True)
            time.sleep(1.2)
    if ok and fresh % 25 == 0:
        json.dump(out, open(OUT, "w"))
        print(f"...{fresh} fetched ({n+1}/{len(UNI)})", flush=True)
    time.sleep(0.35)

json.dump(out, open(OUT, "w"))
missing = [tk for tk in UNI if tk not in out]
print(f"Done: {fresh} fresh · {kept_stale} kept stale · {len(missing)} missing entirely")
if missing:
    print("missing:", missing[:20])
if len(missing) > 15:
    sys.exit(1)   # too broken to build — keep yesterday's site

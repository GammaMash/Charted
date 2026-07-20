"""Build gamedata.json from universe2.json + prices_raw.json.
Runs nightly via GitHub Actions, so every number is recomputed from the fresh
12-month window. Hand-written story narratives carry a validity condition on the
12-mo return — if the market drifts until a narrative no longer holds, that puzzle
falls back to the auto story instead of shipping a stale claim.
"""
import json, math, os
from company_cards import CO

D = os.path.dirname(os.path.abspath(__file__))
prices = json.load(open(f"{D}/prices_raw.json"))
uni = json.load(open(f"{D}/universe2.json"))
uni = {t: v for t, v in uni.items() if t in prices}

# Refine cap bucket for non-S&P (cult) names: last close × approx shares (millions)
SHARES_M = { tk: m for tk, m in {
 "MU":1110,"MSTR":280,"COIN":250,"HOOD":880,"SOFI":1060,"GME":447,"AMC":500,"RIVN":1010,"LCID":3030,
 "IONQ":230,"RGTI":270,"ACHR":530,"JOBY":780,"OKLO":140,"CRCL":230,"GEMI":120,"SNDK":140,"OUST":50,
 "UPST":90,"AFRM":320,"CHWY":415,"WEN":205,"RKLB":500,"SPOT":200,"SHOP":1290,"ARM":1050,"NVO":4450,
 "SNOW":335,"NET":340,"RBLX":650,"CVNA":210,"MRNA":385,"HIMS":215,"MARA":350,"RIOT":350,"BBAI":250,
 "NIO":2100,"QUBT":140,"ROKU":145,"MRVL":866,"ANET":1256,"SMCI":590,"DKNG":490,"SBUX":1130,"LULU":120,
}.items() }
def bucket(cap_b):
    if cap_b >= 200: return "MEGA"
    if cap_b >= 20:  return "LARGE"
    if cap_b >= 2:   return "MID"
    return "SMALL"
for tk, v in uni.items():
    if not v.get("sp500") and tk in SHARES_M:
        cap_b = prices[tk][-1][1] * SHARES_M[tk] / 1000.0
        v["cap"] = bucket(cap_b); v["capB"] = round(cap_b, 1)

BUCKET_ORDER = {"SMALL":0,"MID":1,"LARGE":2,"MEGA":3}

# "Shape match" = what the player's eyes compare on an auto-scaled chart:
# min-max-normalized paths, similarity = 1 - 2*RMSE.
def shape_sim(a, b):
    da = dict(prices[a]); db = dict(prices[b])
    common = sorted(set(da) & set(db))
    if len(common) < 10: return 0.0
    def norm(d2c):
        ys = [d2c[d] for d in common]; lo, hi = min(ys), max(ys)
        return [(y-lo)/(hi-lo) if hi > lo else 0.5 for y in ys]
    xa, xb = norm(da), norm(db)
    rmse = math.sqrt(sum((x-y)**2 for x, y in zip(xa, xb))/len(xa))
    return round(max(-1.0, 1 - 2*rmse), 3)

def stats(ys):
    tot = (ys[-1]/ys[0]-1)*100
    peak = ys[0]; dd = 0.0
    for y in ys:
        peak = max(peak, y); dd = min(dd, y/peak-1)
    wr = [ys[j]/ys[j-1]-1 for j in range(1, len(ys))]
    big = max(wr, key=abs)*100
    return tot, big, dd*100

# Hand narratives: (condition on 12-mo total %, narrative). Numbers are NEVER
# hand-written — the computed stat line is appended to every story, so it can't go stale.
HAND = {
 "MU":   (lambda t: t > 50,        "Micron rode the AI memory supercycle to a trillion-dollar market cap — then gave a chunk back after the late-June '26 earnings peak."),
 "MSTR": (lambda t: t < 0,         "Bitcoin was cut in half from its October '25 all-time high — Strategy, the leveraged Bitcoin proxy, fell even harder."),
 "INTC": (lambda t: t > 50,        "Intel: the comeback almost nobody on this app believed in."),
 "GME":  (lambda t: abs(t) < 60,   "GameStop: multiple squeezes, zero trend — a year of violent round trips."),
 "MSFT": (lambda t: t < 0,         "A rare down year for the market's favorite safe-haven mega cap — while memory and moonshot names tripled."),
 "NKE":  (lambda t: t < -15,       "Nike's slow bleed: no crash, no headline week — just 52 weeks of lower highs."),
 "CAT":  (lambda t: t > 40,        "Caterpillar quietly compounded — the kind of chart nobody screenshots and everybody wishes they owned."),
 "SNDK": (lambda t: t > 300,       "SanDisk, the other memory stock — the single most vertical chart in the whole universe."),
 "NVDA": (lambda t: abs(t) < 40,   "The most talked-about stock on earth, with one of the least dramatic charts in the game. Hard mode."),
}

QUEUE = ["GME","AAPL","TSLA","NFLX","MU","SBUX","KO","DIS","INTC","NKE",
         "MSFT","CAT","AMD","HOOD","COIN","LULU","BA","IBM","RIVN","DELL",
         "MRVL","PLTR","SMCI","AVGO","CVNA","MSTR","CRCL","GEMI","SNDK","NVDA"]

def story(tk, ys):
    tot, big, dd = stats(ys)
    nums = f" The numbers: {tot:+.0f}% in 12 months · biggest week {big:+.0f}% · worst drawdown {dd:.0f}%."
    cond, narr = HAND.get(tk, (None, None))
    if narr and cond(tot):
        return narr + nums
    return f"{uni[tk]['name']} — now you'll recognize this chart next time." + nums

out = []
for i, tk in enumerate(QUEUE):
    assert uni[tk]["answer"], f"{tk} not answer-eligible"
    assert tk in CO, f"{tk} missing a company_cards.CO entry"
    pts = prices[tk]; ys = [c for _, c in pts]; ds = [d for d, _ in pts]
    wr = [(ds[j], ys[j]/ys[j-1]-1) for j in range(1, len(ys))]
    big = max(wr, key=lambda x: abs(x[1]))
    out.append({
      "id": i+1, "answer": tk, "story": story(tk, ys), "co": CO[tk],
      "dates": ds, "closes": [round(y, 2) for y in ys],
      "annot": {"i": ds.index(big[0]), "label": f"biggest week of the year: {big[1]*100:+.0f}%"},
      "corr": {t: shape_sim(tk, t) for t in uni if t != tk},
    })

json.dump({"universe": uni, "bucketOrder": BUCKET_ORDER, "puzzles": out},
          open(f"{D}/gamedata.json", "w"), separators=(",", ":"))
n_ans = sum(v["answer"] for v in uni.values())
print(f"universe {len(uni)} · answers {n_ans} · gamedata {os.path.getsize(f'{D}/gamedata.json')//1024} KB")

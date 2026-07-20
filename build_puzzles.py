"""Build gamedata.json from the two-tier universe (universe2.json + prices_raw.json).
Guess space = everything; answers = the curated story-stock pool (answer flag)."""
import json, math, os
from universe import UNIVERSE as OLD
from company_cards import CO

D = os.path.dirname(os.path.abspath(__file__))
prices = json.load(open(f"{D}/prices_raw.json")); prices.pop("SPCX", None)
uni = json.load(open(f"{D}/universe2.json"))
uni = {t: v for t, v in uni.items() if t in prices}   # drop anything we couldn't fetch (e.g. FDXF)

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

# 30-day launch queue. Hand-written stories where we have verified context; the rest get
# data-driven stories computed from the price series (safe: no unverifiable narrative claims).
HAND_STORIES = {
 "MU":   "Micron rode the AI memory supercycle +663% in a year to a trillion-dollar cap — then gave back ~20% in three weeks after the late-June earnings peak.",
 "MSTR": "Bitcoin was cut in half from its October '25 all-time high — Strategy, the leveraged BTC proxy, fell 77%.",
 "INTC": "+359% in 12 months. The comeback almost nobody on this app believed in.",
 "GME":  "GameStop: multiple squeezes, zero trend — a year of violent round trips to finish roughly flat.",
 "MSFT": "A rare down year (−23%) for the market's favorite safe-haven mega cap — while memory and moonshot names tripled.",
 "NKE":  "Nike's slow bleed: −43% with no crash and no headline week — just 52 weeks of lower highs.",
 "CAT":  "Caterpillar quietly doubled (+103%) — the kind of chart nobody screenshots and everybody wishes they owned.",
 "SNDK": "SanDisk, the other memory stock: +3,089% in 12 months — the single most vertical chart in the whole universe.",
 "NVDA": "The most talked-about stock on earth had the least dramatic chart in the game: +17%, all chop. Hard mode.",
}
QUEUE = ["MU","GME","CRCL","CAT","MSTR","AAPL","SNDK","NKE","PLTR","INTC",
         "DIS","COIN","MSFT","AMD","NFLX","HOOD","LULU","DELL","BA","TSLA",
         "GEMI","SBUX","MRVL","IBM","RIVN","KO","SMCI","AVGO","CVNA","NVDA"]

def auto_story(tk, ys):
    tot=(ys[-1]/ys[0]-1)*100
    peak=ys[0]; dd=0
    for y in ys:
        peak=max(peak,y); dd=min(dd, y/peak-1)
    wr=[ys[j]/ys[j-1]-1 for j in range(1,len(ys))]
    big=max(wr,key=abs)*100
    name=uni[tk]["name"]
    return (f"{name}: {tot:+.0f}% over the 12 months — biggest single week {big:+.0f}%, "
            f"deepest drawdown {dd*100:.0f}% from its high. Now you'll recognize it next time.")

out = []
for i,tk in enumerate(QUEUE):
    assert uni[tk]["answer"], f"{tk} not answer-eligible"
    pts = prices[tk]; ys=[c for _,c in pts]; ds=[d for d,_ in pts]
    wr = [(ds[j], ys[j]/ys[j-1]-1) for j in range(1,len(ys))]
    big = max(wr, key=lambda x: abs(x[1]))
    out.append({
      "id": i+1, "answer": tk, "story": HAND_STORIES.get(tk) or auto_story(tk, ys),
      "co": CO[tk],
      "dates": ds, "closes": [round(y,2) for y in ys],
      "annot": {"i": ds.index(big[0]), "label": f"biggest week of the year: {big[1]*100:+.0f}%"},
      "corr": {t: shape_sim(tk,t) for t in uni if t != tk},
    })

json.dump({"universe":uni,"bucketOrder":BUCKET_ORDER,"puzzles":out}, open(f"{D}/gamedata.json","w"))
n_ans = sum(v["answer"] for v in uni.values())
print(f"universe {len(uni)} · answers {n_ans} · gamedata {os.path.getsize(f'{D}/gamedata.json')//1024} KB")
print("MU corr spot-checks — SNDK:", out[0]["corr"]["SNDK"], "AMAT:", out[0]["corr"].get("AMAT"), "KO:", out[0]["corr"]["KO"])

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
LONG = json.load(open(f"{D}/longterm.json"))

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
    v["price"] = round(prices[tk][-1][1], 2)
    if not v.get("sp500") and tk in SHARES_M:
        cap_b = prices[tk][-1][1] * SHARES_M[tk] / 1000.0
        v["cap"] = bucket(cap_b); v["capB"] = round(cap_b, 1)

BUCKET_ORDER = {"SMALL":0,"MID":1,"LARGE":2,"MEGA":3}

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
 # --- added 2026-07-31: the rest of the queue. Same contract: shape-driven narrative,
 # --- validity condition on the 12-mo return, computed stat line appended automatically.
 "AAPL": (lambda t: t > 25,        "Apple spent half the year going sideways — then woke up in spring and did a year's work in three months."),
 "TSLA": (lambda t: -25 < t < 10,  "A round trip drawn in real time: Tesla ripped into winter, then spent the rest of the year giving it back."),
 "NFLX": (lambda t: t < -25,       "The year every bounce got sold — Netflix made lower highs for twelve straight months."),
 "SBUX": (lambda t: 0 < t < 35,    "Starbucks kept it boring on purpose: one dip, one recovery, and a quiet finish near the highs."),
 "KO":   (lambda t: 5 < t < 40,    "Coke doesn't do drama — barely a dip all year, just the steady grind higher. That calm IS the fingerprint."),
 "DIS":  (lambda t: -30 < t < 0,   "No crisis, no comeback — Disney just leaked lower, one unremarkable month at a time."),
 "AMD":  (lambda t: t > 80,        "AMD nearly tripled — with a gut-check drawdown in the middle that shook out everyone who wasn't sure."),
 "HOOD": (lambda t: t < 5,         "Robinhood got cut in half mid-year, then clawed most of it back — the casino traded like one of its own tickers."),
 "COIN": (lambda t: t < -25,       "Crypto winter came back for Coinbase — down by half, with every rally fading inside a month."),
 "LULU": (lambda t: t < -20,       "Lululemon stretched too far — a steady markdown from last year's highs, one red stretch at a time."),
 "BA":   (lambda t: -25 < t < 10,  "Boeing chopped through turbulence all year and landed roughly where it took off."),
 "IBM":  (lambda t: t < 0,         "Two air pockets in an otherwise sleepy year — when Big Blue drops, it drops all at once."),
 "RIVN": (lambda t: t > 15,        "Rivian finally strung together an up year — violently. Nothing this stock does is gradual."),
 "DELL": (lambda t: t > 100,       "Dell — yes, Dell — tripled. The beige-box company turned momentum stock, and it's sitting at the highs."),
 "MRVL": (lambda t: t > 60,        "Marvell went vertical, then handed a big piece back — AI-chip beta cuts in both directions."),
 "PLTR": (lambda t: t < -10,       "The cult stock cooled: a year of unwinding, with believers buying every dip on the way down."),
 "SMCI": (lambda t: t < -15,       "Supermicro was down two-thirds at the worst — then mounted half a comeback. Momentum in reverse is a different sport."),
 "AVGO": (lambda t: t > 5,         "Broadcom took a full-size correction mid-year and still came out ahead — the quiet giant of the AI trade."),
 "CVNA": (lambda t: -25 < t < 10,  "Carvana's yo-yo year: down 40% at the low, most of the way back by the end. Volatility is the product."),
 "CRCL": (lambda t: t < -35,       "Post-IPO gravity: Circle issues the stablecoin — the stock is anything but."),
 "GEMI": (lambda t: t < -60,       "Gemini has done little but fall since its debut — the listing everyone wanted, the chart nobody did."),
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
      "long": LONG.get(tk),
    })

# Sunday bosses: static curated file (own historical windows); embedded as-is when present
# ---------------------------------------------------------------- multiple choice
# Casual mode is a 12-way pick, so the answer is always in the list. That makes the
# DISTRACTORS the difficulty dial. Two rules keep every clue column alive:
#   - at least 2 share the answer's sector, so the sector hint can't solve it outright
#   - the twelve span >=3 size buckets, or the SIZE clue returns "same" every time (dead column)
# Deterministic per puzzle id, so everyone sees the same twelve on the same day.
# The pool is a fixed cast of recognizable companies — a casual player can't reason about
# a name they've never heard of, and a recurring cast is something they learn over time.
MC_POOL = """AAPL MSFT ORCL IBM DELL CSCO PLTR SNDK
NVDA AMD INTC MU AVGO QCOM MRVL SMCI
GOOGL META NFLX DIS SPOT T VZ EA TTWO WBD ROKU
AMZN MCD SBUX HD ABNB BKNG LOW CVNA LULU NKE CHWY DKNG RBLX GME
WMT COST KO PEP PG TGT MNST
TSLA F GM RIVN LCID NIO
COIN HOOD MSTR CRCL GEMI MARA RIOT
JPM V MA BAC GS AXP SCHW SOFI
LLY JNJ PFE UNH MRK CVS ABBV MRNA HIMS
BA CAT GE UBER DE LMT UNP
XOM CVX COP""".split()
MC_N = 12

def mc_options(tk, pid):
    """Random fill first, then repair to meet the constraints — a greedy 'maximise spread'
    pass instead drags the same rare names (the one small cap) into every single set."""
    import random
    rnd = random.Random(9173 + pid)
    a = uni[tk]
    cand = [t for t in MC_POOL if t != tk and t in uni]
    rnd.shuffle(cand)
    same = [t for t in cand if uni[t]["sector"] == a["sector"]]
    picks = same[:2]                                     # sector hint must leave >=3 live names
    picks += [t for t in cand if t not in picks][: MC_N - 1 - len(picks)]

    def caps_of(ps): return {a["cap"]} | {uni[t]["cap"] for t in ps}
    swappable = [t for t in picks if t not in same[:2]]
    for need in [c for c in ("MEGA", "LARGE", "MID") if c != a["cap"]]:
        if len(caps_of(picks)) >= 3:
            break
        pool_c = [t for t in cand if t not in picks and uni[t]["cap"] == need]
        if not pool_c or not swappable:
            continue
        drop = swappable.pop()                           # trade a duplicate-bucket pick for a missing one
        picks[picks.index(drop)] = pool_c[0]

    opts = picks + [tk]
    rnd.shuffle(opts)                                    # answer sits in a different slot each day
    assert len(opts) == MC_N and tk in opts
    assert len({uni[t]["cap"] for t in opts}) >= 3, f"{tk}: size clue would be dead"
    assert sum(uni[t]["sector"] == a["sector"] for t in opts) >= 3, f"{tk}: sector clue too strong"
    return opts

BOSSES = json.load(open(f"{D}/bosses.json")) if os.path.exists(f"{D}/bosses.json") else []

# pixelated-logo clue: tiny pre-baked data URIs (see gen_pixlogos.py) — pure JSON here,
# so the nightly Action needs no image libraries. Missing ticker -> clue just doesn't show.
PX = json.load(open(f"{D}/pixlogos.json")) if os.path.exists(f"{D}/pixlogos.json") else {}
for p in out + BOSSES:
    if p["answer"] in PX:
        p["px"] = PX[p["answer"]]
    p["opts"] = mc_options(p["answer"], p["id"])

json.dump({"universe": uni, "bucketOrder": BUCKET_ORDER, "puzzles": out, "bosses": BOSSES},
          open(f"{D}/gamedata.json", "w"), separators=(",", ":"))
n_ans = sum(v["answer"] for v in uni.values())
print(f"universe {len(uni)} · answers {n_ans} · gamedata {os.path.getsize(f'{D}/gamedata.json')//1024} KB")

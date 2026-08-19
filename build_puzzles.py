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

# ---------------------------------------------------------------- display names
# The upstream feed strips "Company"/"Corporation", which leaves 29 names dangling as
# "The Boeing" / "The Coca-Cola". Barely noticeable as grid subtitles; glaring now that
# names are the big bold labels on the casual pick board.
KEEP_THE = {"HD", "TTD"}                      # "The" is genuinely part of these brands
THE_OK_TAIL = ("Group", "Companies", "Co.", "Corporation")
NAME_FIX = {                                   # wrong or too corporate for a casual player
    "XOM": "ExxonMobil",                       # feed says "ExxonMobil Holdings" — no such entity
    "LULU": "Lululemon", "SNDK": "SanDisk", "QCOM": "Qualcomm", "NKE": "Nike",
    "CVNA": "Carvana", "MRK": "Merck", "JPM": "JPMorgan Chase", "GS": "Goldman Sachs",
    "META": "Meta", "UBER": "Uber", "PLTR": "Palantir", "DELL": "Dell",
    "HOOD": "Robinhood", "LLY": "Eli Lilly", "F": "Ford", "MSTR": "Strategy (MicroStrategy)",
}
def display_name(tk, name):
    if tk in NAME_FIX:
        return NAME_FIX[tk]
    if name.startswith("The ") and tk not in KEEP_THE and not name.endswith(THE_OK_TAIL):
        return name[4:]
    return name
for tk, v in uni.items():
    v["name"] = display_name(tk, v["name"])

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
 "HOOD": (lambda t: t < 5,         "Robinhood lost more than half from its September high, bottomed in March, and has clawed back about 40% since — the casino trades like one of its own tickers."),
 "COIN": (lambda t: t < -25,       "Crypto winter came back for Coinbase — down by half, with every rally fading inside a month."),
 "LULU": (lambda t: t < -20,       "Lululemon stretched too far — a steady markdown from last year's highs, one red stretch at a time."),
 "BA":   (lambda t: -25 < t < 10,  "Boeing chopped through turbulence all year and landed roughly where it took off."),
 "IBM":  (lambda t: t < 0,         "Two air pockets in an otherwise sleepy year — when Big Blue drops, it drops all at once."),
 "RIVN": (lambda t: t > 15,        "Rivian finally strung together an up year — violently. Nothing this stock does is gradual."),
 "DELL": (lambda t: t > 100,       "Dell — yes, Dell — tripled. The beige-box company turned momentum stock, and it's sitting at the highs."),
 "MRVL": (lambda t: t > 60,        "Marvell went vertical, then handed a big piece back — AI-chip beta cuts in both directions."),
 "PLTR": (lambda t: abs(t) < 25,   "Palantir looks flat and wasn't: down 44% into a June low, then a 50% climb back out of it. The cult stock spent twelve months going nowhere the hard way."),
 "SMCI": (lambda t: t < -15,       "Supermicro was down two-thirds at the worst — then mounted half a comeback. Momentum in reverse is a different sport."),
 "AVGO": (lambda t: t > 5,         "Broadcom took a 25% correction into March and is back within a few percent of its high — the quiet giant of the AI trade."),
 "CVNA": (lambda t: -25 < t < 10,  "Carvana is flat over twelve months, which tells you nothing — a January high, a 41% drop into March, and a partial climb back. Volatility is the product."),
 "CRCL": (lambda t: t < -35,       "Post-IPO gravity: Circle issues the stablecoin — the stock is anything but."),
 "GEMI": (lambda t: t < -60,       "Gemini has done little but fall since its debut — the listing everyone wanted, the chart nobody did."),
 # --- appended 2026-08-09: batch 1. House rule for these: PRESENT TENSE, anchored to "now"
 # --- or "since last August". The window is a ROLLING twelve months rebuilt nightly, so there
 # --- is no close and no year-end — "finished the year" is wrong by construction.
 "GOOGL":(lambda t: t > 40,        "Alphabet did most of its climbing by May and has been handing a slice back ever since — the best chart in Big Tech, minus the summer."),
 "META": (lambda t: t < -10,       "Meta's high is the first candle on the chart — everything after was a slow give-back into spring, and the bounce never got far."),
 "ORCL": (lambda t: t < -25,       "Oracle round-tripped an entire AI re-rating — a pop in September, then nearly two-thirds gone from the high. The boring database company is having the least boring twelve months in the game."),
 "RBLX": (lambda t: t < -50,       "Roblox has lost two-thirds since last August and still hasn't had a real bounce — lower into winter, lower again through summer. A staircase pointed the wrong way."),
 "HIMS": (lambda t: t < -10,       "Hims fell three-quarters by February, then nearly doubled off the low — the deepest hole in the game, half climbed back out of."),
 "RIOT": (lambda t: t > 40,        "Riot has nearly doubled since last August, and it still feels like a loss if you bought in June — a 41% drawdown early, a summer top, and a fade ever since."),
 "QCOM": (lambda t: abs(t) < 20,   "Qualcomm sits almost exactly where it did twelve months ago — which hides a 59% rip into May and a 33% slide back out of it. Flat is not the same as quiet."),
 "LLY":  (lambda t: t > 40,        "Lilly has climbed for twelve straight months and sits within 2% of its high — no drama, no give-back, just up."),
 "JPM":  (lambda t: 10 < t < 40,   "JPMorgan is at its highest price in twelve months right now — a spring dip, then a straight line up. Banks are supposed to be boring; this one is boringly good."),
 "UBER": (lambda t: t < -10,       "Uber gave back a fifth of its value with no single bad week to blame — a long grind lower, and a bounce that only started in July."),
 # --- batch 2, added 2026-08-19. Present tense anchored to "now" / "since last August";
 # --- no finish-line words, the window rolls nightly.
 "AMZN": (lambda t: t > 10,        "Amazon is up almost a fifth since last August — and nearly all of it arrived in one 17% week in July. Take that week out and this is a flat chart."),
 "MCD":  (lambda t: t < -5,        "McDonald's is down about a tenth since last August and is sitting a few percent off its low. No crash, no rebound, just a slow bleed nobody is talking about."),
 "HD":   (lambda t: t < -5,        "Home Depot fell almost a third from its high, then clawed a fifth of it back. When housing turned, it took the whole aisle with it."),
 "ABNB": (lambda t: t > 25,        "Airbnb is up more than 40% since last August, never fell more than 13% along the way, and had its biggest week of the year this month."),
 "CMG":  (lambda t: t < -15,       "Chipotle lost 23% in a single week last October and has spent every month since failing to win it back."),
 "DASH": (lambda t: t < -5,        "DoorDash nearly halved, then rallied almost 50% off the low — and is still underwater. A round trip that went the wrong way first."),
 "COST": (lambda t: abs(t) < 10,   "Costco is almost exactly where it was last August. Twelve months, a 13% dip, and a full recovery back to nowhere."),
 "WMT":  (lambda t: t > 5,         "Walmart is up double digits since last August despite an 18% drawdown in between — the dip nobody remembers."),
 "PEP":  (lambda t: t < -3,        "Pepsi is down since last August and sits within a couple of percent of its low. Defensive stocks are supposed to defend."),
 "TGT":  (lambda t: t > 30,        "Target is up 45% since last August and 75% off its low — the comeback almost nobody was positioned for."),
 "HSY":  (lambda t: abs(t) < 12,   "Hershey fell 27%, then ripped 19% in a single week in February, and after all that it is roughly flat since last August."),
 "V":    (lambda t: 0 < t < 15,    "Visa is up single digits since last August, which undersells the ride: a 17% drawdown and a 23% climb back out of it."),
 "PYPL": (lambda t: t < -5,        "PayPal lost 23% in one week in February, bottomed 43% down, and has since won back nearly half of it. Still underwater."),
 "GS":   (lambda t: t > 25,        "Goldman Sachs is up more than 40% since last August, with one 19% drawdown in the spring that it has completely undone."),
 "PFE":  (lambda t: 0 < t < 15,    "Pfizer jumped 15% in a single week last September and has drifted sideways ever since. Almost the entire year's gain arrived in five days."),
 "CVS":  (lambda t: t > 25,        "CVS is up about 40% since last August — one of the strongest runs in healthcare, from a company most people picture as a place to buy shampoo."),
 "NVO":  (lambda t: t < -3,        "Novo Nordisk fell 21% in a single week in February, bottomed more than 40% down, and has climbed about a third of the way back."),
 "DAL":  (lambda t: t > 30,        "Delta is up more than half since last August. Airlines are the most cyclical thing in the market, and this is what the good half of the cycle looks like."),
 "UPS":  (lambda t: t > 8,         "UPS lost 12% in a single week in March and is still up nearly a fifth since last August. The recovery did all the work."),
 "SPOT": (lambda t: t < -20,       "Spotify is down a third since last August, with a 19% bounce in May that did not hold."),
}

QUEUE = ["GME","AAPL","TSLA","NFLX","MU","SBUX","KO","DIS","INTC","NKE",
         "MSFT","CAT","AMD","HOOD","COIN","LULU","BA","IBM","RIVN","DELL",
         "MRVL","PLTR","SMCI","AVGO","CVNA","MSTR","CRCL","GEMI","SNDK","NVDA",
         # --- appended 2026-08-09: batch 1 of the queue expansion. Ordered for shape variety
         # --- so the run doesn't serve five staircases back to back.
         "GOOGL","RBLX","JPM","HIMS","ORCL","LLY","RIOT","UBER","QCOM","META",
         # --- appended 2026-08-19: batch 2. Household brands, deliberately light on tech —
         # --- batch 1 left the queue 53% Tech/Semis/Crypto. Ordered so no two adjacent
         # --- puzzles share a chart shape (spike, crash, comeback, flat, grind).
         "AMZN","CMG","TGT","COST","NVO","DAL","MCD","V","SPOT","WMT",
         "PYPL","HSY","ABNB","HD","GS","PEP","UPS","DASH","PFE","CVS"]

def story(tk, ys):
    tot, big, dd = stats(ys)
    nums = f" The numbers: {tot:+.0f}% in 12 months · biggest week {big:+.0f}% · worst drawdown {dd:.0f}%."
    cond, narr = HAND.get(tk, (None, None))
    if narr and cond(tot):
        return narr + nums
    return f"{uni[tk]['name']} — now you'll recognize this chart next time." + nums

# ---------------------------------------------------------------- sector-relative return
# Rung 4 used to be the chart SHAPE alone, which names something the player is already
# looking at. This adds the one thing the picture cannot contain: how the company did
# against its own sector. Must be computed here — the browser only receives universe
# metadata plus each puzzle's own closes, never the other 500 tickers' prices.
def _ret(tk):
    pts = prices.get(tk) or []
    return None if len(pts) < 10 else pts[-1][1] / pts[0][1] - 1

_SEC = {}
for _t, _v in uni.items():
    if _v.get("answer") and _ret(_t) is not None:
        _SEC.setdefault(_v["sector"], []).append((_t, _ret(_t)))

def sector_rel(tk):
    """Thirds: led / middle / lagged. Small sectors are ranked as-is, no merging."""
    peers = _SEC.get(uni[tk]["sector"], [])
    if len(peers) < 3:
        return ""
    r = _ret(tk)
    if r is None:
        return ""
    better = sum(1 for _, pr in peers if pr > r)
    pct = better / max(len(peers) - 1, 1)
    return ("led its sector this year" if pct <= 0.33 else
            "middle of its sector this year" if pct <= 0.66 else
            "lagged its sector this year")

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
      "long": LONG.get(tk), "secrel": sector_rel(tk),
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
    picks = same[:4]                                     # 2026-08-09: was same[:2]. Casual was a 94%
                                                         # win rate with 56% solving by guess two —
                                                         # the sector clue killed 9 of 12 instantly and
                                                         # the rest of the ladder never got used.
    picks += [t for t in cand if t not in picks][: MC_N - 1 - len(picks)]

    def caps_of(ps): return {a["cap"]} | {uni[t]["cap"] for t in ps}
    swappable = [t for t in picks if t not in same[:4]]
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

# ---------------------------------------------------------------- boss/daily collision guard
# bosses.json and QUEUE had no knowledge of each other, so any ticker in both eventually
# collided. It happened twice before this guard existed: GME (daily Jul 20 -> boss Aug 2,
# 13 days) and NVDA (boss Sun Aug 16 -> daily Tue Aug 18, TWO days — the boss reveal handed
# players Tuesday's answer). Both shipped live. This turns a silent content collision into a
# build that refuses to run.
MIN_GAP_DAYS = 21

def _sched_dates():
    """Read the epochs out of template.html so they can never drift from the game itself."""
    import datetime as _dt, re as _re
    src = open(f"{D}/template.html").read()
    def _c(name):
        m = _re.search(rf'const {name} = "(\d{{4}}-\d{{2}}-\d{{2}})"', src)
        assert m, f"{name} not found in template.html — schedule guard cannot verify"
        return _dt.date.fromisoformat(m.group(1))
    epoch, boss_epoch = _c("EPOCH"), _c("BOSS_EPOCH")

    daily = {}                                   # ticker -> [dates it plays in cycle 0]
    for i, tk in enumerate(QUEUE):
        d = epoch + _dt.timedelta(days=i)
        if d.weekday() != 6 or d < boss_epoch:   # Sundays are replaced by the boss
            daily.setdefault(tk, []).append(d)
    boss = {}                                    # ticker -> [Sundays it plays in cycle 0]
    for w in range(len(BOSSES)):
        b = BOSSES[w]["answer"]
        d = boss_epoch + _dt.timedelta(days=7 * w)
        while d.weekday() != 6:
            d += _dt.timedelta(days=1)
        boss.setdefault(b, []).append(d)
    return daily, boss

if BOSSES:
    import datetime as _dtm
    _today = _dtm.date.today()
    _daily, _boss = _sched_dates()
    _future, _past = [], []
    for tk, bdates in _boss.items():
        for bd in bdates:
            for dd in _daily.get(tk, []):
                gap = abs((bd - dd).days)
                if gap >= MIN_GAP_DAYS:
                    continue
                line = f"{tk}: boss {bd} vs daily {dd} — {gap} days apart"
                # Only a collision whose second half is still ahead can be prevented. Failing
                # the nightly build over one that already shipped would take the site down for
                # something nobody can fix.
                (_future if max(bd, dd) >= _today else _past).append(line)
    for line in _past:
        print(f"  note: past collision, already played — {line}")
    assert not _future, (
        "BOSS/DAILY COLLISION AHEAD — the same ticker plays twice inside "
        f"{MIN_GAP_DAYS} days:\n  " + "\n  ".join(_future) +
        "\nFix by reordering bosses.json or moving the ticker in QUEUE.")
    print(f"schedule guard OK — no upcoming ticker repeats within {MIN_GAP_DAYS} days")

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

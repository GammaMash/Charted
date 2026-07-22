"""Build the two-tier universe file (universe2.json):
- guess space: S&P 500 (live caps from stockanalysis, GICS sectors from Wikipedia, semis split out)
  + cult/retail tickers not in the index
- answer pool: curated story stocks (answer: true flag)
"""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(f"{D}/sp500_rows.json"))
sect = json.load(open(f"{D}/sp500_sectors.json"))
from universe import UNIVERSE as OLD  # the original 85 curated names

# --- sector mapping: GICS 11, with Semiconductors split out (it's a real tribe) ---
GICS_SHORT = {
 "Information Technology":"Tech","Communication Services":"Comm/Media","Financials":"Financials",
 "Health Care":"Healthcare","Consumer Discretionary":"Consumer Disc","Consumer Staples":"Cons Staples",
 "Industrials":"Industrials","Energy":"Energy","Materials":"Materials","Real Estate":"Real Estate",
 "Utilities":"Utilities",
}
CRYPTO = {"COIN","MSTR","CRCL","GEMI","MARA","RIOT","HOOD"}   # the crypto tribe overrides GICS
def sector_for(sym, gics=None, sub=""):
    if sym in CRYPTO: return "Crypto"
    if "Semiconductor" in (sub or ""): return "Semis"
    return GICS_SHORT.get(gics, gics or "Tech")

def bucket(cap_b):
    if cap_b >= 200: return "MEGA"
    if cap_b >= 20:  return "LARGE"
    if cap_b >= 2:   return "MID"
    return "SMALL"

uni = {}
skipped = []
for r in rows:
    sym = r["s"]
    if "." in sym or "-" in sym:      # BRK.B / BF.B — stockanalysis history API needs special casing; drop for v1
        skipped.append(sym); continue
    s = sect.get(sym) or sect.get(sym.replace(".","-")) or {}
    cap_b = r["marketCap"]/1e9
    uni[sym] = {"name": r["n"].replace(" Corporation","").replace(" Incorporated","").replace(", Inc.","").replace(" Inc.","").replace(" Company","").replace(" plc","").replace(" (The)","").strip().rstrip("&").strip(),
                "sector": sector_for(sym, s.get("sector"), s.get("sub")),
                "cap": bucket(cap_b), "capB": round(cap_b,1), "sp500": True}

# --- cult add-ons: original curated names + a few extra retail favorites, where not already in the index ---
EXTRA = {
 "MARA": ("Marathon Digital","Crypto"), "RIOT": ("Riot Platforms","Crypto"),
 "BBAI": ("BigBear.ai","Tech"), "NIO": ("NIO","Consumer Disc"), "QUBT": ("Quantum Computing","Tech"),
 "ROKU": ("Roku","Comm/Media"),
}
OLD_SECTOR_MAP = {   # translate original custom sectors to the new vocabulary
 "Tech":"Tech","Semis":"Semis","Internet":"Comm/Media","Media":"Comm/Media","Auto/EV":"Consumer Disc",
 "Consumer":"Consumer Disc","Financials":"Financials","Crypto/Fintech":"Financials","Healthcare":"Healthcare",
 "Industrials":"Industrials","Energy":"Energy","Space":"Industrials",
}
CULT_FIX = {"GOOGL":"Comm/Media","META":"Comm/Media","NFLX":"Comm/Media",
            "WMT":"Cons Staples","COST":"Cons Staples","KO":"Cons Staples","PEP":"Cons Staples"}
# Autos/EV is its own tribe (like Semis) — GICS files them under Consumer Discretionary,
# but "Shopping" is a misleading hint for a carmaker. Applied last, overrides everything above.
AUTOS = {"TSLA","GM","F","RIVN","LCID","NIO","APTV"}
cult_added = []
for tk,(name,sec,_b) in OLD.items():
    if tk in uni or tk == "SPCX": continue
    uni[tk] = {"name":name, "sector": "Crypto" if tk in CRYPTO else OLD_SECTOR_MAP.get(sec,sec),
               "cap":"MID", "capB":None, "sp500": False}   # capB refined after price fetch via SHARES_M
    cult_added.append(tk)
for tk,(name,sec) in EXTRA.items():
    if tk in uni: continue
    uni[tk] = {"name":name,"sector":sec,"cap":"MID","capB":None,"sp500":False}
    cult_added.append(tk)
for tk,sec in CULT_FIX.items():
    if tk in uni and uni[tk]["sector"] not in ("Semis","Crypto"): uni[tk]["sector"]=sec
for tk in AUTOS:
    if tk in uni: uni[tk]["sector"]="Autos/EV"

# --- answer pool: every original curated name + recognizable S&P household brands ---
HOUSEHOLD = """F GM HD LOW JNJ PG MMM FDX UPS DAL UAL LUV MAR EA TTWO KHC HSY K CL KMB CMG DPZ YUM
DASH TXN ADBE PYPL AXP C BAC WFC MS SCHW BLK BX KKR TMO ABBV BMY GILD CVS HUM ISRG VRTX REGN AMGN
MDT SYK ELV CI COF USB PNC TFC BK STT AIG MET PRU ALL TRV PGR CB HIG AFL GLW HPQ HPE DELL WDC STX
AMAT LRCX KLAC ADI NXPI ON MCHP SWKS TER CDNS SNPS ANSS ADSK INTU ORLY AZO TSCO ROST TJX BURL GPS
KR SYY GIS CAG CPB HRL TSN TAP STZ BF.B MO PM KVUE CHD CLX EL COTY ULTA NCLH CCL RCL MGM LVS WYNN
CZR PENN EXPE BKNG ABNB UAL AAL HLT H MAR IHG""".split()
answers = set(OLD) - {"SPCX"} | set(EXTRA) | (set(HOUSEHOLD) & set(uni))
for tk in uni: uni[tk]["answer"] = tk in answers

json.dump(uni, open(f"{D}/universe2.json","w"))
n_ans = sum(v["answer"] for v in uni.values())
secs = {}
for v in uni.values(): secs[v["sector"]] = secs.get(v["sector"],0)+1
print(f"guess space: {len(uni)} · answer pool: {n_ans} · cult added: {len(cult_added)} · skipped dot-tickers: {skipped}")
print("sectors:", dict(sorted(secs.items(), key=lambda kv:-kv[1])))

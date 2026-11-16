"""Generate reveal art for the 30-day queue: bg/<TK>.jpg (flux scene) + bg/<TK>_logo.png (white mark).
Incremental — skips files that already exist."""
import json, os, time, urllib.request, urllib.parse
from PIL import Image, ImageFilter, ImageEnhance

D = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{D}/bg", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}
KEY = os.environ.get("POLLINATIONS_KEY", "")
_envp = "/mnt/user-data/uploads/Projects--chartillect/.env"
if not KEY and os.path.exists(_envp):
    for line in open(_envp):
        if line.strip().startswith("POLLINATIONS_KEY"):
            KEY = line.split("=", 1)[1].strip().strip('"').strip("'")

STYLE = ", cinematic wide shot, teal and deep blue accent lighting, dark moody atmosphere, shallow depth of field, photorealistic, no text, no words, no logos"
SCENES = {
 "MU":   "inside a semiconductor memory fabrication plant, glowing DRAM wafers, high tech machinery",
 "GME":  "neon retro video game arcade at night, glowing cabinets, mall storefront",
 "CRCL": "digital dollar coins made of light circulating through glowing financial network circuits",
 "CAT":  "giant yellow excavators and bulldozers at a vast open mining site at dusk",
 "MSTR": "underground vault of bitcoin mining servers, orange coin glow among dark racks",
 "AAPL": "sleek minimalist glass technology store interior, floating product tables, spotlights",
 "SNDK": "extreme macro of flash memory chips and gold circuit traces on dark silicon",
 "NKE":  "empty running track stadium at night, wet asphalt reflections, floodlights",
 "PLTR": "dark intelligence operations control room, wall of glowing data screens and maps",
 "INTC": "silicon wafer cleanroom, robotic arms holding rainbow-reflective wafers",
 "DIS":  "fairytale castle at night with fireworks, magical glow",
 "COIN": "futuristic crypto trading floor with holographic candlestick charts floating in air",
 "MSFT": "vast cloud datacenter corridor, endless server racks with soft blue lights",
 "AMD":  "high-end gaming computer interior, glowing processor and liquid cooling loops",
 "NFLX": "cozy dark home cinema, huge glowing screen light spilling over empty sofa",
 "HOOD": "smartphone on dark desk showing glowing green candlestick chart, feathers floating",
 "LULU": "serene yoga studio at dawn, mats and soft window light, athletic wear on racks",
 "DELL": "professional workstation lab with tower servers and triple monitor setups",
 "BA":   "massive aircraft assembly hangar, airliner fuselage under construction, work lights",
 "TSLA": "electric car factory line, robotic arms assembling a sleek car body, sparks",
 "GEMI": "twin glowing stars over a dark futuristic exchange floor, constellation lines",
 "SBUX": "cozy coffee shop interior on a rainy night, steam rising from cups, warm window glow",
 "MRVL": "glowing fiber optic cables and network switch chips in a dark server room",
 "IBM":  "retro-futuristic mainframe computer hall, tape drives and blinking panels",
 "RIVN": "rugged electric adventure truck on a misty forest trail at dawn, headlights on",
 "KO":   "classic glass soda bottles with condensation on ice, deep red neon glow",
 "SMCI": "dense liquid-cooled server racks with glowing coolant tubes in dark datacenter",
 "AVGO": "macro of broadband communication chips and glowing fiber strands on circuit board",
 "CVNA": "illuminated glass car vending machine tower at night, cars stacked in glowing bays",
 "NVDA": "extreme macro of a giant green glowing GPU die, intricate circuitry landscape",
 # --- batch 5 (2026-11-16)
 "ANET": "dark data-center aisle of high-speed network switches, fiber-optic glow",
 "OKLO": "compact advanced nuclear reactor hall, glowing core behind thick glass, desert night outside",
 "EBAY": "dim warehouse of packed parcels and auction goods on shelves, single warm spotlight",
 "IONQ": "quantum computer of gold wiring inside a dark laboratory, cold blue light",
 "ABBV": "sterile pharmaceutical laboratory, glass vials and amber bottles, cool overhead light",
 "WYNN": "luxurious empty casino floor at night, warm gold chandeliers, no readable signage",
 "LUV":  "commercial airliner on a sunrise runway, ground crew distant, desert light",
 "NOW":  "vast open-plan office at night, rows of monitors with abstract dashboards, no readable text",
 "TSN":  "industrial food plant at dawn, refrigerated trucks and cold mist, no readable signage",
 "MGM":  "grand casino resort exterior at night, fountains and gold light, no readable names",
 "ARM":  "macro of a smartphone processor die, blueprint-like circuit patterns, cool blue light",
 "CCL":  "huge cruise ship at sea at dusk, balcony lights reflecting on dark water",
 "MA":   "abstract global payment network, streams of light between cities at night, no digits, no logos",
 "SNOW": "vast cloud data hall seen through frosted glass, cool white light, snow falling outside",
 "LCID": "sleek luxury electric sedan in a dark studio, soft spotlight, no badges",
 "BKNG": "traveler desk at night, laptop glow, hotel key and a suitcase, city window, no readable text",
 "REGN": "biotech laboratory, silhouettes, rows of antibody vials, blue-green light",
 "UPST": "laptop on a dark kitchen table, soft screen glow, no readable text",
 "NET":  "network operations center, world map of light points, abstract shield glow, no text",
 "CEG":  "nuclear power plant cooling towers at twilight, steam, calm water reflection",
}

def gen_scene(tk):
    out = f"{D}/bg/{tk}.jpg"
    if os.path.exists(out): return "cached"
    prompt = SCENES[tk] + STYLE
    q = urllib.parse.quote(prompt)
    token = f"&token={KEY}" if KEY else ""
    # flux is the house model. The classic endpoint rate-limits anonymous callers, so
    # retry it, then fall back to the same endpoint without a model pin. The blur,
    # brightness and jpeg settings below stay the same either way.
    urls = [
        f"https://image.pollinations.ai/prompt/{q}?width=1024&height=640&model=flux&nologo=true{token}",
        f"https://image.pollinations.ai/prompt/{q}?width=1024&height=640&nologo=true{token}",
    ]
    last = None
    for attempt in range(5):
        url = urls[0 if attempt == 0 else 1]
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=75).read()
            if len(d) < 5000 or d[:2] not in (b"\xff\xd8", b"\x89P"):
                raise ValueError(f"not an image ({len(d)} bytes)")
            tmp = f"{D}/bg/_{tk}_raw.jpg"
            open(tmp, "wb").write(d)
            im = Image.open(tmp).convert("RGB")
            im = im.filter(ImageFilter.GaussianBlur(9))
            im = ImageEnhance.Brightness(im).enhance(1.15)
            im.save(out, quality=70)
            os.remove(tmp)
            return f"{os.path.getsize(out)//1024}KB"
        except Exception as e:
            last = e
            time.sleep(4 if attempt == 0 else 8)
    raise last

def _knockout(lg):
    """White mark on transparency. Corner pixel is the background; near-bg and
    already-transparent pixels drop out. Same threshold the queue has always used.
    A transparent corner has RGB (0,0,0), which would paint a navy mark gray —
    if the corner is already clear, every visible pixel is the mark."""
    px = lg.load(); w, h = lg.size
    cr, cg, cb, ca = px[3, 3]
    if ca < 40:
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a < 40: px[x, y] = (255, 255, 255, 0)
                else: px[x, y] = (255, 255, 255, 255 if a >= 80 else min(255, a * 3))
        return lg
    bg = (cr, cg, cb)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            dist = abs(r-bg[0]) + abs(g-bg[1]) + abs(b-bg[2])
            if dist < 90 or a < 40: px[x, y] = (255, 255, 255, 0)
            else: px[x, y] = (255, 255, 255, min(255, int(dist*1.6)))
    return lg

def _opaque_bbox(px, w, h):
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 40:
                xs.append(x); ys.append(y)
    if not xs: return None
    return min(xs), max(xs), min(ys), max(ys)

def _invert_plate(lg):
    """A solid block with the symbol cut out of it (MGM's lion in a gold square)
    keeps the block and loses the symbol. Trim sparse anti-aliased edges, then
    invert a rectangle that is still mostly filled."""
    px = lg.load(); w, h = lg.size
    box = _opaque_bbox(px, w, h)
    if not box: return lg
    x0, x1, y0, y1 = box
    def rowf(y, a, b):
        return sum(px[x, y][3] > 40 for x in range(a, b + 1)) / (b - a + 1)
    def colf(x, a, b):
        return sum(px[x, y][3] > 40 for y in range(a, b + 1)) / (b - a + 1)
    for _ in range(48):
        if y1 - y0 < 30: break
        if rowf(y0, x0, x1) < 0.4: y0 += 1; continue
        if rowf(y1, x0, x1) < 0.4: y1 -= 1; continue
        if colf(x0, y0, y1) < 0.4: x0 += 1; continue
        if colf(x1, y0, y1) < 0.4: x1 -= 1; continue
        break
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    if bw < 24 or bh < 24: return lg
    edges = min(rowf(y0, x0, x1), rowf(y1, x0, x1), colf(x0, y0, y1), colf(x1, y0, y1))
    op = sum(px[x, y][3] > 40 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))
    fill = op / (bw * bh)
    if edges > 0.50 and 0.50 < fill < 0.82:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px[x, y] = (255, 255, 255, 0) if px[x, y][3] > 40 else (255, 255, 255, 255)
    return lg

def _fill_solid_holes(lg):
    """A backdrop-colored wedge enclosed by the mark (the blue band of Southwest's
    heart, which matched the field behind it) should fill in. Letter counters are
    smaller and live in sparse wordmarks, so they stay open."""
    px = lg.load(); w, h = lg.size
    box = _opaque_bbox(px, w, h)
    if not box: return lg
    x0, x1, y0, y1 = box
    fill = sum(px[x, y][3] > 40 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)) / ((x1 - x0 + 1) * (y1 - y0 + 1))
    if fill < 0.45: return lg
    reach = [[False] * w for _ in range(h)]
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if px[x, y][3] <= 40 and not reach[y][x]:
                reach[y][x] = True; stack.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if px[x, y][3] <= 40 and not reach[y][x]:
                reach[y][x] = True; stack.append((x, y))
    while stack:
        cx, cy = stack.pop()
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h and not reach[ny][nx] and px[nx, ny][3] <= 40:
                reach[ny][nx] = True; stack.append((nx, ny))
    seen = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if reach[y][x] or px[x, y][3] > 40 or seen[y][x]: continue
            stack = [(x, y)]; seen[y][x] = True; comp = []
            while stack:
                cx, cy = stack.pop(); comp.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and not reach[ny][nx] and px[nx, ny][3] <= 40:
                        seen[ny][nx] = True; stack.append((nx, ny))
            if len(comp) >= 1500:
                for cx, cy in comp:
                    px[cx, cy] = (255, 255, 255, 255)
    return lg

def _clean_logo(lg):
    """Some feeds arrive with a hairline frame or a speckled backdrop that survives
    the knockout (CRWD, JPM, HD needed this by hand). Drop a frame that is a line
    rather than part of the mark, then drop isolated specks."""
    px = lg.load(); w, h = lg.size
    def row_frac(y):
        return sum(px[x, y][3] > 40 for x in range(w)) / w
    def col_frac(x):
        return sum(px[x, y][3] > 40 for y in range(h)) / h
    for i in range(3):
        if h > 8 and row_frac(i) > 0.45 and row_frac(i + 3) < 0.12:
            for x in range(w): px[x, i] = (255, 255, 255, 0)
        if h > 8 and row_frac(h - 1 - i) > 0.45 and row_frac(h - 4 - i) < 0.12:
            for x in range(w): px[x, h - 1 - i] = (255, 255, 255, 0)
        if w > 8 and col_frac(i) > 0.45 and col_frac(i + 3) < 0.12:
            for y in range(h): px[i, y] = (255, 255, 255, 0)
        if w > 8 and col_frac(w - 1 - i) > 0.45 and col_frac(w - 4 - i) < 0.12:
            for y in range(h): px[w - 1 - i, y] = (255, 255, 255, 0)
    seen = [[False] * w for _ in range(h)]
    specks = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or px[x, y][3] <= 40: continue
            stack = [(x, y)]; seen[y][x] = True; comp = []
            while stack:
                cx, cy = stack.pop(); comp.append((cx, cy))
                for nx, ny in ((cx-1, cy), (cx+1, cy), (cx, cy-1), (cx, cy+1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and px[nx, ny][3] > 40:
                        seen[ny][nx] = True; stack.append((nx, ny))
            if len(comp) < 24:
                specks.append(comp)
    for comp in specks:
        for x, y in comp:
            px[x, y] = (255, 255, 255, 0)
    # A lone satellite much smaller than the mark (a ® sitting off a snowflake)
    # is not part of the silhouette. A field of similar dots is the mark itself.
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or px[x, y][3] <= 40: continue
            stack = [(x, y)]; seen[y][x] = True; comp = []
            while stack:
                cx, cy = stack.pop(); comp.append((cx, cy))
                for nx, ny in ((cx-1, cy), (cx+1, cy), (cx, cy-1), (cx, cy+1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and px[nx, ny][3] > 40:
                        seen[ny][nx] = True; stack.append((nx, ny))
            comps.append(comp)
    if len(comps) >= 2:
        comps.sort(key=len)
        main = comps[-1]
        mx0, mx1 = min(p[0] for p in main), max(p[0] for p in main)
        my0, my1 = min(p[1] for p in main), max(p[1] for p in main)
        # A ® sitting off in the corner is detached from the mark. Letters under
        # a signature, a flagpole, and dots in a grid are not.
        for comp in comps[:-1]:
            if len(comp) >= 0.2 * len(main):
                continue
            x0, x1 = min(p[0] for p in comp), max(p[0] for p in comp)
            y0, y1 = min(p[1] for p in comp), max(p[1] for p in comp)
            dx = max(0, mx0 - x1, x0 - mx1)
            dy = max(0, my0 - y1, y0 - my1)
            if dx > 10 or dy > 10:
                for x, y in comp:
                    px[x, y] = (255, 255, 255, 0)
    return lg

def _harden(lg):
    """Partial alpha reads as a gray fringe or a speckled veil on the dark reveal."""
    px = lg.load(); w, h = lg.size
    for y in range(h):
        for x in range(w):
            px[x, y] = (255, 255, 255, 255 if px[x, y][3] >= 80 else 0)
    return lg

def gen_logo(tk):
    out = f"{D}/bg/{tk}_logo.png"
    if os.path.exists(out): return "cached"
    url = f"https://assets.parqet.com/logos/symbol/{tk}?format=png&size=512"
    d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
    tmp = f"{D}/bg/_{tk}_lraw.png"
    open(tmp, "wb").write(d)
    lg = Image.open(tmp).convert("RGBA")
    lg = _harden(_clean_logo(_fill_solid_holes(_invert_plate(_knockout(lg)))))
    lg = lg.crop(lg.getbbox() or (0, 0, lg.width, lg.height))
    lg.save(out)
    os.remove(tmp)
    return f"{os.path.getsize(out)//1024}KB"

if __name__ == "__main__":
    t0 = time.time()
    for tk in SCENES:
        if time.time()-t0 > 2400: print("TIME BUDGET — rerun to resume"); break
        try: s = gen_scene(tk)
        except Exception as e: s = f"SCENE FAIL {str(e)[:40]}"
        try: l = gen_logo(tk)
        except Exception as e: l = f"LOGO FAIL {str(e)[:40]}"
        print(f"{tk}: scene {s} · logo {l}", flush=True)
        time.sleep(1.2)

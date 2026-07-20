"""Generate reveal art for the 30-day queue: bg/<TK>.jpg (flux scene) + bg/<TK>_logo.png (white mark).
Incremental — skips files that already exist."""
import json, os, time, urllib.request, urllib.parse
from PIL import Image, ImageFilter, ImageEnhance

D = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{D}/bg", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}
KEY = ""
for line in open("/mnt/user-data/uploads/Projects--chartillect/.env"):
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
}

def gen_scene(tk):
    out = f"{D}/bg/{tk}.jpg"
    if os.path.exists(out): return "cached"
    prompt = SCENES[tk] + STYLE
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=640&model=flux&nologo=true&token={KEY}"
    d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
    tmp = f"{D}/bg/_{tk}_raw.jpg"
    open(tmp, "wb").write(d)
    im = Image.open(tmp).convert("RGB")
    im = im.filter(ImageFilter.GaussianBlur(9))
    im = ImageEnhance.Brightness(im).enhance(1.15)
    im.save(out, quality=70)
    os.remove(tmp)
    return f"{os.path.getsize(out)//1024}KB"

def gen_logo(tk):
    out = f"{D}/bg/{tk}_logo.png"
    if os.path.exists(out): return "cached"
    url = f"https://assets.parqet.com/logos/symbol/{tk}?format=png&size=512"
    d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
    tmp = f"{D}/bg/_{tk}_lraw.png"
    open(tmp, "wb").write(d)
    lg = Image.open(tmp).convert("RGBA")
    px = lg.load(); bg = px[3, 3][:3]
    for y in range(lg.height):
        for x in range(lg.width):
            r, g, b, a = px[x, y]
            dist = abs(r-bg[0]) + abs(g-bg[1]) + abs(b-bg[2])
            if dist < 90 or a < 40: px[x, y] = (255, 255, 255, 0)
            else: px[x, y] = (255, 255, 255, min(255, int(dist*1.6)))
    lg = lg.crop(lg.getbbox() or (0,0,lg.width,lg.height))
    lg.save(out)
    os.remove(tmp)
    return f"{os.path.getsize(out)//1024}KB"

if __name__ == "__main__":
    t0 = time.time()
    for tk in SCENES:
        if time.time()-t0 > 500: print("TIME BUDGET — rerun to resume"); break
        try: s = gen_scene(tk)
        except Exception as e: s = f"SCENE FAIL {str(e)[:40]}"
        try: l = gen_logo(tk)
        except Exception as e: l = f"LOGO FAIL {str(e)[:40]}"
        print(f"{tk}: scene {s} · logo {l}", flush=True)
        time.sleep(1.2)

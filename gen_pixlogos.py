"""One-time generator: bg/<TK>_logo.png -> pixlogos.json  {TK: tiny data-URI}.
Run manually (needs Pillow) whenever a queue/boss ticker gains a logo.
build_puzzles.py just READS pixlogos.json — the nightly Action needs no new deps.
The 12px-wide PNGs are unrecognizable at native size; the game upscales them with
image-rendering:pixelated as the casual late-game "can you make it out?" clue.
Baked into gamedata (data URIs) so NO network request can spoil the answer.
"""
import base64, io, json, os, sys
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(D, "bg")
PXW = 12   # pixels of mystery

out = {}
for fn in sorted(os.listdir(BG)):
    if not fn.endswith("_logo.png"):
        continue
    tk = fn[:-len("_logo.png")]
    im = Image.open(os.path.join(BG, fn)).convert("RGBA")
    im.thumbnail((PXW, PXW * 4), Image.LANCZOS)      # tiny; keeps aspect
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    out[tk] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

json.dump(out, open(os.path.join(D, "pixlogos.json"), "w"), separators=(",", ":"))
total = os.path.getsize(os.path.join(D, "pixlogos.json"))
print(f"pixlogos.json: {len(out)} logos, {total//1024} KB total")

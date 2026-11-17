"""Bake px/<key>.png: one ~64px logo per puzzle, named by puzzle id.

Run manually (needs Pillow) after logosrc/<TK>.png gains a file. The nightly
Action does not run this. It only copies the short path in px/caps.json onto
each puzzle, so the page never inlines the images and never asks for a URL
that contains a ticker.

Daily files are px/d<id>.png, bosses px/b<id>.png. caps.json maps those keys
to a cell cap and does not name a company.

Wordmarks spell the company name. They sharpen through 6, 8, 10, 13, 16 and
stop there. Dell still reads at 16, so it stops at 10. IBM still reads at 16,
so it stops at 12. A symbol (Nike's swoosh, Netflix's N, Google's G) may
reach 64.
"""
import io, json, os, sys
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
LONG = 64
MAX_BYTES = 4096

# Company-name wordmarks. The client never draws these sharper than 16 cells,
# except the two that are still readable at 16.
WORDMARKS = {
    "AMC", "ARM", "AXP", "C", "CAT", "CHWY", "CMG", "COST", "CRCL", "DELL",
    "DIS", "EBAY", "F", "FDX", "GE", "GEMI", "GM", "GME", "GS", "HD", "HIMS",
    "IBM", "INTC", "JNJ", "JPM", "KO", "LCID", "LLY", "LOW", "MARA", "MRVL",
    "MS", "MSTR", "MU", "NOW", "ORCL", "OXY", "PG", "RBLX", "ROKU", "SMCI",
    "SNDK", "TTWO", "UBER", "ULTA", "UPS", "V", "WYNN", "YUM",
}
# Still a readable word at 16 cells, so the last stage is lower.
LOWER = {"DELL": 10, "IBM": 12}


def cap_for(tk):
    if tk in LOWER:
        return LOWER[tk]
    if tk in WORDMARKS:
        return 16
    return 64


def puzzle_keys():
    # Same two lists build_puzzles.py ships. Read the files so this script does
    # not execute the puzzle builder. Keys are d<id> / b<id>, never a ticker.
    bosses = json.load(open(os.path.join(D, "bosses.json"), encoding="utf-8"))
    src = open(os.path.join(D, "build_puzzles.py"), encoding="utf-8").read()
    start = src.index("QUEUE = [")
    i = src.index("[", start)
    depth = 0
    end = None
    for j, ch in enumerate(src[i:], i):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end is None:
        raise SystemExit("could not read QUEUE")
    ns = {}
    exec(src[start:end], ns)
    queue = list(ns["QUEUE"])
    pairs = [(tk, f"d{i+1}") for i, tk in enumerate(queue)]
    pairs += [(b["answer"], f"b{b['id']}") for b in bosses]
    tickers = [tk for tk, _ in pairs]
    if len(tickers) != len(set(tickers)):
        raise SystemExit("duplicate ticker in QUEUE or bosses")
    keys = [key for _, key in pairs]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate logo key")
    return pairs


def fit(im):
    im = im.convert("RGBA")
    bb = im.getchannel("A").getbbox()
    if not bb:
        raise ValueError("fully transparent")
    im = im.crop(bb)
    w, h = im.size
    scale = LONG / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def quantize(im, colors):
    alpha = im.getchannel("A")
    reduced = im.convert("RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB")
    out = reduced.convert("RGBA")
    out.putalpha(alpha)
    return out


def png_bytes(im):
    def dump(img):
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        return buf.getvalue()
    data = dump(im)
    if len(data) <= MAX_BYTES:
        return data
    for colors in (48, 32, 16, 8):
        data = dump(quantize(im, colors))
        if len(data) <= MAX_BYTES:
            return data
    return data


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "logosrc")
    if not os.path.isdir(src_dir):
        raise SystemExit(f"missing {src_dir} — pass the directory of <TK>.png sources")
    out_dir = os.path.join(D, "px")
    os.makedirs(out_dir, exist_ok=True)
    caps = {}
    sizes = []
    lower = []
    for tk, key in puzzle_keys():
        path = os.path.join(src_dir, tk + ".png")
        if not os.path.exists(path):
            raise SystemExit(f"no logo source for {tk}")
        im = fit(Image.open(path))
        if max(im.size) < 48:
            raise SystemExit(f"{tk} long side {max(im.size)} < 48")
        raw = png_bytes(im)
        if len(raw) > MAX_BYTES:
            raise SystemExit(f"{tk} is {len(raw)} bytes, over {MAX_BYTES}")
        open(os.path.join(out_dir, key + ".png"), "wb").write(raw)
        cap = cap_for(tk)
        caps[key] = cap
        if cap < 16:
            lower.append(f"{tk}={cap}")
        sizes.append(len(raw))
    json.dump(caps, open(os.path.join(out_dir, "caps.json"), "w"), separators=(",", ":"), sort_keys=True)
    print(f"px/: {len(caps)} logos, {sum(sizes)} bytes of PNG, largest {max(sizes)}")
    print(f"wordmarks at 16: {sum(1 for v in caps.values() if v == 16)}; lower: {' '.join(lower)}")


if __name__ == "__main__":
    main()

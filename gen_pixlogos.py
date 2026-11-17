"""Bake pixlogos.json: one ~64px logo per puzzle, as a data URI.

Run manually (needs Pillow) after logosrc/<TK>.png gains a file. The nightly
Action only reads pixlogos.json, so it needs no image libraries.

Sources live in logosrc/ (not shipped). Each puzzle's mark is fit to a 64px
long side, aspect kept, transparent or left on its own neutral field, and
kept under 4 KB. The game downscales that source on a canvas
(PX_CELLS = 6, 10, 16, 28, 64) and pixelates it back up.

Wordmarks spell the company name (eBay, Coca-Cola, Oracle, …). Those are
capped at 28 cells in the client so the last stage never spells the name.
A symbol that merely uses a letter (Nike's swoosh, Netflix's N, Google's G)
is not a wordmark and may reach 64.
"""
import base64, io, json, os, sys
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
LONG = 64
MAX_BYTES = 4096

# Company-name wordmarks. The client never draws these sharper than 28 cells.
WORDMARKS = {
    "AMC", "ARM", "AXP", "C", "CAT", "CHWY", "CMG", "COST", "CRCL", "DELL",
    "DIS", "EBAY", "F", "FDX", "GE", "GEMI", "GM", "GME", "GS", "HD", "HIMS",
    "IBM", "INTC", "JNJ", "JPM", "KO", "LCID", "LLY", "LOW", "MARA", "MRVL",
    "MS", "MSTR", "MU", "NOW", "ORCL", "OXY", "PG", "RBLX", "ROKU", "SMCI",
    "SNDK", "TTWO", "UBER", "ULTA", "UPS", "V", "WYNN", "YUM",
}


def puzzle_tickers():
    # Same two lists build_puzzles.py ships. Imported by reading the files so
    # this script does not execute the puzzle builder.
    bosses = json.load(open(os.path.join(D, "bosses.json"), encoding="utf-8"))
    # QUEUE is a Python literal inside build_puzzles.py. Exec only that list.
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
    tickers = list(ns["QUEUE"]) + [b["answer"] for b in bosses]
    if len(tickers) != len(set(tickers)):
        raise SystemExit("duplicate ticker in QUEUE or bosses")
    return tickers


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
    out = {}
    sizes = []
    for tk in puzzle_tickers():
        path = os.path.join(src_dir, tk + ".png")
        if not os.path.exists(path):
            raise SystemExit(f"no logo source for {tk}")
        im = fit(Image.open(path))
        if max(im.size) < 48:
            raise SystemExit(f"{tk} long side {max(im.size)} < 48")
        raw = png_bytes(im)
        if len(raw) > MAX_BYTES:
            raise SystemExit(f"{tk} is {len(raw)} bytes, over {MAX_BYTES}")
        entry = {"d": "data:image/png;base64," + base64.b64encode(raw).decode()}
        if tk in WORDMARKS:
            entry["cap"] = 28
        out[tk] = entry
        sizes.append((len(raw), tk))
    dest = os.path.join(D, "pixlogos.json")
    json.dump(out, open(dest, "w"), separators=(",", ":"))
    total = os.path.getsize(dest)
    sizes.sort(reverse=True)
    caps = sorted(tk for tk, e in out.items() if e.get("cap") == 28)
    print(f"pixlogos.json: {len(out)} logos, {total} bytes, largest {sizes[0][0]} ({sizes[0][1]})")
    print(f"wordmarks capped at 28: {len(caps)}")
    print(" ".join(caps))


if __name__ == "__main__":
    main()

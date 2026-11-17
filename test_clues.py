"""Clue text must not contain the answer's ticker or company name.

The strings come from clueRungs() in template.html, via test_clues.js.
Founding clues have to be a year line, and only a year we stored from a source.
"""
import io, json, os, re, subprocess, sys
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
CLUE_RE = re.compile(r"^Founded in \d{4}(?:, public in \d{4})?$|^Went public in \d{4}$")


def _png_long_side(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    return max(im.size)


def test_px_logos():
    """Every per-puzzle logo file decodes, is at least 48px, and is not named by ticker."""
    template = open(os.path.join(D, "template.html"), encoding="utf-8").read()
    if "const PX_CELLS = [6, 10, 16, 28, 64];" not in template:
        raise SystemExit("PX_CELLS is not the 6/10/16/28/64 ladder")
    if "return [6, 8, 10, 13, 16];" not in template:
        raise SystemExit("wordmark ladder is not 6/8/10/13/16")
    px_dir = os.path.join(D, "px")
    caps = json.load(open(os.path.join(px_dir, "caps.json"), encoding="utf-8"))
    names = [n for n in os.listdir(px_dir) if n.endswith(".png")]
    if set(names) != {k + ".png" for k in caps}:
        raise SystemExit("px/*.png does not match px/caps.json")
    for name in names:
        if not re.fullmatch(r"[db]\d+\.png", name):
            raise SystemExit(f"logo filename is not an id: {name}")
        raw = open(os.path.join(px_dir, name), "rb").read()
        long = _png_long_side(raw)
        if long < 48:
            raise SystemExit(f"{name} long side {long} < 48")
    gd = json.load(open(os.path.join(D, "gamedata.json"), encoding="utf-8"))
    puzzles = gd["puzzles"] + gd["bosses"]
    index = open(os.path.join(D, "index.html"), encoding="utf-8").read()
    if "data:image/png;base64," in index:
        raise SystemExit("index.html still inlines logo images")
    with_px = 0
    for p in puzzles:
        uri = p.get("px") or ""
        if not uri:
            continue
        with_px += 1
        if not re.fullmatch(r"/px/[db]\d+\.png", uri):
            raise SystemExit(f"puzzle {p['answer']} logo path is not an id: {uri}")
        if p["answer"] in uri:
            raise SystemExit(f"logo path contains the ticker {p['answer']}")
        raw = open(os.path.join(D, uri.lstrip("/")), "rb").read()
        if _png_long_side(raw) < 48:
            raise SystemExit(f"puzzle {p['answer']} logo long side < 48")
        cap = p.get("pxCap")
        if cap not in (None, 16, 12, 10):
            raise SystemExit(f"puzzle {p['answer']} has an unexpected logo cap {cap}")
        key = uri.rsplit("/", 1)[-1][:-4]
        if caps.get(key, 64) != (cap or 64):
            raise SystemExit(f"puzzle {p['answer']} cap does not match caps.json")
    if with_px != len(names):
        raise SystemExit(f"gamedata has {with_px} logos, px/ has {len(names)}")
    by = {p["answer"]: p.get("pxCap") for p in puzzles}
    if by.get("EBAY") != 16 or by.get("DELL") != 10 or by.get("IBM") != 12:
        raise SystemExit(f"wordmark caps drifted: ebay={by.get('EBAY')} dell={by.get('DELL')} ibm={by.get('IBM')}")
    print(f"px logos {with_px}, each decodes, long side >= 48, loaded by id")


def main():
    founding = json.load(open(os.path.join(D, "founding.json"), encoding="utf-8"))
    gd = json.load(open(os.path.join(D, "gamedata.json"), encoding="utf-8"))
    puzzles = gd["puzzles"] + gd["bosses"]
    attached = 0
    for p in puzzles:
        origin = p.get("origin") or {}
        clue = origin.get("clue") or ""
        if not clue:
            continue
        attached += 1
        if not CLUE_RE.match(clue):
            raise SystemExit(f"odd origin clue for {p['answer']}: {clue}")
        stored = founding.get(p["answer"], {}).get("clue")
        if clue != stored:
            raise SystemExit(f"origin clue for {p['answer']} is not the sourced line")
        name = gd["universe"][p["answer"]]["name"]
        if name.lower() in clue.lower():
            raise SystemExit(f"origin clue names {p['answer']}")
    if attached != len(founding):
        raise SystemExit(f"attached {attached} origin clues, file has {len(founding)}")
    proc = subprocess.run(
        ["node", os.path.join(D, "test_clues.js")],
        text=True, capture_output=True, cwd=D,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise SystemExit("clue leak check failed")
    print(f"origin clues {attached} of {len(puzzles)}")
    test_px_logos()


if __name__ == "__main__":
    main()

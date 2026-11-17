"""Clue text must not contain the answer's ticker or company name.

The strings come from clueRungs() in template.html, via test_clues.js.
Founding clues have to be a year line, and only a year we stored from a source.
"""
import base64, io, json, os, re, subprocess, sys
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
CLUE_RE = re.compile(r"^Founded in \d{4}(?:, public in \d{4})?$|^Went public in \d{4}$")


def _png_long_side(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    return max(im.size)


def test_px_logos():
    """Every baked pixel-logo source decodes and is at least 48px on the long side."""
    template = open(os.path.join(D, "template.html"), encoding="utf-8").read()
    if "const PX_CELLS = [6, 10, 16, 28, 64];" not in template:
        raise SystemExit("PX_CELLS is not the 6/10/16/28/64 ladder")
    px = json.load(open(os.path.join(D, "pixlogos.json"), encoding="utf-8"))
    seen = set()
    for tk, entry in px.items():
        uri = entry["d"] if isinstance(entry, dict) else entry
        raw = base64.b64decode(uri.split(",", 1)[1])
        long = _png_long_side(raw)
        if long < 48:
            raise SystemExit(f"{tk} logo long side {long} < 48")
        seen.add(tk)
    gd = json.load(open(os.path.join(D, "gamedata.json"), encoding="utf-8"))
    puzzles = gd["puzzles"] + gd["bosses"]
    with_px = 0
    for p in puzzles:
        uri = p.get("px")
        if not uri:
            continue
        with_px += 1
        raw = base64.b64decode(uri.split(",", 1)[1])
        long = _png_long_side(raw)
        if long < 48:
            raise SystemExit(f"puzzle {p['answer']} logo long side {long} < 48")
        if p.get("pxCap") not in (None, 28):
            raise SystemExit(f"puzzle {p['answer']} has an unexpected logo cap")
    if with_px != len(seen):
        raise SystemExit(f"gamedata has {with_px} logos, pixlogos.json has {len(seen)}")
    print(f"px logos {with_px}, each decodes, long side >= 48")


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

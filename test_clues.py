"""Clue text must not contain the answer's ticker or company name.

The strings come from clueRungs() in template.html, via test_clues.js.
Founding clues have to be a year line, and only a year we stored from a source.
"""
import json, os, re, subprocess, sys

D = os.path.dirname(os.path.abspath(__file__))
CLUE_RE = re.compile(r"^Founded in \d{4}(?:, public in \d{4})?$|^Went public in \d{4}$")


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


if __name__ == "__main__":
    main()

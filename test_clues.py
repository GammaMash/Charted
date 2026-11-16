"""Clue text must not contain the answer's ticker or company name.

The strings come from clueRungs() in template.html, via test_clues.js.
"""
import os, subprocess, sys

D = os.path.dirname(os.path.abspath(__file__))


def main():
    proc = subprocess.run(
        ["node", os.path.join(D, "test_clues.js")],
        text=True, capture_output=True, cwd=D,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise SystemExit("clue leak check failed")


if __name__ == "__main__":
    main()

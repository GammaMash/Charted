"""Render og.png — the link-preview card — from YESTERDAY's chart.

Every share used to land as a bare blue URL because the head had no og:image. This gives
iMessage, X and Facebook something to draw, and it changes daily so the preview never goes stale.

Deliberately UNLABELLED: no ticker, no company name. The game runs on the player's LOCAL
calendar day, so at 05:30 UTC someone in Hawaii is still on yesterday's puzzle — naming the
answer here would spoil it for them. An unnamed chart is the better hook anyway; "what stock
is that?" is the whole game.
"""
import json, os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
W, H = 1200, 630
BG, PANEL, LINE, ACCENT, INK, MUTED = "#0b0d15", "#161927", "#3ddc84", "#35e0e8", "#ffffff", "#bcc0d6"
EPOCH, BOSS_EPOCH = "2026-07-20", "2026-08-02"          # must match template.html


def font(sz, bold=True):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
              else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def pick(data):
    """Yesterday's puzzle, mirroring todaysPuzzleIndex() / bossIndex() in template.html."""
    y = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)).date()
    days = max(0, (y - datetime.strptime(EPOCH, "%Y-%m-%d").date()).days)
    bosses = data.get("bosses") or []
    if y.weekday() == 6 and bosses:                      # Sunday Boss replaces the queue puzzle
        w = (y - datetime.strptime(BOSS_EPOCH, "%Y-%m-%d").date()).days // 7
        return bosses[w % len(bosses)], True
    return data["puzzles"][days % len(data["puzzles"])], False


def main():
    data = json.load(open(f"{D}/gamedata.json"))
    puz, boss = pick(data)
    ys = puz["closes"]

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    cx, cy, cw, ch = 70, 150, W - 140, 340
    d.rounded_rectangle([cx, cy, cx + cw, cy + ch], 18, fill=PANEL, outline="#454a68", width=2)

    lo, hi = min(ys), max(ys)
    rng = (hi - lo) or 1
    pad = 26
    pts = [(cx + pad + i * (cw - 2 * pad) / (len(ys) - 1),
            cy + pad + (hi - v) / rng * (ch - 2 * pad)) for i, v in enumerate(ys)]

    up = ys[-1] >= ys[0]                                 # a down year drawn in green reads as a lie
    stroke, wash = (LINE, "#172a24") if up else ("#ff5964", "#2a1a1e")
    d.polygon([(pts[0][0], cy + ch - pad)] + pts + [(pts[-1][0], cy + ch - pad)], fill=wash)
    d.line(pts, fill=stroke, width=6, joint="curve")
    d.ellipse([pts[-1][0] - 9, pts[-1][1] - 9, pts[-1][0] + 9, pts[-1][1] + 9], fill=stroke)

    d.text((70, 56), "C H A R T E D", font=font(52), fill=INK)
    d.text((70, 118), "yesterday's chart" + (" · SUNDAY BOSS" if boss else ""),
           font=font(24, False), fill=ACCENT if not boss else "#ffd166")
    d.text((70, 528), "Which company's stock is this?", font=font(40), fill=INK)
    d.text((70, 582), "chartedgame.com  ·  new chart every day", font=font(24, False), fill=MUTED)

    img.save(f"{D}/og.png", optimize=True)
    print(f"og.png written: puzzle #{puz['id']}{' (boss)' if boss else ''}, "
          f"{os.path.getsize(f'{D}/og.png') // 1024} KB")


if __name__ == "__main__":
    main()

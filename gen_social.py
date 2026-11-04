"""Write the morning social card: social/today.png and social/today.json.

The nightly job runs at 05:30 UTC. On the East Coast that is already the
morning the @chartillect account posts, at 7:00am. The chart is whichever
puzzle todaysPuzzleIndex() in template.html serves that calendar day —
schedule_eval.js runs the function, the same way the archive does. This file
does not reimplement BATCH4 or Sunday bosses.

The picture is the opening view of the game: dark theme, percent axis, no
dollar prices, no ticker, no company name. Yesterday's answer is included in
the JSON because that puzzle is the one the account replies about. Today's
answer is not written anywhere.
"""
import json, os, re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.PngImagePlugin import PngInfo

import build_archive as arch

D = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
SITE = arch.SITE
PLAY_URL = "https://chartedgame.com/?ref=x"
W, H = 1080, 1350

BG = (8, 9, 15)
GLOW = (18, 20, 29, 210)
PANEL = (22, 25, 39)
BORDER = (69, 74, 104)
GRID = (60, 63, 82)
INK = (255, 255, 255)
MUTED = (139, 142, 163)
FOOT = (188, 192, 214)
ACCENT = (53, 224, 232)
GREEN = (61, 220, 132)
RED = (255, 89, 100)
YELLOW = (255, 209, 102)

# Hooks, not summaries. Keyed on the date so the same morning always gets the
# same line. No question marks in the words — the only "?" is inside the link.
DAILY_CAPTIONS = [
    "One year. One stock. Name it.",
    "One line. Twelve months. Name the company.",
    "A full year on one line. Name the stock.",
    "New chart this morning. Name the company.",
    "No ticker on the picture. Name the stock.",
    "Today's chart is live. One stock. Name it.",
    "Twelve months. One company. Name it.",
]
BOSS_CAPTIONS = [
    "Sunday boss. One chart. Name the company.",
    "Boss day. A longer chart. Name the company.",
    "Sunday boss chart. The name stays off it.",
    "Boss chart this morning. Name the company.",
]
BANNED = re.compile(r"\b(but|while|still|despite|though|receipt)\b", re.I)


def font(size, kind="sans-bold"):
    paths = {
        "sans-bold": (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        "sans": (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ),
        "mono": (
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ),
    }
    for path in paths[kind]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise SystemExit(f"no {kind} font found; social card would render blank")


def et_today(now=None):
    """Calendar date the game is serving in ET, which is the 7:00am post."""
    if now is None:
        now = datetime.now(ET)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(ET).date()


def check_caption(text, boss):
    if PLAY_URL not in text:
        raise SystemExit("caption is missing the play link")
    prose = text.replace(PLAY_URL, "", 1)
    if "?" in prose:
        raise SystemExit("caption has a question mark: " + prose)
    if text.count("?") != 1:
        raise SystemExit("caption should contain only the ? inside the link")
    hit = BANNED.search(text)
    if hit:
        raise SystemExit(f"caption contains {hit.group(0)!r}")
    if len(text) > 280:
        raise SystemExit(f"caption is {len(text)} characters")
    if boss and "boss" not in text.lower():
        raise SystemExit("sunday caption never says it is a boss chart")
    if not boss and "boss" in text.lower():
        raise SystemExit("weekday caption calls the chart a boss")
    # A boss window is not a year. Saying so would mislabel the picture.
    if boss and ("twelve" in text.lower() or "one year" in text.lower()):
        raise SystemExit("sunday caption describes the chart as one year")
    return text


def suggested_caption(when, boss):
    variants = BOSS_CAPTIONS if boss else DAILY_CAPTIONS
    line = variants[when.toordinal() % len(variants)]
    return check_caption(line + "\n" + PLAY_URL, boss)


def leaks(text, ticker, name):
    """Today's answer, the way the archive checks a page."""
    if name and name in text:
        return name
    if ticker and re.search(rf"(?<![A-Za-z]){re.escape(ticker)}(?![A-Za-z])", text):
        return ticker
    return None


def raw_without_yesterday(raw):
    start = raw.find('"yesterday"')
    if start < 0:
        raise SystemExit("today.json has no yesterday block")
    brace = raw.find("{", start)
    depth = 0
    end = None
    for i, ch in enumerate(raw[brace:], brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit("yesterday block did not close")
    return raw[:start] + raw[end:]


def pct_label(v):
    """Percent axis the way the game draws it before any guesses."""
    n = int(round(v))
    if n > 0:
        return f"+{n}%"
    return f"{n}%"


def tracked_width(draw, text, face, tracking):
    if not text:
        return 0
    return sum(draw.textlength(ch, font=face) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(draw, xy, text, face, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=face, fill=fill)
        x += draw.textlength(ch, font=face) + tracking
    return x


def gradient_text(base, xy, text, face, tracking, c1, c2):
    """Paint text left-to-right from c1 to c2. Returns the x after the word."""
    draw = ImageDraw.Draw(base)
    width = tracked_width(draw, text, face, tracking)
    bbox = draw.textbbox((0, 0), "Hg", font=face)
    height = bbox[3] - bbox[1] + 8
    mask = Image.new("L", (max(1, int(width) + 4), height), 0)
    md = ImageDraw.Draw(mask)
    x = 0
    for ch in text:
        md.text((x, -bbox[1] + 2), ch, font=face, fill=255)
        x += draw.textlength(ch, font=face) + tracking
    grad = Image.new("RGBA", mask.size)
    gd = ImageDraw.Draw(grad)
    span = max(mask.size[0] - 1, 1)
    for i in range(mask.size[0]):
        t = i / span
        col = tuple(int(c1[j] * (1 - t) + c2[j] * t) for j in range(3)) + (255,)
        gd.line([(i, 0), (i, mask.size[1])], fill=col)
    grad.putalpha(mask)
    base.alpha_composite(grad, (int(xy[0]), int(xy[1] + bbox[1] - 2)))
    return xy[0] + width


def draw_logo(draw, x, y, size):
    """The header mark from template.html: cyan rounded rect, green sparkline."""
    width = max(2, size // 16)
    draw.rounded_rectangle([x, y, x + size, y + size], radius=size * 0.24, outline=ACCENT, width=width)
    pts = [(6, 23), (11, 17), (15, 20), (20, 10), (24, 14), (28, 8)]
    mapped = [(x + px / 34 * size, y + py / 34 * size) for px, py in pts]
    stroke = max(3, size // 12)
    draw.line(mapped, fill=GREEN, width=stroke, joint="curve")
    r = stroke / 2
    for px, py in mapped:
        draw.ellipse([px - r, py - r, px + r, py + r], fill=GREEN)


def time_labels(dates, n):
    """Month ticks on a one-year chart, years on a long boss window. Same rule as the game."""
    if not dates or len(dates) != n:
        return []
    labels = []
    if n > 60:
        seen = set()
        for i, ds in enumerate(dates):
            year = ds[:4]
            if year not in seen:
                seen.add(year)
                labels.append((i, year))
        return labels
    seen = set()
    for i, ds in enumerate(dates):
        dd = date.fromisoformat(ds[:10])
        key = (dd.year, dd.month)
        if key in seen:
            continue
        seen.add(key)
        if (dd.month - 1) % 2 == 0:  # JS getMonth() % 2 === 0
            labels.append((i, dd.strftime("%b")))
    return labels


def paint(closes, dates, when, day_number, boss):
    """Draw the card. Ticker and company name are not arguments, so they cannot be painted."""
    if len(closes) < 2:
        raise SystemExit(f"no chart for {when}")
    scale = 2
    def S(v):
        return int(round(v * scale))

    img = Image.new("RGBA", (S(W), S(H)), BG + (255,))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([S(40), S(-220), S(W - 40), S(460)], fill=GLOW)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=S(36)))
    img.alpha_composite(glow)

    draw = ImageDraw.Draw(img)
    word = font(S(58), "sans-bold")
    date_face = font(S(42), "sans-bold")
    sub_face = font(S(26), "sans")
    foot_face = font(S(28), "sans")
    axis_face = font(S(24), "mono")

    labels = []
    logo = S(84)
    lx, ly = S(64), S(56)
    draw_logo(draw, lx, ly, logo)

    tracking = S(8)
    chart_w = tracked_width(draw, "CHART", word, tracking)
    word_x = lx + logo + S(20)
    bbox = draw.textbbox((0, 0), "CHART", font=word)
    word_y = ly + (logo - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw_tracked(draw, (word_x, word_y), "CHART", word, INK, tracking)
    gradient_text(img, (word_x + chart_w + tracking, word_y), "ED", word, tracking, ACCENT, GREEN)
    # refresh draw after alpha composites
    draw = ImageDraw.Draw(img)

    date_text = arch.pretty(when)
    labels.append(date_text)
    date_y = ly + logo + S(32)
    draw.text((lx, date_y), date_text, font=date_face, fill=INK)
    if boss:
        sub = f"Sunday Boss  ·  Day {int(day_number)}"
        sub_fill = YELLOW
    else:
        sub = f"{arch.weekday(when)}  ·  Day {int(day_number)}"
        sub_fill = FOOT
    labels.append(sub)
    sub_y = date_y + S(52)
    draw.text((lx, sub_y), sub, font=sub_face, fill=sub_fill)

    card = [S(48), sub_y + S(26) + S(36), S(W - 48), S(1232)]
    border = YELLOW if boss else BORDER
    bw = S(4) if boss else S(3)
    draw.rounded_rectangle(card, radius=S(28), fill=PANEL, outline=border, width=bw)

    base = closes[0] or 1
    ser = [(c / base - 1) * 100 for c in closes]
    lo, hi = min(ser), max(ser)
    span = (hi - lo) or 1
    lo -= span * 0.08
    hi += span * 0.08
    grid_vals = [lo + (hi - lo) * g / 4 for g in range(5)]
    grid_text = [pct_label(v) for v in grid_vals]
    labels.extend(grid_text)
    longest = max(draw.textlength(t, font=axis_face) for t in grid_text)
    pad_l, pad_t, pad_b = S(28), S(36), S(58)
    pad_r = int(max(S(118), longest + S(36)))
    plot_l = card[0] + pad_l
    plot_r = card[2] - pad_r
    plot_t = card[1] + pad_t
    plot_b = card[3] - pad_b
    n = len(ser)

    def X(i):
        return plot_l + (plot_r - plot_l) * (i / (n - 1))

    def Y(v):
        return plot_t + (plot_b - plot_t) * (1 - (v - lo) / (hi - lo))

    for v, text in zip(grid_vals, grid_text):
        y = Y(v)
        draw.line([(plot_l, y), (plot_r, y)], fill=GRID, width=max(1, S(1)))
        tb = draw.textbbox((0, 0), text, font=axis_face)
        ty = y - (tb[3] - tb[1]) / 2 - tb[1]
        draw.text((plot_r + S(12), ty), text, font=axis_face, fill=MUTED)

    # A daily chart is one year, so say so. A boss window is not, and naming
    # the years in a sentence would only add a clue the axis already draws.
    if not boss:
        cap = "last 12 months"
        labels.append(cap)
        draw.text((plot_l, card[1] + S(12)), cap, font=font(S(18), "mono"), fill=MUTED)

    ticks = time_labels(dates, n)
    prev_x = -10_000
    for i, text in ticks:
        x = X(i)
        tw = draw.textlength(text, font=axis_face)
        if x - prev_x < tw + S(8):
            continue
        prev_x = x
        x = min(max(x, plot_l + tw / 2), plot_r - tw / 2)
        labels.append(text)
        tb = draw.textbbox((0, 0), text, font=axis_face)
        draw.text((x - tw / 2, plot_b + S(16) - tb[1]), text, font=axis_face, fill=MUTED)

    up = ser[-1] >= ser[0]
    stroke = GREEN if up else RED
    fill = (61, 220, 132, 56) if up else (255, 89, 100, 52)
    pts = [(X(i), Y(v)) for i, v in enumerate(ser)]
    area = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ad = ImageDraw.Draw(area)
    poly = [(pts[0][0], plot_b)] + pts + [(pts[-1][0], plot_b)]
    ad.polygon(poly, fill=fill)
    img.alpha_composite(area)

    draw = ImageDraw.Draw(img)
    line_w = S(6)
    glow_c = (61, 220, 132, 90) if up else (255, 89, 100, 90)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.line(pts, fill=glow_c, width=line_w + S(8), joint="curve")
    img.alpha_composite(layer)
    draw = ImageDraw.Draw(img)
    draw.line(pts, fill=stroke + (255,), width=line_w, joint="curve")
    ex, ey = pts[-1]
    r = S(8)
    draw.ellipse([ex - r, ey - r, ex + r, ey + r], fill=stroke + (255,))

    foot = "chartedgame.com"
    labels.append(foot)
    fw = draw.textlength(foot, font=foot_face)
    draw.text(((S(W) - fw) / 2, S(1262)), foot, font=foot_face, fill=FOOT)

    out = img.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    # Date and boss flag only. A hash of the line would identify the company
    # to anyone who can rebuild the puzzles, so it stays off the published file.
    meta = PngInfo()
    meta.add_text("charted-date", when.isoformat())
    meta.add_text("charted-day", str(int(day_number)))
    meta.add_text("charted-boss", "1" if boss else "0")
    out.charted_meta = meta
    out.charted_hash = arch.chart_hash(closes)
    out.charted_labels = labels
    return out


def payload_for(today_row, yest_row):
    when = date.fromisoformat(today_row["d"])
    boss = bool(today_row["boss"])
    return {
        "date": today_row["d"],
        "day_number": int(today_row["day"]),
        "is_sunday_boss": boss,
        "play_url": PLAY_URL,
        "suggested_caption": suggested_caption(when, boss),
        "yesterday": {
            "date": yest_row["d"],
            "ticker": yest_row["t"],
            "name": yest_row["name"],
            "archive_url": f"{SITE}/archive/{yest_row['d']}/",
        },
    }


def build_for(when):
    epoch = arch.epoch_from_template()
    yday = when - timedelta(days=1)
    if when < epoch:
        raise SystemExit(f"{when} is before launch {epoch}")
    if yday < epoch:
        raise SystemExit(f"no yesterday puzzle before launch {epoch}")
    yest_row, today_row = arch.query_schedule([yday, when])
    if today_row["d"] != when.isoformat() or yest_row["d"] != yday.isoformat():
        raise SystemExit("schedule returned the wrong dates")
    img = paint(
        today_row["closes"], today_row.get("dates") or [], when,
        int(today_row["day"]), bool(today_row["boss"]),
    )
    payload = payload_for(today_row, yest_row)
    assert_card(payload, img, today_row)
    return payload, img, today_row, yest_row


def assert_card(payload, img, today_row):
    if img.size != (W, H):
        raise SystemExit(f"social image is {img.size}, expected {(W, H)}")
    check_caption(payload["suggested_caption"], payload["is_sunday_boss"])
    blob = "\n".join(img.charted_labels)
    hit = leaks(blob, today_row["t"], today_row["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} was painted on the card")
    if any("$" in lab for lab in img.charted_labels):
        raise SystemExit("card shows a dollar price")
    if not any(lab.endswith("%") for lab in img.charted_labels):
        raise SystemExit("card is missing the percent axis")
    dumped = json.dumps({k: v for k, v in payload.items() if k != "yesterday"}, ensure_ascii=False)
    hit = leaks(dumped, today_row["t"], today_row["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} is outside the yesterday block")
    y = payload["yesterday"]
    if y["ticker"] == today_row["t"] or y["name"] == today_row["name"]:
        # Same company two days running would make the public yesterday block
        # equal today's answer. Refuse rather than publish it.
        raise SystemExit(f"{payload['date']} repeats yesterday's answer")
    if img.charted_hash != arch.chart_hash(today_row["closes"]):
        raise SystemExit("chart hash mismatch")


def assert_files(today_row):
    png_path = os.path.join(D, "social", "today.png")
    json_path = os.path.join(D, "social", "today.json")
    if not os.path.isfile(png_path):
        raise SystemExit("social/today.png was not written")
    img = Image.open(png_path)
    if img.size != (W, H):
        raise SystemExit(f"social/today.png is {img.size}, expected {(W, H)}")
    if img.info.get("charted-date") != today_row["d"]:
        raise SystemExit("today.png date does not match today's puzzle")
    if "charted-chart" in img.info or today_row["t"] in img.info or today_row["name"] in img.info:
        raise SystemExit("today.png text metadata names the puzzle")
    fresh = paint(
        today_row["closes"], today_row.get("dates") or [],
        date.fromisoformat(today_row["d"]), int(today_row["day"]), bool(today_row["boss"]),
    )
    if img.convert("RGB").tobytes() != fresh.tobytes():
        raise SystemExit("today.png pixels are not today's chart")
    raw = open(json_path, encoding="utf-8").read()
    doc = json.loads(raw)
    bare = raw_without_yesterday(raw)
    hit = leaks(bare, today_row["t"], today_row["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} appears outside yesterday in today.json")
    meta_text = "\n".join(str(v) for v in img.info.values())
    hit = leaks(meta_text, today_row["t"], today_row["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} is in the image text")
    check_caption(doc["suggested_caption"], doc["is_sunday_boss"])
    if doc["date"] != today_row["d"] or int(doc["day_number"]) != int(today_row["day"]):
        raise SystemExit("today.json does not match the schedule")
    if bool(doc["is_sunday_boss"]) != bool(today_row["boss"]):
        raise SystemExit("today.json boss flag does not match the schedule")
    if doc["play_url"] != PLAY_URL:
        raise SystemExit("play_url changed")
    y = doc["yesterday"]
    for key in ("date", "ticker", "name", "archive_url"):
        if key not in y:
            raise SystemExit(f"yesterday is missing {key}")
    return doc


def write_outputs(when=None):
    when = when or et_today()
    payload, img, today_row, _yest = build_for(when)
    folder = os.path.join(D, "social")
    os.makedirs(folder, exist_ok=True)
    img.save(os.path.join(folder, "today.png"), "PNG", optimize=True, pnginfo=img.charted_meta)
    with open(os.path.join(folder, "today.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    assert_files(today_row)
    kind = "sunday boss" if payload["is_sunday_boss"] else "daily"
    print(
        f"social: {payload['date']} day {payload['day_number']} {kind}"
        f" · {W}x{H} · caption {len(payload['suggested_caption'])} chars"
    )
    return payload


def main():
    write_outputs()


if __name__ == "__main__":
    main()

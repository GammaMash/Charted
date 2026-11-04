"""Write the morning social card, and later the answer for a finished day.

The 05:30 UTC job writes social/today.png and social/today.json for the chart
the game serves that Eastern morning. On the East Coast that is already the
day of the 7:00am post. West of there, the previous puzzle is still live, so
this file names no company.

social/yesterday.json is written by the 12:05 UTC job. That is just after
midnight in UTC−12, the same cutoff build_archive.py uses, so the date is
over everywhere the archive will publish it. The archive page for that date
is built in the same job, and the answer file points at it.

Which puzzle a date is comes from todaysPuzzleIndex() in template.html, via
schedule_eval.js — the same path the archive uses. This file does not
reimplement BATCH4 or Sunday bosses.
"""
import json, os, re, sys
from datetime import date, datetime, timedelta, timezone
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


def today_payload(today_row):
    """Morning file. No ticker and no company name, including yesterday's."""
    when = date.fromisoformat(today_row["d"])
    boss = bool(today_row["boss"])
    payload = {
        "date": today_row["d"],
        "day_number": int(today_row["day"]),
        "is_sunday_boss": boss,
        "play_url": PLAY_URL,
        "suggested_caption": suggested_caption(when, boss),
    }
    if "ticker" in payload or "yesterday" in payload:
        raise SystemExit("morning file grew an answer")
    return payload


def assert_answer_is_over(when, now):
    """The archive's own gate. A date that fails this is still in progress somewhere."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    arch.assert_past([when], now.astimezone(timezone.utc))


def revealed_date(now):
    """Newest puzzle date the archive would already publish. None before launch ends."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(timezone.utc)
    latest = arch.cutoff_date(now_utc) - timedelta(days=1)
    if latest < arch.epoch_from_template():
        return None
    assert_answer_is_over(latest, now_utc)
    return latest


def answer_payload(now):
    when = revealed_date(now)
    if when is None:
        raise SystemExit("no puzzle is over everywhere yet")
    assert_answer_is_over(when, now)
    row = arch.query_schedule([when])[0]
    got = date.fromisoformat(row["d"])
    if got != when:
        raise SystemExit("schedule date mismatch")
    assert_answer_is_over(got, now)
    return {
        "date": row["d"],
        "ticker": row["t"],
        "name": row["name"],
        "archive_url": f"{SITE}/archive/{row['d']}/",
    }


def build_for(when):
    epoch = arch.epoch_from_template()
    if when < epoch:
        raise SystemExit(f"{when} is before launch {epoch}")
    today_row = arch.query_schedule([when])[0]
    if today_row["d"] != when.isoformat():
        raise SystemExit("schedule returned the wrong date")
    img = paint(
        today_row["closes"], today_row.get("dates") or [], when,
        int(today_row["day"]), bool(today_row["boss"]),
    )
    payload = today_payload(today_row)
    assert_card(payload, img, today_row)
    return payload, img, today_row


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
    if "yesterday" in payload or "ticker" in payload:
        raise SystemExit("morning payload carries an answer")
    dumped = json.dumps(payload, ensure_ascii=False)
    hit = leaks(dumped, today_row["t"], today_row["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} is in the morning file")
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
    if "yesterday" in doc or "ticker" in doc or "name" in doc:
        raise SystemExit("today.json carries an answer")
    hit = leaks(raw, today_row["t"], today_row["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} is in today.json")
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
    return doc


def write_outputs(when=None):
    when = when or et_today()
    payload, img, today_row = build_for(when)
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


def write_yesterday(now=None, path=None):
    """Publish the answer for the newest date that is over everywhere."""
    now = now or datetime.now(timezone.utc)
    payload = answer_payload(now)
    assert_answer_is_over(date.fromisoformat(payload["date"]), now)
    folder = os.path.join(D, "social")
    os.makedirs(folder, exist_ok=True)
    dest = path or os.path.join(folder, "yesterday.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    got = json.loads(open(dest, encoding="utf-8").read())
    assert_answer_is_over(date.fromisoformat(got["date"]), now)
    if got["date"] != payload["date"] or got["ticker"] != payload["ticker"]:
        raise SystemExit("yesterday.json does not match the finished puzzle")
    print(f"yesterday: {got['date']} is over everywhere")
    return got


def main():
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "reveal"):
        raise SystemExit("usage: gen_social.py [reveal]")
    if len(sys.argv) == 2:
        write_yesterday()
    else:
        write_outputs()


if __name__ == "__main__":
    main()

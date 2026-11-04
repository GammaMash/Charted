"""Build the static SEO archive from the game's own schedule.

One page per past daily puzzle at /archive/YYYY-MM-DD/, plus /archive/,
sitemap.xml and robots.txt. Which puzzle fell on which date is decided by
todaysPuzzleIndex() / isBossDay() / bossIndex() in template.html — this script
asks Node to run those functions and does not reimplement them.

A date is included only once it is over in UTC−12, the last timezone. Until
then someone can still be playing it, including a Sunday boss.
"""
import base64, hashlib, html, json, os, re, shutil, subprocess
from datetime import date, datetime, timedelta, timezone
from xml.etree import ElementTree as ET

D = os.path.dirname(os.path.abspath(__file__))
SITE = "https://chartedgame.com"
UTC_MINUS_12 = timezone(timedelta(hours=-12))
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PAGE_CSS = """
:root{
  --bg:#08090f; --panel:#161927; --border:#343850; --txt:#dde0ea; --muted:#bcc0d6;
  --ink:#fff; --accent:#35e0e8; --accent-ink:#062a2e; --green:#3ddc84; --yellow:#ffd166;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box;}
html,body{margin:0;}
body{background:radial-gradient(1200px 500px at 50% -100px, #12141d, var(--bg)) fixed, var(--bg);
  color:var(--txt); font-family:var(--sans); font-size:15px; line-height:1.45;}
main{width:100%; max-width:560px; margin:0 auto; padding:16px 14px 48px;}
a{color:var(--accent);}
header{display:flex; align-items:center; gap:10px; margin-bottom:14px;}
header a.brand{display:flex; align-items:center; gap:10px; text-decoration:none; color:inherit;}
#logo{width:34px; height:34px; flex:none;}
.word{font-size:22px; letter-spacing:4px; font-weight:800; color:var(--ink); margin:0;}
.word span{background:linear-gradient(90deg,var(--accent),var(--green)); -webkit-background-clip:text; background-clip:text; color:transparent;}
h1{font-size:28px; line-height:1.15; letter-spacing:-.3px; color:var(--ink); margin:8px 0 6px;}
.lede{margin:0 0 12px; color:var(--muted); font-size:15px;}
.boss{display:inline-block; color:var(--yellow); font-weight:800; letter-spacing:.4px; font-size:13px; margin:0 0 10px;}
.chart{background:var(--panel); border:1px solid #454a68; border-radius:16px; padding:8px; margin:8px 0 4px;}
.chart svg{width:100%; height:auto; display:block;}
.play{display:block; text-align:center; background:var(--accent); color:var(--accent-ink);
  font-weight:800; font-size:17px; line-height:1.2; padding:16px 16px; border-radius:14px;
  text-decoration:none; margin:16px 0 10px;}
.reveal{display:block; width:100%; background:transparent; color:var(--txt);
  border:1.5px solid var(--border); border-radius:14px; padding:14px 16px; font:inherit;
  font-weight:700; font-size:15px; cursor:pointer;}
#answer{margin:12px 0 0; padding:14px; background:var(--panel); border:1.5px solid var(--green);
  border-radius:14px; color:var(--ink); font-size:17px; font-weight:750;}
#answer[hidden]{display:none !important;}
.fine{color:var(--muted); font-size:13px; margin:14px 0 0;}
.days{display:flex; flex-direction:column; gap:8px; margin:8px 0 20px;}
a.day{display:flex; justify-content:space-between; align-items:center; gap:12px;
  min-height:48px; padding:12px 14px; background:var(--panel); border:1px solid var(--border);
  border-radius:12px; text-decoration:none; color:inherit;}
a.day .when{font-weight:700; color:var(--ink);}
a.day .meta{display:flex; flex-direction:column; align-items:flex-end; gap:2px;
  color:var(--muted); font-family:var(--mono); font-size:12px; font-weight:650; text-align:right;}
a.day .tag{color:var(--yellow); font-family:var(--sans); font-size:12px; font-weight:800;}
h2{font-size:13px; letter-spacing:1.2px; text-transform:uppercase; color:var(--muted);
  margin:18px 2px 8px; font-weight:750;}
footer{margin-top:22px; font-size:12px; color:var(--muted); text-align:center;}
footer a{color:inherit;}
@media (max-width:480px){
  main{padding:12px 12px 40px;}
  h1{font-size:24px;}
  .word{font-size:18px; letter-spacing:2px;}
}
"""

LOGO = """<svg id="logo" viewBox="0 0 34 34" fill="none" aria-hidden="true">
<rect x="1" y="1" width="32" height="32" rx="8" stroke="#35e0e8" stroke-width="1.6"/>
<path d="M6 23 L11 17 L15 20 L20 10 L24 14 L28 8" stroke="#3ddc84" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def cutoff_date(now_utc):
    """Calendar date that is still 'today' in the last timezone (UTC−12).

    Archive strictly before this. A Sunday boss is included only after that
    Sunday has ended there too.
    """
    if now_utc.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now_utc.astimezone(UTC_MINUS_12).date()


def assert_past(dates, now_utc):
    """Fail the build if any archive date is today or later."""
    cutoff = cutoff_date(now_utc)
    utc_today = now_utc.astimezone(timezone.utc).date()
    for d in dates:
        if d >= cutoff or d >= utc_today:
            raise SystemExit(
                f"archive assertion failed: {d.isoformat()} is not past "
                f"(UTC-12 today is {cutoff.isoformat()}, UTC today is {utc_today.isoformat()})"
            )


def epoch_from_template():
    src = open(os.path.join(D, "template.html"), encoding="utf-8").read()
    m = re.search(r'const EPOCH = "(\d{4}-\d{2}-\d{2})"', src)
    if not m:
        raise SystemExit("EPOCH missing from template.html")
    return date.fromisoformat(m.group(1))


def daterange(start, stop):
    d = start
    while d < stop:
        yield d
        d += timedelta(days=1)


def query_schedule(dates):
    """Ask template.html's schedule functions which puzzle each date played."""
    payload = "\n".join(d.isoformat() for d in dates) + "\n"
    env = dict(os.environ)
    env["TZ"] = "UTC"
    proc = subprocess.run(
        ["node", os.path.join(D, "schedule_eval.js"), "query"],
        input=payload, text=True, capture_output=True, cwd=D, env=env,
    )
    if proc.returncode != 0:
        raise SystemExit("schedule_eval.js failed:\n" + proc.stderr)
    rows = json.loads(proc.stdout)
    if len(rows) != len(dates):
        raise SystemExit(f"schedule returned {len(rows)} rows for {len(dates)} dates")
    for want, row in zip(dates, rows):
        if row["d"] != want.isoformat():
            raise SystemExit(f"schedule row {row['d']} != {want.isoformat()}")
        if not row.get("t") or not row.get("closes"):
            raise SystemExit(f"schedule row {row['d']} missing puzzle")
    return rows


_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
_MONTHS_FULL = "January February March April May June July August September October November December".split()
_WEEKDAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()


def pretty(d):
    return f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"


def month_heading(d):
    return f"{_MONTHS_FULL[d.month - 1]} {d.year}"


def weekday(d):
    return _WEEKDAYS[d.weekday()]


def leaks_answer(page, blob, ticker, name):
    """The ticker and company name may live only inside the base64 blob."""
    bare = page.replace(blob, "")
    if name and name in bare:
        return True
    if re.search(rf"(?<![A-Za-z]){re.escape(ticker)}(?![A-Za-z])", bare):
        return True
    return False


def obfuscate(ticker, name):
    raw = json.dumps({"t": ticker, "n": name}, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


def chart_hash(closes):
    blob = ",".join(f"{c:.2f}" for c in closes).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def pct_label(v):
    if abs(v) >= 1000:
        return f"{v / 1000:+.1f}k%"
    return f"{v:+.0f}%"


def chart_svg(closes, dates):
    n = len(closes)
    base = closes[0] or 1
    ser = [(c / base - 1) * 100 for c in closes]
    lo, hi = min(ser), max(ser)
    span = (hi - lo) or 1
    lo -= span * 0.08
    hi += span * 0.08
    W, H = 640, 380
    padL, padR, padT, padB = 14, 64, 18, 32

    def X(i):
        return padL + (W - padL - padR) * (i / (n - 1) if n > 1 else 0)

    def Y(v):
        return padT + (H - padT - padB) * (1 - (v - lo) / (hi - lo))

    up = ser[-1] >= ser[0]
    stroke = "#3ddc84" if up else "#ff5964"
    fill = "rgba(61,220,132,.20)" if up else "rgba(255,89,100,.18)"
    pts = [(X(i), Y(v)) for i, v in enumerate(ser)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pts[0][0]:.1f},{H - padB:.1f} " + poly + f" {pts[-1][0]:.1f},{H - padB:.1f}"
    parts = [
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Unlabeled stock chart" data-points="{n}" data-chart="{chart_hash(closes)}">',
        "<title>Unlabeled stock chart</title>",
    ]
    for g in range(5):
        v = lo + (hi - lo) * g / 4
        y = Y(v)
        label = pct_label(v)
        parts.append(f'<line x1="{padL}" y1="{y:.1f}" x2="{W - padR}" y2="{y:.1f}" stroke="#3c3f52" stroke-width="1"/>')
        parts.append(
            f'<text x="{W - padR + 8}" y="{y + 4:.1f}" fill="#8b8ea3" font-size="12" '
            f'font-family="ui-monospace, Menlo, monospace">{label}</text>'
        )
    # Month labels on a one-year chart, years on a long boss window. Same rule as the game.
    if dates and len(dates) == n:
        labels = []
        if n > 60:
            seen = set()
            for i, ds in enumerate(dates):
                year = ds[:4]
                if year not in seen:
                    seen.add(year)
                    labels.append((i, year))
        else:
            seen = set()
            for i, ds in enumerate(dates):
                dd = date.fromisoformat(ds[:10])
                key = (dd.year, dd.month)
                if key in seen:
                    continue
                seen.add(key)
                if (dd.month - 1) % 2 == 0:  # JS getMonth() % 2 === 0
                    labels.append((i, dd.strftime("%b")))
        for i, text in labels:
            x = min(max(X(i), padL + 16), W - padR - 12)
            parts.append(
                f'<text x="{x:.1f}" y="{H - 10}" text-anchor="middle" fill="#8b8ea3" font-size="12" '
                f'font-family="ui-monospace, Menlo, monospace">{html.escape(text)}</text>'
            )
    parts.append(f'<polygon points="{area}" fill="{fill}"/>')
    parts.append(f'<polyline points="{poly}" fill="none" stroke="{stroke}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    ex, ey = pts[-1]
    parts.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" fill="{stroke}"/>')
    parts.append("</svg>")
    return "".join(parts)


def shell(title, description, canonical, body, extra_head=""):
    t = html.escape(title)
    desc = html.escape(description)
    can = html.escape(canonical)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{can}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="CHARTED">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{can}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{desc}">
<meta name="theme-color" content="#0c0e14">
<link rel="icon" href="/apple-touch-icon.png">
{extra_head}<style>{PAGE_CSS}</style>
</head>
<body>
<main>
<header><a class="brand" href="/">{LOGO}<p class="word">CHART<span>ED</span></p></a></header>
{body}
<footer><a href="/">Today's chart</a> · <a href="/archive/">All past puzzles</a></footer>
</main>
</body>
</html>
"""


def day_page(row):
    d = date.fromisoformat(row["d"])
    label = pretty(d)
    title = f"CHARTED {label}: guess the stock from its chart"
    desc = title
    if row["boss"]:
        desc = f"{title} Sunday Boss edition."
    canonical = f"{SITE}/archive/{row['d']}/"
    boss = '<p class="boss">Sunday Boss</p>' if row["boss"] else ""
    blob = obfuscate(row["t"], row["name"])
    svg = chart_svg(row["closes"], row.get("dates") or [])
    body = f"""
<h1>{html.escape(label)}</h1>
<p class="lede">{html.escape(weekday(d))} · guess the stock from its chart.</p>
{boss}
<div class="chart">{svg}</div>
<a class="play" href="/?d={row['d']}">Play this chart</a>
<button type="button" class="reveal" id="show" data-a="{blob}">Reveal the answer</button>
<p id="answer" hidden></p>
<p class="fine">Day {int(row['day'])}. Practice only — it won't change your streak. The name stays hidden until you play or tap reveal.</p>
<script>
document.getElementById("show").addEventListener("click", function(){{
  var a = JSON.parse(atob(this.getAttribute("data-a")));
  var el = document.getElementById("answer");
  el.hidden = false;
  el.textContent = a.n + " ($" + a.t + ")";
  this.hidden = true;
}});
</script>
"""
    page = shell(title, desc, canonical, body)
    if "www.chartedgame.com" in page:
        raise SystemExit("refusing to write a www canonical")
    if leaks_answer(page, blob, row["t"], row["name"]):
        raise SystemExit(f"spoiler leaked onto {row['d']}")
    return page


def index_page(rows):
    title = "CHARTED archive — past daily charts"
    desc = "Past CHARTED puzzles, newest first. Guess the stock from its chart."
    canonical = f"{SITE}/archive/"
    chunks = [
        "<h1>Past puzzles</h1>",
        '<p class="lede">Newest first. Every chart the game has already used. The answer stays hidden until you play.</p>',
        '<a class="play" href="/">Play today\'s chart</a>',
    ]
    month = None
    days_html = []
    for row in sorted(rows, key=lambda r: r["d"], reverse=True):
        d = date.fromisoformat(row["d"])
        head = month_heading(d)
        if head != month:
            if days_html:
                chunks.append('<div class="days">' + "".join(days_html) + "</div>")
                days_html = []
            chunks.append(f"<h2>{html.escape(head)}</h2>")
            month = head
        tag = '<span class="tag">Sunday Boss</span>' if row["boss"] else ""
        days_html.append(
            f'<a class="day" href="/archive/{row["d"]}/">'
            f'<span class="when">{html.escape(weekday(d)[:3])}, {html.escape(pretty(d))}</span>'
            f'<span class="meta">{tag}<span>Day {int(row["day"])}</span></span></a>'
        )
    if days_html:
        chunks.append('<div class="days">' + "".join(days_html) + "</div>")
    if not rows:
        chunks.append('<p class="lede">No past charts yet. Check back after today\'s puzzle is over.</p>')
    page = shell(title, desc, canonical, "\n".join(chunks))
    if "www.chartedgame.com" in page:
        raise SystemExit("refusing to write a www canonical")
    return page


def write_sitemap(dates):
    locs = [f"{SITE}/", f"{SITE}/archive/"]
    locs += [f"{SITE}/archive/{d.isoformat()}/" for d in dates]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc in locs:
        lines.append(f"  <url><loc>{html.escape(loc)}</loc></url>")
    lines.append("</urlset>\n")
    text = "\n".join(lines)
    if "www.chartedgame.com" in text:
        raise SystemExit("sitemap used www")
    path = os.path.join(D, "sitemap.xml")
    open(path, "w", encoding="utf-8").write(text)
    ET.parse(path)  # fail the build on invalid XML
    return locs


def write_robots():
    text = "User-agent: *\nAllow: /\n\nSitemap: https://chartedgame.com/sitemap.xml\n"
    open(os.path.join(D, "robots.txt"), "w", encoding="utf-8").write(text)


def existing_date_dirs():
    root = os.path.join(D, "archive")
    found = []
    if not os.path.isdir(root):
        return found
    for name in os.listdir(root):
        if os.path.isdir(os.path.join(root, name)) and DATE_RE.match(name):
            found.append(date.fromisoformat(name))
    return found


def main():
    now = datetime.now(timezone.utc)
    cutoff = cutoff_date(now)
    epoch = epoch_from_template()
    dates = list(daterange(epoch, cutoff))
    assert_past(dates, now)
    rows = query_schedule(dates) if dates else []
    assert_past([date.fromisoformat(r["d"]) for r in rows], now)

    arch = os.path.join(D, "archive")
    os.makedirs(arch, exist_ok=True)
    allowed = {d.isoformat() for d in dates}
    for name in list(os.listdir(arch)):
        path = os.path.join(arch, name)
        if os.path.isdir(path) and DATE_RE.match(name) and name not in allowed:
            shutil.rmtree(path)

    for row in rows:
        folder = os.path.join(arch, row["d"])
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, "index.html"), "w", encoding="utf-8").write(day_page(row))
    open(os.path.join(arch, "index.html"), "w", encoding="utf-8").write(index_page(rows))

    on_disk = existing_date_dirs()
    assert_past(on_disk, now)
    missing = [d for d in dates if d not in on_disk]
    extra = [d for d in on_disk if d not in dates]
    if missing or extra:
        raise SystemExit(f"archive dirs mismatch missing={missing[:3]} extra={extra[:3]}")

    locs = write_sitemap(dates)
    write_robots()
    last = dates[-1].isoformat() if dates else "none"
    print(f"archive: {len(dates)} past puzzles through {last} · cutoff {cutoff.isoformat()} (UTC-12) · sitemap {len(locs)} urls")


if __name__ == "__main__":
    main()

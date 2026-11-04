"""Archive safety checks.

The date→ticker mapping is compared to todaysPuzzleIndex() in template.html
(via schedule_eval.js). A separate 1000-day simulation must match the schedule
captured before the replay hook existed — that hook is not allowed to change
which puzzle plays on any date.
"""
import base64, json, os, re, subprocess, sys
from datetime import date, datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import build_archive as arch

D = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(D, "test", "schedule_golden.json")


def run_node(cmd, tz="UTC"):
    env = dict(os.environ)
    env["TZ"] = tz
    proc = subprocess.run(
        ["node", os.path.join(D, "schedule_eval.js"), *cmd],
        text=True, capture_output=True, cwd=D, env=env,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"node {' '.join(cmd)} failed")
    return proc.stdout


def test_cutoff_waits_out_sunday():
    # Monday 05:30 UTC, the night after a Sunday: UTC−12 is still Sunday evening.
    # That Sunday boss must not be archived yet.
    monday = datetime(2026, 11, 2, 5, 30, tzinfo=timezone.utc)
    assert arch.cutoff_date(monday) == date(2026, 11, 1)
    sunday = date(2026, 11, 1)
    assert not sunday < arch.cutoff_date(monday)
    # Tuesday 05:30 UTC: Sunday has been over everywhere since Monday 12:00 UTC.
    tuesday = datetime(2026, 11, 3, 5, 30, tzinfo=timezone.utc)
    assert arch.cutoff_date(tuesday) == date(2026, 11, 2)
    assert sunday < arch.cutoff_date(tuesday)
    # The assertion itself has to fail closed.
    try:
        arch.assert_past([date(2026, 11, 4)], datetime(2026, 11, 4, 15, tzinfo=timezone.utc))
    except SystemExit:
        pass
    else:
        raise SystemExit("assert_past allowed today")


def test_accept_gate():
    out = run_node(["accept"])
    assert "accept ok" in out


def test_schedule_unchanged():
    got = json.loads(run_node(["simulate", "1000"]))
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    if got != golden:
        for a, b in zip(got, golden):
            if a != b:
                raise SystemExit(f"schedule changed on {a['d']}: now {a} was {b}")
        raise SystemExit(f"schedule length {len(got)} != golden {len(golden)}")
    assert len(got) == 1000
    # Same calendar date, same puzzle, in the timezones where players actually are.
    for tz in ("America/New_York", "Pacific/Honolulu", "Etc/GMT+12"):
        other = json.loads(run_node(["simulate", "1000"], tz=tz))
        if other != golden:
            raise SystemExit(f"schedule differs in {tz}")
    out = run_node(["match", "1000"])
    assert "match ok" in out


def test_pages_match_schedule():
    now = datetime.now(timezone.utc)
    cutoff = arch.cutoff_date(now)
    epoch = arch.epoch_from_template()
    dates = list(arch.daterange(epoch, cutoff))
    arch.assert_past(dates, now)
    rows = arch.query_schedule(dates)
    by_date = {r["d"]: r for r in rows}

    root = os.path.join(D, "archive")
    pages = sorted(
        name for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name)) and arch.DATE_RE.match(name)
    )
    assert pages == [d.isoformat() for d in dates], "archive folders are not exactly the past dates"
    arch.assert_past([date.fromisoformat(n) for n in pages], now)

    index = open(os.path.join(root, "index.html"), encoding="utf-8").read()
    assert "www.chartedgame.com" not in index
    assert 'href="/"' in index
    # Newest first: the first day link is the latest date.
    first_link = re.search(r'href="/archive/(\d{4}-\d{2}-\d{2})/"', index)
    assert first_link and first_link.group(1) == dates[-1].isoformat()

    for name in pages:
        html = open(os.path.join(root, name, "index.html"), encoding="utf-8").read()
        row = by_date[name]
        m = re.search(r'data-a="([^"]+)"', html)
        assert m, name
        decoded = json.loads(base64.b64decode(m.group(1)))
        assert decoded["t"] == row["t"], (name, decoded["t"], row["t"])
        assert decoded["n"] == row["name"]
        if arch.leaks_answer(html, m.group(1), row["t"], row["name"]):
            raise SystemExit(f"spoiler visible on {name}")
        assert row["name"] not in index
        label = arch.pretty(date.fromisoformat(name))
        assert f"<title>CHARTED {label}: guess the stock from its chart</title>" in html
        canon = f"https://chartedgame.com/archive/{name}/"
        assert f'rel="canonical" href="{canon}"' in html
        assert f'property="og:url" content="{canon}"' in html
        assert f'property="og:title"' in html
        assert f'name="description" content="CHARTED {label}: guess the stock from its chart' in html
        assert f'href="/?d={name}"' in html
        assert 'class="play"' in html
        assert "www.chartedgame.com" not in html
        assert ("Sunday Boss" in html) == bool(row["boss"])
        assert f'data-points="{len(row["closes"])}"' in html
        assert f'data-chart="{arch.chart_hash(row["closes"])}"' in html
        # Answer element starts hidden.
        assert 'id="answer" hidden' in html


def test_sitemap_and_robots():
    now = datetime.now(timezone.utc)
    dates = list(arch.daterange(arch.epoch_from_template(), arch.cutoff_date(now)))
    path = os.path.join(D, "sitemap.xml")
    root = ET.parse(path).getroot()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in root.findall("s:url/s:loc", ns)]
    expect = ["https://chartedgame.com/", "https://chartedgame.com/archive/"]
    expect += [f"https://chartedgame.com/archive/{d.isoformat()}/" for d in dates]
    assert locs == expect, (len(locs), len(expect))
    assert all(loc.startswith("https://chartedgame.com/") for loc in locs)
    assert not any("www." in loc for loc in locs)
    robots = open(os.path.join(D, "robots.txt"), encoding="utf-8").read()
    assert "Sitemap: https://chartedgame.com/sitemap.xml" in robots
    assert "www." not in robots


def test_home_links_archive():
    for name in ("template.html", "index.html"):
        text = open(os.path.join(D, name), encoding="utf-8").read()
        assert 'href="/archive/"' in text, name
        assert "function gameNow()" in text, name
        assert 'const VERSION = "2026-11-04a"' in text, name
    assert open(os.path.join(D, "version.txt"), encoding="utf-8").read().strip() == "2026-11-04a"


def main():
    test_cutoff_waits_out_sunday()
    test_accept_gate()
    test_schedule_unchanged()
    test_pages_match_schedule()
    test_sitemap_and_robots()
    test_home_links_archive()
    n = len([
        name for name in os.listdir(os.path.join(D, "archive"))
        if arch.DATE_RE.match(name)
    ])
    print(f"archive tests passed · {n} pages")


if __name__ == "__main__":
    main()

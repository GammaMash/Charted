"""Social-card checks.

The picture for a date has to be the puzzle todaysPuzzleIndex() returns.
schedule_eval.js runs that function; this file does not reimplement it.
An answer is published only for a date the archive already considers over
everywhere (UTC−12). The morning file names no company.
"""
import json, os, subprocess, sys, tempfile
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from PIL import Image

import build_archive as arch
import gen_social as social

D = os.path.dirname(os.path.abspath(__file__))


def node_schedule(dates):
    """todaysPuzzleIndex() for each date, called directly — not via gen_social."""
    payload = "\n".join(d.isoformat() for d in dates) + "\n"
    env = dict(os.environ)
    env["TZ"] = "UTC"
    proc = subprocess.run(
        ["node", os.path.join(D, "schedule_eval.js"), "query"],
        input=payload, text=True, capture_output=True, cwd=D, env=env,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit("schedule_eval.js query failed")
    rows = json.loads(proc.stdout)
    if len(rows) != len(dates):
        raise SystemExit(f"schedule returned {len(rows)} rows for {len(dates)} dates")
    return rows


def test_et_morning_is_the_post_date():
    # 05:30 UTC in November is 12:30am Eastern, the morning of the 7:00am post.
    early = datetime(2026, 11, 5, 5, 30, tzinfo=timezone.utc)
    assert social.et_today(early) == social.et_today(
        datetime(2026, 11, 5, 7, 0, tzinfo=ZoneInfo("America/New_York"))
    )
    # Same UTC instant is still the previous evening on the west coast, and the
    # card is the East Coast morning anyway — that is the post time.
    assert social.et_today(early) == datetime(2026, 11, 5).date()
    summer = datetime(2026, 7, 21, 5, 30, tzinfo=timezone.utc)
    assert social.et_today(summer) == datetime(2026, 7, 21).date()
    late = datetime(2026, 11, 5, 23, 30, tzinfo=ZoneInfo("America/New_York"))
    assert social.et_today(late) == datetime(2026, 11, 5).date()


def test_captions():
    when = datetime(2026, 11, 5).date()
    seen = set()
    for i in range(len(social.DAILY_CAPTIONS)):
        text = social.suggested_caption(when + timedelta(days=i), False)
        seen.add(text)
        social.check_caption(text, False)
        assert "\n" + social.PLAY_URL in text
        assert len(text) <= 280
        assert "?" not in text.replace(social.PLAY_URL, "")
    assert len(seen) == len(social.DAILY_CAPTIONS)
    boss = social.suggested_caption(datetime(2026, 11, 8).date(), True)
    social.check_caption(boss, True)
    assert "boss" in boss.lower()
    assert "twelve" not in boss.lower()
    assert "?" not in boss.replace(social.PLAY_URL, "")


def test_files_and_no_spoiler():
    png = os.path.join(D, "social", "today.png")
    js = os.path.join(D, "social", "today.json")
    assert os.path.isfile(png), "social/today.png missing — run gen_social.py"
    img = Image.open(png)
    assert img.size == (1080, 1350)
    assert img.format == "PNG"
    raw = open(js, encoding="utf-8").read()
    doc = json.loads(raw)
    when = social.et_today()
    assert doc["date"] == when.isoformat()
    assert doc["play_url"] == "https://chartedgame.com/?ref=x"
    social.check_caption(doc["suggested_caption"], doc["is_sunday_boss"])
    assert len(doc["suggested_caption"]) <= 280
    assert "?" not in doc["suggested_caption"].replace(social.PLAY_URL, "")

    truth = node_schedule([when - timedelta(days=1), when])
    yest, today = truth
    assert "yesterday" not in doc and "ticker" not in doc and "name" not in doc
    assert int(doc["day_number"]) == int(today["day"])
    assert bool(doc["is_sunday_boss"]) == bool(today["boss"])
    assert img.info.get("charted-date") == today["d"]
    assert img.info.get("charted-boss") == ("1" if today["boss"] else "0")
    assert "charted-chart" not in img.info
    fresh = social.paint(today["closes"], today.get("dates") or [], when, int(today["day"]), bool(today["boss"]))
    assert fresh.charted_hash == arch.chart_hash(today["closes"])
    assert img.convert("RGB").tobytes() == fresh.tobytes()

    for row in (today, yest):
        hit = social.leaks(raw, row["t"], row["name"])
        if hit:
            raise SystemExit(f"today.json names {row['d']} ({hit})")
    meta = "\n".join(str(v) for v in img.info.values())
    hit = social.leaks(meta, today["t"], today["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} is stored in the image")


def test_next_60_dates_match_puzzle_index():
    start = social.et_today()
    dates = [start + timedelta(days=i) for i in range(60)]
    truth = node_schedule(dates)
    # The generator's own read of the schedule, which is what it paints.
    chosen = arch.query_schedule(dates)
    assert [r["d"] for r in chosen] == [d.isoformat() for d in dates]
    bosses = 0
    captions = set()
    for got, row in zip(chosen, truth):
        assert got["d"] == row["d"]
        assert got["i"] == row["i"]
        assert got["t"] == row["t"]
        assert bool(got["boss"]) == bool(row["boss"])
        assert int(got["day"]) == int(row["day"])
        assert got["closes"] == row["closes"]
        when = date.fromisoformat(row["d"])
        img = social.paint(row["closes"], row.get("dates") or [], when, int(row["day"]), bool(row["boss"]))
        assert img.size == (1080, 1350)
        assert img.charted_hash == arch.chart_hash(row["closes"])
        painted = "\n".join(img.charted_labels)
        hit = social.leaks(painted, row["t"], row["name"])
        if hit:
            raise SystemExit(f"{row['d']}: painted today's answer {hit!r}")
        assert not any("$" in lab for lab in img.charted_labels)
        assert any(lab.endswith("%") for lab in img.charted_labels)
        caption = social.suggested_caption(when, bool(row["boss"]))
        social.check_caption(caption, bool(row["boss"]))
        hit = social.leaks(caption, row["t"], row["name"])
        if hit:
            raise SystemExit(f"{row['d']}: caption contains {hit!r}")
        captions.add(caption)
        if row["boss"]:
            bosses += 1
            assert when.weekday() == 6
        else:
            assert "boss" not in caption.lower()
    assert bosses >= 8  # 60 days covers eight or nine Sundays
    assert len(captions) > 1


def _refuses(when, now):
    try:
        social.assert_answer_is_over(when, now)
    except SystemExit:
        return True
    return False


def test_answer_waits_until_the_archive_cutoff():
    """05:30 UTC and 10:30 UTC are both too early. 12:05 UTC is the first run
    where UTC−12 has rolled, which is when the archive will publish the page."""
    early = datetime(2026, 11, 5, 5, 30, tzinfo=timezone.utc)
    hawaii = datetime(2026, 11, 5, 10, 30, tzinfo=timezone.utc)
    ready = datetime(2026, 11, 5, 12, 5, tzinfo=timezone.utc)
    live = date(2026, 11, 4)
    assert _refuses(live, early)
    assert _refuses(live, hawaii)
    assert social.revealed_date(early) == date(2026, 11, 3)
    assert social.revealed_date(hawaii) == date(2026, 11, 3)
    assert social.revealed_date(ready) == live
    social.assert_answer_is_over(live, ready)
    # The archive build includes exactly the dates before the cutoff, so the
    # reveal link exists only once this same gate has opened.
    epoch = arch.epoch_from_template()
    assert live in list(arch.daterange(epoch, arch.cutoff_date(ready)))
    assert live not in list(arch.daterange(epoch, arch.cutoff_date(hawaii)))
    assert live not in list(arch.daterange(epoch, arch.cutoff_date(early)))
    # The morning card for Nov 5 still must not carry Nov 4's answer.
    morning = social.today_payload(node_schedule([date(2026, 11, 5)])[0])
    raw = json.dumps(morning)
    nov4 = node_schedule([live])[0]
    assert "yesterday" not in morning and "ticker" not in morning
    hit = social.leaks(raw, nov4["t"], nov4["name"])
    if hit:
        raise SystemExit(f"morning file names a live puzzle ({hit})")
    # Writing the answer at 12:05 publishes Nov 4, and only because it is over.
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "yesterday.json")
        got = social.write_yesterday(ready, path)
        assert got["date"] == live.isoformat()
        assert got["ticker"] == nov4["t"] and got["name"] == nov4["name"]
        assert got["archive_url"] == f"https://chartedgame.com/archive/{live.isoformat()}/"
        social.assert_answer_is_over(date.fromisoformat(got["date"]), ready)
        too_soon = social.write_yesterday(hawaii, os.path.join(tmp, "early.json"))
        assert too_soon["date"] == "2026-11-03"
        assert too_soon["date"] != live.isoformat()


def test_yesterday_file_is_over():
    path = os.path.join(D, "social", "yesterday.json")
    assert os.path.isfile(path), "social/yesterday.json missing — run gen_social.py reveal"
    doc = json.loads(open(path, encoding="utf-8").read())
    now = datetime.now(timezone.utc)
    when = date.fromisoformat(doc["date"])
    social.assert_answer_is_over(when, now)
    assert social.revealed_date(now) == when
    row = node_schedule([when])[0]
    assert doc["ticker"] == row["t"] and doc["name"] == row["name"]
    assert doc["archive_url"] == f"https://chartedgame.com/archive/{when.isoformat()}/"


def test_workflow_publishes_the_card():
    yml = open(os.path.join(D, ".github", "workflows", "rebuild.yml"), encoding="utf-8").read()
    reveal = open(os.path.join(D, ".github", "workflows", "reveal.yml"), encoding="utf-8").read()
    assert "python3 gen_social.py" in yml
    assert "python3 gen_social.py reveal" not in yml
    assert "python3 test_social.py" in yml
    assert "social/today.png" in yml
    assert "social/today.json" in yml
    assert "social/yesterday.json" not in yml
    assert "264815017+GammaMash@users.noreply.github.com" in yml
    assert yml.index("gen_social.py") < yml.index("git commit")
    assert yml.index("test_social.py") < yml.index("git commit")
    assert 'cron: "5 12 * * *"' in reveal
    assert "python3 gen_social.py reveal" in reveal
    assert "python3 build_archive.py" in reveal
    assert "social/yesterday.json" in reveal
    assert "264815017+GammaMash@users.noreply.github.com" in reveal
    assert reveal.index("gen_social.py reveal") < reveal.index("git commit")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    test_answer_waits_until_the_archive_cutoff()
    if only == "reveal":
        test_yesterday_file_is_over()
        print("reveal tests passed")
        return
    test_et_morning_is_the_post_date()
    test_captions()
    test_files_and_no_spoiler()
    test_yesterday_file_is_over()
    test_next_60_dates_match_puzzle_index()
    test_workflow_publishes_the_card()
    print("social tests passed")


if __name__ == "__main__":
    main()

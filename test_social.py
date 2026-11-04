"""Social-card checks.

The picture for a date has to be the puzzle todaysPuzzleIndex() returns.
schedule_eval.js runs that function; this file does not reimplement it.
Today's ticker and company name may show up only inside the yesterday block.
"""
import json, os, subprocess, sys
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
    assert doc["yesterday"]["date"] == yest["d"]
    assert doc["yesterday"]["ticker"] == yest["t"]
    assert doc["yesterday"]["name"] == yest["name"]
    assert doc["yesterday"]["archive_url"] == f"https://chartedgame.com/archive/{yest['d']}/"
    assert int(doc["day_number"]) == int(today["day"])
    assert bool(doc["is_sunday_boss"]) == bool(today["boss"])
    assert img.info.get("charted-date") == today["d"]
    assert img.info.get("charted-boss") == ("1" if today["boss"] else "0")
    assert "charted-chart" not in img.info
    fresh = social.paint(today["closes"], today.get("dates") or [], when, int(today["day"]), bool(today["boss"]))
    assert fresh.charted_hash == arch.chart_hash(today["closes"])
    assert img.convert("RGB").tobytes() == fresh.tobytes()

    bare = social.raw_without_yesterday(raw)
    hit = social.leaks(bare, today["t"], today["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} leaked outside yesterday")
    # The answer block really is the only place the name is allowed.
    assert today["t"] not in bare
    assert today["name"] not in bare
    meta = "\n".join(str(v) for v in img.info.values())
    hit = social.leaks(meta, today["t"], today["name"])
    if hit:
        raise SystemExit(f"today's answer {hit!r} is stored in the image")
    # Yesterday's answer is supposed to be present, and only there.
    assert yest["t"] in raw and yest["name"] in raw
    assert yest["t"] not in bare and yest["name"] not in bare


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


def test_real_yesterday_stays_in_its_block():
    """The published file's yesterday is the real previous puzzle, and the
    next 60 mornings keep today's answer out of every other field."""
    start = social.et_today()
    dates = [start - timedelta(days=1)] + [start + timedelta(days=i) for i in range(60)]
    rows = {r["d"]: r for r in node_schedule(dates)}
    for i in range(60):
        when = start + timedelta(days=i)
        yday = when - timedelta(days=1)
        today, yest = rows[when.isoformat()], rows[yday.isoformat()]
        payload = social.payload_for(today, yest)
        assert payload["is_sunday_boss"] is bool(today["boss"])
        assert payload["date"] == today["d"]
        assert int(payload["day_number"]) == int(today["day"])
        raw = json.dumps(payload, ensure_ascii=False, indent=2)
        bare = social.raw_without_yesterday(raw)
        hit = social.leaks(bare, today["t"], today["name"])
        if hit:
            raise SystemExit(f"{when}: {hit!r} escaped the yesterday block")
        assert payload["yesterday"]["ticker"] == yest["t"]
        assert payload["yesterday"]["name"] == yest["name"]
        assert payload["yesterday"]["archive_url"].endswith(f"/archive/{yday.isoformat()}/")
        if today["t"] == yest["t"] or today["name"] == yest["name"]:
            raise SystemExit(f"{when} would publish today's answer as yesterday")


def test_workflow_publishes_the_card():
    yml = open(os.path.join(D, ".github", "workflows", "rebuild.yml"), encoding="utf-8").read()
    assert "python3 gen_social.py" in yml
    assert "python3 test_social.py" in yml
    assert "social/today.png" in yml
    assert "social/today.json" in yml
    assert "264815017+GammaMash@users.noreply.github.com" in yml
    # The card is written before the commit step, on the same job as the
    # nightly data refresh, so it is in the commit that goes live.
    assert yml.index("gen_social.py") < yml.index("git commit")
    assert yml.index("test_social.py") < yml.index("git commit")


def main():
    test_et_morning_is_the_post_date()
    test_captions()
    test_files_and_no_spoiler()
    test_next_60_dates_match_puzzle_index()
    test_real_yesterday_stays_in_its_block()
    test_workflow_publishes_the_card()
    print("social tests passed")


if __name__ == "__main__":
    main()

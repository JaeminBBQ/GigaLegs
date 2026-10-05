from datetime import date

from gigalegs.engine import DayContext, recommend
from gigalegs.engine.shorthand import parse

MON = date(2026, 10, 5)


def test_parse_full_example():
    r = parse(
        """lift onramp A day 1
ready 2 7 8
psq 100x7x2 @4
rdl 160x10 @5, 160x10 @6 !pain lower back
plank 60s x2
situp x10x3 @7
note squats felt like warmups
ride sat 8.5mi 42min z2 home +120ft note marina
sore 3
bw 10/3 180.6""",
        MON,
    )
    assert r.errors == []
    lift = r.lifts[0]
    assert (lift.phase, lift.week, lift.day, lift.readiness) == ("onramp", "A", 1, (2, 7, 8))
    assert [s.exercise for s in lift.sets] == ["high_bar_paused_squat"] * 2 + [
        "romanian_deadlift"
    ] * 2 + ["plank"] * 2 + ["weighted_sit_up"] * 3
    assert lift.sets[2].pain is None and lift.sets[3].pain == "lower back"
    assert lift.sets[4].seconds == 60 and lift.sets[6].weight_lb is None
    ride = r.rides[0]
    assert (ride.date, ride.miles, ride.minutes, ride.zone, ride.commute, ride.elevation_ft) == (
        date(2026, 10, 3),
        8.5,
        42,
        2,
        "out",
        120,
    )
    assert ride.note == "marina"
    assert [(m.kind, m.value, m.date) for m in r.metrics] == [
        ("soreness", 3, MON),
        ("bodyweight", 180.6, date(2026, 10, 3)),
    ]


def test_parse_flags_and_amrap():
    r = parse("lift\ndl 225x5 @8 !form, 225x8 amrap @9.5", MON)
    a, b = r.lifts[0].sets
    assert a.form_ok is False and b.form_ok is True and b.amrap and b.rpe == 9.5


def test_parse_errors_are_per_line():
    r = parse("lift\npsq 100x7x2 @11\nride 5mi\nsore 12\npsq banana", MON)
    assert [line for line, _ in r.errors] == [2, 3, 4, 5]


def test_parse_set_before_lift_is_an_error():
    assert parse("psq 100x5", MON).errors


def test_parse_date_future_rolls_back_a_year():
    assert parse("sore 12/30 2", MON).metrics[0].date == date(2025, 12, 30)


def _ctx(**kw):
    base = {
        "next_day_heavy": True,
        "hours_since_heavy": None,
        "hours_since_lift": None,
        "program_sessions_7d": 0,
        "easy_day_in_last_7d": True,
        "active_streak": 0,
        "yesterday_hard": False,
        "open_pain": False,
    }
    base.update(kw)
    return DayContext(**base)


def test_recommend_first_day_lifts():
    assert recommend(_ctx()).kind == "lift"


def test_recommend_heavy_spacing():
    r = recommend(_ctx(hours_since_heavy=30, hours_since_lift=30))
    assert r.kind == "recovery" or r.kind == "ride"
    assert any("48" in x for x in r.reasons)


def test_recommend_light_day_ok_after_heavy():
    assert (
        recommend(_ctx(next_day_heavy=False, hours_since_heavy=24, hours_since_lift=24)).kind
        == "lift"
    )


def test_recommend_min_gap_between_lifts():
    assert recommend(_ctx(next_day_heavy=False, hours_since_lift=10)).kind != "lift"


def test_recommend_three_per_week_cap():
    assert recommend(_ctx(program_sessions_7d=3)).kind == "ride"


def test_recommend_soreness_blocks_heavy():
    assert recommend(_ctx(soreness=7)).kind == "recovery"


def test_recommend_pain_first():
    assert recommend(_ctx(open_pain=True)).kind == "recovery"


def test_recommend_smart_rest():
    assert recommend(_ctx(sleep=2, energy=3)).kind == "rest"


def test_recommend_easy_day_after_long_streak():
    assert recommend(_ctx(active_streak=6, easy_day_in_last_7d=False)).kind == "recovery"


def test_recommend_no_back_to_back_hard():
    assert (
        recommend(_ctx(hours_since_heavy=72, hours_since_lift=72, yesterday_hard=True)).kind
        == "recovery"
    )

"""One named test per rule in METHODOLOGY / ONRAMP / GAMIFICATION."""

import pytest

from gigalegs.engine import (
    Adjustment,
    Decision,
    Position,
    Prescription,
    SetResult,
    adjust_program_weight,
    apply_adjustment,
    can_advance_onramp,
    day_plan,
    decide,
    e1rm,
    level,
    load_program,
    next_phase_step,
    next_position,
    next_weight,
    onramp_prescription,
    plates_per_side,
    readiness_adjust,
    ride_xp,
    round_to_increment,
    set_xp,
    xp_to_next_level,
)

# --- rounding & plates


@pytest.mark.parametrize("x,want", [(202.5, 205), (168.75, 170), (167.4, 165)])
def test_round_halves_up(x, want):
    assert round_to_increment(x) == want


@pytest.mark.parametrize(
    "total,want",
    [
        (225, [45, 45]),
        (135, [45]),
        (185, [45, 25]),
        (205, [45, 35]),
        (170, [45, 10, 5, 2.5]),
        (45, []),
    ],
)
def test_plates(total, want):
    assert plates_per_side(total) == want


@pytest.mark.parametrize("total", [136, 40])
def test_plates_unloadable(total):
    with pytest.raises(ValueError):
        plates_per_side(total)


# --- on-ramp (ONRAMP.md example: 4x5 @ 225, max RPE 8)


@pytest.mark.parametrize(
    "week,want", [("A", (2, 5, 135.0, 6.0)), ("B", (3, 5, 170.0, 7.0)), ("C", (4, 5, 205.0, 7.0))]
)
def test_onramp_example(week, want):
    assert onramp_prescription(week, 4, 5, 225.0, 8.0) == Prescription(*want)


@pytest.mark.parametrize(
    "sets,week,want", [(10, "B", 7), (3, "A", 2), (5, "A", 3), (1, "A", 1), (5, "B", 4)]
)
def test_onramp_sets(sets, week, want):
    assert onramp_prescription(week, sets, 5, None, None).sets == want


def test_onramp_cap_without_target():
    assert onramp_prescription("C", 4, 5, 225.0, None).rpe_cap == 8.0


def test_onramp_weight_none():
    assert onramp_prescription("A", 4, 5, None, 8.0).weight_lb is None


def test_onramp_unknown_week():
    with pytest.raises(ValueError):
        onramp_prescription("D", 4, 5, 225.0, 8.0)


@pytest.mark.parametrize(
    "args,want",
    [
        ((5, False, True), True),
        ((6, False, True), False),
        ((2, True, True), False),
        ((2, False, False), False),
    ],
)
def test_onramp_gate(args, want):
    assert can_advance_onramp(*args) is want


def test_next_phase_step():
    assert next_phase_step("C", True) == "program"
    assert next_phase_step("A", True) == "B"
    assert next_phase_step("B", False) == "B"


# --- e1RM


def test_e1rm():
    assert e1rm(225, 5, 8) == pytest.approx(277.5)
    assert e1rm(225, 5, 6.5) is None
    assert e1rm(225, 0, 8) is None


# --- progression


def _s(reps=5, rpe=8.0, cap=8.0, form=True):
    return SetResult(5, reps, cap, rpe, form)


def test_progression_clean_advances():
    assert decide([_s(), _s(rpe=7.5)], 0) == (Decision.ADVANCE, 0)


def test_progression_over_cap_repeats():
    assert decide([_s(), _s(rpe=8.5)], 0) == (Decision.REPEAT, 0)


def test_progression_unrated_repeats():
    assert decide([_s(rpe=None)], 0) == (Decision.REPEAT, 0)


def test_progression_first_miss_repeats():
    assert decide([_s(reps=4)], 0) == (Decision.REPEAT, 1)


def test_progression_second_miss_resets():
    assert decide([_s(reps=4)], 1) == (Decision.RESET, 0)


def test_progression_form_counts_as_miss():
    assert decide([_s(form=False)], 0) == (Decision.REPEAT, 1)


def test_progression_empty():
    with pytest.raises(ValueError):
        decide([], 0)


def test_next_weight():
    assert next_weight(225, Decision.RESET, "squat", False, 235) == 205
    assert next_weight(315, Decision.ADVANCE, "deadlift", True) == 325
    assert next_weight(225, Decision.ADVANCE, "squat", True) == 230
    assert next_weight(225, Decision.ADVANCE, "squat", False, 235) == 235
    assert next_weight(225, Decision.REPEAT, "squat", False, 235) == 225
    with pytest.raises(ValueError):
        next_weight(225, Decision.ADVANCE, "squat", False)
    with pytest.raises(ValueError):
        next_weight(225, Decision.ADVANCE, "bench", True)


def test_adjust_program_weight_holds_back():
    assert adjust_program_weight(235, None, None) == 235
    assert adjust_program_weight(235, 225, Decision.ADVANCE) == 235
    assert adjust_program_weight(235, 225, Decision.REPEAT) == 225
    assert adjust_program_weight(235, 225, Decision.RESET) == 205


# --- readiness


def test_readiness_high_soreness():
    a = readiness_adjust(7, 7, 7, None)
    assert (a.load_factor, a.rpe_cap_delta, a.flag_repeat_week) == (0.9, -1.0, False)


def test_readiness_repeat_flag():
    assert readiness_adjust(7, 7, 7, 8).flag_repeat_week is True
    assert readiness_adjust(7, 7, 7, 6).flag_repeat_week is False


def test_readiness_smart_rest():
    assert readiness_adjust(2, 3, 3, None).suggest_smart_rest is True
    assert readiness_adjust(2, 3, 4, None).suggest_smart_rest is False


def test_readiness_range():
    with pytest.raises(ValueError):
        readiness_adjust(11, 7, 7, None)


def test_apply_adjustment():
    p = apply_adjustment(Prescription(4, 5, 225.0, 8.0), readiness_adjust(7, 7, 7, None))
    assert p == Prescription(4, 5, 205.0, 7.0)
    assert apply_adjustment(
        Prescription(3, 10, None, None), Adjustment(0.9, -1, False, False)
    ) == Prescription(3, 10, None, None)


# --- XP


def test_set_xp_rules():
    assert set_xp(8, True, 8, (7, 8)) == 10
    assert set_xp(7.5, True, 8, (7, 8)) == 10
    assert set_xp(6, True, 8, (7, 8)) == 5  # under target range: logged, not on target
    assert set_xp(8.5, True, 8, (7, 8)) == 0  # over cap: no XP (D5)
    assert set_xp(8, False, 8, (7, 8)) == 0
    assert set_xp(None, True, 8, (7, 8)) == 0
    assert set_xp(5, True, 6, None) == 10  # on-ramp: within 2 under the cap
    assert set_xp(3, True, 6, None) == 5


def test_ride_xp():
    assert ride_xp(17.3, True, 2) == 25
    assert ride_xp(8.2, False, 2) == 8
    assert ride_xp(10, False, 3) == 0


@pytest.mark.parametrize(
    "xp,lvl", [(0, 1), (99, 1), (100, 2), (399, 2), (400, 3), (1600, 5), (8100, 10), (36100, 20)]
)
def test_level(xp, lvl):
    assert level(xp) == lvl


def test_level_negative_and_next():
    with pytest.raises(ValueError):
        level(-1)
    assert xp_to_next_level(150) == 250


# --- program as data


def test_onramp_day_plan(fake_program_data):
    prog = load_program(fake_program_data)
    plan = day_plan(prog, Position("onramp", "B", 1))
    sq = plan.exercises[0]
    assert (sq.sets, sq.reps, sq.weight_lb, sq.rpe_cap) == (3, 5, 170.0, 7.0)
    assert plan.exercises[1].kind == "hold" and "70%" in plan.exercises[1].note
    assert plan.heavy


def test_program_day_plan(fake_program_data):
    prog = load_program(fake_program_data)
    row = day_plan(prog, Position("program", "1", 2)).exercises[0]
    assert (row.kind, row.rpe_cap, row.rpe_range) == ("rpe", 8.0, (8.0, 8.0))
    assert not day_plan(prog, Position("program", "1", 2)).heavy
    test = day_plan(prog, Position("program", "2", 3)).exercises[0]
    assert test.kind == "test" and "5RM" in test.note


def test_queue_order(fake_program_data):
    prog = load_program(fake_program_data)
    assert next_position(prog, Position("onramp", "A", 2)) == Position("onramp", "A", 3)
    assert next_position(prog, Position("onramp", "C", 3)) == Position("program", "1", 1)
    assert next_position(prog, Position("program", "2", 3)) == Position("deload", "1", 1)
    assert next_position(prog, Position("onramp", "A", 3), advance_week=False) == Position(
        "onramp", "A", 1
    )

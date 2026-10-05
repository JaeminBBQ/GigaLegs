"""Program-as-data → concrete prescriptions (docs/ARCHITECTURE.md → Program as data).

Pure: callers load the JSON and pass the dict in.
"""

from dataclasses import dataclass, field

from .onramp import ONRAMP_ORDER, hold_percent, onramp_prescription, onramp_rpe_cap

HEAVY_CATEGORIES = ("squat", "deadlift")


@dataclass(frozen=True)
class ProgramExercise:
    key: str
    name: str
    category: str
    sets: int
    reps: int
    load: dict
    rpe_min: float | None = None
    rpe_max: float | None = None


@dataclass(frozen=True)
class Program:
    id: str
    name: str
    days_per_week: int
    weeks: dict[int, dict[int, list[ProgramExercise]]]

    @property
    def n_weeks(self) -> int:
        return max(self.weeks)


@dataclass(frozen=True)
class PrescribedExercise:
    key: str
    name: str
    category: str
    kind: str  # weight | rpe | hold | test | off
    sets: int
    reps: int
    weight_lb: float | None = None
    rpe_cap: float | None = None
    rpe_range: tuple[float, float] | None = None
    note: str = ""


@dataclass(frozen=True)
class Position:
    phase: str  # onramp | program | deload | squat_block
    week: str  # "A"/"B"/"C" for onramp, "1".."N" for program
    day: int


@dataclass(frozen=True)
class DayPlan:
    position: Position
    exercises: list[PrescribedExercise] = field(default_factory=list)

    @property
    def heavy(self) -> bool:
        return any(e.category in HEAVY_CATEGORIES and e.kind != "off" for e in self.exercises)


def load_program(data: dict) -> Program:
    weeks: dict[int, dict[int, list[ProgramExercise]]] = {}
    for w in data["weeks"]:
        days: dict[int, list[ProgramExercise]] = {}
        for d in w["days"]:
            days[int(d["day"])] = [
                ProgramExercise(
                    key=e["key"],
                    name=e["name"],
                    category=e["category"],
                    sets=int(e["sets"]),
                    reps=int(e["reps"]),
                    load=e["load"],
                    rpe_min=e.get("rpe_min"),
                    rpe_max=e.get("rpe_max"),
                )
                for e in d["exercises"]
            ]
        weeks[int(w["week"])] = days
    return Program(
        id=data["id"],
        name=data["name"],
        days_per_week=int(data.get("days_per_week", 3)),
        weeks=weeks,
    )


def _range(e: ProgramExercise) -> tuple[float, float] | None:
    if e.load["type"] == "rpe":
        return (float(e.load["min"]), float(e.load["max"]))
    if e.rpe_min is not None and e.rpe_max is not None:
        return (float(e.rpe_min), float(e.rpe_max))
    return None


def _program_exercise(e: ProgramExercise) -> PrescribedExercise:
    t = e.load["type"]
    rng = _range(e)
    base = {"key": e.key, "name": e.name, "category": e.category, "sets": e.sets, "reps": e.reps}
    if t == "weight":
        return PrescribedExercise(
            **base,
            kind="weight",
            weight_lb=float(e.load["lb"]),
            rpe_cap=rng[1] if rng else None,
            rpe_range=rng,
        )
    if t == "rpe":
        return PrescribedExercise(**base, kind="rpe", rpe_cap=rng[1], rpe_range=rng)
    if t == "hold_alap":
        return PrescribedExercise(
            **base, kind="hold", note="Hold close to as long as possible (~90% of your best)"
        )
    if t == "test":
        return PrescribedExercise(
            **base,
            kind="test",
            rpe_cap=10.0,
            note=f"Test: work up to a {e.load['rm']}RM (one all-out set, good form only)",
        )
    return PrescribedExercise(**base, kind="off", note="Skip this week")


def _onramp_exercise(e: ProgramExercise, week: str) -> PrescribedExercise:
    t = e.load["type"]
    rng = _range(e)
    max_rpe = rng[1] if rng else None
    if t == "weight":
        p = onramp_prescription(week, e.sets, e.reps, float(e.load["lb"]), max_rpe)
        return PrescribedExercise(
            key=e.key,
            name=e.name,
            category=e.category,
            kind="weight",
            sets=p.sets,
            reps=p.reps,
            weight_lb=p.weight_lb,
            rpe_cap=p.rpe_cap,
        )
    if t == "rpe":
        p = onramp_prescription(week, e.sets, e.reps, None, max_rpe)
        return PrescribedExercise(
            key=e.key,
            name=e.name,
            category=e.category,
            kind="rpe",
            sets=p.sets,
            reps=p.reps,
            rpe_cap=p.rpe_cap,
            note=f"Pick a load that feels like RPE {p.rpe_cap:g}",
        )
    if t == "hold_alap":
        p = onramp_prescription(week, e.sets, e.reps, None, None)
        return PrescribedExercise(
            key=e.key,
            name=e.name,
            category=e.category,
            kind="hold",
            sets=p.sets,
            reps=p.reps,
            note=f"Hold ~{hold_percent(week)}% of your best time",
        )
    return PrescribedExercise(
        key=e.key,
        name=e.name,
        category=e.category,
        kind="off",
        sets=0,
        reps=e.reps,
        rpe_cap=onramp_rpe_cap(week, None),
        note="Skip",
    )


def day_plan(program: Program, pos: Position) -> DayPlan:
    if pos.phase == "onramp":
        if pos.week not in ONRAMP_ORDER:
            raise ValueError(f"unknown on-ramp week {pos.week!r}")
        src = program.weeks[1][pos.day]
        return DayPlan(pos, [_onramp_exercise(e, pos.week) for e in src])
    if pos.phase == "program":
        src = program.weeks[int(pos.week)][pos.day]
        return DayPlan(pos, [_program_exercise(e) for e in src])
    return DayPlan(pos, [])


def next_position(program: Program, pos: Position, advance_week: bool = True) -> Position:
    """The queue: day 1 → 2 → 3, then the next week (or the same week if not advancing)."""
    if pos.day < program.days_per_week:
        return Position(pos.phase, pos.week, pos.day + 1)
    if not advance_week:
        return Position(pos.phase, pos.week, 1)
    if pos.phase == "onramp":
        i = ONRAMP_ORDER.index(pos.week)
        if i + 1 < len(ONRAMP_ORDER):
            return Position("onramp", ONRAMP_ORDER[i + 1], 1)
        return Position("program", "1", 1)
    if pos.phase == "program":
        w = int(pos.week)
        if w < program.n_weeks:
            return Position("program", str(w + 1), 1)
        return Position("deload", "1", 1)
    return pos

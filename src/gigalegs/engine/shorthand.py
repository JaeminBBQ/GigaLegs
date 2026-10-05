"""Parser for the logging shorthand in docs/LOGGING.md. Pure: pass `today` in."""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

ALIASES = {
    "psq": "high_bar_paused_squat",
    "sq": "back_squat",
    "dl": "deadlift",
    "ddl": "deficit_deadlift",
    "rdl": "romanian_deadlift",
    "row": "barbell_row",
    "prow": "pendlay_row",
    "situp": "weighted_sit_up",
    "dsitup": "decline_weighted_sit_up",
    "bext": "back_extension",
    "pbext": "paused_back_extension",
    "plank": "plank",
    "splank": "side_plank",
    "hipdrop": "side_plank_hip_drop",
}
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass
class ParsedSet:
    exercise: str
    weight_lb: float | None
    reps: int | None
    seconds: int | None
    rpe: float | None
    form_ok: bool = True
    pain: str | None = None
    amrap: bool = False


@dataclass
class ParsedLift:
    date: date
    phase: str | None = None
    week: str | None = None
    day: int | None = None
    readiness: tuple[int, int, int] | None = None
    sets: list[ParsedSet] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ParsedRide:
    date: date
    miles: float
    minutes: int
    zone: int | None = None
    commute: str | None = None  # in | out | round
    elevation_ft: int | None = None
    note: str = ""


@dataclass
class ParsedMetric:
    date: date
    kind: str  # soreness | bodyweight
    value: float


@dataclass
class ParseResult:
    lifts: list[ParsedLift] = field(default_factory=list)
    rides: list[ParsedRide] = field(default_factory=list)
    metrics: list[ParsedMetric] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.lifts or self.rides or self.metrics)


def parse_date(token: str, today: date) -> date | None:
    t = token.lower()
    if t == "today":
        return today
    if t == "yesterday":
        return today - timedelta(days=1)
    if t[:3] in WEEKDAYS and t.isalpha() and len(t) <= 9:
        back = (today.weekday() - WEEKDAYS.index(t[:3])) % 7
        return today - timedelta(days=back)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", t)
    if m:
        year = int(m[3]) if m[3] else today.year
        if year < 100:
            year += 2000
        d = date(year, int(m[1]), int(m[2]))
        if not m[3] and d > today:
            d = d.replace(year=year - 1)
        return d
    return None


def exercise_key(name: str) -> str:
    n = name.lower()
    return ALIASES.get(n, re.sub(r"[^a-z0-9]+", "_", n).strip("_"))


_SPEC = re.compile(
    r"""^(?:
        (?P<w>\d+(?:\.\d+)?)?\s*x\s*(?P<r>\d+)(?:\s*x\s*(?P<s>\d+))?   # 100x7x2 | x10x3 | 100x7
      | (?P<sec>\d+)\s*s(?:\s*x\s*(?P<hs>\d+))?                        # 60s x2
    )\s*(?:@\s*(?P<rpe>\d+(?:\.\d+)?))?$""",
    re.VERBOSE,
)


def _parse_chunk(exercise: str, chunk: str) -> list[ParsedSet]:
    form_ok = True
    pain = None
    amrap = False
    m = re.search(r"!pain\b\s*(.*)$", chunk)
    if m:
        pain = m[1].strip() or "unspecified"
        chunk = chunk[: m.start()]
    if "!form" in chunk:
        form_ok = False
        chunk = chunk.replace("!form", "")
    if re.search(r"\bamrap\b", chunk):
        amrap = True
        chunk = re.sub(r"\bamrap\b", "", chunk)
    spec = _SPEC.match(chunk.strip())
    if not spec:
        raise ValueError(f"can't read {chunk.strip()!r} (expected e.g. 100x7x2 @6 or 60s x2)")
    rpe = float(spec["rpe"]) if spec["rpe"] else None
    if rpe is not None and not 1 <= rpe <= 10:
        raise ValueError(f"RPE {rpe:g} is outside 1-10")
    if spec["sec"]:
        n = int(spec["hs"] or 1)
        return [
            ParsedSet(exercise, None, None, int(spec["sec"]), rpe, form_ok, pain, amrap)
            for _ in range(n)
        ]
    n = int(spec["s"] or 1)
    w = float(spec["w"]) if spec["w"] else None
    return [
        ParsedSet(exercise, w, int(spec["r"]), None, rpe, form_ok, pain, amrap) for _ in range(n)
    ]


def _int_0_10(tok: str, what: str) -> int:
    v = int(tok)
    if not 0 <= v <= 10:
        raise ValueError(f"{what} must be 0-10")
    return v


def parse(text: str, today: date) -> ParseResult:
    res = ParseResult()
    current: ParsedLift | None = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        toks = line.split()
        head = toks[0].lower()
        try:
            if head == "lift":
                current = ParsedLift(date=today)
                rest = [t.lower() for t in toks[1:]]
                i = 0
                while i < len(rest):
                    t = rest[i]
                    d = parse_date(t, today)
                    if t == "onramp" and i + 1 < len(rest):
                        current.phase, current.week = "onramp", rest[i + 1].upper()
                        i += 1
                    elif t == "week" and i + 1 < len(rest):
                        current.phase, current.week = "program", str(int(rest[i + 1]))
                        i += 1
                    elif t == "day" and i + 1 < len(rest):
                        current.day = int(rest[i + 1])
                        i += 1
                    elif d is not None:
                        current.date = d
                    else:
                        raise ValueError(f"unknown word {t!r} on the lift line")
                    i += 1
                res.lifts.append(current)
            elif head == "ride":
                current = None
                res.rides.append(_parse_ride(toks[1:], today))
            elif head in ("sore", "bw"):
                current = None
                args = toks[1:]
                d = today
                if len(args) == 2:
                    d = parse_date(args[0], today) or _bad(f"bad date {args[0]!r}")
                    args = args[1:]
                if len(args) != 1:
                    raise ValueError(f"expected '{head} [date] <value>'")
                if head == "sore":
                    res.metrics.append(ParsedMetric(d, "soreness", _int_0_10(args[0], "soreness")))
                else:
                    res.metrics.append(ParsedMetric(d, "bodyweight", float(args[0])))
            elif current is None:
                raise ValueError("start with 'lift', 'ride', 'sore', or 'bw'")
            elif head == "ready":
                if len(toks) != 4:
                    raise ValueError("expected 'ready <soreness> <sleep> <energy>'")
                current.readiness = tuple(  # type: ignore[assignment]
                    _int_0_10(t, w) for t, w in zip(toks[1:], ("soreness", "sleep", "energy"))
                )
            elif head == "note":
                current.notes.append(line[4:].strip())
            else:
                ex = exercise_key(toks[0])
                body = line[len(toks[0]) :].strip()
                if not body:
                    raise ValueError(f"no sets after {toks[0]!r}")
                for chunk in body.split(","):
                    current.sets.extend(_parse_chunk(ex, chunk))
        except ValueError as e:
            res.errors.append((lineno, str(e)))
    return res


def _bad(msg: str):
    raise ValueError(msg)


def _parse_ride(args: list[str], today: date) -> ParsedRide:
    d = today
    miles = minutes = None
    zone = elevation = None
    commute = None
    note_parts: list[str] = []
    i = 0
    while i < len(args):
        t = args[i]
        tl = t.lower()
        if tl == "note":
            note_parts = args[i + 1 :]
            break
        if m := re.fullmatch(r"(\d+(?:\.\d+)?)mi", tl):
            miles = float(m[1])
        elif m := re.fullmatch(r"(\d+)min", tl):
            minutes = int(m[1])
        elif m := re.fullmatch(r"z([1-5])", tl):
            zone = int(m[1])
        elif m := re.fullmatch(r"\+(\d+)ft", tl):
            elevation = int(m[1])
        elif tl in ("in", "home", "out", "round"):
            commute = "out" if tl == "home" else tl
        elif (pd := parse_date(tl, today)) is not None:
            d = pd
        else:
            raise ValueError(f"unknown word {t!r} on the ride line")
        i += 1
    if miles is None or minutes is None:
        raise ValueError("a ride needs <miles>mi and <minutes>min")
    return ParsedRide(d, miles, minutes, zone, commute, elevation, " ".join(note_parts))

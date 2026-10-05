import math

DEFAULT_PLATES: tuple[float, ...] = (45, 35, 25, 10, 5, 2.5)


def round_to_increment(x: float, inc: float = 5.0) -> float:
    """Nearest increment, halves round up (unlike the built-in banker's rounding)."""
    return math.floor(x / inc + 0.5) * inc


def plates_per_side(
    total_lb: float, bar_lb: float = 45.0, plates: tuple[float, ...] = DEFAULT_PLATES
) -> list[float]:
    if total_lb < bar_lb:
        raise ValueError(f"{total_lb} lb is lighter than the {bar_lb} lb bar")
    remaining = (total_lb - bar_lb) / 2
    result: list[float] = []
    for plate in sorted(plates, reverse=True):
        while remaining >= plate - 1e-9:
            result.append(float(plate))
            remaining -= plate
    if remaining > 1e-9:
        raise ValueError(f"{total_lb} lb can't be loaded exactly with {plates}")
    return result

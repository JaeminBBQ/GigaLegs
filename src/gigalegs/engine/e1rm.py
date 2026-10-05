def e1rm(weight_lb: float, reps: int, rpe: float) -> float | None:
    """RPE-adjusted Epley. Only trusted for RPE 7-10 (METHODOLOGY §3)."""
    if rpe < 7 or rpe > 10 or reps < 1:
        return None
    return weight_lb * (1 + (reps + (10 - rpe)) / 30)

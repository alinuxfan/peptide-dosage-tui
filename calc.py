import re

# Pure dosing-math and adherence-heuristic functions shared by main.py (live UI)
# and db.py (file export), so the formula only lives in one place.


def concentration_mg_ml(vial_mg: float, water_ml: float) -> float:
    if water_ml <= 0:
        return 0.0
    return vial_mg / water_ml


def dose_to_mg(dose: float, unit: str) -> float:
    return dose / 1000.0 if unit == "mcg" else dose


def draw_volume_ml(dose_mg: float, conc_mg_ml: float) -> float:
    if conc_mg_ml <= 0:
        return 0.0
    return dose_mg / conc_mg_ml


def syringe_units(volume_ml: float) -> float:
    return volume_ml * 100.0


def doses_per_vial(vial_mg: float, dose_mg: float) -> float:
    if dose_mg <= 0:
        return 0.0
    return vial_mg / dose_mg


_RANGE_X_WEEKLY_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*x", re.IGNORECASE)
_X_WEEKLY_RE = re.compile(r"(\d+)\s*x", re.IGNORECASE)


def parse_weekly_frequency(freq: str) -> float | None:
    """Best-effort parse of a free-text frequency string into expected doses/week.

    Frequency strings are free text (e.g. "daily (at bedtime)", "3x weekly"),
    so this is a heuristic, not an exact parser -- unrecognized phrasing
    returns None rather than guessing.
    """
    if not freq:
        return None
    text = freq.strip().lower()

    range_match = _RANGE_X_WEEKLY_RE.search(text)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        return (low + high) / 2.0

    x_match = _X_WEEKLY_RE.search(text)
    if x_match:
        return float(x_match.group(1))

    if "daily" in text or "nightly" in text:
        return 7.0

    if "weekly" in text:
        return 1.0

    return None


def adherence_percent(logged_count: int, weekly_expected: float | None, days_elapsed: float) -> float | None:
    """Percentage of expected doses actually logged, capped at 100.

    Returns None when adherence can't be meaningfully measured: the
    frequency couldn't be parsed, or the protocol is too new (<1 day old).
    """
    if weekly_expected is None or weekly_expected <= 0:
        return None
    if days_elapsed < 1:
        return None

    expected_count = weekly_expected * (days_elapsed / 7.0)
    if expected_count <= 0:
        return None

    return min(100.0, (logged_count / expected_count) * 100.0)

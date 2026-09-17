import re
from datetime import datetime, timedelta

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

    # Per-day range: e.g. '1-3x/day', '1-3x daily', '1-3 times daily'
    day_range = re.search(r"(\d+)\s*-\s*(\d+)\s*(?:x|times)?\s*(?:/|\s*per\s*|\s*a\s*)?(?:day|daily)", text)
    if day_range:
        low, high = int(day_range.group(1)), int(day_range.group(2))
        return ((low + high) / 2.0) * 7.0

    # Per-day exact: e.g. '2x/day', '2x daily', '3 times a day'
    day_exact = re.search(r"(\d+)\s*(?:x|times)?\s*(?:/|\s*per\s*|\s*a\s*)?(?:day|daily)", text)
    if day_exact and not re.search(r"(?:every\s+other\s+day|\beod\b)", text):
        return float(day_exact.group(1)) * 7.0

    if "twice daily" in text or "2x daily" in text or "split am/pm" in text or re.search(r"\bbid\b", text):
        return 14.0
    if "three times daily" in text or "thrice daily" in text or re.search(r"\btid\b", text):
        return 21.0

    if "every other day" in text or re.search(r"\beod\b", text) or re.search(r"\bqod\b", text):
        return 3.5

    if "every other week" in text or "every 2 weeks" in text or re.search(r"\bq2w\b", text):
        return 0.5

    # Check range first so '2-3x weekly' is not matched as '3x weekly'
    range_match = _RANGE_X_WEEKLY_RE.search(text)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        return (low + high) / 2.0

    if re.search(r"\b(?:twice|2x|2 times)\s*weekly\b", text) or text == "twice weekly":
        return 2.0
    if re.search(r"\b(?:three times|thrice|3x|3 times)\s*weekly\b", text):
        return 3.0
    if re.search(r"\b(?:four times|4x|4 times)\s*weekly\b", text):
        return 4.0

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


def next_dose_due_at(
    weekly_expected: float | None,
    last_taken_at: datetime | None,
    fallback_at: datetime | None,
) -> datetime | None:
    """When the next dose is due, given an expected weekly dose count.

    Anchors off the most recently logged dose if there is one, otherwise
    off `fallback_at` (typically the protocol's created_at) so a
    never-logged protocol still reports a due date instead of nothing.
    Returns None when frequency couldn't be parsed into a weekly count.
    """
    if weekly_expected is None or weekly_expected <= 0:
        return None
    anchor = last_taken_at or fallback_at
    if anchor is None:
        return None

    interval_days = 7.0 / weekly_expected
    return anchor + timedelta(days=interval_days)


def format_due_label(next_due_at: datetime | None, now: datetime) -> str:
    """Human-readable label for a next_dose_due_at value relative to `now`."""
    if next_due_at is None:
        return "N/A"

    delta_days = (next_due_at - now).total_seconds() / 86400.0
    if delta_days < 0:
        overdue_days = abs(delta_days)
        return "Overdue (today)" if overdue_days < 1 else f"Overdue {overdue_days:.0f}d"

    return "Due today" if delta_days < 1 else f"Due in {delta_days:.0f}d"


def format_vial_duration(doses_per_vial: float, weekly_expected: float | None, freq_text: str = "") -> str:
    """Format an estimated time duration a vial will last based on doses and frequency."""
    if doses_per_vial <= 0:
        return "0 doses"
    if weekly_expected is None or weekly_expected <= 0:
        return f"{doses_per_vial:.1f} doses"

    total_days = doses_per_vial / (weekly_expected / 7.0)
    total_weeks = doses_per_vial / weekly_expected

    if total_days <= 14:
        return f"~{total_days:.1f} days"
    elif total_weeks <= 8:
        return f"~{total_weeks:.1f} wks (~{total_days:.0f} days)"
    else:
        months = total_days / 30.4375
        return f"~{months:.1f} mos ({total_weeks:.1f} wks)"


def syringe_draw_status(units: float, max_capacity: float = 100.0) -> tuple[str, str]:
    """Return a short draw string and safety status for a U-100 syringe draw.

    Returns (draw_label, safety_status).
    e.g. ("80.0 Units", "✓ Normal draw (80.0U / 100U)")
    or ("⚠️ 160.0 Units", "⚠️ Exceeds 100U (requires 2 draws: 100U + 60.0U)")
    """
    if units <= 0:
        return "0.0 Units", "—"
    if units <= max_capacity:
        return f"{units:.1f} Units", f"✓ Normal draw ({units:.1f}U / 100U)"

    draws = int(units // max_capacity)
    remainder = units % max_capacity
    if remainder > 0.05:
        draw_desc = f"{draws}x 100U + 1x {remainder:.1f}U"
    else:
        draw_desc = f"{draws}x 100U"
    return f"⚠️ {units:.1f} Units", f"⚠️ Exceeds 100U ({draw_desc})"


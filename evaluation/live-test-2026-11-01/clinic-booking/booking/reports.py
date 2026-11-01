"""Monthly reporting."""

from .storage import AppointmentStore


def monthly_visit_count(store: AppointmentStore, year: int, month: int) -> int:
    """Number of visits in a month."""
    return len(store.in_month(year, month))

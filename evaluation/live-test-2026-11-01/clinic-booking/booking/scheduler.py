"""Booking rules: opening hours, slot listing, booking and cancellation."""

from datetime import date, datetime, time, timedelta
from typing import List

from .models import DEFAULT_MINUTES, Appointment
from .storage import AppointmentStore

OPENING = time(9, 0)
CLOSING = time(17, 0)
SLOT = timedelta(minutes=DEFAULT_MINUTES)


class BookingError(Exception):
    """Raised when a booking request breaks a booking rule."""


def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """True when two half-open intervals share time; back-to-back intervals do not overlap."""
    return start_a < end_b and start_b < end_a


class Scheduler:
    def __init__(self, store: AppointmentStore) -> None:
        self.store = store

    def _active_on(self, day: date) -> List[Appointment]:
        """Appointments that occupy time on a day; cancelled ones free their slot."""
        return [appointment for appointment in self.store.on_day(day) if appointment.status != "cancelled"]

    def available_slots(self, day: date) -> List[datetime]:
        booked = self._active_on(day)
        slots = []
        current = datetime.combine(day, OPENING)
        closing = datetime.combine(day, CLOSING)
        while current + SLOT <= closing:
            if not any(_overlaps(current, current + SLOT, other.start, other.end) for other in booked):
                slots.append(current)
            current += SLOT
        return slots

    def book(self, patient_name: str, start: datetime, minutes: int = DEFAULT_MINUTES) -> Appointment:
        name = patient_name.strip()
        if not name:
            raise BookingError("patient name is required")
        end = start + timedelta(minutes=minutes)
        if start.time() < OPENING or end.time() > CLOSING or end.date() != start.date():
            raise BookingError("appointment must be within opening hours")
        for existing in self._active_on(start.date()):
            if _overlaps(start, end, existing.start, existing.end):
                raise BookingError("that time overlaps an existing appointment")
        return self.store.add(Appointment(patient_name=name, start=start, minutes=minutes))

    def cancel(self, appointment_id: int) -> None:
        if self.store.get(appointment_id) is None:
            raise BookingError("no such appointment")
        self.store.set_status(appointment_id, "cancelled")

"""Appointment model."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

DEFAULT_MINUTES = 30


@dataclass
class Appointment:
    patient_name: str
    start: datetime
    minutes: int = DEFAULT_MINUTES
    status: str = "booked"
    id: Optional[int] = None

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.minutes)

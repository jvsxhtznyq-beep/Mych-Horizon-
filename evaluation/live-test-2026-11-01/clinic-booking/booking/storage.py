"""SQLite storage for appointments (see docs/decisions/0001-use-sqlite.md)."""

import sqlite3
from datetime import date, datetime
from typing import List, Optional

from .models import Appointment

SCHEMA = """
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    start TEXT NOT NULL,
    minutes INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'booked'
)
"""


def _row_to_appointment(row) -> Appointment:
    return Appointment(id=row[0], patient_name=row[1], start=datetime.fromisoformat(row[2]),
                       minutes=row[3], status=row[4])


class AppointmentStore:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)

    def add(self, appointment: Appointment) -> Appointment:
        cursor = self.conn.execute(
            "INSERT INTO appointments (patient_name, start, minutes, status) VALUES (?, ?, ?, ?)",
            (appointment.patient_name, appointment.start.isoformat(timespec="minutes"),
             appointment.minutes, appointment.status),
        )
        self.conn.commit()
        appointment.id = cursor.lastrowid
        return appointment

    def get(self, appointment_id: int) -> Optional[Appointment]:
        row = self.conn.execute(
            "SELECT id, patient_name, start, minutes, status FROM appointments WHERE id = ?",
            (appointment_id,),
        ).fetchone()
        return _row_to_appointment(row) if row else None

    def on_day(self, day: date) -> List[Appointment]:
        rows = self.conn.execute(
            "SELECT id, patient_name, start, minutes, status FROM appointments "
            "WHERE start LIKE ? ORDER BY start",
            (day.isoformat() + "%",),
        ).fetchall()
        return [_row_to_appointment(row) for row in rows]

    def in_month(self, year: int, month: int) -> List[Appointment]:
        rows = self.conn.execute(
            "SELECT id, patient_name, start, minutes, status FROM appointments "
            "WHERE start LIKE ? ORDER BY start",
            ("{:04d}-{:02d}-%".format(year, month),),
        ).fetchall()
        return [_row_to_appointment(row) for row in rows]

    def set_status(self, appointment_id: int, status: str) -> None:
        self.conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))
        self.conn.commit()

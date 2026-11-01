"""Formatting helpers for confirmations and reminders."""

from datetime import date, datetime


def format_date(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}-{day.day:02d}"


def format_time(moment: datetime) -> str:
    return f"{moment.hour:02d}:{moment.minute:02d}"


def confirmation_message(patient_name: str, start: datetime) -> str:
    return f"{patient_name}, your appointment is on {format_date(start.date())} at {format_time(start)}."

import unittest
from datetime import date, datetime

from booking.formatting import confirmation_message, format_date, format_time


class FormattingTest(unittest.TestCase):
    def test_format_time_pads_hours_and_minutes(self):
        self.assertEqual(format_time(datetime(2026, 11, 2, 9, 5)), "09:05")

    def test_format_date(self):
        self.assertEqual(format_date(date(2026, 11, 12)), "2026-11-12")

    def test_format_date_pads_single_digit_month_and_day(self):
        self.assertEqual(format_date(date(2026, 1, 5)), "2026-01-05")

    def test_confirmation_message(self):
        message = confirmation_message("Ada", datetime(2026, 12, 15, 14, 30))
        self.assertEqual(message, "Ada, your appointment is on 2026-12-15 at 14:30.")


if __name__ == "__main__":
    unittest.main()

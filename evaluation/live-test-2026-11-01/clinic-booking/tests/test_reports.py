import unittest
from datetime import datetime

from booking.reports import monthly_visit_count
from booking.scheduler import Scheduler
from booking.storage import AppointmentStore


class ReportsTest(unittest.TestCase):
    def test_counts_visits_in_month(self):
        store = AppointmentStore()
        scheduler = Scheduler(store)
        scheduler.book("Ada", datetime(2026, 11, 2, 10))
        scheduler.book("Bo", datetime(2026, 11, 3, 10))
        scheduler.book("Cy", datetime(2026, 12, 1, 10))
        self.assertEqual(monthly_visit_count(store, 2026, 11), 2)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date, datetime

from booking.scheduler import BookingError, Scheduler
from booking.storage import AppointmentStore

DAY = date(2026, 11, 2)


def at(hour, minute=0):
    return datetime(2026, 11, 2, hour, minute)


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler(AppointmentStore())

    def test_books_a_free_slot(self):
        appointment = self.scheduler.book("Ada Patient", at(10))
        self.assertIsNotNone(appointment.id)
        self.assertEqual(appointment.end, at(10, 30))

    def test_rejects_times_outside_opening_hours(self):
        with self.assertRaises(BookingError):
            self.scheduler.book("Ada Patient", at(8, 30))
        with self.assertRaises(BookingError):
            self.scheduler.book("Ada Patient", at(16, 45))

    def test_rejects_the_same_start_time_twice(self):
        self.scheduler.book("Ada Patient", at(11))
        with self.assertRaises(BookingError):
            self.scheduler.book("Bo Patient", at(11))

    def test_available_slots_exclude_booked_times(self):
        self.scheduler.book("Ada Patient", at(10))
        slots = self.scheduler.available_slots(DAY)
        self.assertNotIn(at(10), slots)
        self.assertEqual(len(slots), 15)

    def test_cancelling_an_unknown_appointment_fails(self):
        with self.assertRaises(BookingError):
            self.scheduler.cancel(999)

    # Reported 2026-11-01: a patient was booked at 09:15 while 09:00-09:30 was taken.
    def test_rejects_a_booking_that_overlaps_an_existing_one(self):
        self.scheduler.book("Ada Patient", at(9))
        with self.assertRaises(BookingError):
            self.scheduler.book("Bo Patient", at(9, 15))

    def test_long_appointment_hides_the_slots_it_covers(self):
        self.scheduler.book("Ada Patient", at(9), minutes=60)
        slots = self.scheduler.available_slots(DAY)
        self.assertNotIn(at(9, 30), slots)
        self.assertIn(at(10), slots)

    # Reported 2026-11-01: slots freed by cancellations never become bookable again.
    def test_cancelled_slot_is_listed_again(self):
        appointment = self.scheduler.book("Ada Patient", at(10))
        self.scheduler.cancel(appointment.id)
        self.assertIn(at(10), self.scheduler.available_slots(DAY))

    def test_cancelled_slot_can_be_booked_again(self):
        appointment = self.scheduler.book("Ada Patient", at(10))
        self.scheduler.cancel(appointment.id)
        rebooked = self.scheduler.book("Bo Patient", at(10))
        self.assertEqual(rebooked.start, at(10))


if __name__ == "__main__":
    unittest.main()

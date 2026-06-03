"""Tests for date_utils and other utility functions."""
import unittest
from datetime import date, timedelta


class DateUtilsTests(unittest.TestCase):
    def setUp(self):
        from actionhub.utils import date_utils as du
        self.du = du

    # parse_date
    def test_parse_date_iso(self):
        self.assertEqual(self.du.parse_date("2026-01-15"), date(2026, 1, 15))

    def test_parse_date_none(self):
        self.assertIsNone(self.du.parse_date(None))

    def test_parse_date_empty_string(self):
        self.assertIsNone(self.du.parse_date(""))

    def test_parse_date_whitespace(self):
        self.assertIsNone(self.du.parse_date("   "))

    def test_parse_date_datetime_string(self):
        result = self.du.parse_date("2026-03-10T14:30:00")
        self.assertEqual(result, date(2026, 3, 10))

    def test_parse_date_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.du.parse_date("not-a-date")

    # is_overdue
    def test_is_overdue_past(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        self.assertTrue(self.du.is_overdue(past, "Open"))

    def test_is_overdue_future(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        self.assertFalse(self.du.is_overdue(future, "Open"))

    def test_is_overdue_done_status(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        self.assertFalse(self.du.is_overdue(past, "Done"))

    def test_is_overdue_cancelled(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        self.assertFalse(self.du.is_overdue(past, "Cancelled"))

    def test_is_overdue_none_deadline(self):
        self.assertFalse(self.du.is_overdue(None, "Open"))

    # sla_days
    def test_sla_days_critical(self):
        self.assertEqual(self.du.sla_days("Critical"), 3)

    def test_sla_days_high(self):
        self.assertEqual(self.du.sla_days("High"), 7)

    def test_sla_days_medium(self):
        self.assertEqual(self.du.sla_days("Medium"), 14)

    def test_sla_days_low(self):
        self.assertEqual(self.du.sla_days("Low"), 30)

    def test_sla_days_unknown(self):
        self.assertEqual(self.du.sla_days("Unknown"), 14)

    # sla_status
    def test_sla_status_closed_done(self):
        self.assertEqual(self.du.sla_status("2026-01-01", "Medium", "Done"), "Closed")

    def test_sla_status_closed_cancelled(self):
        self.assertEqual(self.du.sla_status("2026-01-01", "High", "Cancelled"), "Closed")

    def test_sla_status_no_deadline(self):
        self.assertEqual(self.du.sla_status(None, "Medium", "Open"), "Unknown")

    def test_sla_status_overdue(self):
        past = (date.today() - timedelta(days=2)).isoformat()
        self.assertEqual(self.du.sla_status(past, "Medium", "Open"), "Overdue")

    def test_sla_status_on_track(self):
        future = (date.today() + timedelta(days=20)).isoformat()
        self.assertEqual(self.du.sla_status(future, "Medium", "Open"), "On Track")

    def test_sla_status_at_risk(self):
        # Medium SLA=14 days — at-risk threshold is max(1, 14//3)=4 days
        soon = (date.today() + timedelta(days=2)).isoformat()
        self.assertEqual(self.du.sla_status(soon, "Medium", "Open"), "At Risk")


if __name__ == "__main__":
    unittest.main()

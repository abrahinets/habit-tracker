"""Тести трекера звичок."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import habits
import storage

TODAY = date(2026, 11, 7)


class CalculateStreakTests(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(habits.calculate_streak([], TODAY), 0)

    def test_one_day(self):
        self.assertEqual(habits.calculate_streak(["2026-11-07"], TODAY), 1)

    def test_several_days_in_a_row(self):
        dates = ["2026-11-05", "2026-11-06", "2026-11-07"]
        self.assertEqual(habits.calculate_streak(dates, TODAY), 3)

    def test_gap_stops_streak(self):
        dates = ["2026-11-03", "2026-11-04", "2026-11-06", "2026-11-07"]
        self.assertEqual(habits.calculate_streak(dates, TODAY), 2)

    def test_today_not_marked_but_yesterday_is(self):
        dates = ["2026-11-05", "2026-11-06"]
        self.assertEqual(habits.calculate_streak(dates, TODAY), 2)

    def test_none_and_garbage_ignored(self):
        dates = [None, "not-a-date", 123, "2026-11-07"]
        self.assertEqual(habits.calculate_streak(dates, TODAY), 1)

    def test_duplicate_dates_counted_once(self):
        dates = ["2026-11-06", "2026-11-06", "2026-11-07", "2026-11-07"]
        self.assertEqual(habits.calculate_streak(dates, TODAY), 2)


class AddHabitTests(unittest.TestCase):
    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            habits.add_habit([], "   ")

    def test_duplicate_name_raises(self):
        habit_list = []
        habits.add_habit(habit_list, "Read book")
        with self.assertRaises(ValueError):
            habits.add_habit(habit_list, "Read book")

    def test_duplicate_ignores_extra_spaces_and_case(self):
        habit_list = []
        habits.add_habit(habit_list, "Read book")
        with self.assertRaises(ValueError):
            habits.add_habit(habit_list, "  read   book  ")


class MarkDoneTests(unittest.TestCase):
    def test_marking_twice_same_day_adds_one_date(self):
        habit = {"id": 1, "name": "Read book", "dates": []}
        self.assertTrue(habits.mark_done(habit, TODAY))
        self.assertFalse(habits.mark_done(habit, TODAY))
        self.assertEqual(habit["dates"], ["2026-11-07"])


class IsDoneTests(unittest.TestCase):
    def test_iso_string(self):
        habit = {"dates": ["2026-11-07"]}
        self.assertTrue(habits.is_done(habit, TODAY))

    def test_date_object(self):
        habit = {"dates": [TODAY]}
        self.assertTrue(habits.is_done(habit, TODAY))

    def test_false_when_not_marked(self):
        habit = {"dates": ["2026-11-06"]}
        self.assertFalse(habits.is_done(habit, TODAY))


class StorageTests(unittest.TestCase):
    def test_save_and_load_roundtrip_in_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "habits.json"
            data = {
                "habits": [
                    {
                        "id": 1,
                        "name": "Читання",
                        "created": "2026-11-07",
                        "dates": ["2026-11-07"],
                    }
                ]
            }
            storage.save(path, data)
            self.assertEqual(storage.load(path), data)

    def test_load_missing_file_returns_empty_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertEqual(storage.load(path), {"habits": []})


if __name__ == "__main__":
    unittest.main()

"""Тести трекера звичок."""

import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

import db
import habits

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


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.conn = db.connect(Path(self._tmp.name) / "test.db")
        self.addCleanup(self.conn.close)


class AddHabitTests(DatabaseTestCase):
    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            db.add_habit(self.conn, "   ")

    def test_duplicate_name_raises(self):
        db.add_habit(self.conn, "Read book")
        with self.assertRaises(ValueError):
            db.add_habit(self.conn, "Read book")

    def test_duplicate_ignores_extra_spaces_and_case(self):
        db.add_habit(self.conn, "Read book")
        with self.assertRaises(ValueError):
            db.add_habit(self.conn, "  read   book  ")


class MarkDoneTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.habit = db.add_habit(self.conn, "Read book")

    def test_marking_twice_same_day_adds_one_date(self):
        self.assertTrue(db.mark_day(self.conn, self.habit["id"], TODAY))
        self.assertFalse(db.mark_day(self.conn, self.habit["id"], TODAY))
        self.assertEqual(db.get_history(self.conn, self.habit["id"]), ["2026-11-07"])

    def test_datetime_string_does_not_create_duplicate(self):
        self.conn.execute(
            "INSERT INTO checkins (habit_id, date) VALUES (?, ?)",
            (self.habit["id"], "2026-11-07T00:00:00"),
        )
        self.conn.commit()
        self.assertFalse(db.mark_day(self.conn, self.habit["id"], TODAY))
        self.assertEqual(
            db.get_history(self.conn, self.habit["id"]),
            ["2026-11-07T00:00:00"],
        )


class UniqueCheckinTests(DatabaseTestCase):
    def test_duplicate_habit_and_date_rejected(self):
        habit = db.add_habit(self.conn, "Спорт")
        self.conn.execute(
            "INSERT INTO checkins (habit_id, date) VALUES (?, ?)",
            (habit["id"], "2026-11-07"),
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO checkins (habit_id, date) VALUES (?, ?)",
                (habit["id"], "2026-11-07"),
            )
        self.conn.rollback()


class IsDoneTests(DatabaseTestCase):
    def test_iso_string(self):
        habit = db.add_habit(self.conn, "Читання")
        self.conn.execute(
            "INSERT INTO checkins (habit_id, date) VALUES (?, ?)",
            (habit["id"], "2026-11-07"),
        )
        self.conn.commit()
        self.assertTrue(db.is_done(self.conn, habit["id"], TODAY))

    def test_date_object(self):
        habit = db.add_habit(self.conn, "Читання")
        self.assertTrue(db.mark_day(self.conn, habit["id"], TODAY))
        self.assertTrue(db.is_done(self.conn, habit["id"], TODAY))

    def test_false_when_not_marked(self):
        habit = db.add_habit(self.conn, "Читання")
        self.conn.execute(
            "INSERT INTO checkins (habit_id, date) VALUES (?, ?)",
            (habit["id"], "2026-11-06"),
        )
        self.conn.commit()
        self.assertFalse(db.is_done(self.conn, habit["id"], TODAY))


class DeleteHabitTests(DatabaseTestCase):
    def test_delete_existing_id(self):
        first = db.add_habit(self.conn, "Читання")
        second = db.add_habit(self.conn, "Спорт")
        removed = db.delete_habit(self.conn, second["id"])
        self.assertEqual(removed["name"], "Спорт")
        self.assertEqual([habit["id"] for habit in db.list_habits(self.conn)], [first["id"]])

    def test_delete_missing_id(self):
        db.add_habit(self.conn, "Читання")
        self.assertIsNone(db.delete_habit(self.conn, 99))
        self.assertEqual(len(db.list_habits(self.conn)), 1)

    def test_delete_cascades_checkins(self):
        habit = db.add_habit(self.conn, "Читання")
        self.assertTrue(db.mark_day(self.conn, habit["id"], TODAY))
        self.assertTrue(db.mark_day(self.conn, habit["id"], date(2026, 11, 6)))
        db.delete_habit(self.conn, habit["id"])
        count = self.conn.execute("SELECT COUNT(*) FROM checkins").fetchone()[0]
        self.assertEqual(count, 0)


class DatabaseTests(DatabaseTestCase):
    def test_schema_tables_created(self):
        names = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertIn("habits", names)
        self.assertIn("checkins", names)

    def test_created_at_filled(self):
        habit = db.add_habit(self.conn, "Читання")
        self.assertEqual(date.fromisoformat(habit["created_at"]), date.today())

    def test_foreign_keys_enabled(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO checkins (habit_id, date) VALUES (?, ?)",
                (999, "2026-11-07"),
            )
        self.conn.rollback()


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)
        self.db_path = self.directory / "habits.db"

    def write_legacy(self, data):
        (self.directory / "habits.json").write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_imports_legacy_json(self):
        self.write_legacy(
            {
                "habits": [
                    {
                        "id": 1,
                        "name": "Читання",
                        "created": "2026-11-01",
                        "dates": ["2026-11-06", "2026-11-07", None, "garbage"],
                    }
                ]
            }
        )

        conn = db.connect(self.db_path)
        self.addCleanup(conn.close)

        habit_list = db.list_habits(conn)
        self.assertEqual(len(habit_list), 1)
        self.assertEqual(habit_list[0]["created_at"], "2026-11-01")
        self.assertEqual(
            db.get_history(conn, habit_list[0]["id"]),
            ["2026-11-06", "2026-11-07"],
        )
        self.assertEqual(
            habits.calculate_streak(db.get_history(conn, habit_list[0]["id"]), TODAY),
            2,
        )

    def test_does_not_reimport_when_database_not_empty(self):
        self.write_legacy(
            {"habits": [{"id": 1, "name": "Читання", "created": "2026-11-01", "dates": []}]}
        )

        first = db.connect(self.db_path)
        first.close()

        second = db.connect(self.db_path)
        self.addCleanup(second.close)
        self.assertEqual(len(db.list_habits(second)), 1)


if __name__ == "__main__":
    unittest.main()

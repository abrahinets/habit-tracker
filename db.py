"""Робота з SQLite-базою трекера звичок."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().with_name("habits.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS checkins (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL
             REFERENCES habits(id) ON DELETE CASCADE,
    date     TEXT NOT NULL,
    UNIQUE (habit_id, date)
);
"""


def as_date(value):
    """Перетворює None/date/datetime/ISO-рядок у datetime.date."""
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def parse_stored_date(value):
    """Перетворює збережене значення у date; None і некоректні — у None."""
    if value is None:
        return None
    try:
        return as_date(value)
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
    return None


def name_key(name):
    """Ключ для порівняння назв: без зайвих пробілів і без урахування регістру."""
    return " ".join(name.split()).casefold()


def create_tables(conn):
    """Створює таблиці, якщо їх ще немає."""
    conn.executescript(SCHEMA)
    conn.commit()


def connect(path=DEFAULT_PATH, *, migrate=True):
    """Відкриває базу, вмикає зовнішні ключі й створює схему."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)

    if migrate:
        migrate_json(conn, path.with_name("habits.json"))
    return conn


def migrate_json(conn, path):
    """Імпортує старий habits.json, якщо база порожня. Повертає кількість звичок."""
    path = Path(path)
    if not path.exists():
        return 0
    if conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0]:
        return 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Файл {path} містить некоректний JSON: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("habits", []), list):
        raise ValueError(f"Файл {path} має неочікувану структуру")

    imported = 0
    for habit in data.get("habits", []):
        if not isinstance(habit, dict):
            continue

        name = str(habit.get("name", "")).strip()
        if not name:
            continue

        created = parse_stored_date(habit.get("created")) or date.today()
        habit_id = habit.get("id")
        if isinstance(habit_id, int):
            cursor = conn.execute(
                "INSERT INTO habits (id, name, created_at) VALUES (?, ?, ?)",
                (habit_id, name, created.isoformat()),
            )
        else:
            cursor = conn.execute(
                "INSERT INTO habits (name, created_at) VALUES (?, ?)",
                (name, created.isoformat()),
            )

        new_id = cursor.lastrowid
        for value in habit.get("dates", []) or []:
            day = parse_stored_date(value)
            if day is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO checkins (habit_id, date) VALUES (?, ?)",
                    (new_id, day.isoformat()),
                )
        imported += 1

    conn.commit()
    return imported


def list_habits(conn):
    """Повертає всі звички за зростанням id."""
    rows = conn.execute("SELECT id, name, created_at FROM habits ORDER BY id")
    return [dict(row) for row in rows]


def get_habit(conn, habit_id):
    """Повертає звичку за id або None."""
    row = conn.execute(
        "SELECT id, name, created_at FROM habits WHERE id = ?",
        (habit_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def add_habit(conn, name):
    """Додає звичку і повертає її.

    Назва обрізається від пробілів; порожня назва або дублікат
    (без урахування регістру) піднімають ValueError.
    """
    name = name.strip()
    if not name:
        raise ValueError("Назва звички не може бути порожньою")

    key = name_key(name)
    for row in conn.execute("SELECT name FROM habits"):
        if name_key(row["name"]) == key:
            raise ValueError(f"Звичка «{name}» вже існує")

    cursor = conn.execute(
        "INSERT INTO habits (name, created_at) VALUES (?, ?)",
        (name, date.today().isoformat()),
    )
    conn.commit()
    return get_habit(conn, cursor.lastrowid)


def get_history(conn, habit_id):
    """Повертає відмічені дні звички у форматі YYYY-MM-DD за зростанням."""
    rows = conn.execute(
        "SELECT date FROM checkins WHERE habit_id = ? ORDER BY date",
        (habit_id,),
    )
    return [row["date"] for row in rows]


def is_done(conn, habit_id, day=None):
    """Чи відмічено виконання звички за вказаний день (типово — сьогодні)."""
    target = as_date(day)
    rows = conn.execute(
        "SELECT date FROM checkins WHERE habit_id = ?",
        (habit_id,),
    )
    return any(parse_stored_date(row["date"]) == target for row in rows)


def mark_day(conn, habit_id, day=None):
    """Відмічає виконання за день (типово — сьогодні).

    Повертає True, якщо відмітку додано, і False, якщо вона вже була.
    """
    target = as_date(day)
    if is_done(conn, habit_id, target):
        return False

    cursor = conn.execute(
        "INSERT OR IGNORE INTO checkins (habit_id, date) VALUES (?, ?)",
        (habit_id, target.isoformat()),
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_habit(conn, habit_id):
    """Видаляє звичку разом з її відмітками. Повертає звичку або None."""
    habit = get_habit(conn, habit_id)
    if habit is None:
        return None

    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    return habit

"""Консольний трекер звичок: add, done, list, delete."""

import argparse
import sqlite3
import sys

import db
import habits


def build_parser():
    """Створює парсер підкоманд."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Консольний трекер звичок.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="додати звичку")
    add_parser.add_argument("name", help="назва звички")

    done_parser = subparsers.add_parser("done", help="відмітити виконання за сьогодні")
    done_parser.add_argument("id", type=int, help="ID звички")

    subparsers.add_parser("list", help="показати звички та серії")

    delete_parser = subparsers.add_parser("delete", help="видалити звичку")
    delete_parser.add_argument("id", type=int, help="ID звички")
    delete_parser.add_argument(
        "--yes",
        action="store_true",
        help="видалити без підтвердження",
    )

    return parser


def cmd_add(conn, name):
    """Додає звичку і зберігає її у базі."""
    habit = db.add_habit(conn, name)
    print(f"Додано: {habit['id']}. {habit['name']}")


def cmd_done(conn, habit_id):
    """Відмічає звичку за сьогодні. Повертає код виходу."""
    habit = db.get_habit(conn, habit_id)
    if habit is None:
        print(f"Звичку з id={habit_id} не знайдено.", file=sys.stderr)
        return 1

    if db.mark_day(conn, habit_id):
        print(f"Відмічено: {habit['name']}")
    else:
        print(f"Вже відмічено сьогодні: {habit['name']}")
    return 0


def cmd_list(conn):
    """Друкує список звичок із серіями."""
    records = db.list_habits(conn)
    if not records:
        print('Звичок ще немає. Додай першу: python main.py add "Назва"')
        return

    for habit in records:
        streak = habits.calculate_streak(db.get_history(conn, habit["id"]))
        mark = "[x]" if db.is_done(conn, habit["id"]) else "[ ]"
        print(f"{habit['id']}. {mark} {habit['name']} — серія: {streak} дн.")


def cmd_delete(conn, habit_id, assume_yes=False):
    """Видаляє звичку, питаючи підтвердження. Повертає код виходу."""
    habit = db.get_habit(conn, habit_id)
    if habit is None:
        print(f"Звичку з id={habit_id} не знайдено.", file=sys.stderr)
        return 1

    if not assume_yes:
        try:
            answer = input(f"Видалити «{habit['name']}»? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().casefold() not in ("y", "yes"):
            print("Скасовано.")
            return 0

    db.delete_habit(conn, habit_id)
    print(f"Видалено: {habit['name']}")
    return 0


def main(argv=None):
    """Точка входу CLI. Повертає код виходу."""
    args = build_parser().parse_args(argv)

    conn = None
    try:
        conn = db.connect()
        if args.command == "add":
            cmd_add(conn, args.name)
        elif args.command == "done":
            return cmd_done(conn, args.id)
        elif args.command == "list":
            cmd_list(conn)
        elif args.command == "delete":
            return cmd_delete(conn, args.id, args.yes)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Помилка: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

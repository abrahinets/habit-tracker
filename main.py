"""Консольний трекер звичок: add, done, list, delete."""

import argparse
import sys

import habits
import storage


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


def cmd_add(path, name):
    """Додає звичку і зберігає дані."""
    data = storage.load(path)
    habit = habits.add_habit(data["habits"], name)
    storage.save(path, data)
    print(f"Додано: {habit['id']}. {habit['name']}")


def cmd_done(path, habit_id):
    """Відмічає звичку за сьогодні. Повертає код виходу."""
    data = storage.load(path)
    habit = habits.find_habit(data["habits"], habit_id)
    if habit is None:
        print(f"Звичку з id={habit_id} не знайдено.", file=sys.stderr)
        return 1

    if habits.mark_done(habit):
        storage.save(path, data)
        print(f"Відмічено: {habit['name']}")
    else:
        print(f"Вже відмічено сьогодні: {habit['name']}")
    return 0


def cmd_list(path):
    """Друкує список звичок із серіями."""
    data = storage.load(path)
    if not data["habits"]:
        print('Звичок ще немає. Додай першу: python main.py add "Назва"')
        return

    for habit in data["habits"]:
        streak = habits.calculate_streak(habit.get("dates", []))
        mark = "[x]" if habits.is_done(habit) else "[ ]"
        print(f"{habit['id']}. {mark} {habit['name']} — серія: {streak} дн.")


def cmd_delete(path, habit_id, assume_yes=False):
    """Видаляє звичку, питаючи підтвердження. Повертає код виходу."""
    data = storage.load(path)
    habit = habits.delete_habit(data["habits"], habit_id)
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

    storage.save(path, data)
    print(f"Видалено: {habit['name']}")
    return 0


def main(argv=None):
    """Точка входу CLI. Повертає код виходу."""
    args = build_parser().parse_args(argv)

    try:
        if args.command == "add":
            cmd_add(storage.DEFAULT_PATH, args.name)
        elif args.command == "done":
            return cmd_done(storage.DEFAULT_PATH, args.id)
        elif args.command == "list":
            cmd_list(storage.DEFAULT_PATH)
        elif args.command == "delete":
            return cmd_delete(storage.DEFAULT_PATH, args.id, args.yes)
    except (OSError, ValueError) as exc:
        print(f"Помилка: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

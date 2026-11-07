"""Логіка трекера звичок: додавання, відмітки виконання, серії днів."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _as_date(value):
    """Перетворює None/date/datetime/ISO-рядок у datetime.date."""
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _parse_stored_date(value):
    """Перетворює збережене значення у date; None і некоректні — у None."""
    if value is None:
        return None
    try:
        return _as_date(value)
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
    return None


def _name_key(name):
    """Ключ для порівняння назв: без зайвих пробілів і без урахування регістру."""
    return " ".join(name.split()).casefold()


def next_id(habits):
    """Повертає наступний вільний id для нової звички."""
    return max((habit.get("id", 0) for habit in habits), default=0) + 1


def add_habit(habits, name):
    """Додає звичку у список і повертає її.

    Назва обрізається від пробілів; порожня назва або дублікат
    (без урахування регістру) піднімають ValueError.
    """
    name = name.strip()
    if not name:
        raise ValueError("Назва звички не може бути порожньою")

    if any(_name_key(habit.get("name", "")) == _name_key(name) for habit in habits):
        raise ValueError(f"Звичка «{name}» вже існує")

    habit = {
        "id": next_id(habits),
        "name": name,
        "created": date.today().isoformat(),
        "dates": [],
    }
    habits.append(habit)
    return habit


def find_habit(habits, habit_id):
    """Знаходить звичку за id або повертає None."""
    for habit in habits:
        if habit.get("id") == habit_id:
            return habit
    return None


def delete_habit(habits, habit_id):
    """Видаляє звичку за id і повертає її або None, якщо id не знайдено."""
    habit = find_habit(habits, habit_id)
    if habit is None:
        return None

    habits.remove(habit)
    return habit


def is_done(habit, day=None):
    """Чи відмічено виконання звички за вказаний день (типово — сьогодні).

    Збережені дати нормалізуються так само, як у calculate_streak:
    None і некоректні значення ігноруються.
    """
    day = _as_date(day)
    return any(_parse_stored_date(value) == day for value in habit.get("dates", []))


def mark_done(habit, day=None):
    """Відмічає виконання за день (типово — сьогодні).

    Повертає True, якщо відмітку додано, і False, якщо вона вже була.
    Повторний виклик за той самий день дубліката не створює. Збережені дати
    нормалізуються так само, як у is_done: ISO-рядки, date-об'єкти й
    datetime-рядки розпізнаються, а некоректні значення лишаються на місці.
    """
    day = _as_date(day)
    dates = habit.setdefault("dates", [])
    if any(_parse_stored_date(value) == day for value in dates):
        return False

    dates.append(day.isoformat())
    positions = [
        index
        for index, value in enumerate(dates)
        if _parse_stored_date(value) is not None
    ]
    valid = sorted((dates[index] for index in positions), key=_parse_stored_date)
    for index, value in zip(positions, valid):
        dates[index] = value
    return True


def calculate_streak(dates, today=None):
    """Рахує серію днів поспіль.

    Серія тягнеться назад від сьогодні, якщо сьогодні вже відмічено, або від
    вчора, якщо сьогодні ще ні (щоб поточна серія не обнулялась зранку).
    Якщо немає ні сьогоднішньої, ні вчорашньої відмітки — серія 0.
    None і некоректні дати у списку ігноруються.
    """
    today = _as_date(today)

    days = set()
    for value in dates:
        parsed = _parse_stored_date(value)
        if parsed is not None:
            days.add(parsed)

    if today in days:
        anchor = today
    elif today - timedelta(days=1) in days:
        anchor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    current = anchor
    while current in days:
        streak += 1
        current -= timedelta(days=1)
    return streak

"""Логіка трекера звичок: серії днів поспіль."""

from datetime import timedelta

import db


def calculate_streak(dates, today=None):
    """Рахує серію днів поспіль.

    Серія тягнеться назад від сьогодні, якщо сьогодні вже відмічено, або від
    вчора, якщо сьогодні ще ні (щоб поточна серія не обнулялась зранку).
    Якщо немає ні сьогоднішньої, ні вчорашньої відмітки — серія 0.
    None і некоректні дати у списку ігноруються.
    """
    today = db.as_date(today)

    days = set()
    for value in dates:
        parsed = db.parse_stored_date(value)
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

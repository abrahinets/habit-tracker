"""Збереження даних трекера звичок у JSON-файлі."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().with_name("habits.json")


def load(path=DEFAULT_PATH):
    """Читає дані з JSON-файлу.

    Якщо файлу ще немає, повертає порожню структуру. Якщо JSON некоректний
    або структура неочікувана, піднімає ValueError з зрозумілим повідомленням.
    """
    path = Path(path)
    if not path.exists():
        return {"habits": []}

    with path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Файл {path} містить некоректний JSON: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("habits", []), list):
        raise ValueError(f"Файл {path} має неочікувану структуру")

    data.setdefault("habits", [])
    return data


def save(path, data):
    """Атомарно записує дані у JSON-файл.

    Спочатку пише у тимчасовий файл у тій самій теці, а потім підміняє
    основний через os.replace — так дані не пошкодяться при збої посередині.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

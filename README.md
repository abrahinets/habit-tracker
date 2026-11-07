# Habit Tracker

Консольний трекер звичок на Python без зовнішніх залежностей. Звички та дати
виконання зберігаються у базі `habits.db` (SQLite), для кожної звички
показується серія днів поспіль.

## Запуск

Додати звичку:

```console
python main.py add "Читання"
```

Відмітити виконання за сьогодні (ID видно у `list`):

```console
python main.py done 1
```

Видалити звичку (запитає підтвердження, типова відповідь — `N`):

```console
python main.py delete 2
```

Пропустити підтвердження можна прапорцем `--yes`:

```console
python main.py delete 2 --yes
```

Показати звички та серії:

```console
python main.py list
```

Приклад виводу:

```text
1. [x] Читання — серія: 3 дн.
2. [ ] Спорт — серія: 0 дн.
```

`[x]` — сьогодні вже відмічено, `[ ]` — ще ні. Повторний `done` за той самий
день дубліката не створює.

## Тести

```console
python -m unittest
```

Тести працюють з тимчасовою базою SQLite і не торкаються реального
`habits.db`.

## База даних

`habits.db` (SQLite) створюється автоматично при першому запуску:

```sql
CREATE TABLE habits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE checkins (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date     TEXT NOT NULL,
    UNIQUE (habit_id, date)
);
```

- `habits` — звички: назва й дата створення (`YYYY-MM-DD`);
- `checkins` — відмітки виконання; пара `habit_id` + `date` унікальна, тому
  один день не можна відмітити двічі;
- `ON DELETE CASCADE` прибирає відмітки разом зі звичкою.

Якщо поруч лежить старий `habits.json`, а база порожня, дані імпортуються
один раз, після чого файл перейменовується у `habits.json.migrated` і більше
не читається.

`habits.db` доданий у `.gitignore`, бо це локальні дані.

## Правило серії

Серія рахується назад від сьогодні, якщо сьогодні вже відмічено. Якщо
сьогодні ще не відмічено, відлік іде від учора — щоб поточна серія не
обнулялася зранку. Якщо немає ні сьогоднішньої, ні вчорашньої відмітки,
серія дорівнює 0.

## Навчання

Проєкт створено разом з AI-агентом під час проходження курсу Claude Code 101.
Практикували:

- plan mode — спочатку план файлів і кроків, потім реалізація;
- робочий цикл explore → plan → code → commit;
- рев'ю результатів агента (знаходили й виправляли граничні випадки);
- тести як критерій готовності: `python -m unittest` має проходити;
- `AGENTS.md` — аналог `CLAUDE.md` для цього середовища.

### Друга частина курсу

Далі практикували:

- skills — власний `commit-style` у `.opencode/skills/` задає стиль комітів;
- MCP — Context7 у `opencode.json` дає агенту актуальну документацію бібліотек;
- hooks — плагін `guard.js` блокує `rm -rf` і `git push --force`;
- context management — `/compact` стискає історію, субагенти ізолюють дослідження.

